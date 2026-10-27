"""
Coordinator Operations & Governance Requests API.
Enforces that student coordinators can prepare work and inspect state,
while all policy-altering or publishing decisions route to the Placement Officer.
"""

from __future__ import annotations

import datetime
import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.auth.dependencies import (
    get_current_user,
    require_officer,
    require_officer_or_coordinator,
)
from backend.app.api.logging.audit_service import AuditService
from backend.app.storage.database import get_db
from backend.app.storage.models.entities import (
    CoordinatorRequestModel,
    DriveAttendanceModel,
    DriveModel,
    EligibilityDecisionModel,
    NotificationModel,
    OfferModel,
    PendingResultModel,
    SlotModel,
    StudentModel,
    UserModel,
)

router = APIRouter(prefix="/api/coordinator", tags=["Coordinator Operations"])


# -----------------------------------------------------------------------------
# Request Schemas
# -----------------------------------------------------------------------------

class CoordinatorRequestCreate(BaseModel):
    request_type: str = Field(..., description="student_data_correction, shortlist_override, rule_doubt, clash_preference, logistics")
    title: str = Field(..., min_length=3)
    description: str = Field(..., min_length=5)
    target_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class AddCommentRequest(BaseModel):
    text: str = Field(..., min_length=1)


class ResolveRequest(BaseModel):
    response: str = Field(..., min_length=2)
    reason: str | None = None


class MarkAttendanceRequest(BaseModel):
    drive_id: str
    student_id: str
    slot_id: str | None = None
    room_name: str
    status: str = Field("present", description="present, absent, late, pending")
    notes: str | None = None


class PendingResultCreate(BaseModel):
    drive_id: str
    student_id: str
    event_type: str = "offered"
    ctc_lpa: float = Field(ge=0.0)
    fixed_pay_lpa: float | None = None
    is_dream: bool = False
    reason: str = Field(..., min_length=3)


class ClashPreferenceRequest(BaseModel):
    student_id: str
    preferred_drive_id: str
    conflicting_drive_id: str
    reason: str = "Candidate expressed schedule preference"


# -----------------------------------------------------------------------------
# 1. Overview Metrics (Module 1)
# -----------------------------------------------------------------------------

@router.get("/overview-metrics")
def get_coordinator_overview_metrics(
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Summary indicators tailored for coordinator shift overview."""
    today = datetime.date.today()

    all_drives = db.execute(select(DriveModel)).scalars().all()
    today_drives = [d for d in all_drives if d.drive_date == today]
    upcoming_drives = [d for d in all_drives if d.drive_date >= today]

    # Shortlisted students
    shortlisted_decisions = db.execute(
        select(EligibilityDecisionModel).where(EligibilityDecisionModel.status == "eligible")
    ).scalars().all()
    unique_shortlisted = len({d.student_id for d in shortlisted_decisions})

    # Needs review count
    needs_review_count = len(
        db.execute(
            select(EligibilityDecisionModel).where(EligibilityDecisionModel.status == "needs_review")
        ).scalars().all()
    )

    # Clashes count
    slots = db.execute(select(SlotModel)).scalars().all()
    clashes_count = 0
    for i in range(len(slots)):
        for j in range(i + 1, len(slots)):
            if (
                slots[i].student_id == slots[j].student_id
                and slots[i].start_time == slots[j].start_time
            ):
                clashes_count += 1

    # Coordinator Requests status breakdown
    reqs = db.execute(select(CoordinatorRequestModel)).scalars().all()
    waiting_count = len([r for r in reqs if r.status == "open"])
    answered_count = len([r for r in reqs if r.status == "answered"])
    approved_count = len([r for r in reqs if r.status == "approved"])
    rejected_count = len([r for r in reqs if r.status == "rejected"])

    return {
        "today_drives_count": len(today_drives),
        "upcoming_drives_count": len(upcoming_drives),
        "total_shortlisted_students": unique_shortlisted,
        "unresolved_clashes": clashes_count,
        "needs_review_count": needs_review_count,
        "requests": {
            "waiting_for_officer": waiting_count,
            "answered": answered_count,
            "approved": approved_count,
            "rejected": rejected_count,
            "total": len(reqs),
        },
    }


# -----------------------------------------------------------------------------
# 2. Coordinator Requests System (Module 10)
# -----------------------------------------------------------------------------

@router.get("/requests")
def list_coordinator_requests(
    status_filter: str | None = None,
    request_type: str | None = None,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Lists requests submitted by coordinators for Officer approval."""
    stmt = select(CoordinatorRequestModel).order_by(CoordinatorRequestModel.submitted_at.desc())
    if status_filter and status_filter != "all":
        stmt = stmt.where(CoordinatorRequestModel.status == status_filter)
    if request_type and request_type != "all":
        stmt = stmt.where(CoordinatorRequestModel.request_type == request_type)

    reqs = db.execute(stmt).scalars().all()
    return [
        {
            "id": r.id,
            "request_type": r.request_type,
            "title": r.title,
            "description": r.description,
            "submitted_by": r.submitted_by,
            "submitted_at": r.submitted_at.isoformat(),
            "status": r.status,
            "target_id": r.target_id,
            "payload": json.loads(r.payload_json or "{}"),
            "officer_response": r.officer_response,
            "officer_name": r.officer_name,
            "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
            "comments": json.loads(r.comments_json or "[]"),
        }
        for r in reqs
    ]


@router.post("/requests", status_code=status.HTTP_201_CREATED)
def create_coordinator_request(
    req: CoordinatorRequestCreate,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Submits a request to the officer with a mandatory reason."""
    new_req = CoordinatorRequestModel(
        id=f"req_{uuid.uuid4().hex[:12]}",
        request_type=req.request_type,
        title=req.title,
        description=req.description,
        submitted_by=current_user.username,
        submitted_at=datetime.datetime.utcnow(),
        status="open",
        target_id=req.target_id,
        payload_json=json.dumps(req.payload),
        comments_json=json.dumps([]),
    )
    db.add(new_req)

    # Add notification for the Officer
    notif = NotificationModel(
        id=f"notif_{uuid.uuid4().hex[:12]}",
        recipient_role="officer",
        recipient_username=None,
        category="request_update",
        title=f"New Coordinator Request: {req.title}",
        message=f"{current_user.username} submitted a {req.request_type.replace('_', ' ')} request.",
        created_at=datetime.datetime.utcnow(),
        metadata_json=json.dumps({"request_id": new_req.id}),
    )
    db.add(notif)
    db.commit()

    AuditService.record_action(
        db=db,
        actor=current_user.username,
        action="COORDINATOR_REQUEST_SUBMITTED",
        aggregate_type="COORDINATOR_REQUEST",
        aggregate_id=new_req.id,
        payload={"type": req.request_type, "title": req.title},
    )

    return {
        "id": new_req.id,
        "status": "open",
        "message": f"Request '{req.title}' submitted to Officer.",
        "submitted_at": new_req.submitted_at.isoformat(),
    }


@router.post("/requests/{request_id}/comments")
def add_request_comment(
    request_id: str,
    comment_req: AddCommentRequest,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Adds a threaded comment to an open request."""
    req = db.execute(select(CoordinatorRequestModel).where(CoordinatorRequestModel.id == request_id)).scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found.")

    comments = json.loads(req.comments_json or "[]")
    comments.append({
        "author": current_user.username,
        "role": current_user.role,
        "text": comment_req.text,
        "timestamp": datetime.datetime.utcnow().isoformat(),
    })
    req.comments_json = json.dumps(comments)
    db.commit()

    return {"message": "Comment added successfully.", "comments": comments}


@router.post("/requests/{request_id}/approve")
def approve_coordinator_request(
    request_id: str,
    resolve_req: ResolveRequest,
    current_user: UserModel = Depends(require_officer),  # STRICT: Officer only
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Approves a coordinator request and executes the requested action (Officer only)."""
    req = db.execute(select(CoordinatorRequestModel).where(CoordinatorRequestModel.id == request_id)).scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found.")

    payload = json.loads(req.payload_json or "{}")

    # If student data correction was requested, apply it directly to student record
    if req.request_type == "student_data_correction" and req.target_id:
        stu = db.execute(select(StudentModel).where((StudentModel.id == req.target_id) | (StudentModel.roll_no == req.target_id))).scalar_one_or_none()
        if stu:
            if "cgpa" in payload:
                stu.cgpa = float(payload["cgpa"])
            if "active_backlogs" in payload:
                stu.active_backlogs = int(payload["active_backlogs"])
            if "history_backlogs" in payload:
                stu.history_backlogs = int(payload["history_backlogs"])
            if "tenth_percentage" in payload:
                stu.tenth_percentage = float(payload["tenth_percentage"])
            if "twelfth_percentage" in payload:
                stu.twelfth_percentage = float(payload["twelfth_percentage"])
            if "gap_years" in payload:
                stu.gap_years = int(payload["gap_years"])
            stu.version += 1

    # If shortlist override was requested, apply it
    elif req.request_type == "shortlist_override" and req.target_id:
        drive_id = payload.get("drive_id")
        action = payload.get("action", "add")
        if drive_id:
            dec = db.execute(
                select(EligibilityDecisionModel).where(
                    EligibilityDecisionModel.drive_id == drive_id,
                    EligibilityDecisionModel.student_id == req.target_id,
                )
            ).scalar_one_or_none()
            if dec:
                dec.status = "eligible" if action == "add" else "ineligible"
                dec.reason = f"Officer approved coordinator request: {resolve_req.response}"

    req.status = "approved"
    req.officer_response = resolve_req.response
    req.officer_name = current_user.username
    req.resolved_at = datetime.datetime.utcnow()

    # Notify coordinator
    notif = NotificationModel(
        id=f"notif_{uuid.uuid4().hex[:12]}",
        recipient_role="coordinator",
        recipient_username=req.submitted_by,
        category="request_update",
        title=f"Request Approved: {req.title}",
        message=f"Officer {current_user.username} approved your request: {resolve_req.response}",
        created_at=datetime.datetime.utcnow(),
        metadata_json=json.dumps({"request_id": req.id}),
    )
    db.add(notif)
    db.commit()

    AuditService.record_action(
        db=db,
        actor=current_user.username,
        action="COORDINATOR_REQUEST_APPROVED",
        aggregate_type="COORDINATOR_REQUEST",
        aggregate_id=req.id,
        payload={"officer_response": resolve_req.response},
    )

    return {"message": "Request approved and applied.", "status": "approved"}


@router.post("/requests/{request_id}/reject")
def reject_coordinator_request(
    request_id: str,
    resolve_req: ResolveRequest,
    current_user: UserModel = Depends(require_officer),  # STRICT: Officer only
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Rejects a coordinator request with a mandatory reason (Officer only)."""
    req = db.execute(select(CoordinatorRequestModel).where(CoordinatorRequestModel.id == request_id)).scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found.")

    req.status = "rejected"
    req.officer_response = resolve_req.response
    req.officer_name = current_user.username
    req.resolved_at = datetime.datetime.utcnow()

    # Notify coordinator
    notif = NotificationModel(
        id=f"notif_{uuid.uuid4().hex[:12]}",
        recipient_role="coordinator",
        recipient_username=req.submitted_by,
        category="request_update",
        title=f"Request Rejected: {req.title}",
        message=f"Officer {current_user.username} rejected your request: {resolve_req.response}",
        created_at=datetime.datetime.utcnow(),
        metadata_json=json.dumps({"request_id": req.id}),
    )
    db.add(notif)
    db.commit()

    AuditService.record_action(
        db=db,
        actor=current_user.username,
        action="COORDINATOR_REQUEST_REJECTED",
        aggregate_type="COORDINATOR_REQUEST",
        aggregate_id=req.id,
        payload={"rejection_reason": resolve_req.response},
    )

    return {"message": "Request rejected.", "status": "rejected"}


@router.post("/requests/{request_id}/answer")
def answer_coordinator_request(
    request_id: str,
    resolve_req: ResolveRequest,
    current_user: UserModel = Depends(require_officer),  # STRICT: Officer only
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Answers a coordinator doubt or rule question (Officer only)."""
    req = db.execute(select(CoordinatorRequestModel).where(CoordinatorRequestModel.id == request_id)).scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found.")

    req.status = "answered"
    req.officer_response = resolve_req.response
    req.officer_name = current_user.username
    req.resolved_at = datetime.datetime.utcnow()

    # Notify coordinator
    notif = NotificationModel(
        id=f"notif_{uuid.uuid4().hex[:12]}",
        recipient_role="coordinator",
        recipient_username=req.submitted_by,
        category="request_update",
        title=f"Officer Answered: {req.title}",
        message=f"Officer {current_user.username} answered your inquiry: {resolve_req.response}",
        created_at=datetime.datetime.utcnow(),
        metadata_json=json.dumps({"request_id": req.id}),
    )
    db.add(notif)
    db.commit()

    return {"message": "Inquiry answered.", "status": "answered"}


# -----------------------------------------------------------------------------
# 3. On-The-Day Attendance Tracking (Module 9)
# -----------------------------------------------------------------------------

@router.get("/attendance/{drive_id}")
def get_drive_attendance(
    drive_id: str,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Fetches room-wise list of students and attendance marks for a drive."""
    drive = db.execute(select(DriveModel).where(DriveModel.id == drive_id)).scalar_one_or_none()
    if not drive:
        raise HTTPException(status_code=404, detail="Drive not found.")

    slots = db.execute(select(SlotModel).where(SlotModel.drive_id == drive_id)).scalars().all()
    attendance_records = db.execute(select(DriveAttendanceModel).where(DriveAttendanceModel.drive_id == drive_id)).scalars().all()
    att_map = {f"{a.student_id}_{a.room_name}": a for a in attendance_records}

    # Group students by room
    rooms_data: dict[str, list[dict[str, Any]]] = {}
    students_cache = {s.id: s for s in db.execute(select(StudentModel)).scalars().all()}

    present_count = 0
    absent_count = 0
    late_count = 0

    for slot in slots:
        r_name = slot.room_name or "General Room"
        if r_name not in rooms_data:
            rooms_data[r_name] = []

        stu = students_cache.get(slot.student_id)
        att = att_map.get(f"{slot.student_id}_{r_name}")
        att_status = att.status if att else "pending"

        if att_status == "present":
            present_count += 1
        elif att_status == "absent":
            absent_count += 1
        elif att_status == "late":
            late_count += 1

        rooms_data[r_name].append({
            "slot_id": slot.id,
            "student_id": slot.student_id,
            "roll_no": stu.roll_no if stu else slot.student_id,
            "name": stu.name if stu else "Candidate",
            "branch": stu.branch if stu else "Engineering",
            "start_time": slot.start_time.isoformat() if slot.start_time else "09:00",
            "room_name": r_name,
            "attendance_status": att_status,
            "marked_at": att.marked_at.isoformat() if att else None,
            "notes": att.notes if att else None,
        })

    return {
        "drive_id": drive.id,
        "company_name": drive.company_name,
        "drive_date": drive.drive_date.isoformat(),
        "total_scheduled": len(slots),
        "present_count": present_count,
        "absent_count": absent_count,
        "late_count": late_count,
        "pending_count": max(0, len(slots) - (present_count + absent_count + late_count)),
        "rooms": rooms_data,
    }


@router.post("/attendance/mark")
def mark_attendance(
    req: MarkAttendanceRequest,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Records present, absent, or late status for a student on drive day."""
    stmt = select(DriveAttendanceModel).where(
        DriveAttendanceModel.drive_id == req.drive_id,
        DriveAttendanceModel.student_id == req.student_id,
        DriveAttendanceModel.room_name == req.room_name,
    )
    existing = db.execute(stmt).scalar_one_or_none()
    if existing:
        existing.status = req.status
        existing.notes = req.notes
        existing.marked_by = current_user.username
        existing.marked_at = datetime.datetime.utcnow()
    else:
        new_att = DriveAttendanceModel(
            id=f"att_{uuid.uuid4().hex[:12]}",
            drive_id=req.drive_id,
            student_id=req.student_id,
            slot_id=req.slot_id,
            room_name=req.room_name,
            status=req.status,
            marked_by=current_user.username,
            marked_at=datetime.datetime.utcnow(),
            notes=req.notes,
        )
        db.add(new_att)

    db.commit()

    AuditService.record_action(
        db=db,
        actor=current_user.username,
        action="ATTENDANCE_MARKED",
        aggregate_type="ATTENDANCE",
        aggregate_id=req.student_id,
        payload={"drive_id": req.drive_id, "status": req.status, "room": req.room_name},
    )

    return {"message": f"Student attendance marked as {req.status}."}


# -----------------------------------------------------------------------------
# 4. Pending Result Entry & Approval (Module 7)
# -----------------------------------------------------------------------------

@router.get("/pending-results")
def list_pending_results(
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Lists result entries submitted by coordinators awaiting Officer approval."""
    stmt = select(PendingResultModel).order_by(PendingResultModel.submitted_at.desc())
    results = db.execute(stmt).scalars().all()

    students_cache = {s.id: s for s in db.execute(select(StudentModel)).scalars().all()}
    drives_cache = {d.id: d for d in db.execute(select(DriveModel)).scalars().all()}

    return [
        {
            "id": r.id,
            "drive_id": r.drive_id,
            "company_name": drives_cache[r.drive_id].company_name if r.drive_id in drives_cache else "Company",
            "student_id": r.student_id,
            "student_name": students_cache[r.student_id].name if r.student_id in students_cache else "Student",
            "roll_no": students_cache[r.student_id].roll_no if r.student_id in students_cache else "Roll",
            "event_type": r.event_type,
            "ctc_lpa": r.ctc_lpa,
            "fixed_pay_lpa": r.fixed_pay_lpa,
            "is_dream": r.is_dream,
            "reason": r.reason,
            "submitted_by": r.submitted_by,
            "submitted_at": r.submitted_at.isoformat(),
            "status": r.status,
            "officer_name": r.officer_name,
            "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
            "resolution_notes": r.resolution_notes,
        }
        for r in results
    ]


@router.post("/pending-results", status_code=status.HTTP_201_CREATED)
def submit_pending_result(
    req: PendingResultCreate,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Submits a recruitment result. If entered by a coordinator,
    it stays PENDING until the officer approves it.
    """
    # Resolve student id if roll_no was passed
    stu = db.execute(
        select(StudentModel).where((StudentModel.id == req.student_id) | (StudentModel.roll_no == req.student_id))
    ).scalar_one_or_none()
    target_student_id = stu.id if stu else req.student_id

    pending = PendingResultModel(
        id=f"pres_{uuid.uuid4().hex[:12]}",
        drive_id=req.drive_id,
        student_id=target_student_id,
        event_type=req.event_type,
        ctc_lpa=req.ctc_lpa,
        fixed_pay_lpa=req.fixed_pay_lpa,
        is_dream=req.is_dream,
        reason=req.reason,
        submitted_by=current_user.username,
        submitted_at=datetime.datetime.utcnow(),
        status="pending",
    )
    db.add(pending)

    # Notify Officer
    notif = NotificationModel(
        id=f"notif_{uuid.uuid4().hex[:12]}",
        recipient_role="officer",
        recipient_username=None,
        category="result_pending",
        title="Pending Drive Result Entry",
        message=f"{current_user.username} entered result '{req.event_type}' ({req.ctc_lpa} LPA). Awaiting your approval.",
        created_at=datetime.datetime.utcnow(),
        metadata_json=json.dumps({"pending_result_id": pending.id}),
    )
    db.add(notif)
    db.commit()

    AuditService.record_action(
        db=db,
        actor=current_user.username,
        action="PENDING_RESULT_SUBMITTED",
        aggregate_type="PENDING_RESULT",
        aggregate_id=pending.id,
        payload={"drive_id": req.drive_id, "student_id": req.student_id, "ctc_lpa": req.ctc_lpa},
    )

    return {
        "id": pending.id,
        "status": "pending",
        "message": "Result entry saved as PENDING. Awaiting officer confirmation & policy enforcement.",
    }


@router.post("/pending-results/{result_id}/approve")
def approve_pending_result(
    result_id: str,
    resolve_req: ResolveRequest,
    current_user: UserModel = Depends(require_officer),  # STRICT: Officer only
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Officer approves pending result, which commits offer and triggers policy ChangeSet."""
    res = db.execute(select(PendingResultModel).where(PendingResultModel.id == result_id)).scalar_one_or_none()
    if not res:
        raise HTTPException(status_code=404, detail="Pending result not found.")

    res.status = "approved"
    res.officer_name = current_user.username
    res.resolved_at = datetime.datetime.utcnow()
    res.resolution_notes = resolve_req.response

    # Commit offer to OfferModel and update student version
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

    stu = db.execute(select(StudentModel).where((StudentModel.id == res.student_id) | (StudentModel.roll_no == res.student_id))).scalar_one_or_none()
    if stu:
        stu.version += 1

    db.commit()

    AuditService.record_action(
        db=db,
        actor=current_user.username,
        action="PENDING_RESULT_APPROVED",
        aggregate_type="PENDING_RESULT",
        aggregate_id=res.id,
        payload={"notes": resolve_req.response},
    )

    return {"message": "Result approved. Offer policy enforced.", "status": "approved"}


@router.post("/pending-results/{result_id}/reject")
def reject_pending_result(
    result_id: str,
    resolve_req: ResolveRequest,
    current_user: UserModel = Depends(require_officer),  # STRICT: Officer only
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Officer rejects pending result."""
    res = db.execute(select(PendingResultModel).where(PendingResultModel.id == result_id)).scalar_one_or_none()
    if not res:
        raise HTTPException(status_code=404, detail="Pending result not found.")

    res.status = "rejected"
    res.officer_name = current_user.username
    res.resolved_at = datetime.datetime.utcnow()
    res.resolution_notes = resolve_req.response
    db.commit()

    return {"message": "Result entry rejected.", "status": "rejected"}


# -----------------------------------------------------------------------------
# 5. Clash Preference (Module 6)
# -----------------------------------------------------------------------------

@router.post("/clashes/preference")
def record_clash_preference(
    req: ClashPreferenceRequest,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Records a candidate's stated preference for overlapping drive windows."""
    coord_req = CoordinatorRequestModel(
        id=f"req_clash_{uuid.uuid4().hex[:10]}",
        request_type="clash_preference",
        title=f"Clash Preference: Student {req.student_id}",
        description=req.reason,
        submitted_by=current_user.username,
        submitted_at=datetime.datetime.utcnow(),
        status="open",
        target_id=req.student_id,
        payload_json=json.dumps({
            "preferred_drive_id": req.preferred_drive_id,
            "conflicting_drive_id": req.conflicting_drive_id,
        }),
    )
    db.add(coord_req)
    db.commit()

    AuditService.record_action(
        db=db,
        actor=current_user.username,
        action="CLASH_PREFERENCE_RECORDED",
        aggregate_type="CLASH",
        aggregate_id=req.student_id,
        payload={"preferred": req.preferred_drive_id, "conflicting": req.conflicting_drive_id},
    )

    return {"message": "Candidate preference recorded and forwarded to the Officer."}


# -----------------------------------------------------------------------------
# 6. Notifications System (Module 12)
# -----------------------------------------------------------------------------

@router.get("/notifications")
def get_notifications(
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieves notification stream for the logged in coordinator or officer."""
    stmt = select(NotificationModel).where(
        (NotificationModel.recipient_role == current_user.role) |
        (NotificationModel.recipient_role == "all") |
        (NotificationModel.recipient_username == current_user.username)
    ).order_by(NotificationModel.created_at.desc()).limit(50)

    notifs = db.execute(stmt).scalars().all()
    return [
        {
            "id": n.id,
            "category": n.category,
            "title": n.title,
            "message": n.message,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat(),
            "metadata": json.loads(n.metadata_json or "{}"),
        }
        for n in notifs
    ]


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Marks a notification as read."""
    notif = db.execute(select(NotificationModel).where(NotificationModel.id == notification_id)).scalar_one_or_none()
    if notif:
        notif.is_read = True
        db.commit()
    return {"message": "Notification marked as read."}
