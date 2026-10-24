"""
Data Models for IMATS Integration and Offline Outbox.
"""

from __future__ import annotations

import datetime
import uuid
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OutboxStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class OutboxEntry(BaseModel):
    """Encapsulates a queued outbound transmission for reliable offline delivery."""
    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    endpoint: str  # "push_shortlist" | "push_schedule"
    payload: dict[str, Any]
    idempotency_key: str
    status: OutboxStatus = OutboxStatus.PENDING
    attempts: int = 0
    max_retries: int = 5
    last_error: str | None = None
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    sent_at: datetime.datetime | None = None
