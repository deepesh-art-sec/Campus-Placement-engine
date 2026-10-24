"""
Infeasibility diagnosis and explanation generator for placement scheduling.
Performs conflict-graph, capacity, and panel bottleneck analysis to produce
precise, actionable explanations instead of generic failure messages.
"""

from __future__ import annotations

import collections
import datetime
import math

from backend.app.scheduler.models import (
    ScheduleConfig,
    SchedulerDrive,
    SchedulerRoom,
)


class InfeasibilityExplainer:
    """Diagnoses why a placement schedule cannot be solved without clashes."""

    def explain(
        self,
        drives: list[SchedulerDrive],
        rooms: list[SchedulerRoom],
        config: ScheduleConfig,
    ) -> str:
        """Analyzes bottlenecks and returns a specific, human-readable diagnosis."""
        reasons: list[str] = []

        day_hours = config.day_end_hour - config.day_start_hour
        lunch_hours = config.lunch_duration_minutes / 60.0
        effective_hours_per_day = max(0.0, day_hours - lunch_hours)

        # ---------------------------------------------------------------------
        # 1. Fixed Window Duration Check
        # ---------------------------------------------------------------------
        for d in drives:
            if d.fixed_window:
                win_mins = d.fixed_window.duration_minutes()
                total_round_mins = sum(r.duration_minutes for r in d.rounds)
                if win_mins < total_round_mins:
                    reasons.append(
                        f"Fixed company window for '{d.company_name}' ({win_mins} mins) is shorter than "
                        f"its total round sequence duration ({total_round_mins} mins). Expand the fixed window."
                    )

        # ---------------------------------------------------------------------
        # 2. Panel Interview Throughput Bottleneck
        # ---------------------------------------------------------------------
        for d in drives:
            for r in d.rounds:
                if not r.is_group_round and r.panels:
                    total_student_interviews = len(d.shortlisted_student_ids)
                    total_needed_mins = total_student_interviews * r.duration_minutes
                    available_mins_per_panel = effective_hours_per_day * 60.0
                    total_panel_capacity_mins = len(r.panels) * available_mins_per_panel

                    if total_needed_mins > total_panel_capacity_mins:
                        panels_needed = math.ceil(total_needed_mins / available_mins_per_panel)
                        reasons.append(
                            f"Panel bottleneck for '{d.company_name}' (Round {r.round_number}: {r.name}): "
                            f"{total_student_interviews} shortlisted candidates require {total_needed_mins} interview mins, "
                            f"but {len(r.panels)} panel(s) provide only {int(total_panel_capacity_mins)} mins. "
                            f"Add at least {panels_needed - len(r.panels)} panel(s) or extend the drive schedule."
                        )

        # ---------------------------------------------------------------------
        # 3. Room Capacity Bottleneck per Day
        # ---------------------------------------------------------------------
        drives_by_date: dict[datetime.date, list[SchedulerDrive]] = collections.defaultdict(list)
        for d in drives:
            drives_by_date[d.drive_date].append(d)

        active_rooms = [rm for rm in rooms if rm.is_active]
        total_seat_capacity = sum(rm.capacity for rm in active_rooms)
        total_computer_seats = sum(rm.capacity for rm in active_rooms if rm.has_computers)

        for dt, day_drives in drives_by_date.items():
            # Calculate total student-hours required for group tests on date dt
            group_seat_hours_needed = 0.0
            computer_seats_needed = 0

            for d in day_drives:
                for r in d.rounds:
                    if r.is_group_round:
                        hrs = r.duration_minutes / 60.0
                        group_seat_hours_needed += len(d.shortlisted_student_ids) * hrs
                        if r.requires_computers:
                            computer_seats_needed += len(d.shortlisted_student_ids)

            available_seat_hours = total_seat_capacity * effective_hours_per_day
            if group_seat_hours_needed > available_seat_hours:
                reasons.append(
                    f"Testing room shortage on {dt.isoformat()}: {group_seat_hours_needed:.1f} student-hours required "
                    f"across {len(day_drives)} drives, but campus rooms provide only {available_seat_hours:.1f} student-hours. "
                    f"Add rooms or stagger drives across multiple days."
                )

            if computer_seats_needed > (total_computer_seats * (effective_hours_per_day / 2.0)):
                reasons.append(
                    f"Computer lab deficit on {dt.isoformat()}: {computer_seats_needed} candidates require computer labs, "
                    f"exceeding available computer seats ({total_computer_seats}). Add computer labs or stagger test shifts."
                )

        # ---------------------------------------------------------------------
        # 4. Student Conflict Graph Overlap Bottleneck
        # ---------------------------------------------------------------------
        for i in range(len(drives)):
            for j in range(i + 1, len(drives)):
                d1 = drives[i]
                d2 = drives[j]

                # Check if on same date
                if d1.drive_date == d2.drive_date:
                    common_students = set(d1.shortlisted_student_ids) & set(d2.shortlisted_student_ids)
                    if common_students:
                        # Total hours needed for common students
                        d1_hours = sum(r.duration_minutes for r in d1.rounds) / 60.0
                        d2_hours = sum(r.duration_minutes for r in d2.rounds) / 60.0

                        if (d1_hours + d2_hours) > effective_hours_per_day:
                            reasons.append(
                                f"Drive '{d1.company_name}' and Drive '{d2.company_name}' share {len(common_students)} "
                                f"shortlisted students on {d1.drive_date.isoformat()}, requiring {d1_hours + d2_hours:.1f}h "
                                f"exceeding the {effective_hours_per_day:.1f}h placement window. "
                                f"Move one drive to another day or split into morning/afternoon batches."
                            )

        if not reasons:
            return (
                "Schedule constraints over-constrained: insufficient non-overlapping room/panel intervals "
                "to accommodate all student transit buffers and round precedence simultaneously. "
                "Consider increasing time horizon or adding interview panels."
            )

        return "; ".join(reasons)
