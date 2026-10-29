"""
On-The-Day Drive Attendance Routes.
Supports room-wise and drive-wise attendance tracking (Present, Absent, Late)
by Coordinators and Officers with running counts.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.auth.dependencies import (
    get_current_user,
    require_officer_or_coordinator,
)
from backend.app.api.logging.audit_service import AuditService
from backend.app.storage.database import get_db
from backend.app.storage.models.entities import (
    AttendanceRecordModel,
    SlotModel,
    StudentModel,
    UserModel,
)

router = APIRouter(prefix="/api/attendance", tags=["On-The-Day Attendance"])


class MarkAttendancePayload(BaseModel):
    drive_id: str
    student_id: str
    student_name: str
    roll_no: str
    room_name: str | None = None
    status: str  # "PRESENT", "ABSENT", "LATE"
    notes: str | None = None


@router.post("/mark")
def mark_attendance(
    payload: MarkAttendancePayload,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Marks or updates candidate attendance on drive day."""
    st = payload.status.upper()
    if st not in ("PRESENT", "ABSENT", "LATE"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status must be PRESENT, ABSENT, or LATE.",
        )

    # Upsert attendance record for this drive + student
    stmt = select(AttendanceRecordModel).where(
        AttendanceRecordModel.drive_id == payload.drive_id,
        AttendanceRecordModel.student_id == payload.student_id,
    )
    record = db.execute(stmt).scalar_one_or_none()

    if not record:
        record = AttendanceRecordModel(
            id=str(uuid.uuid4()),
            drive_id=payload.drive_id,
            student_id=payload.student_id,
            student_name=payload.student_name,
            roll_no=payload.roll_no,
            room_name=payload.room_name,
            status=st,
            notes=payload.notes,
            marked_by=current_user.username,
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
        )
        db.add(record)
    else:
        record.status = st
        if payload.room_name:
            record.room_name = payload.room_name
        if payload.notes is not None:
            record.notes = payload.notes
        record.marked_by = current_user.username
        record.updated_at = datetime.datetime.utcnow()

    db.commit()

    AuditService.record_event(
        db=db,
        actor=current_user.username,
        event_type="ATTENDANCE_MARKED",
        entity_id=record.id,
        payload={
            "drive_id": payload.drive_id,
            "roll_no": payload.roll_no,
            "status": st,
            "room": payload.room_name,
        },
    )

    return {
        "status": "success",
        "attendance_id": record.id,
        "student_id": payload.student_id,
        "roll_no": payload.roll_no,
        "new_status": st,
        "marked_by": current_user.username,
    }


@router.get("/{drive_id}")
def get_drive_attendance(
    drive_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Returns real-time attendance statistics and roster for the specified drive."""
    records = db.execute(
        select(AttendanceRecordModel).where(AttendanceRecordModel.drive_id == drive_id)
    ).scalars().all()

    counts = {"PRESENT": 0, "ABSENT": 0, "LATE": 0}
    for r in records:
        if r.status in counts:
            counts[r.status] += 1

    return {
        "drive_id": drive_id,
        "total_marked": len(records),
        "present_count": counts["PRESENT"],
        "absent_count": counts["ABSENT"],
        "late_count": counts["LATE"],
        "records": [
            {
                "id": r.id,
                "student_id": r.student_id,
                "student_name": r.student_name,
                "roll_no": r.roll_no,
                "room_name": r.room_name,
                "status": r.status,
                "notes": r.notes,
                "marked_by": r.marked_by,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in records
        ],
    }
