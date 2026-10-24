"""
IMATS (Institutional Management & Academic Tracking System) Port Interface.
Decouples placement scheduling from external enterprise college ERPs.
"""

from __future__ import annotations

from typing import Any, Protocol


class IIMATSClient(Protocol):
    """Port interface for academic tracking system integrations."""

    def push_shortlist(
        self,
        drive_id: str,
        student_ids: list[str],
        idempotency_key: str,
    ) -> dict[str, Any]: ...

    def push_schedule(
        self,
        drive_id: str,
        schedule_items: list[dict[str, Any]],
        idempotency_key: str,
    ) -> dict[str, Any]: ...

    def fetch_drive_requirements(
        self,
        company_id: str,
        drive_code: str,
    ) -> dict[str, Any]: ...
