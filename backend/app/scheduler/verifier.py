"""
Independent, zero-dependency schedule clash verifier.
Validates student conflicts, room double-booking, panel concurrency,
capacity bounds, room transit buffers, and blackout windows.
"""

from __future__ import annotations

import collections
import datetime

from backend.app.scheduler.models import (
    ClashVerificationResult,
    ScheduleConfig,
    ScheduledItem,
    SchedulerDrive,
    SchedulerRoom,
)


def verify_schedule(
    items: list[ScheduledItem],
    rooms: list[SchedulerRoom],
    drives: list[SchedulerDrive] | None = None,
    config: ScheduleConfig | None = None,
) -> ClashVerificationResult:
    """
    Comprehensively audits a placement schedule for all physical and temporal constraints.
    Returns ClashVerificationResult with exact violation strings.
    """
    cfg = config or ScheduleConfig()
    room_map = {r.id: r for r in rooms}
    drive_map = {d.id: d for d in drives} if drives else {}

    student_clashes: list[str] = []
    room_clashes: list[str] = []
    panel_clashes: list[str] = []
    capacity_violations: list[str] = []
    buffer_violations: list[str] = []
    blackout_violations: list[str] = []
    all_violations: list[str] = []

    # -------------------------------------------------------------------------
    # 1. Student Clashes, Buffer, and Max Rounds
    # -------------------------------------------------------------------------
    student_sessions: dict[str, list[ScheduledItem]] = collections.defaultdict(list)
    for it in items:
        for sid in it.student_ids:
            student_sessions[sid].append(it)

    buffer_delta = datetime.timedelta(minutes=cfg.transition_buffer_minutes)

    for sid, sessions in student_sessions.items():
        # Sort by start time
        sorted_sessions = sorted(sessions, key=lambda s: s.start_time)

        # Check overlaps and buffers
        for i in range(len(sorted_sessions) - 1):
            s1 = sorted_sessions[i]
            s2 = sorted_sessions[i + 1]

            # Overlap check
            if s2.start_time < s1.end_time:
                msg = (
                    f"Student '{sid}' double-booked: '{s1.round_name}' ({s1.start_time.strftime('%H:%M')}-{s1.end_time.strftime('%H:%M')}) "
                    f"overlaps with '{s2.round_name}' ({s2.start_time.strftime('%H:%M')}-{s2.end_time.strftime('%H:%M')})"
                )
                student_clashes.append(msg)
                all_violations.append(msg)

            # Transition buffer check across different rooms
            elif s1.room_id != s2.room_id and s2.start_time < s1.end_time + buffer_delta:
                actual_gap = int((s2.start_time - s1.end_time).total_seconds() / 60)
                msg = (
                    f"Insufficient transition buffer for student '{sid}' between room '{s1.room_name}' and '{s2.room_name}': "
                    f"gap is {actual_gap}m (required {cfg.transition_buffer_minutes}m) at {s1.end_time.strftime('%H:%M')}"
                )
                buffer_violations.append(msg)
                all_violations.append(msg)

            # Round precedence check within same drive
            if s1.drive_id == s2.drive_id and s1.round_number > s2.round_number:
                msg = (
                    f"Round precedence inverted for student '{sid}' in drive '{s1.drive_id}': "
                    f"Round {s1.round_number} scheduled at {s1.start_time.strftime('%H:%M')} before Round {s2.round_number} at {s2.start_time.strftime('%H:%M')}"
                )
                student_clashes.append(msg)
                all_violations.append(msg)

        # Daily round limit check
        daily_counts: dict[datetime.date, int] = collections.defaultdict(int)
        for s in sessions:
            daily_counts[s.start_time.date()] += 1

        for dt, count in daily_counts.items():
            if count > cfg.max_rounds_per_student_per_day:
                msg = (
                    f"Student '{sid}' exceeds daily round limit on {dt.isoformat()}: "
                    f"{count} rounds scheduled (max allowed {cfg.max_rounds_per_student_per_day})"
                )
                student_clashes.append(msg)
                all_violations.append(msg)

    # -------------------------------------------------------------------------
    # 2. Room Clashes, Capacities, and Facility Matching
    # -------------------------------------------------------------------------
    room_sessions: dict[str, list[ScheduledItem]] = collections.defaultdict(list)
    for it in items:
        room_sessions[it.room_id].append(it)

    for rid, sessions in room_sessions.items():
        room = room_map.get(rid)
        room_name = room.name if room else rid
        sorted_sessions = sorted(sessions, key=lambda s: s.start_time)

        # Room overlap check
        for i in range(len(sorted_sessions) - 1):
            r1 = sorted_sessions[i]
            r2 = sorted_sessions[i + 1]
            if r2.start_time < r1.end_time:
                msg = (
                    f"Room '{room_name}' ({rid}) double-booked: session '{r1.round_name}' ({r1.start_time.strftime('%H:%M')}-{r1.end_time.strftime('%H:%M')}) "
                    f"overlaps with '{r2.round_name}' ({r2.start_time.strftime('%H:%M')}-{r2.end_time.strftime('%H:%M')})"
                )
                room_clashes.append(msg)
                all_violations.append(msg)

        # Room capacity & facility checks
        if room:
            for s in sessions:
                # Capacity
                if len(s.student_ids) > room.capacity:
                    msg = (
                        f"Room '{room_name}' capacity exceeded: scheduled {len(s.student_ids)} students "
                        f"for '{s.round_name}', room capacity is {room.capacity}"
                    )
                    capacity_violations.append(msg)
                    all_violations.append(msg)

                # Room blackouts
                for bw in room.blackout_windows:
                    if s.start_time < bw.end_time and bw.start_time < s.end_time:
                        msg = (
                            f"Room '{room_name}' booked during room blackout ({bw.start_time.strftime('%H:%M')}-{bw.end_time.strftime('%H:%M')}): "
                            f"session '{s.round_name}' at {s.start_time.strftime('%H:%M')}"
                        )
                        blackout_violations.append(msg)
                        all_violations.append(msg)

    # -------------------------------------------------------------------------
    # 3. Panel Clashes
    # -------------------------------------------------------------------------
    panel_sessions: dict[str, list[ScheduledItem]] = collections.defaultdict(list)
    for it in items:
        if it.panel_id:
            panel_sessions[it.panel_id].append(it)

    for pid, sessions in panel_sessions.items():
        sorted_sessions = sorted(sessions, key=lambda s: s.start_time)
        for i in range(len(sorted_sessions) - 1):
            p1 = sorted_sessions[i]
            p2 = sorted_sessions[i + 1]
            if p2.start_time < p1.end_time:
                panel_name = p1.panel_name or pid
                msg = (
                    f"Panel '{panel_name}' ({pid}) double-booked: interview ({p1.start_time.strftime('%H:%M')}-{p1.end_time.strftime('%H:%M')}) "
                    f"overlaps with interview ({p2.start_time.strftime('%H:%M')}-{p2.end_time.strftime('%H:%M')})"
                )
                panel_clashes.append(msg)
                all_violations.append(msg)

    # -------------------------------------------------------------------------
    # 4. Lunch Blackout Window Checks
    # -------------------------------------------------------------------------
    for it in items:
        # Check if item overlaps lunch window on its scheduled day
        item_date = it.start_time.date()
        lunch_start = datetime.datetime.combine(item_date, datetime.time(cfg.lunch_start_hour, 0))
        lunch_end = lunch_start + datetime.timedelta(minutes=cfg.lunch_duration_minutes)

        if it.start_time < lunch_end and lunch_start < it.end_time:
            msg = (
                f"Session '{it.round_name}' scheduled during lunch blackout ({lunch_start.strftime('%H:%M')}-{lunch_end.strftime('%H:%M')}): "
                f"{it.start_time.strftime('%H:%M')}-{it.end_time.strftime('%H:%M')}"
            )
            blackout_violations.append(msg)
            all_violations.append(msg)

    # -------------------------------------------------------------------------
    # 5. Fixed Company Window Checks
    # -------------------------------------------------------------------------
    if drive_map:
        for it in items:
            drive = drive_map.get(it.drive_id)
            if drive and drive.fixed_window:
                fw = drive.fixed_window
                if it.start_time < fw.start_time or it.end_time > fw.end_time:
                    msg = (
                        f"Session '{it.round_name}' of drive '{drive.company_name}' scheduled outside fixed window "
                        f"({fw.start_time.strftime('%H:%M')}-{fw.end_time.strftime('%H:%M')}): "
                        f"{it.start_time.strftime('%H:%M')}-{it.end_time.strftime('%H:%M')}"
                    )
                    all_violations.append(msg)

    total_clashes = len(student_clashes) + len(room_clashes) + len(panel_clashes)
    is_valid = len(all_violations) == 0

    return ClashVerificationResult(
        is_valid=is_valid,
        clash_count=total_clashes,
        student_clashes=student_clashes,
        room_clashes=room_clashes,
        panel_clashes=panel_clashes,
        capacity_violations=capacity_violations,
        buffer_violations=buffer_violations,
        blackout_violations=blackout_violations,
        all_violations=all_violations,
    )
