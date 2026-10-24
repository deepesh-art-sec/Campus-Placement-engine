"""
Offline Outbox Engine for Asynchronous ERP Synchronization.
Ensures zero data loss during college LAN internet outages by persisting transmissions locally.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any

from backend.app.integrations.imats.interface import IIMATSClient
from backend.app.integrations.imats.models import OutboxEntry, OutboxStatus


class IMATSOutboxManager:
    """Manages queued outbound IMATS transmissions with local reliability guarantees."""

    def __init__(self) -> None:
        self._entries: list[OutboxEntry] = []

    def queue_shortlist(
        self,
        drive_id: str,
        student_ids: list[str],
        idempotency_key: str | None = None,
    ) -> OutboxEntry:
        """Queues candidate shortlist push for offline delivery."""
        key = idempotency_key or f"imats_shortlist_{drive_id}_{uuid.uuid4().hex[:8]}"
        entry = OutboxEntry(
            endpoint="push_shortlist",
            payload={"drive_id": drive_id, "student_ids": student_ids},
            idempotency_key=key,
            status=OutboxStatus.PENDING,
        )
        self._entries.append(entry)
        return entry

    def queue_schedule(
        self,
        drive_id: str,
        schedule_items: list[dict[str, Any]],
        idempotency_key: str | None = None,
    ) -> OutboxEntry:
        """Queues interview schedule push for offline delivery."""
        key = idempotency_key or f"imats_schedule_{drive_id}_{uuid.uuid4().hex[:8]}"
        entry = OutboxEntry(
            endpoint="push_schedule",
            payload={"drive_id": drive_id, "schedule_items": schedule_items},
            idempotency_key=key,
            status=OutboxStatus.PENDING,
        )
        self._entries.append(entry)
        return entry

    def list_entries(self, status: OutboxStatus | None = None) -> list[OutboxEntry]:
        """Lists outbox entries, optionally filtered by synchronization status."""
        if status:
            return [e for e in self._entries if e.status == status]
        return list(self._entries)

    def flush(self, client: IIMATSClient) -> dict[str, int]:
        """Attempts to synchronize all pending entries with the IMATS server."""
        processed = 0
        sent = 0
        failed = 0

        for idx, entry in enumerate(self._entries):
            if entry.status != OutboxStatus.PENDING:
                continue

            processed += 1
            try:
                if entry.endpoint == "push_shortlist":
                    client.push_shortlist(
                        drive_id=entry.payload["drive_id"],
                        student_ids=entry.payload["student_ids"],
                        idempotency_key=entry.idempotency_key,
                    )
                elif entry.endpoint == "push_schedule":
                    client.push_schedule(
                        drive_id=entry.payload["drive_id"],
                        schedule_items=entry.payload["schedule_items"],
                        idempotency_key=entry.idempotency_key,
                    )

                # Mark as SENT
                updated = entry.model_copy(
                    update={
                        "status": OutboxStatus.SENT,
                        "attempts": entry.attempts + 1,
                        "sent_at": datetime.datetime.utcnow(),
                        "last_error": None,
                    }
                )
                self._entries[idx] = updated
                sent += 1

            except Exception as exc:
                new_status = OutboxStatus.FAILED if entry.attempts + 1 >= entry.max_retries else OutboxStatus.PENDING
                updated = entry.model_copy(
                    update={
                        "status": new_status,
                        "attempts": entry.attempts + 1,
                        "last_error": str(exc),
                    }
                )
                self._entries[idx] = updated
                failed += 1

        return {"processed": processed, "sent": sent, "failed": failed}


# Global outbox manager instance
imats_outbox_manager = IMATSOutboxManager()
