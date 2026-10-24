"""
Event Sourcing and Audit Trail Engine.
Records immutable append-only events for all business state transitions.
Enables full historical reconstruction and explanation replay.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from backend.app.domain.models import Event
from backend.app.storage.repositories.interfaces import IUnitOfWork


class EventType:
    STUDENT_CREATED = "STUDENT_CREATED"
    STUDENT_UPDATED = "STUDENT_UPDATED"
    STUDENT_DELETED = "STUDENT_DELETED"
    COMPANY_CREATED = "COMPANY_CREATED"
    DRIVE_CREATED = "DRIVE_CREATED"
    REQUIREMENT_RULE_REVISED = "REQUIREMENT_RULE_REVISED"
    POLICY_CREATED = "POLICY_CREATED"
    POLICY_REVISED = "POLICY_REVISED"
    ELIGIBILITY_RUN_COMPLETED = "ELIGIBILITY_RUN_COMPLETED"
    ELIGIBILITY_OVERRIDE_APPLIED = "ELIGIBILITY_OVERRIDE_APPLIED"
    SCHEDULE_GENERATED = "SCHEDULE_GENERATED"
    SCHEDULE_MODIFIED = "SCHEDULE_MODIFIED"


def calculate_diff(before: dict[str, Any] | None, after: dict[str, Any] | None) -> dict[str, Any]:
    """Calculates field-by-field differences between before and after states."""
    if before is None and after is None:
        return {}
    if before is None:
        return {"created": after}
    if after is None:
        return {"deleted": before}

    changes: dict[str, Any] = {}
    all_keys = set(before.keys()).union(set(after.keys()))

    for key in all_keys:
        val_before = before.get(key)
        val_after = after.get(key)
        if val_before != val_after:
            changes[key] = {
                "before": val_before,
                "after": val_after,
            }

    return changes


class EventService:
    """Manages append-only event logging, aggregate timeline retrieval, and replay."""

    @staticmethod
    def record_change(
        uow: IUnitOfWork,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        actor: str,
        before_state: dict[str, Any] | None = None,
        after_state: dict[str, Any] | None = None,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> Event:
        diff = calculate_diff(before_state, after_state)
        payload = {
            "before": before_state,
            "after": after_state,
            "diff": diff,
            "reason": reason,
            "metadata": metadata or {},
        }

        event = Event(
            id=str(uuid.uuid4()),
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            actor=actor,
            timestamp=timestamp or datetime.utcnow(),
            payload=payload,
        )

        uow.events.append(event)
        return event

    @staticmethod
    def get_timeline(uow: IUnitOfWork, aggregate_type: str, aggregate_id: str) -> list[Event]:
        """Returns the chronological history of an aggregate."""
        return uow.events.get_events_for_aggregate(aggregate_type, aggregate_id)

    @staticmethod
    def replay_state_at(
        uow: IUnitOfWork,
        aggregate_type: str,
        aggregate_id: str,
        target_timestamp: datetime,
    ) -> dict[str, Any] | None:
        """
        Reconstructs the aggregate's exact historical state as of `target_timestamp`
        by replaying events forward from inception.
        """
        timeline = uow.events.get_events_for_aggregate(aggregate_type, aggregate_id)
        if not timeline:
            return None

        state: dict[str, Any] = {}
        found_any = False

        for event in timeline:
            if event.timestamp > target_timestamp:
                break
            found_any = True
            payload = event.payload
            # If full snapshot is available in after
            if payload.get("after") is not None:
                state = dict(payload["after"])
            elif "diff" in payload:
                # Apply incremental diff
                for field, change in payload["diff"].items():
                    if isinstance(change, dict) and "after" in change:
                        state[field] = change["after"]

        return state if found_any else None
