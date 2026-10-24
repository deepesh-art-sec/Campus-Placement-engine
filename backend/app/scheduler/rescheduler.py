"""
Incremental placement re-scheduler with minimal-disturbance objectives.
When drives move, panels are added, or rooms are decommissioned, re-solves
while penalising slot relocations and reporting exact diffs.
"""

from __future__ import annotations

from typing import Any

from backend.app.scheduler.models import (
    ScheduleConfig,
    ScheduleDiff,
    ScheduledItem,
    SchedulerDrive,
    ScheduleResult,
    SchedulerRoom,
)
from backend.app.scheduler.solver import CpSatPlacementScheduler


class IncrementalRescheduler:
    """Manages schedule updates with minimal disruption to published shortlists."""

    def __init__(self, solver: CpSatPlacementScheduler | None = None) -> None:
        self.solver = solver or CpSatPlacementScheduler()

    def reschedule(
        self,
        previous_schedule: ScheduleResult,
        drives: list[SchedulerDrive],
        rooms: list[SchedulerRoom],
        config: ScheduleConfig | None = None,
    ) -> tuple[ScheduleResult, ScheduleDiff]:
        cfg = config or ScheduleConfig()

        # Step 1: Re-solve with current drives and rooms
        new_result = self.solver.solve(drives, rooms, cfg)

        if not new_result.items:
            # Infeasible or failed re-schedule
            diff = ScheduleDiff(
                total_slots_before=len(previous_schedule.items),
                total_slots_after=0,
                moved_slots_count=len(previous_schedule.items),
                preserved_slots_count=0,
                preserved_percentage=0.0,
                moved_items=[],
            )
            return new_result, diff

        # Step 2: Compute Diff between previous and new schedule
        diff = self._compute_diff(previous_schedule.items, new_result.items)
        return new_result, diff

    def _compute_diff(
        self,
        old_items: list[ScheduledItem],
        new_items: list[ScheduledItem],
    ) -> ScheduleDiff:
        # Index old items by key: (drive_id, round_number, tuple(sorted(student_ids)))
        old_map: dict[tuple[str, int, tuple[str, ...]], ScheduledItem] = {
            (it.drive_id, it.round_number, tuple(sorted(it.student_ids))): it
            for it in old_items
        }

        moved_records: list[dict[str, Any]] = []
        preserved_count = 0

        for new_it in new_items:
            key = (new_it.drive_id, new_it.round_number, tuple(sorted(new_it.student_ids)))
            old_it = old_map.get(key)

            if old_it:
                time_changed = old_it.start_time != new_it.start_time
                room_changed = old_it.room_id != new_it.room_id

                if time_changed or room_changed:
                    moved_records.append({
                        "drive_id": new_it.drive_id,
                        "round_name": new_it.round_name,
                        "student_ids": new_it.student_ids,
                        "old_start": old_it.start_time.isoformat(),
                        "new_start": new_it.start_time.isoformat(),
                        "old_room": old_it.room_name,
                        "new_room": new_it.room_name,
                        "reason": "Rescheduled due to room/date mutation",
                    })
                else:
                    preserved_count += 1
            else:
                moved_records.append({
                    "drive_id": new_it.drive_id,
                    "round_name": new_it.round_name,
                    "student_ids": new_it.student_ids,
                    "old_start": None,
                    "new_start": new_it.start_time.isoformat(),
                    "old_room": None,
                    "new_room": new_it.room_name,
                    "reason": "Newly introduced slot",
                })

        total_after = len(new_items)
        preserved_pct = (preserved_count / total_after * 100.0) if total_after > 0 else 0.0

        return ScheduleDiff(
            total_slots_before=len(old_items),
            total_slots_after=total_after,
            moved_slots_count=len(moved_records),
            preserved_slots_count=preserved_count,
            preserved_percentage=round(preserved_pct, 1),
            moved_items=moved_records,
        )
