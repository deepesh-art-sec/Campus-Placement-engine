"""
High-level placement scheduler facade with process-pool execution,
asynchronous dispatch, early clash detection, verification, and diff generation.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ProcessPoolExecutor

from backend.app.scheduler.clash_detector import detect_student_fixed_window_clashes
from backend.app.scheduler.infeasibility import InfeasibilityExplainer
from backend.app.scheduler.models import (
    ClashVerificationResult,
    ScheduleConfig,
    ScheduleDiff,
    ScheduledItem,
    SchedulerDrive,
    ScheduleResult,
    SchedulerRoom,
    StudentClashOption,
)
from backend.app.scheduler.rescheduler import IncrementalRescheduler
from backend.app.scheduler.solver import CpSatPlacementScheduler
from backend.app.scheduler.verifier import verify_schedule


def _solve_task(
    drives: list[SchedulerDrive],
    rooms: list[SchedulerRoom],
    config: ScheduleConfig,
) -> ScheduleResult:
    """Worker function for process pool execution."""
    scheduler = CpSatPlacementScheduler()
    return scheduler.solve(drives, rooms, config)


class PlacementSchedulerEngine:
    """Enterprise scheduling engine managing CP-SAT optimization and process isolation."""

    def __init__(self) -> None:
        self.solver = CpSatPlacementScheduler()
        self.rescheduler = IncrementalRescheduler(self.solver)
        self.explainer = InfeasibilityExplainer()

    def generate_schedule(
        self,
        drives: list[SchedulerDrive],
        rooms: list[SchedulerRoom],
        config: ScheduleConfig | None = None,
        existing_slots: list[dict[str, Any]] | None = None,
    ) -> ScheduleResult:
        """Synchronous clash-free schedule generation."""
        cfg = config or ScheduleConfig()
        return self.solver.solve(drives, rooms, cfg, existing_slots=existing_slots)

    async def generate_schedule_async(
        self,
        drives: list[SchedulerDrive],
        rooms: list[SchedulerRoom],
        config: ScheduleConfig | None = None,
    ) -> ScheduleResult:
        """Asynchronous schedule generation dispatched to background process pool."""
        cfg = config or ScheduleConfig()
        loop = asyncio.get_running_loop()

        with ProcessPoolExecutor(max_workers=1) as pool:
            result = await loop.run_in_executor(
                pool, _solve_task, drives, rooms, cfg
            )
        return result

    def reschedule(
        self,
        previous_schedule: ScheduleResult,
        drives: list[SchedulerDrive],
        rooms: list[SchedulerRoom],
        config: ScheduleConfig | None = None,
    ) -> tuple[ScheduleResult, ScheduleDiff]:
        """Performs incremental re-scheduling with minimal disturbance."""
        return self.rescheduler.reschedule(previous_schedule, drives, rooms, config)

    def detect_early_clashes(
        self,
        drives: list[SchedulerDrive],
        student_name_map: dict[str, str] | None = None,
    ) -> list[StudentClashOption]:
        """Detects conflicting company windows before running the solver."""
        return detect_student_fixed_window_clashes(drives, student_name_map)

    def verify(
        self,
        items: list[ScheduledItem],
        rooms: list[SchedulerRoom],
        drives: list[SchedulerDrive] | None = None,
        config: ScheduleConfig | None = None,
    ) -> ClashVerificationResult:
        """Audits any schedule for physical and temporal integrity."""
        return verify_schedule(items, rooms, drives, config)
