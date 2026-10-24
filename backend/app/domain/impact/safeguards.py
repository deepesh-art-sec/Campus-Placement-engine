"""
Publish safeguards and versioning governance.
Blocks publication when unresolved reviews, clashes, or stale version locks occur.
Enforces optimistic concurrency, confirmation preview, and immutable audit logs.
"""

from __future__ import annotations

import datetime
import hashlib

from backend.app.domain.exceptions import StaleVersionError
from backend.app.domain.impact.models import (
    DriveVersionState,
    ImpactReport,
    PublishValidationResult,
)
from backend.app.domain.models import Drive, RequirementSet
from backend.app.events.event_service import EventService
from backend.app.scheduler.models import (
    ScheduledItem,
    SchedulerDrive,
    SchedulerRoom,
)
from backend.app.scheduler.verifier import verify_schedule
from backend.app.storage.repositories.interfaces import IUnitOfWork


class PublishSafeguards:
    """Safeguards preventing publication of flawed or stale recruitment schedules."""

    def validate_for_publish(
        self,
        drive_id: str,
        current_version: int,
        expected_base_version: int,
        unresolved_review_items: list[str],
        schedule_items: list[ScheduledItem],
        rooms: list[SchedulerRoom],
        drives: list[SchedulerDrive],
        impact_report: ImpactReport,
    ) -> PublishValidationResult:
        block_reasons: list[str] = []
        stale_version = False

        # 1. Optimistic Concurrency Check
        if expected_base_version != current_version:
            stale_version = True
            block_reasons.append(
                f"Stale version lock: current drive version is v{current_version}, but publish was requested "
                f"against v{expected_base_version}. Refresh required to prevent overwriting concurrent updates."
            )

        # 2. Unresolved Needs-Review Check
        if unresolved_review_items:
            block_reasons.append(
                f"{len(unresolved_review_items)} unresolved review queue items remain. "
                "All ambiguous requirements or missing student credentials must be confirmed by an officer."
            )

        # 3. Schedule Clash Check
        verification = verify_schedule(schedule_items, rooms, drives)
        if not verification.is_valid:
            block_reasons.append(
                f"Unresolved schedule clashes detected: {verification.clash_count} collisions "
                f"({len(verification.all_violations)} violations) must be resolved prior to publication."
            )

        can_publish = (len(block_reasons) == 0)

        return PublishValidationResult(
            can_publish=can_publish,
            block_reasons=block_reasons,
            unresolved_reviews=unresolved_review_items,
            unresolved_clashes=verification.all_violations,
            stale_version_detected=stale_version,
            requires_confirmation=True,
            impact_summary=impact_report.headline,
        )

    def commit_publish(
        self,
        uow: IUnitOfWork,
        drive: Drive,
        requirements: RequirementSet,
        shortlist_student_ids: list[str],
        schedule_items: list[ScheduledItem],
        expected_base_version: int,
        actor: str = "TPO_OFFICER",
        reason: str = "Published finalized drive requirements and schedule",
    ) -> DriveVersionState:
        """Publishes an immutable versioned snapshot and appends an audit event."""
        if drive.version != expected_base_version:
            raise StaleVersionError(
                f"Cannot publish: drive version has advanced to v{drive.version} (expected v{expected_base_version})."
            )

        new_version = drive.version + 1
        drive.version = new_version

        # Compute deterministic snapshot hash
        payload_repr = f"{drive.id}|v{new_version}|{len(shortlist_student_ids)}|{len(schedule_items)}"
        audit_hash = hashlib.sha256(payload_repr.encode("utf-8")).hexdigest()

        snapshot = DriveVersionState(
            drive_id=drive.id,
            version=new_version,
            is_published=True,
            published_at=datetime.datetime.utcnow(),
            published_by=actor,
            requirements=requirements,
            shortlist_student_ids=shortlist_student_ids,
            schedule_items=schedule_items,
            audit_hash=audit_hash,
        )

        # Record audit event via append-only event service
        EventService.record_change(
            uow=uow,
            aggregate_type="DRIVE_PUBLISH",
            aggregate_id=drive.id,
            event_type="DRIVE_VERSION_PUBLISHED",
            actor=actor,
            before_state={"version": expected_base_version, "is_published": False},
            after_state={
                "version": new_version,
                "is_published": True,
                "shortlist_count": len(shortlist_student_ids),
                "scheduled_slots_count": len(schedule_items),
                "audit_hash": audit_hash,
            },
            reason=reason,
        )

        return snapshot

    def rollback_to_version(
        self,
        uow: IUnitOfWork,
        drive: Drive,
        target_snapshot: DriveVersionState,
        actor: str = "TPO_OFFICER",
        reason: str = "Rolled back to previous version",
    ) -> DriveVersionState:
        """Rolls back drive state to a previously published snapshot."""
        old_version = drive.version
        drive.version += 1  # Version increments forward in event-sourcing

        drive.requirements = target_snapshot.requirements

        EventService.record_change(
            uow=uow,
            aggregate_type="DRIVE_ROLLBACK",
            aggregate_id=drive.id,
            event_type="DRIVE_VERSION_ROLLED_BACK",
            actor=actor,
            before_state={"version": old_version},
            after_state={"version": drive.version, "restored_from_version": target_snapshot.version},
            reason=f"Rollback to v{target_snapshot.version}: {reason}",
        )

        return target_snapshot.model_copy(update={"version": drive.version})
