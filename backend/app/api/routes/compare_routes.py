"""
Candidate Dispute and Policy Comparison Routes.
Explains precisely why Candidate A was blocked while Candidate B was allowed to sit.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.auth.dependencies import require_officer_or_coordinator
from backend.app.domain.models import Drive
from backend.app.domain.policy.catalog import STRICT_ONE_OFFER_POLICY
from backend.app.domain.policy.checker import compare_students
from backend.app.storage.database import get_db
from backend.app.storage.models.entities import DriveModel, StudentModel, UserModel
from backend.app.storage.repositories.mappers import student_entity_to_domain

router = APIRouter(prefix="/api/compare", tags=["Dispute & Comparison"])


class CompareStudentsRequest(BaseModel):
    student_a_id: str
    student_b_id: str
    drive_id: str


@router.post("/students")
def compare_two_students(
    req: CompareStudentsRequest,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Compares two candidates under institutional offer policy to resolve student disputes."""
    # Fetch Student A
    stmt_a = select(StudentModel).where(
        (StudentModel.id == req.student_a_id) | (StudentModel.roll_no == req.student_a_id)
    )
    sa_entity = db.execute(stmt_a).scalar_one_or_none()
    if not sa_entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student A not found.")

    # Fetch Student B
    stmt_b = select(StudentModel).where(
        (StudentModel.id == req.student_b_id) | (StudentModel.roll_no == req.student_b_id)
    )
    sb_entity = db.execute(stmt_b).scalar_one_or_none()
    if not sb_entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student B not found.")

    # Fetch Drive
    stmt_d = select(DriveModel).where(
        (DriveModel.id == req.drive_id) | (DriveModel.company_name == req.drive_id)
    )
    d_entity = db.execute(stmt_d).scalar_one_or_none()
    if not d_entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drive not found.")

    student_a = student_entity_to_domain(sa_entity)
    student_b = student_entity_to_domain(sb_entity)
    drive = Drive(
        id=d_entity.id,
        company_id=d_entity.company_id,
        company_name=d_entity.company_name,
        drive_date=d_entity.drive_date,
        ctc_lpa=d_entity.ctc_lpa,
    )

    result = compare_students(
        student_a=student_a,
        student_b=student_b,
        drive=drive,
        policy=STRICT_ONE_OFFER_POLICY,
    )

    return result.model_dump()
