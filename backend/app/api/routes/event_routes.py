"""
Recruitment Event Sourcing and Live Policy Enforcement Routes.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.auth.dependencies import get_uow, require_officer_or_coordinator
from backend.app.domain.models import Drive, OfferSource
from backend.app.domain.policy.catalog import STRICT_ONE_OFFER_POLICY
from backend.app.domain.policy.enforcement import (
    LiveOfferEnforcementEngine,
    OfferLifecycleEvent,
    OfferLifecycleEventType,
)
from backend.app.events.event_service import EventService
from backend.app.storage.database import get_db
from backend.app.storage.models.entities import (
    DriveModel,
    EventModel,
    OfferModel,
    StudentModel,
    UserModel,
)
from backend.app.storage.repositories.mappers import student_entity_to_domain
from backend.app.storage.repositories.sqlalchemy_repo import SqlAlchemyUnitOfWork

router = APIRouter(prefix="/api/events", tags=["Event Sourcing & Live Enforcement"])


class RecordResultRequest(BaseModel):
    student_id: str
    drive_id: str
    event_type: OfferLifecycleEventType
    ctc_lpa: float = Field(default=0.0, ge=0.0)
    fixed_pay_lpa: float | None = None
    offer_date: datetime.date = Field(default_factory=datetime.date.today)
    reason: str = "Recruitment round outcome recorded"


@router.post("/record-result")
def record_recruitment_result(
    req: RecordResultRequest,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
    uow: SqlAlchemyUnitOfWork = Depends(get_uow),
) -> dict[str, Any]:
    """
    Appends an offer lifecycle result event, recomputes policy status across
    all upcoming drives for that candidate, and flags schedule conflicts.
    """
    # 1. Fetch student and drive
    stmt_stu = select(StudentModel).where(
        (StudentModel.id == req.student_id) | (StudentModel.roll_no == req.student_id)
    )
    student_entity = db.execute(stmt_stu).scalar_one_or_none()
    if not student_entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

    stmt_drv = select(DriveModel).where(
        (DriveModel.id == req.drive_id) | (DriveModel.company_name == req.drive_id)
    )
    drive_entity = db.execute(stmt_drv).scalar_one_or_none()
    if not drive_entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drive not found.")

    student = student_entity_to_domain(student_entity)

    # 2. Construct offer event
    event_id = f"evt_{uuid.uuid4().hex[:10]}"
    lifecycle_event = OfferLifecycleEvent(
        event_id=event_id,
        student_id=student.id,
        company=drive_entity.company_name,
        ctc_lpa=req.ctc_lpa or drive_entity.ctc_lpa,
        fixed_pay_lpa=req.fixed_pay_lpa or getattr(drive_entity, "fixed_pay_lpa", None),
        offer_date=req.offer_date,
        event_type=req.event_type,
        source=OfferSource.ON_CAMPUS,
    )

    # 3. Upcoming drives
    all_drives = [
        Drive(
            id=d.id,
            company_id=d.company_id,
            company_name=d.company_name,
            drive_date=d.drive_date,
            ctc_lpa=d.ctc_lpa,
        )
        for d in db.execute(select(DriveModel)).scalars().all()
    ]

    # 4. Apply live enforcement
    updated_student, change_set = LiveOfferEnforcementEngine.apply_event(
        student=student,
        event=lifecycle_event,
        upcoming_drives=all_drives,
        published_slots=[],
        policy=STRICT_ONE_OFFER_POLICY,
    )

    # 5. Record to event sourcing log via UnitOfWork
    with uow:
        EventService.record_change(
            uow=uow,
            aggregate_type="STUDENT_OFFER",
            aggregate_id=student.id,
            event_type=f"OFFER_{req.event_type.value.upper()}",
            actor=current_user.username,
            before_state={"offers_count": len(student.existing_offers)},
            after_state={
                "offers_count": len(updated_student.existing_offers),
                "company": drive_entity.company_name,
                "ctc_lpa": lifecycle_event.ctc_lpa,
                "newly_blocked_count": len(change_set.newly_blocked_drives),
            },
            reason=req.reason,
        )
        uow.commit()

    # 6. Update student offers in DB if offered/accepted
    if req.event_type in (OfferLifecycleEventType.OFFERED, OfferLifecycleEventType.ACCEPTED):
        offer_entity = OfferModel(
            id=str(uuid.uuid4()),
            student_id=student.id,
            company=drive_entity.company_name,
            ctc_lpa=lifecycle_event.ctc_lpa,
            fixed_pay_lpa=lifecycle_event.fixed_pay_lpa,
            offer_date=req.offer_date,
            source="on_campus",
            is_dream=(lifecycle_event.ctc_lpa >= STRICT_ONE_OFFER_POLICY.dream_threshold_lpa),
            status="accepted" if req.event_type == OfferLifecycleEventType.ACCEPTED else "offered",
        )
        db.add(offer_entity)
        db.commit()

    return {
        "event_id": event_id,
        "student_id": student.id,
        "company_name": drive_entity.company_name,
        "event_type": req.event_type.value,
        "policy_changeset": change_set.model_dump(),
        "message": f"Recorded '{req.event_type.value}' for {student.name}. Newly blocked drives: {len(change_set.newly_blocked_drives)}.",
    }


@router.get("/timeline/{aggregate_type}/{aggregate_id}")
def get_timeline(
    aggregate_type: str,
    aggregate_id: str,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieves the append-only event sourcing timeline for any entity."""
    stmt = (
        select(EventModel)
        .where(
            EventModel.aggregate_type == aggregate_type,
            EventModel.aggregate_id == aggregate_id,
        )
        .order_by(EventModel.timestamp.asc())
    )
    events = db.execute(stmt).scalars().all()
    return [
        {
            "id": e.id,
            "aggregate_type": e.aggregate_type,
            "aggregate_id": e.aggregate_id,
            "event_type": e.event_type,
            "actor": e.actor,
            "timestamp": e.timestamp.isoformat(),
            "payload": e.payload_json,
        }
        for e in events
    ]
