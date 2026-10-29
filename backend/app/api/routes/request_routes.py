"""
Request and Communication Routes.
Handles coordinator requests, student data corrections, recruiter inquiries,
and officer approval/rejection workflows with complete audit logging.
"""

from __future__ import annotations

import datetime
import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.app.api.auth.dependencies import (
    get_current_user,
    require_officer,
    require_officer_or_coordinator,
)
from backend.app.api.logging.audit_service import AuditService
from backend.app.storage.database import get_db
from backend.app.storage.models.entities import (
    PlacementRequestModel,
    StudentModel,
    UserModel,
)

router = APIRouter(prefix="/api/requests", tags=["Requests & Communication"])


class CreateRequestPayload(BaseModel):
    request_type: str  # "DATA_CORRECTION", "RULE_DOUBT", "EXTRA_PANEL", "CLASH_PREFERENCE", "RECRUITER_QUERY", "ADD_REMOVE_STUDENT"
    subject: str
    details: dict[str, Any] = {}
    drive_id: str | None = None
    student_id: str | None = None


class RequestActionPayload(BaseModel):
    action: str  # "APPROVE", "REJECT", "ANSWER"
    reply: str
    apply_correction: bool = False


@router.post("", status_code=status.HTTP_201_CREATED)
def submit_request(
    payload: CreateRequestPayload,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Submits a new request from any authenticated role."""
    req_id = str(uuid.uuid4())
    student_id = payload.student_id or current_user.student_id

    req_entity = PlacementRequestModel(
        id=req_id,
        requester_id=current_user.id,
        requester_role=current_user.role,
        requester_name=current_user.username,
        request_type=payload.request_type,
        drive_id=payload.drive_id,
        student_id=student_id,
        subject=payload.subject,
        details_json=json.dumps(payload.details),
        status="PENDING",
        created_at=datetime.datetime.utcnow(),
        updated_at=datetime.datetime.utcnow(),
    )
    db.add(req_entity)
    db.commit()

    AuditService.record_event(
        db=db,
        actor=current_user.username,
        event_type="REQUEST_SUBMITTED",
        entity_id=req_id,
        payload={
            "type": payload.request_type,
            "subject": payload.subject,
            "role": current_user.role,
        },
    )

    return {
        "id": req_id,
        "status": "PENDING",
        "message": "Request submitted successfully to the Placement Officer.",
    }


@router.get("")
def list_requests(
    status_filter: str | None = Query(None, alias="status"),
    type_filter: str | None = Query(None, alias="type"),
    limit: int = 100,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    Returns requests filtered by permissions:
    - Officer: sees all requests
    - Coordinator: sees coordinator and student requests
    - Student: sees only their own requests
    - Recruiter: sees only their own inquiries
    """
    stmt = select(PlacementRequestModel)

    if current_user.role == "student":
        stmt = stmt.where(
            (PlacementRequestModel.requester_id == current_user.id)
            | (PlacementRequestModel.student_id == current_user.student_id)
        )
    elif current_user.role == "recruiter_readonly":
        stmt = stmt.where(PlacementRequestModel.requester_id == current_user.id)
    elif current_user.role == "coordinator":
        stmt = stmt.where(
            PlacementRequestModel.requester_role.in_(["coordinator", "student"])
        )

    if status_filter:
        stmt = stmt.where(PlacementRequestModel.status == status_filter.upper())
    if type_filter:
        stmt = stmt.where(PlacementRequestModel.request_type == type_filter.upper())

    stmt = stmt.order_by(desc(PlacementRequestModel.created_at)).limit(limit)
    rows = db.execute(stmt).scalars().all()

    results = []
    for r in rows:
        details = {}
        try:
            details = json.loads(r.details_json)
        except Exception:
            pass

        results.append({
            "id": r.id,
            "requester_id": r.requester_id,
            "requester_role": r.requester_role,
            "requester_name": r.requester_name,
            "request_type": r.request_type,
            "drive_id": r.drive_id,
            "student_id": r.student_id,
            "subject": r.subject,
            "details": details,
            "status": r.status,
            "officer_reply": r.officer_reply,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        })
    return results


@router.post("/{request_id}/action")
def process_request_action(
    request_id: str,
    payload: RequestActionPayload,
    current_user: UserModel = Depends(require_officer),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Allows Placement Officer to approve, reject, or answer a request."""
    req_entity = db.execute(
        select(PlacementRequestModel).where(PlacementRequestModel.id == request_id)
    ).scalar_one_or_none()

    if not req_entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found.",
        )

    act = payload.action.upper()
    if act not in ("APPROVE", "REJECT", "ANSWER"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Must be APPROVE, REJECT, or ANSWER.",
        )

    new_status = "APPROVED" if act == "APPROVE" else "REJECTED" if act == "REJECT" else "ANSWERED"
    req_entity.status = new_status
    req_entity.officer_reply = payload.reply
    req_entity.updated_at = datetime.datetime.utcnow()

    # If approving a student data correction, apply to StudentModel
    if act == "APPROVE" and payload.apply_correction and req_entity.student_id:
        try:
            details = json.loads(req_entity.details_json)
            field = details.get("field")
            new_val = details.get("new_value")

            stu = db.execute(
                select(StudentModel).where(
                    (StudentModel.id == req_entity.student_id)
                    | (StudentModel.roll_no == req_entity.student_id)
                )
            ).scalar_one_or_none()

            if stu and field and hasattr(stu, field) and new_val is not None:
                # Type cast based on field
                if field == "cgpa":
                    setattr(stu, field, float(new_val))
                elif "percentage" in field:
                    setattr(stu, field, float(new_val))
                elif field in ("active_backlogs", "history_backlogs", "gap_years"):
                    setattr(stu, field, int(new_val))
                else:
                    setattr(stu, field, str(new_val))
                stu.version += 1
                db.commit()
        except Exception:
            pass

    db.commit()

    AuditService.record_event(
        db=db,
        actor=current_user.username,
        event_type=f"REQUEST_{new_status}",
        entity_id=request_id,
        payload={"reply": payload.reply, "action": act},
    )

    return {
        "id": request_id,
        "status": new_status,
        "message": f"Request {new_status.lower()} successfully.",
    }
