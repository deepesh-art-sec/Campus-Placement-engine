"""
Sandbox IMATS Client Adapter with Exponential Backoff and Idempotency Protection.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from backend.app.integrations.imats.interface import IIMATSClient


class SandboxIMATSClient(IIMATSClient):
    """
    Mock & Sandbox IMATS ERP client.
    Supports transient failure simulation, exponential backoff, and strict idempotency key deduping.
    """

    def __init__(
        self,
        is_online: bool = True,
        initial_backoff_sec: float = 0.05,
        max_retries: int = 3,
    ) -> None:
        self.is_online = is_online
        self.initial_backoff_sec = initial_backoff_sec
        self.max_retries = max_retries

        self._idempotency_cache: dict[str, dict[str, Any]] = {}
        self.transient_failures_remaining: int = 0
        self.calls_attempted: int = 0
        self.stored_shortlists: dict[str, list[str]] = {}
        self.stored_schedules: dict[str, list[dict[str, Any]]] = {}

    def simulate_transient_failures(self, count: int) -> None:
        """Configures the client to fail the next N attempts before succeeding."""
        self.transient_failures_remaining = count

    def push_shortlist(
        self,
        drive_id: str,
        student_ids: list[str],
        idempotency_key: str,
    ) -> dict[str, Any]:
        """Pushes candidate shortlist to institutional tracking system."""
        if idempotency_key in self._idempotency_cache:
            return self._idempotency_cache[idempotency_key]

        def _action() -> dict[str, Any]:
            self.stored_shortlists[drive_id] = list(student_ids)
            return {
                "status": "acknowledged",
                "message": "Shortlist successfully indexed in IMATS ERP",
                "drive_id": drive_id,
                "candidates_count": len(student_ids),
                "idempotency_key": idempotency_key,
            }

        res = self._execute_with_retry(_action, idempotency_key)
        self._idempotency_cache[idempotency_key] = res
        return res

    def push_schedule(
        self,
        drive_id: str,
        schedule_items: list[dict[str, Any]],
        idempotency_key: str,
    ) -> dict[str, Any]:
        """Pushes finalized clash-free schedule slots to institutional tracking system."""
        if idempotency_key in self._idempotency_cache:
            return self._idempotency_cache[idempotency_key]

        def _action() -> dict[str, Any]:
            self.stored_schedules[drive_id] = list(schedule_items)
            return {
                "status": "acknowledged",
                "message": "Interview schedule successfully committed to IMATS ERP",
                "drive_id": drive_id,
                "slots_count": len(schedule_items),
                "idempotency_key": idempotency_key,
            }

        res = self._execute_with_retry(_action, idempotency_key)
        self._idempotency_cache[idempotency_key] = res
        return res

    def fetch_drive_requirements(
        self,
        company_id: str,
        drive_code: str,
    ) -> dict[str, Any]:
        """Fetches recruitment requirements directly from IMATS university registry."""
        if not self.is_online:
            raise ConnectionError("IMATS host unreachable: Network connection offline.")

        return {
            "company_id": company_id,
            "drive_code": drive_code,
            "min_cgpa": 7.0,
            "min_tenth_percentage": 65.0,
            "min_twelfth_percentage": 65.0,
            "allowed_branches": ["CSE", "IT", "ECE"],
            "max_active_backlogs": 0,
            "max_gap_years": 1,
            "fetched_from": "IMATS University Master API",
        }

    def _execute_with_retry(
        self,
        action: Callable[[], dict[str, Any]],
        idempotency_key: str,
    ) -> dict[str, Any]:
        """Executes action with exponential backoff on transient network faults."""
        attempt = 0
        while attempt < self.max_retries:
            self.calls_attempted += 1
            if not self.is_online:
                raise ConnectionError("IMATS client is operating in offline mode.")

            if self.transient_failures_remaining > 0:
                self.transient_failures_remaining -= 1
                attempt += 1
                sleep_sec = self.initial_backoff_sec * (2 ** (attempt - 1))
                time.sleep(sleep_sec)
                continue

            return action()

        raise ConnectionError(f"IMATS request failed after {self.max_retries} attempts (key: {idempotency_key}).")
