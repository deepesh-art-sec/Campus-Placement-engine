"""
Recruiter Read-Only Portal Routes.
Restricts corporate campus recruiters to strictly their own company's shortlist and schedule.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.auth.dependencies import require_recruiter
from backend.app.storage.database import get_db
from backend.app.storage.models.entities import (
    DriveModel,
    EligibilityDecisionModel,
    SlotModel,
    StudentModel,
    UserModel,
)

router = APIRouter(prefix="/api/recruiter", tags=["Recruiter Portal"])


@router.get("/my-drive")
def get_recruiter_drive_data(
    current_user: UserModel = Depends(require_recruiter),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Returns only the recruiter's assigned company shortlist and interview schedule.
    Enforces strict tenant isolation on the server.
    """
    company_id = getattr(current_user, "company_id", None)
    if not company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Recruiter account is not associated with an authorized corporate partner.",
        )

    # Fetch recruiter's company drive
    stmt_drv = select(DriveModel).where(DriveModel.company_id == company_id)
    drives = db.execute(stmt_drv).scalars().all()
    if not drives:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No recruitment drives found for your organization.",
        )

    drive = drives[0]

    # Fetch approved shortlist
    dec_stmt = select(EligibilityDecisionModel).where(
        EligibilityDecisionModel.drive_id == drive.id,
        EligibilityDecisionModel.status == "eligible",
    )
    eligible_decisions = db.execute(dec_stmt).scalars().all()
    shortlist_ids = [d.student_id for d in eligible_decisions]

    students = db.execute(
        select(StudentModel).where(StudentModel.id.in_(shortlist_ids))
    ).scalars().all() if shortlist_ids else []

    # Fetch schedule slots
    slots = db.execute(
        select(SlotModel).where(SlotModel.drive_id == drive.id).order_by(SlotModel.start_time.asc())
    ).scalars().all()

    return {
        "company_id": drive.company_id,
        "company_name": drive.company_name,
        "drive_date": drive.drive_date.isoformat(),
        "total_shortlisted": len(students),
        "shortlist": [
            {
                "roll_no": s.roll_no,
                "name": s.name,
                "branch": s.branch,
                "cgpa": s.cgpa,
                "tenth_percentage": s.tenth_percentage,
                "twelfth_percentage": s.twelfth_percentage,
            }
            for s in students
        ],
        "schedule": [
            {
                "round_name": f"Round {sl.round_number}",
                "candidate_name": sl.student.name if sl.student else "Candidate",
                "candidate_roll_no": sl.student.roll_no if sl.student else "",
                "slot_time": sl.start_time.strftime("%d-%b-%Y %H:%M"),
                "venue": sl.room.name if sl.room else "Venue",
                "panel": sl.panel.name if sl.panel else "Panel A",
            }
            for sl in slots
        ],
    }
