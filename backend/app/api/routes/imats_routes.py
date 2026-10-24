"""
IMATS ERP Integration and Offline Outbox Routes.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.app.api.auth.dependencies import require_officer_or_coordinator
from backend.app.integrations.imats.client import SandboxIMATSClient
from backend.app.integrations.imats.models import OutboxStatus
from backend.app.integrations.imats.outbox import imats_outbox_manager
from backend.app.storage.models.entities import UserModel

router = APIRouter(prefix="/api/imats", tags=["IMATS Integration"])

# Default sandbox client
imats_client = SandboxIMATSClient(is_online=True)


class PushShortlistRequest(BaseModel):
    drive_id: str
    student_ids: list[str]
    idempotency_key: str | None = None
    force_offline_outbox: bool = False


class PushScheduleRequest(BaseModel):
    drive_id: str
    schedule_items: list[dict[str, Any]]
    idempotency_key: str | None = None
    force_offline_outbox: bool = False


@router.post("/push-shortlist")
def push_shortlist_to_imats(
    req: PushShortlistRequest,
    current_user: UserModel = Depends(require_officer_or_coordinator),
) -> dict[str, Any]:
    """Pushes shortlist to external IMATS ERP, or queues in offline outbox if unreachable."""
    key = req.idempotency_key or f"shortlist_{req.drive_id}_{uuid.uuid4().hex[:8]}"

    if req.force_offline_outbox or not imats_client.is_online:
        entry = imats_outbox_manager.queue_shortlist(req.drive_id, req.student_ids, key)
        return {
            "status": "queued",
            "message": "IMATS ERP unreachable or queued in offline outbox. Will push when online.",
            "outbox_id": entry.id,
            "idempotency_key": key,
        }

    try:
        res = imats_client.push_shortlist(req.drive_id, req.student_ids, key)
        return res
    except Exception as exc:
        entry = imats_outbox_manager.queue_shortlist(req.drive_id, req.student_ids, key)
        return {
            "status": "queued",
            "message": f"Connection interrupted ({exc}). Saved to offline outbox for auto-sync.",
            "outbox_id": entry.id,
            "idempotency_key": key,
        }


@router.post("/push-schedule")
def push_schedule_to_imats(
    req: PushScheduleRequest,
    current_user: UserModel = Depends(require_officer_or_coordinator),
) -> dict[str, Any]:
    """Pushes schedule slots to external IMATS ERP, or queues in offline outbox if unreachable."""
    key = req.idempotency_key or f"sched_{req.drive_id}_{uuid.uuid4().hex[:8]}"

    if req.force_offline_outbox or not imats_client.is_online:
        entry = imats_outbox_manager.queue_schedule(req.drive_id, req.schedule_items, key)
        return {
            "status": "queued",
            "message": "Queued in offline outbox. Will synchronize when online.",
            "outbox_id": entry.id,
            "idempotency_key": key,
        }

    try:
        res = imats_client.push_schedule(req.drive_id, req.schedule_items, key)
        return res
    except Exception as exc:
        entry = imats_outbox_manager.queue_schedule(req.drive_id, req.schedule_items, key)
        return {
            "status": "queued",
            "message": f"Network transmission error ({exc}). Enqueued in offline outbox.",
            "outbox_id": entry.id,
            "idempotency_key": key,
        }


@router.get("/outbox")
def list_outbox_entries(
    status_filter: OutboxStatus | None = None,
    current_user: UserModel = Depends(require_officer_or_coordinator),
) -> list[dict[str, Any]]:
    """Inspects pending and processed offline outbox transmissions."""
    entries = imats_outbox_manager.list_entries(status=status_filter)
    return [e.model_dump() for e in entries]


@router.post("/sync")
def flush_outbox_transmissions(
    current_user: UserModel = Depends(require_officer_or_coordinator),
) -> dict[str, Any]:
    """Flushes queued offline transmissions to the IMATS server."""
    stats = imats_outbox_manager.flush(imats_client)
    return {
        "message": "Outbox flush completed.",
        "processed_count": stats["processed"],
        "sent_count": stats["sent"],
        "failed_count": stats["failed"],
    }
