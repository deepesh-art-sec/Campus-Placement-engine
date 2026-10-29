"""
User Administration & Role Management Routes.
Allows Officers to manage coordinator and recruiter accounts,
bind recruiters to corporate partners, and issue one-time student access codes.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.auth.dependencies import require_officer
from backend.app.api.auth.hasher import hash_password
from backend.app.api.logging.audit_service import AuditService
from backend.app.storage.database import get_db
from backend.app.storage.models.entities import CompanyModel, StudentModel, UserModel

router = APIRouter(prefix="/api/admin/users", tags=["User Administration"])


class CreateUserPayload(BaseModel):
    username: str
    password: str
    email: str
    role: str  # "coordinator", "recruiter_readonly", "officer"
    company_id: str | None = None


class IssueStudentCodePayload(BaseModel):
    roll_no: str
    custom_code: str | None = None


@router.get("")
def list_managed_users(
    current_user: UserModel = Depends(require_officer),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Returns all staff coordinators and corporate recruiter accounts."""
    stmt = (
        select(UserModel)
        .where(UserModel.role.in_(["officer", "coordinator", "recruiter_readonly"]))
        .order_by(UserModel.created_at.desc())
    )
    users = db.execute(stmt).scalars().all()

    # Pre-fetch company names for display
    companies = {c.id: c.name for c in db.execute(select(CompanyModel)).scalars().all()}

    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active,
            "company_id": getattr(u, "company_id", None),
            "company_name": companies.get(getattr(u, "company_id", ""), "None"),
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_managed_user(
    payload: CreateUserPayload,
    current_user: UserModel = Depends(require_officer),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Creates a new coordinator or recruiter account."""
    if payload.role not in ("coordinator", "recruiter_readonly", "officer"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be 'coordinator', 'recruiter_readonly', or 'officer'.",
        )

    # Check for duplicate username
    existing = db.execute(
        select(UserModel).where(UserModel.username == payload.username.strip())
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{payload.username}' is already in use.",
        )

    user_id = f"usr_{uuid.uuid4()}"
    new_user = UserModel(
        id=user_id,
        username=payload.username.strip(),
        password_hash=hash_password(payload.password),
        email=payload.email.strip(),
        role=payload.role,
        is_active=True,
        company_id=payload.company_id,
        created_at=datetime.datetime.utcnow(),
    )
    db.add(new_user)
    db.commit()

    AuditService.record_event(
        db=db,
        actor=current_user.username,
        event_type="USER_CREATED",
        entity_id=user_id,
        payload={"username": payload.username, "role": payload.role},
    )

    return {
        "id": user_id,
        "username": new_user.username,
        "role": new_user.role,
        "message": f"Account for '{new_user.username}' created successfully.",
    }


@router.post("/{user_id}/toggle")
def toggle_user_active_state(
    user_id: str,
    current_user: UserModel = Depends(require_officer),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Activates or deactivates a user account."""
    target_user = db.execute(
        select(UserModel).where(UserModel.id == user_id)
    ).scalar_one_or_none()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own administrative account.",
        )

    target_user.is_active = not target_user.is_active
    db.commit()

    action_label = "activated" if target_user.is_active else "deactivated"
    AuditService.record_event(
        db=db,
        actor=current_user.username,
        event_type=f"USER_{action_label.upper()}",
        entity_id=user_id,
        payload={"username": target_user.username, "is_active": target_user.is_active},
    )

    return {
        "id": user_id,
        "username": target_user.username,
        "is_active": target_user.is_active,
        "message": f"Account '{target_user.username}' {action_label}.",
    }


@router.post("/issue-student-code")
def issue_student_access_code(
    payload: IssueStudentCodePayload,
    current_user: UserModel = Depends(require_officer),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Issues or resets a student's one-time LAN portal access code."""
    roll = payload.roll_no.strip()
    stu = db.execute(
        select(StudentModel).where(StudentModel.roll_no == roll)
    ).scalar_one_or_none()

    if not stu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with Roll No '{roll}' not found in institutional roster.",
        )

    code = payload.custom_code.strip() if payload.custom_code else "admin123"
    code_hash = hash_password(code)

    user = db.execute(
        select(UserModel).where(UserModel.username == roll, UserModel.role == "student")
    ).scalar_one_or_none()

    if not user:
        user = UserModel(
            id=f"usr_{stu.id}",
            username=roll,
            password_hash=code_hash,
            email=stu.email,
            role="student",
            student_id=stu.id,
            is_active=True,
            created_at=datetime.datetime.utcnow(),
        )
        db.add(user)
    else:
        user.password_hash = code_hash
        user.is_active = True

    db.commit()

    return {
        "roll_no": roll,
        "student_name": stu.name,
        "access_code": code,
        "status": "ISSUED",
        "message": f"Access code issued for {stu.name} ({roll}).",
    }
