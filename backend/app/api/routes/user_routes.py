"""
User & Access Code Administration Routes (Module 11).
Enables the Training & Placement Officer to create and deactivate coordinator and recruiter accounts,
link recruiters to companies, and issue individual and bulk printable student access codes.
"""

from __future__ import annotations

import datetime
import secrets
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.auth.dependencies import require_officer
from backend.app.api.auth.hasher import hash_password
from backend.app.api.auth.session_manager import issue_student_access_code
from backend.app.api.logging.audit_service import AuditService
from backend.app.storage.database import get_db
from backend.app.storage.models.entities import CompanyModel, StudentModel, UserModel

router = APIRouter(prefix="/api/users", tags=["Users & Roles"])


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: str = Field(min_length=5, max_length=255)
    role: str = Field(pattern="^(officer|coordinator|recruiter_readonly)$")
    password: str = Field(min_length=6)
    company_id: str | None = None


class ToggleStatusRequest(BaseModel):
    is_active: bool
    reason: str = Field(default="Administrative status update")


class BulkStudentCodeRequest(BaseModel):
    branch: str | None = None
    limit: int = Field(default=200, ge=1, le=2000)


@router.get("")
def list_users(
    role: str | None = None,
    current_user: UserModel = Depends(require_officer),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Lists staff, coordinator, and recruiter accounts (Officer only)."""
    stmt = select(UserModel).where(UserModel.role != "student")
    if role:
        stmt = stmt.where(UserModel.role == role)
    stmt = stmt.order_by(UserModel.created_at.desc())

    users = db.execute(stmt).scalars().all()
    results = []
    for u in users:
        company_name = None
        if u.company_id:
            comp = db.execute(select(CompanyModel).where(CompanyModel.id == u.company_id)).scalar_one_or_none()
            if comp:
                company_name = comp.name

        results.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active,
            "company_id": u.company_id,
            "company_name": company_name,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        })
    return results


@router.post("", status_code=status.HTTP_201_CREATED)
def create_user_account(
    req: CreateUserRequest,
    current_user: UserModel = Depends(require_officer),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Creates a coordinator or recruiter account (Officer only)."""
    # Verify username uniqueness
    existing = db.execute(select(UserModel).where(UserModel.username == req.username)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{req.username}' is already in use.",
        )

    # If recruiter, verify company exists
    if req.role == "recruiter_readonly" and req.company_id:
        comp = db.execute(select(CompanyModel).where(CompanyModel.id == req.company_id)).scalar_one_or_none()
        if not comp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with ID '{req.company_id}' not found.",
            )

    user_id = f"usr_{uuid.uuid4().hex[:8]}"
    pw_hash = hash_password(req.password)

    new_user = UserModel(
        id=user_id,
        username=req.username,
        email=req.email,
        password_hash=pw_hash,
        role=req.role,
        is_active=True,
        company_id=req.company_id if req.role == "recruiter_readonly" else None,
        created_at=datetime.datetime.utcnow(),
    )
    db.add(new_user)
    db.commit()

    AuditService.record_event(
        db=db,
        event_type="USER_ACCOUNT_CREATED",
        aggregate_type="USER",
        aggregate_id=user_id,
        payload={
            "username": req.username,
            "role": req.role,
            "company_id": req.company_id,
            "created_by": current_user.username,
        },
        actor_id=str(current_user.id),
        actor_role=str(current_user.role),
    )

    return {
        "id": user_id,
        "username": req.username,
        "role": req.role,
        "message": f"Account for '{req.username}' ({req.role}) created successfully.",
    }


@router.patch("/{user_id}/status")
def toggle_user_status(
    user_id: str,
    req: ToggleStatusRequest,
    current_user: UserModel = Depends(require_officer),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Activates or deactivates a user account (Officer only)."""
    user = db.execute(select(UserModel).where(UserModel.id == user_id)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found.")

    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Officers cannot deactivate their own account.")

    old_status = user.is_active
    user.is_active = req.is_active
    db.commit()

    AuditService.record_event(
        db=db,
        event_type="USER_STATUS_UPDATED",
        aggregate_type="USER",
        aggregate_id=user_id,
        payload={
            "username": user.username,
            "old_active": old_status,
            "new_active": req.is_active,
            "reason": req.reason,
            "updated_by": current_user.username,
        },
        actor_id=str(current_user.id),
        actor_role=str(current_user.role),
    )

    action_name = "activated" if req.is_active else "deactivated"
    return {
        "id": user_id,
        "username": user.username,
        "is_active": user.is_active,
        "message": f"Account '{user.username}' successfully {action_name}.",
    }


@router.get("/companies")
def list_companies_for_recruiter(
    current_user: UserModel = Depends(require_officer),
    db: Session = Depends(get_db),
) -> list[dict[str, str]]:
    """Returns available company options for linking recruiter accounts."""
    companies = db.execute(select(CompanyModel).order_by(CompanyModel.name.asc())).scalars().all()
    return [{"id": c.id, "name": c.name, "tier": c.tier or "Tier 1"} for c in companies]


@router.post("/student-codes/bulk")
def issue_bulk_student_codes(
    req: BulkStudentCodeRequest,
    current_user: UserModel = Depends(require_officer),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Generates or refreshes one-time login access codes for students in bulk (Officer only).
    Returns printable roster of candidate roll numbers, names, branches, and passcodes.
    """
    stmt = select(StudentModel)
    if req.branch:
        stmt = stmt.where(StudentModel.branch == req.branch)
    stmt = stmt.order_by(StudentModel.roll_no.asc()).limit(req.limit)

    students = db.execute(stmt).scalars().all()
    if not students:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No matching student records found.")

    issued_roster = []
    for s in students:
        code = issue_student_access_code(db=db, roll_no=s.roll_no)
        issued_roster.append({
            "roll_no": s.roll_no,
            "name": s.name,
            "branch": s.branch,
            "access_code": code,
        })

    AuditService.record_event(
        db=db,
        event_type="BULK_STUDENT_CODES_ISSUED",
        aggregate_type="STUDENT",
        aggregate_id="BULK",
        payload={
            "count": len(issued_roster),
            "branch": req.branch,
            "issued_by": current_user.username,
        },
        actor_id=str(current_user.id),
        actor_role=str(current_user.role),
    )

    return {
        "total_issued": len(issued_roster),
        "branch_filtered": req.branch,
        "roster": issued_roster,
        "message": f"Generated {len(issued_roster)} one-time candidate access codes ready for printing.",
    }
