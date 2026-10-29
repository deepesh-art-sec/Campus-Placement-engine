"""
Audit History and Historical Decision Replay Routes.
"""

from __future__ import annotations

import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.auth.dependencies import get_uow, require_officer_or_coordinator
from backend.app.domain.impact.replay import DecisionReplayer, ReplayExplanation
from backend.app.domain.models import Drive, RequirementSet
from backend.app.domain.policy.catalog import STRICT_ONE_OFFER_POLICY
from backend.app.storage.database import get_db
from backend.app.storage.models.entities import (
    AuditLogModel,
    DriveModel,
    StudentModel,
    UserModel,
)
from backend.app.storage.repositories.mappers import student_entity_to_domain
from backend.app.storage.repositories.sqlalchemy_repo import SqlAlchemyUnitOfWork

router = APIRouter(prefix="/api/audit", tags=["Audit & Replay"])

_replayer = DecisionReplayer()


class ReplayRequest(BaseModel):
    student_id: str
    drive_id: str
    as_of: datetime.datetime


@router.get("/logs")
def list_audit_logs(
    limit: int = Query(default=100, ge=1, le=1000),
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Lists compliance audit logs (data accesses, exports, manual overrides)."""
    stmt = select(AuditLogModel).order_by(AuditLogModel.timestamp.desc()).limit(limit)
    logs = db.execute(stmt).scalars().all()
    return [
        {
            "id": log.id,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "aggregate_type": log.entity_type,
            "aggregate_id": log.entity_id,
            "action": log.action,
            "event_type": log.action,
            "actor": log.actor,
            "timestamp": log.timestamp.isoformat(),
            "payload": log.changes_json,
        }
        for log in logs
    ]


@router.get("/student-access")
def list_student_access_logs(
    limit: int = Query(default=100, ge=1, le=1000),
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Lists student access audit records for privacy and transparency audit."""
    stmt = (
        select(AuditLogModel)
        .where(AuditLogModel.entity_type == "student")
        .order_by(AuditLogModel.timestamp.desc())
        .limit(limit)
    )
    logs = db.execute(stmt).scalars().all()
    return [
        {
            "id": log.id,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "aggregate_type": log.entity_type,
            "aggregate_id": log.entity_id,
            "action": log.action,
            "event_type": log.action,
            "actor": log.actor,
            "timestamp": log.timestamp.isoformat(),
            "payload": log.changes_json,
        }
        for log in logs
    ]


@router.post("/replay", response_model=ReplayExplanation)
def replay_historical_decision(
    req: ReplayRequest,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
    uow: SqlAlchemyUnitOfWork = Depends(get_uow),
) -> ReplayExplanation:
    """
    Reconstructs the deterministic eligibility and offer policy status for a candidate
    as of an exact historical timestamp ('why was candidate X excluded on 3 Oct?').
    """
    stmt_stu = select(StudentModel).where(StudentModel.id == req.student_id)
    stu_entity = db.execute(stmt_stu).scalar_one_or_none()
    if not stu_entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    stmt_drv = select(DriveModel).where(DriveModel.id == req.drive_id)
    drv_entity = db.execute(stmt_drv).scalar_one_or_none()
    if not drv_entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drive not found.")

    student = student_entity_to_domain(stu_entity)
    drive = Drive(
        id=drv_entity.id,
        company_id=drv_entity.company_id,
        company_name=drv_entity.company_name,
        drive_date=drv_entity.drive_date,
        ctc_lpa=drv_entity.ctc_lpa,
        requirements=RequirementSet(id=f"req_{drv_entity.id}", drive_id=drv_entity.id, min_cgpa=6.0),
    )

    with uow:
        explanation = _replayer.explain_historical_decision(
            uow=uow,
            student=student,
            drive=drive,
            policy=STRICT_ONE_OFFER_POLICY,
            as_of=req.as_of,
        )

    return explanation
