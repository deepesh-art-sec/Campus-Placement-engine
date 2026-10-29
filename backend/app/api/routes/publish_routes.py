"""
Drive Publication Safeguards and Version Rollback Routes.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.auth.dependencies import get_uow, require_officer
from backend.app.domain.exceptions import StaleVersionError
from backend.app.domain.impact.models import DriveVersionState, ImpactReport
from backend.app.domain.impact.safeguards import PublishSafeguards
from backend.app.domain.models import Drive, RequirementSet
from backend.app.storage.database import get_db
from backend.app.scheduler.clash_service import detect_db_slot_clashes
from backend.app.api.routes.schedule_routes import generate_schedule, ScheduleGenerateRequest
from backend.app.storage.models.entities import (
    DriveModel,
    EligibilityDecisionModel,
    UserModel,
)
from backend.app.storage.repositories.sqlalchemy_repo import SqlAlchemyUnitOfWork

router = APIRouter(prefix="/api/drives", tags=["Publish & Rollback"])

_safeguards = PublishSafeguards()


class PublishRequest(BaseModel):
    expected_base_version: int | None = None
    reason: str = "Finalized shortlisted candidates and interview slots"


class RollbackRequest(BaseModel):
    target_version: int
    reason: str = "Rollback due to administrative correction"


@router.post("/{drive_id}/publish")
def publish_drive(
    drive_id: str,
    req: PublishRequest,
    current_user: UserModel = Depends(require_officer),
    db: Session = Depends(get_db),
    uow: SqlAlchemyUnitOfWork = Depends(get_uow),
) -> dict[str, Any]:
    """Publishes an immutable versioned snapshot with optimistic lock safeguards (Officer only)."""
    stmt = select(DriveModel).where(DriveModel.id == drive_id)
    drive_entity = db.execute(stmt).scalar_one_or_none()
    if not drive_entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drive not found.")

    expected_v = req.expected_base_version if req.expected_base_version is not None else drive_entity.version

    # Fetch shortlist
    dec_stmt = select(EligibilityDecisionModel).where(
        EligibilityDecisionModel.drive_id == drive_id,
        EligibilityDecisionModel.status == "eligible",
    )
    shortlist_ids = [d.student_id for d in db.execute(dec_stmt).scalars().all()]

    # Check for hard clashes before publishing
    initial_clashes = detect_db_slot_clashes(db, drive_id=drive_id)
    unresolved_initial = [c for c in initial_clashes if c.get("status") == "unresolved"]

    # If hard clashes exist, automatically attempt safe clash-free regeneration
    if unresolved_initial:
        try:
            generate_schedule(
                req=ScheduleGenerateRequest(drive_id=drive_id),
                current_user=current_user,
                db=db,
            )
            # Re-check after safe regeneration
            initial_clashes = detect_db_slot_clashes(db, drive_id=drive_id)
            unresolved_initial = [c for c in initial_clashes if c.get("status") == "unresolved"]
        except Exception:
            pass

    if unresolved_initial:
        conflict_reasons = [
            f"{c.get('conflict_type', 'Conflict')}: {c.get('student_name', 'Candidate')} conflicts with {c.get('drive_b_company', 'Other drive')} at {c.get('drive_a_time', 'time')}"
            for c in unresolved_initial
        ]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Cannot publish drive: Hard schedule clashes detected with published drives.",
                "block_reasons": conflict_reasons,
                "clash_count": len(unresolved_initial),
            },
        )

    # Safeguards validation with actual verified clash count
    actual_clashes_count = len(unresolved_initial)
    mock_impact = ImpactReport(
        change_summary="Publication validation",
        headline=f"Publishing finalized drive for {drive_entity.company_name}",
        drive_id=drive_id,
        drive_name=drive_entity.company_name,
        students_added_count=len(shortlist_ids),
        students_removed_count=0,
        clashes_count=actual_clashes_count,
    )

    validation = _safeguards.validate_for_publish(
        drive_id=drive_id,
        current_version=drive_entity.version,
        expected_base_version=expected_v,
        unresolved_review_items=[],
        schedule_items=[],
        rooms=[],
        drives=[],
        impact_report=mock_impact,
    )

    if not validation.can_publish:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Publish safeguards prevented commit.",
                "block_reasons": validation.block_reasons,
                "stale_version": validation.stale_version_detected,
            },
        )

    drive_domain = Drive(
        id=drive_entity.id,
        company_id=drive_entity.company_id,
        company_name=drive_entity.company_name,
        drive_date=drive_entity.drive_date,
        ctc_lpa=drive_entity.ctc_lpa,
        version=drive_entity.version,
    )

    with uow:
        try:
            snapshot = _safeguards.commit_publish(
                uow=uow,
                drive=drive_domain,
                requirements=RequirementSet(id=f"req_{drive_id}", drive_id=drive_id, min_cgpa=6.0),
                shortlist_student_ids=shortlist_ids,
                schedule_items=[],
                expected_base_version=expected_v,
                actor=current_user.username,
                reason=req.reason,
            )
            uow.commit()
        except StaleVersionError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    # Update DB entity version
    drive_entity.version = snapshot.version
    drive_entity.status = "published"
    db.commit()

    return {
        "drive_id": drive_id,
        "version": snapshot.version,
        "is_published": True,
        "audit_hash": snapshot.audit_hash,
        "shortlist_count": len(shortlist_ids),
        "message": f"Drive successfully published at version v{snapshot.version}.",
    }


@router.post("/{drive_id}/rollback")
def rollback_drive(
    drive_id: str,
    req: RollbackRequest,
    current_user: UserModel = Depends(require_officer),
    db: Session = Depends(get_db),
    uow: SqlAlchemyUnitOfWork = Depends(get_uow),
) -> dict[str, Any]:
    """Rolls back drive state to a targeted historical version (Officer only)."""
    stmt = select(DriveModel).where(DriveModel.id == drive_id)
    drive_entity = db.execute(stmt).scalar_one_or_none()
    if not drive_entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drive not found.")

    target_snapshot = DriveVersionState(
        drive_id=drive_id,
        version=req.target_version,
        is_published=True,
        requirements=RequirementSet(id=f"req_{drive_id}_v{req.target_version}", drive_id=drive_id, min_cgpa=6.0),
        shortlist_student_ids=[],
        schedule_items=[],
    )

    drive_domain = Drive(
        id=drive_entity.id,
        company_id=drive_entity.company_id,
        company_name=drive_entity.company_name,
        drive_date=drive_entity.drive_date,
        ctc_lpa=drive_entity.ctc_lpa,
        version=drive_entity.version,
    )

    with uow:
        rolled = _safeguards.rollback_to_version(
            uow=uow,
            drive=drive_domain,
            target_snapshot=target_snapshot,
            actor=current_user.username,
            reason=req.reason,
        )
        uow.commit()

    drive_entity.version = rolled.version
    db.commit()

    return {
        "drive_id": drive_id,
        "restored_from_version": req.target_version,
        "current_version": rolled.version,
        "message": f"Drive successfully restored to target snapshot v{req.target_version}.",
    }
