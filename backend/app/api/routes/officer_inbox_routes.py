"""
Officer Message Box & Approval Hub Routes.
Consolidates all inbound approval requests, data corrections, inquiries,
and communications from Coordinator, Student, and Recruiter dashboards.
"""

from __future__ import annotations

import datetime
import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.app.api.auth.dependencies import require_officer
from backend.app.api.logging.audit_service import AuditService
from backend.app.storage.database import get_db
from backend.app.storage.models.entities import (
    CoordinatorRequestModel,
    DriveModel,
    EligibilityDecisionModel,
    NotificationModel,
    OfferModel,
    PendingResultModel,
    PlacementRequestModel,
    StudentModel,
    UserModel,
)

router = APIRouter(prefix="/api/officer/inbox", tags=["Officer Message Box & Approvals"])


class ApproveRequestPayload(BaseModel):
    item_id: str
    source_type: str = "coordinator_request"  # coordinator_request, pending_result, placement_request
    response_note: str = Field(default="Approved by Placement Officer.")


class RejectRequestPayload(BaseModel):
    item_id: str
    source_type: str = "coordinator_request"
    reason: str = Field(..., min_length=2, description="Mandatory justification for rejection.")


class AddCommentPayload(BaseModel):
    item_id: str
    source_type: str = "coordinator_request"
    text: str = Field(..., min_length=1)


class OfficerSendMessagePayload(BaseModel):
    recipient_role: str = "all"  # "all", "students", "coordinators", "recruiters", "individual"
    recipient_username: str | None = None  # roll_no for individual
    title: str = Field(..., min_length=2)
    message: str = Field(..., min_length=2)
    category: str = "announcement"  # "announcement", "urgent_alert", "direct_message"
    drive_id: str | None = None


@router.get("/summary")
def get_inbox_summary(
    current_user: UserModel = Depends(require_officer),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Returns counts of pending approvals and messages across all dashboards."""
    coord_reqs = db.execute(select(CoordinatorRequestModel)).scalars().all()
    pending_results = db.execute(select(PendingResultModel)).scalars().all()
    placement_reqs = db.execute(select(PlacementRequestModel)).scalars().all()

    # Count pending coordinator requests by type
    coord_pending = 0
    student_corr_pending = 0
    recruiter_inq_pending = 0

    for r in coord_reqs:
        is_pending = r.status.lower() in ("open", "pending")
        if is_pending:
            if r.request_type == "student_data_correction":
                student_corr_pending += 1
            elif r.request_type == "recruiter_inquiry":
                recruiter_inq_pending += 1
            else:
                coord_pending += 1

    # Count pending drive results
    results_pending = sum(1 for r in pending_results if r.status.lower() == "pending")

    # Count placement requests
    placement_pending = sum(1 for r in placement_reqs if r.status.lower() == "pending")

    total_pending = coord_pending + student_corr_pending + recruiter_inq_pending + results_pending + placement_pending

    return {
        "total_pending": total_pending,
        "coordinator_requests_pending": coord_pending,
        "pending_results_pending": results_pending,
        "student_corrections_pending": student_corr_pending,
        "recruiter_inquiries_pending": recruiter_inq_pending,
        "placement_requests_pending": placement_pending,
        "total_items": len(coord_reqs) + len(pending_results) + len(placement_reqs),
    }


@router.get("/items")
def get_inbox_items(
    filter_tab: str = Query("all", description="all, pending, coordinator, results, students, recruiters"),
    status_filter: str = Query("all", description="all, pending, approved, rejected, answered"),
    search: str | None = Query(None),
    limit: int = 150,
    current_user: UserModel = Depends(require_officer),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    Returns a unified feed of approval requests, results entries, student corrections,
    and recruiter inquiries from all dashboards.
    """
    students_map = {s.id: s for s in db.execute(select(StudentModel)).scalars().all()}
    students_by_roll = {s.roll_no: s for s in students_map.values()}
    drives_map = {d.id: d for d in db.execute(select(DriveModel)).scalars().all()}

    unified_items: list[dict[str, Any]] = []

    # 1. CoordinatorRequestModel (Coordinators, Student corrections, Recruiter inquiries)
    req_stmt = select(CoordinatorRequestModel).order_by(desc(CoordinatorRequestModel.submitted_at))
    all_coord_reqs = db.execute(req_stmt).scalars().all()

    for r in all_coord_reqs:
        st_lower = (r.status or "open").lower()
        is_pending = st_lower in ("open", "pending")

        # Determine source dashboard & role
        if r.request_type == "student_data_correction":
            source_dashboard = "Student Portal"
            source_role = "student"
        elif r.request_type == "recruiter_inquiry":
            source_dashboard = "Recruiter Portal"
            source_role = "recruiter"
        else:
            source_dashboard = "Coordinator Dashboard"
            source_role = "coordinator"

        # Resolve target name
        target_name = None
        if r.target_id:
            if r.target_id in students_map:
                target_name = f"{students_map[r.target_id].name} ({students_map[r.target_id].roll_no})"
            elif r.target_id in students_by_roll:
                target_name = f"{students_by_roll[r.target_id].name} ({r.target_id})"
            elif r.target_id in drives_map:
                target_name = drives_map[r.target_id].company_name

        if not target_name and r.submitted_by in students_by_roll:
            target_name = f"{students_by_roll[r.submitted_by].name} ({r.submitted_by})"

        payload = {}
        if r.payload_json:
            try:
                payload = json.loads(r.payload_json)
            except Exception:
                payload = {}

        comments = []
        if r.comments_json:
            try:
                comments = json.loads(r.comments_json)
            except Exception:
                comments = []

        unified_items.append({
            "id": r.id,
            "source_type": "coordinator_request",
            "request_type": r.request_type,
            "source_dashboard": source_dashboard,
            "source_role": source_role,
            "sender_name": r.submitted_by,
            "title": r.title,
            "description": r.description,
            "status": "pending" if is_pending else st_lower,
            "is_pending": is_pending,
            "target_id": r.target_id,
            "target_name": target_name,
            "payload": payload,
            "officer_response": r.officer_response,
            "officer_name": r.officer_name,
            "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
            "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
            "comments": comments,
        })

    # 2. PendingResultModel (On-The-Day Results from Coordinator)
    res_stmt = select(PendingResultModel).order_by(desc(PendingResultModel.submitted_at))
    all_pending_results = db.execute(res_stmt).scalars().all()

    for pr in all_pending_results:
        st_lower = (pr.status or "pending").lower()
        is_pending = st_lower == "pending"

        stu = students_map.get(pr.student_id) or students_by_roll.get(pr.student_id)
        drv = drives_map.get(pr.drive_id)

        stu_display = f"{stu.name} ({stu.roll_no})" if stu else (pr.student_id or "Unknown Candidate")
        drv_display = drv.company_name if drv else (pr.drive_id or "Company Drive")

        unified_items.append({
            "id": pr.id,
            "source_type": "pending_result",
            "request_type": "drive_result_entry",
            "source_dashboard": "Coordinator Dashboard",
            "source_role": "coordinator",
            "sender_name": pr.submitted_by,
            "title": f"Result Entry: {pr.event_type.upper()} — {stu_display}",
            "description": f"{pr.submitted_by} recorded candidate outcome '{pr.event_type}' for {drv_display} at {pr.ctc_lpa} LPA. Reason: {pr.reason}",
            "status": "pending" if is_pending else st_lower,
            "is_pending": is_pending,
            "target_id": pr.student_id,
            "target_name": f"{drv_display} • {stu_display}",
            "payload": {
                "drive_id": pr.drive_id,
                "company_name": drv_display,
                "student_id": pr.student_id,
                "student_name": stu.name if stu else "",
                "roll_no": stu.roll_no if stu else "",
                "event_type": pr.event_type,
                "ctc_lpa": pr.ctc_lpa,
                "fixed_pay_lpa": pr.fixed_pay_lpa,
                "is_dream": pr.is_dream,
                "reason": pr.reason,
            },
            "officer_response": pr.resolution_notes,
            "officer_name": pr.officer_name,
            "submitted_at": pr.submitted_at.isoformat() if pr.submitted_at else None,
            "resolved_at": pr.resolved_at.isoformat() if pr.resolved_at else None,
            "comments": [],
        })

    # 3. PlacementRequestModel (Generic role submissions)
    plc_stmt = select(PlacementRequestModel).order_by(desc(PlacementRequestModel.created_at))
    all_plc = db.execute(plc_stmt).scalars().all()

    for pl in all_plc:
        st_lower = (pl.status or "PENDING").lower()
        is_pending = st_lower == "pending"

        details = {}
        if pl.details_json:
            try:
                details = json.loads(pl.details_json)
            except Exception:
                details = {}

        dashboard_name = (
            "Coordinator Dashboard" if pl.requester_role == "coordinator"
            else "Student Portal" if pl.requester_role == "student"
            else "Recruiter Portal" if "recruiter" in pl.requester_role
            else "Institutional User"
        )

        unified_items.append({
            "id": pl.id,
            "source_type": "placement_request",
            "request_type": pl.request_type,
            "source_dashboard": dashboard_name,
            "source_role": pl.requester_role,
            "sender_name": pl.requester_name,
            "title": pl.subject,
            "description": f"Request from {pl.requester_name}: {json.dumps(details)}",
            "status": "pending" if is_pending else st_lower,
            "is_pending": is_pending,
            "target_id": pl.student_id or pl.drive_id,
            "target_name": pl.student_id or pl.drive_id,
            "payload": details,
            "officer_response": pl.officer_reply,
            "officer_name": "Placement Officer" if not is_pending else None,
            "submitted_at": pl.created_at.isoformat() if pl.created_at else None,
            "resolved_at": pl.updated_at.isoformat() if pl.updated_at and not is_pending else None,
            "comments": [],
        })

    # Sort all items newest first
    unified_items.sort(
        key=lambda x: x["submitted_at"] or "",
        reverse=True,
    )

    # Filter by filter_tab
    filtered = unified_items
    if filter_tab == "pending":
        filtered = [item for item in filtered if item["is_pending"]]
    elif filter_tab == "coordinator":
        filtered = [item for item in filtered if item["source_role"] == "coordinator" and item["source_type"] != "pending_result"]
    elif filter_tab == "results":
        filtered = [item for item in filtered if item["source_type"] == "pending_result"]
    elif filter_tab == "students":
        filtered = [item for item in filtered if item["source_role"] == "student" or item["request_type"] == "student_data_correction"]
    elif filter_tab == "recruiters":
        filtered = [item for item in filtered if item["source_role"] == "recruiter" or item["request_type"] == "recruiter_inquiry"]

    # Filter by status_filter
    if status_filter != "all":
        if status_filter == "pending":
            filtered = [item for item in filtered if item["is_pending"]]
        else:
            filtered = [item for item in filtered if item["status"] == status_filter.lower()]

    # Filter by search string
    if search and search.strip():
        q = search.strip().lower()
        filtered = [
            item for item in filtered
            if q in item["title"].lower()
            or q in item["description"].lower()
            or q in item["sender_name"].lower()
            or (item["target_name"] and q in item["target_name"].lower())
            or (item["target_id"] and q in item["target_id"].lower())
            or q in item["source_dashboard"].lower()
        ]

    return filtered[:limit]


@router.post("/approve")
def approve_inbox_item(
    payload: ApproveRequestPayload,
    current_user: UserModel = Depends(require_officer),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Approves an inbound request or result entry.
    Executes real database state changes (Student marks/backlogs update, Offer commit, Shortlist change)
    with institutional audit trail.
    """
    note = payload.response_note.strip() or "Approved by Placement Officer."

    if payload.source_type == "pending_result":
        # 1. Approve Pending Result
        res = db.execute(
            select(PendingResultModel).where(PendingResultModel.id == payload.item_id)
        ).scalar_one_or_none()

        if not res:
            raise HTTPException(status_code=404, detail="Pending result record not found.")

        res.status = "approved"
        res.officer_name = current_user.username
        res.resolved_at = datetime.datetime.utcnow()
        res.resolution_notes = note

        # Commit official offer
        drv = db.execute(select(DriveModel).where(DriveModel.id == res.drive_id)).scalar_one_or_none()
        company_name = drv.company_name if drv else "Recruitment Partner"

        new_offer = OfferModel(
            id=f"off_{uuid.uuid4().hex[:12]}",
            student_id=res.student_id,
            company=company_name,
            ctc_lpa=res.ctc_lpa or 0.0,
            fixed_pay_lpa=res.fixed_pay_lpa,
            offer_date=datetime.date.today(),
            source="on_campus",
            is_dream=res.is_dream or False,
            status="offered" if res.event_type in ["offered", "shortlisted", "selected"] else res.event_type,
        )
        db.add(new_offer)

        # Increment student version
        stu = db.execute(
            select(StudentModel).where((StudentModel.id == res.student_id) | (StudentModel.roll_no == res.student_id))
        ).scalar_one_or_none()
        if stu:
            stu.version += 1

        db.commit()

        AuditService.record_action(
            db=db,
            actor=current_user.username,
            action="OFFICER_INBOX_RESULT_APPROVED",
            aggregate_type="PENDING_RESULT",
            aggregate_id=res.id,
            payload={"notes": note, "company": company_name, "student_id": res.student_id},
        )

        return {
            "status": "success",
            "message": f"Result entry for {company_name} approved and committed to student record.",
            "item_id": payload.item_id,
        }

    elif payload.source_type == "placement_request":
        # 2. Approve PlacementRequestModel
        pl = db.execute(
            select(PlacementRequestModel).where(PlacementRequestModel.id == payload.item_id)
        ).scalar_one_or_none()

        if not pl:
            raise HTTPException(status_code=404, detail="Request record not found.")

        pl.status = "APPROVED"
        pl.officer_reply = note
        pl.updated_at = datetime.datetime.utcnow()
        db.commit()

        return {
            "status": "success",
            "message": "Request approved.",
            "item_id": payload.item_id,
        }

    else:
        # 3. Approve CoordinatorRequestModel (Coordinator, Student correction, Recruiter)
        req = db.execute(
            select(CoordinatorRequestModel).where(CoordinatorRequestModel.id == payload.item_id)
        ).scalar_one_or_none()

        if not req:
            raise HTTPException(status_code=404, detail="Request record not found.")

        req_payload = {}
        if req.payload_json:
            try:
                req_payload = json.loads(req.payload_json)
            except Exception:
                req_payload = {}

        # If Student Data Correction, apply to StudentModel
        if req.request_type == "student_data_correction":
            target_id = req.target_id or req.submitted_by
            stu = db.execute(
                select(StudentModel).where((StudentModel.id == target_id) | (StudentModel.roll_no == target_id))
            ).scalar_one_or_none()

            if stu:
                # Support both direct key style and {field, requested_value} style
                field_name = req_payload.get("field")
                req_val = req_payload.get("requested_value") or req_payload.get("new_value")

                if field_name and req_val is not None:
                    try:
                        if field_name == "cgpa":
                            stu.cgpa = float(req_val)
                        elif "percentage" in field_name:
                            setattr(stu, field_name, float(req_val))
                        elif field_name in ("active_backlogs", "history_backlogs", "gap_years"):
                            setattr(stu, field_name, int(req_val))
                        elif hasattr(stu, field_name):
                            setattr(stu, field_name, str(req_val))
                        stu.version += 1
                    except Exception:
                        pass
                else:
                    # Direct keys
                    if "cgpa" in req_payload:
                        stu.cgpa = float(req_payload["cgpa"])
                    if "active_backlogs" in req_payload:
                        stu.active_backlogs = int(req_payload["active_backlogs"])
                    if "history_backlogs" in req_payload:
                        stu.history_backlogs = int(req_payload["history_backlogs"])
                    if "tenth_percentage" in req_payload:
                        stu.tenth_percentage = float(req_payload["tenth_percentage"])
                    if "twelfth_percentage" in req_payload:
                        stu.twelfth_percentage = float(req_payload["twelfth_percentage"])
                    if "gap_years" in req_payload:
                        stu.gap_years = int(req_payload["gap_years"])
                    stu.version += 1

        # If Shortlist Override, apply to EligibilityDecisionModel
        elif req.request_type == "shortlist_override" and req.target_id:
            drive_id = req_payload.get("drive_id")
            action = req_payload.get("action", "add")
            if drive_id:
                dec = db.execute(
                    select(EligibilityDecisionModel).where(
                        EligibilityDecisionModel.drive_id == drive_id,
                        EligibilityDecisionModel.student_id == req.target_id,
                    )
                ).scalar_one_or_none()
                if dec:
                    dec.status = "eligible" if action == "add" else "ineligible"
                    dec.reason = f"Officer approved coordinator override: {note}"

        req.status = "approved"
        req.officer_response = note
        req.officer_name = current_user.username
        req.resolved_at = datetime.datetime.utcnow()

        # Send in-app notification to the requester
        recipient_role = "student" if req.request_type == "student_data_correction" else (
            "recruiter" if req.request_type == "recruiter_inquiry" else "coordinator"
        )
        notif = NotificationModel(
            id=f"notif_{uuid.uuid4().hex[:12]}",
            recipient_role=recipient_role,
            recipient_username=req.submitted_by,
            category="request_update",
            title=f"Request Approved: {req.title}",
            message=f"Placement Officer {current_user.username} approved your request: {note}",
            created_at=datetime.datetime.utcnow(),
            metadata_json=json.dumps({"request_id": req.id}),
        )
        db.add(notif)
        db.commit()

        AuditService.record_action(
            db=db,
            actor=current_user.username,
            action="OFFICER_INBOX_REQUEST_APPROVED",
            aggregate_type="COORDINATOR_REQUEST",
            aggregate_id=req.id,
            payload={"response": note, "type": req.request_type},
        )

        return {
            "status": "success",
            "message": f"Request '{req.title}' has been approved and applied.",
            "item_id": payload.item_id,
        }


@router.post("/reject")
def reject_inbox_item(
    payload: RejectRequestPayload,
    current_user: UserModel = Depends(require_officer),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Rejects an inbound request with mandatory explanation."""
    reason = payload.reason.strip()
    if not reason:
        raise HTTPException(status_code=400, detail="Rejection reason is required.")

    if payload.source_type == "pending_result":
        res = db.execute(
            select(PendingResultModel).where(PendingResultModel.id == payload.item_id)
        ).scalar_one_or_none()
        if not res:
            raise HTTPException(status_code=404, detail="Pending result not found.")

        res.status = "rejected"
        res.officer_name = current_user.username
        res.resolved_at = datetime.datetime.utcnow()
        res.resolution_notes = reason
        db.commit()

        return {
            "status": "success",
            "message": "Result entry rejected.",
            "item_id": payload.item_id,
        }

    elif payload.source_type == "placement_request":
        pl = db.execute(
            select(PlacementRequestModel).where(PlacementRequestModel.id == payload.item_id)
        ).scalar_one_or_none()
        if not pl:
            raise HTTPException(status_code=404, detail="Request not found.")

        pl.status = "REJECTED"
        pl.officer_reply = reason
        pl.updated_at = datetime.datetime.utcnow()
        db.commit()

        return {
            "status": "success",
            "message": "Request rejected.",
            "item_id": payload.item_id,
        }

    else:
        req = db.execute(
            select(CoordinatorRequestModel).where(CoordinatorRequestModel.id == payload.item_id)
        ).scalar_one_or_none()
        if not req:
            raise HTTPException(status_code=404, detail="Request not found.")

        req.status = "rejected"
        req.officer_response = reason
        req.officer_name = current_user.username
        req.resolved_at = datetime.datetime.utcnow()

        recipient_role = "student" if req.request_type == "student_data_correction" else (
            "recruiter" if req.request_type == "recruiter_inquiry" else "coordinator"
        )
        notif = NotificationModel(
            id=f"notif_{uuid.uuid4().hex[:12]}",
            recipient_role=recipient_role,
            recipient_username=req.submitted_by,
            category="request_update",
            title=f"Request Rejected: {req.title}",
            message=f"Placement Officer {current_user.username} rejected your request: {reason}",
            created_at=datetime.datetime.utcnow(),
            metadata_json=json.dumps({"request_id": req.id}),
        )
        db.add(notif)
        db.commit()

        AuditService.record_action(
            db=db,
            actor=current_user.username,
            action="OFFICER_INBOX_REQUEST_REJECTED",
            aggregate_type="COORDINATOR_REQUEST",
            aggregate_id=req.id,
            payload={"reason": reason, "type": req.request_type},
        )

        return {
            "status": "success",
            "message": f"Request '{req.title}' has been rejected.",
            "item_id": payload.item_id,
        }


@router.post("/comment")
def add_inbox_comment(
    payload: AddCommentPayload,
    current_user: UserModel = Depends(require_officer),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Posts an officer reply or note to the request discussion thread."""
    req = db.execute(
        select(CoordinatorRequestModel).where(CoordinatorRequestModel.id == payload.item_id)
    ).scalar_one_or_none()

    if not req:
        raise HTTPException(status_code=404, detail="Request thread not found.")

    comments = []
    if req.comments_json:
        try:
            comments = json.loads(req.comments_json)
        except Exception:
            comments = []

    comments.append({
        "author": current_user.username,
        "role": current_user.role,
        "text": payload.text.strip(),
        "timestamp": datetime.datetime.utcnow().isoformat(),
    })
    req.comments_json = json.dumps(comments)
    db.commit()

    return {
        "status": "success",
        "message": "Reply posted to thread.",
        "comments": comments,
    }


@router.post("/send-message", status_code=status.HTTP_201_CREATED)
def send_officer_message(
    payload: OfficerSendMessagePayload,
    current_user: UserModel = Depends(require_officer),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Dispatches an official message or broadcast to another dashboard / candidate."""
    broadcast_id = f"msg_{uuid.uuid4().hex[:12]}"
    created_at = datetime.datetime.utcnow()

    meta = {
        "broadcast_id": broadcast_id,
        "sender": current_user.username,
        "sender_role": current_user.role,
        "category": payload.category,
        "drive_id": payload.drive_id,
    }

    if payload.recipient_role == "individual":
        if not payload.recipient_username:
            raise HTTPException(status_code=400, detail="Recipient roll number or username is required.")

        notif = NotificationModel(
            id=broadcast_id,
            recipient_role="student",
            recipient_username=payload.recipient_username.strip(),
            category=payload.category,
            title=payload.title,
            message=payload.message,
            is_read=False,
            created_at=created_at,
            metadata_json=json.dumps(meta),
        )
        db.add(notif)
    else:
        notif = NotificationModel(
            id=broadcast_id,
            recipient_role=payload.recipient_role,
            recipient_username=None,
            category=payload.category,
            title=payload.title,
            message=payload.message,
            is_read=False,
            created_at=created_at,
            metadata_json=json.dumps(meta),
        )
        db.add(notif)

    db.commit()

    AuditService.record_action(
        db=db,
        actor=current_user.username,
        action="OFFICER_DISPATCH_MESSAGE",
        aggregate_type="COMMUNICATION",
        aggregate_id=broadcast_id,
        payload={"title": payload.title, "target": payload.recipient_role},
    )

    return {
        "status": "success",
        "message": f"Message dispatched to {payload.recipient_role}.",
        "broadcast_id": broadcast_id,
    }
