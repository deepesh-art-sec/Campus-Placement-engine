"""
Event-Driven Live Offer Policy Enforcement Engine.
Calculates immediate downstream impacts of offer changes:
  - newly blocked drives
  - newly unblocked drives
  - clashes and conflicts with published shortlists and room schedules.
"""

from __future__ import annotations

import copy
import uuid
from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from backend.app.domain.models import (
    Drive,
    OfferRecord,
    OfferSource,
    OfferStatus,
    Slot,
    Student,
)
from backend.app.domain.policy.checker import policy_check
from backend.app.domain.policy.models import CollegeOfferPolicy, PolicyCheckStatus


class OfferLifecycleEventType(StrEnum):
    SHORTLISTED = "shortlisted"
    SELECTED = "selected"
    OFFERED = "offered"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    REVOKED = "revoked"


class OfferLifecycleEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: str
    student_id: str
    company: str
    ctc_lpa: float = Field(ge=0.0)
    fixed_pay_lpa: float | None = Field(default=None, ge=0.0)
    offer_date: date
    event_type: OfferLifecycleEventType
    source: OfferSource = OfferSource.ON_CAMPUS
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PublishedConflict(BaseModel):
    model_config = ConfigDict(frozen=True)

    drive_id: str
    company_name: str
    drive_date: date
    slot_id: str | None = None
    round_number: int | None = None
    room_id: str | None = None
    scheduled_start_time: datetime | None = None
    scheduled_end_time: datetime | None = None
    conflict_reason: str


class PolicyChangeSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    student_id: str
    student_roll_no: str
    event_id: str
    event_type: OfferLifecycleEventType
    policy_id: str
    policy_version: int
    newly_blocked_drives: list[str] = Field(default_factory=list)
    newly_unblocked_drives: list[str] = Field(default_factory=list)
    published_schedule_conflicts: list[PublishedConflict] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class LiveOfferEnforcementEngine:
    """Manages real-time policy enforcement and conflict detection."""

    @staticmethod
    def apply_event(
        student: Student,
        event: OfferLifecycleEvent,
        upcoming_drives: list[Drive],
        published_slots: list[Slot],
        policy: CollegeOfferPolicy,
        as_of: date | None = None,
    ) -> tuple[Student, PolicyChangeSet]:
        """
        Applies an offer lifecycle event to a student, recomputes policy checks across
        all upcoming drives, and detects any conflicts with published schedules.
        Returns the updated student domain object and the computed PolicyChangeSet.
        """
        ref_date = as_of or date.today()

        # 1. Capture baseline policy check status before event
        baseline_status: dict[str, PolicyCheckStatus] = {}
        for d in upcoming_drives:
            baseline_status[d.id] = policy_check(student, d, policy, ref_date).status

        # 2. Mutate student offers according to event type
        updated_student = copy.deepcopy(student)
        existing_offer_idx = None
        for idx, o in enumerate(updated_student.existing_offers):
            if o.company.lower() == event.company.lower():
                existing_offer_idx = idx
                break

        if event.event_type in (OfferLifecycleEventType.OFFERED, OfferLifecycleEventType.ACCEPTED, OfferLifecycleEventType.SELECTED):
            st = OfferStatus.ACCEPTED if event.event_type == OfferLifecycleEventType.ACCEPTED else OfferStatus.OFFERED
            new_record = OfferRecord(
                id=str(uuid.uuid4()),
                company=event.company,
                ctc_lpa=event.ctc_lpa,
                fixed_pay_lpa=event.fixed_pay_lpa,
                offer_date=event.offer_date,
                source=event.source,
                is_dream=(event.ctc_lpa >= policy.dream_threshold_lpa),
                status=st,
            )
            if existing_offer_idx is not None:
                updated_student.existing_offers[existing_offer_idx] = new_record
            else:
                updated_student.existing_offers.append(new_record)

        elif event.event_type == OfferLifecycleEventType.DECLINED:
            if existing_offer_idx is not None:
                curr = updated_student.existing_offers[existing_offer_idx]
                updated_student.existing_offers[existing_offer_idx] = OfferRecord(
                    id=curr.id,
                    company=curr.company,
                    ctc_lpa=curr.ctc_lpa,
                    fixed_pay_lpa=curr.fixed_pay_lpa,
                    offer_date=curr.offer_date,
                    source=curr.source,
                    is_dream=curr.is_dream,
                    status=OfferStatus.REJECTED,
                )

        elif event.event_type == OfferLifecycleEventType.REVOKED:
            if existing_offer_idx is not None:
                curr = updated_student.existing_offers[existing_offer_idx]
                updated_student.existing_offers[existing_offer_idx] = OfferRecord(
                    id=curr.id,
                    company=curr.company,
                    ctc_lpa=curr.ctc_lpa,
                    fixed_pay_lpa=curr.fixed_pay_lpa,
                    offer_date=curr.offer_date,
                    source=curr.source,
                    is_dream=curr.is_dream,
                    status=OfferStatus.REVOKED,
                )

        # 3. Recompute policy checks after event
        newly_blocked: list[str] = []
        newly_unblocked: list[str] = []
        conflicts: list[PublishedConflict] = []

        for d in upcoming_drives:
            before_st = baseline_status.get(d.id, PolicyCheckStatus.ALLOWED)
            res_after = policy_check(updated_student, d, policy, ref_date)

            if before_st == PolicyCheckStatus.ALLOWED and res_after.status == PolicyCheckStatus.BLOCKED:
                newly_blocked.append(d.id)

                # Check if student is scheduled in published slots for this newly blocked drive
                for slot in published_slots:
                    if slot.student_id == student.id and slot.drive_id == d.id:
                        conflicts.append(
                            PublishedConflict(
                                drive_id=d.id,
                                company_name=d.company_name,
                                drive_date=d.drive_date,
                                slot_id=slot.id,
                                round_number=slot.round_number,
                                room_id=slot.room_id,
                                scheduled_start_time=slot.start_time,
                                scheduled_end_time=slot.end_time,
                                conflict_reason=(
                                    f"Student secured an offer from {event.company} ({event.ctc_lpa:.1f} LPA) and is now BLOCKED "
                                    f"under {res_after.clause_id}, but holds an active interview/test slot for {d.company_name} in Room {slot.room_id} "
                                    f"at {slot.start_time.strftime('%H:%M')}!"
                                ),
                            )
                        )

            elif before_st == PolicyCheckStatus.BLOCKED and res_after.status == PolicyCheckStatus.ALLOWED:
                newly_unblocked.append(d.id)

        changeset = PolicyChangeSet(
            student_id=student.id,
            student_roll_no=student.roll_no,
            event_id=event.event_id,
            event_type=event.event_type,
            policy_id=policy.id,
            policy_version=policy.version,
            newly_blocked_drives=newly_blocked,
            newly_unblocked_drives=newly_unblocked,
            published_schedule_conflicts=conflicts,
        )

        return updated_student, changeset
