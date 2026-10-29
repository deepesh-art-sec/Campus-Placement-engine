"""
CP-SAT constraint programming scheduler for campus recruitment drives.
Uses interval variables, NoOverlap constraints across rooms, panels, and students,
capacity bounds, fixed company windows, and soft optimization objectives.
"""

from __future__ import annotations

import collections
import datetime
import math
import sys
import uuid
from typing import Any

# Prevent Windows pyarrow DLL warning when ortools optionally probes pandas/pyarrow
if "pyarrow" not in sys.modules:
    sys.modules["pyarrow"] = None  # type: ignore[assignment]

from ortools.sat.python import cp_model

from backend.app.scheduler.heuristic import DSaturHeuristicScheduler
from backend.app.scheduler.infeasibility import InfeasibilityExplainer
from backend.app.scheduler.models import (
    RoomType,
    ScheduleConfig,
    ScheduledItem,
    SchedulerDrive,
    ScheduleResult,
    SchedulerPanel,
    SchedulerRoom,
    ScheduleStatus,
)
from backend.app.scheduler.verifier import verify_schedule


class CpSatPlacementScheduler:
    """Exact CP-SAT placement scheduling engine."""

    def __init__(self) -> None:
        self.explainer = InfeasibilityExplainer()
        self.heuristic = DSaturHeuristicScheduler()

    def solve(
        self,
        drives: list[SchedulerDrive],
        rooms: list[SchedulerRoom],
        config: ScheduleConfig | None = None,
        existing_slots: list[dict[str, Any]] | None = None,
    ) -> ScheduleResult:
        cfg = config or ScheduleConfig()
        start_clock = datetime.datetime.now()

        # If no drives or rooms, return empty feasible
        if not drives or not rooms:
            return ScheduleResult(
                schedule_id=str(uuid.uuid4()),
                status=ScheduleStatus.FEASIBLE,
                items=[],
                solver_time_seconds=0.0,
                solver_name="cp-sat",
                is_optimal=True,
            )

        active_rooms = [r for r in rooms if r.is_active]
        if not active_rooms:
            return ScheduleResult(
                schedule_id=str(uuid.uuid4()),
                status=ScheduleStatus.INFEASIBLE,
                items=[],
                solver_time_seconds=0.0,
                solver_name="cp-sat",
                infeasibility_explanation="No active campus rooms available for scheduling.",
            )

        model = cp_model.CpModel()

        # Map unique dates to indices
        all_dates = sorted({d.drive_date for d in drives})
        date_to_idx = {dt: i for i, dt in enumerate(all_dates)}

        slots_per_day = int((cfg.day_end_hour - cfg.day_start_hour) * 60 / cfg.slot_duration_minutes)
        buffer_slots = int(math.ceil(cfg.transition_buffer_minutes / cfg.slot_duration_minutes))

        # Lunch blackout slots
        lunch_slot_start = int((cfg.lunch_start_hour - cfg.day_start_hour) * 60 / cfg.slot_duration_minutes)
        lunch_slots_count = int(cfg.lunch_duration_minutes / cfg.slot_duration_minutes)
        lunch_slot_end = lunch_slot_start + lunch_slots_count

        max_room_cap = max(r.capacity for r in active_rooms)
        # Classrooms and cabins suitable for interview sessions
        cabins_classrooms = [
            r for r in active_rooms
            if r.capacity <= 60 or r.room_type in (RoomType.CABIN, RoomType.CLASSROOM)
        ]
        if not cabins_classrooms:
            cabins_classrooms = active_rooms

        # Track rooms already busy on this date to assign empty classrooms / cabins
        busy_rooms_on_date: set[str] = set()
        if existing_slots:
            for ext in existing_slots:
                st = ext.get("start_time")
                rid = ext.get("room_id")
                if isinstance(st, datetime.datetime) and rid:
                    busy_rooms_on_date.add(rid)

        # Prioritize unbooked empty classrooms and cabins
        unbooked_rooms = [rm for rm in cabins_classrooms if rm.id not in busy_rooms_on_date]
        booked_rooms = [rm for rm in cabins_classrooms if rm.id in busy_rooms_on_date]
        available_pool = unbooked_rooms + booked_rooms if unbooked_rooms else cabins_classrooms

        # ---------------------------------------------------------------------
        # Pre-assign rooms to interview panels per day
        # ---------------------------------------------------------------------
        drives_by_date: dict[datetime.date, list[SchedulerDrive]] = collections.defaultdict(list)
        for d in drives:
            drives_by_date[d.drive_date].append(d)

        # Panel to Room mapping
        panel_room_map: dict[str, SchedulerRoom] = {}
        allocated_rooms_this_run: set[str] = set()

        for _dt, day_drives in drives_by_date.items():
            used_room_indices = 0
            for d in day_drives:
                for r in d.rounds:
                    if not r.is_group_round:
                        for p in r.panels:
                            if (
                                p.preferred_room_id
                                and p.preferred_room_id not in busy_rooms_on_date
                                and p.preferred_room_id not in allocated_rooms_this_run
                            ):
                                matched = next((rm for rm in active_rooms if rm.id == p.preferred_room_id), None)
                                if matched:
                                    panel_room_map[p.id] = matched
                                    allocated_rooms_this_run.add(matched.id)
                                    continue
                            # Allocate an empty classroom / cabin for this panel
                            assigned_rm = available_pool[used_room_indices % len(available_pool)]
                            used_room_indices += 1
                            allocated_rooms_this_run.add(assigned_rm.id)
                            panel_room_map[p.id] = assigned_rm

        # ---------------------------------------------------------------------
        # Session Definition & CP Variables
        # ---------------------------------------------------------------------
        sessions: list[dict[str, Any]] = []
        room_intervals: dict[str, list[cp_model.IntervalVar]] = collections.defaultdict(list)
        panel_intervals: dict[str, list[cp_model.IntervalVar]] = collections.defaultdict(list)
        student_intervals: dict[str, list[cp_model.IntervalVar]] = collections.defaultdict(list)

        # Process existing busy slots to guarantee cross-drive clash avoidance
        if existing_slots:
            stu_busy_ranges: dict[str, list[tuple[int, int]]] = collections.defaultdict(list)
            rm_busy_ranges: dict[str, list[tuple[int, int]]] = collections.defaultdict(list)

            for ext in existing_slots:
                st = ext.get("start_time")
                et = ext.get("end_time")
                if not isinstance(st, datetime.datetime) or not isinstance(et, datetime.datetime):
                    continue
                ext_date = st.date()
                if ext_date not in date_to_idx:
                    continue

                d_idx = date_to_idx[ext_date]
                day_slot_offset = d_idx * slots_per_day
                day_start_dt = datetime.datetime.combine(ext_date, datetime.time(cfg.day_start_hour, 0))

                start_min = max(0, int((st - day_start_dt).total_seconds() / 60))
                end_min = min(slots_per_day * cfg.slot_duration_minutes, int((et - day_start_dt).total_seconds() / 60))
                if end_min <= start_min:
                    continue

                start_slot = day_slot_offset + (start_min // cfg.slot_duration_minutes)
                end_slot = day_slot_offset + math.ceil(end_min / cfg.slot_duration_minutes)

                sid = ext.get("student_id")
                if sid:
                    b_start = max(day_slot_offset, start_slot - buffer_slots)
                    b_end = min(day_slot_offset + slots_per_day, end_slot + buffer_slots)
                    stu_busy_ranges[sid].append((b_start, b_end))

                rid = ext.get("room_id")
                if rid:
                    rm_busy_ranges[rid].append((start_slot, end_slot))

            def merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
                if not intervals:
                    return []
                sorted_inv = sorted(intervals, key=lambda x: x[0])
                merged = [sorted_inv[0]]
                for cur_start, cur_end in sorted_inv[1:]:
                    last_start, last_end = merged[-1]
                    if cur_start <= last_end:
                        merged[-1] = (last_start, max(last_end, cur_end))
                    else:
                        merged.append((cur_start, cur_end))
                return merged

            ext_counter = 0
            for sid, ranges in stu_busy_ranges.items():
                for m_start, m_end in merge_intervals(ranges):
                    dur = m_end - m_start
                    if dur > 0:
                        fixed_iv = model.new_fixed_size_interval_var(m_start, dur, f"ext_busy_stu_{sid}_{ext_counter}")
                        student_intervals[sid].append(fixed_iv)
                        ext_counter += 1

            for rid, ranges in rm_busy_ranges.items():
                for m_start, m_end in merge_intervals(ranges):
                    dur = m_end - m_start
                    if dur > 0:
                        fixed_iv = model.new_fixed_size_interval_var(m_start, dur, f"ext_busy_rm_{rid}_{ext_counter}")
                        room_intervals[rid].append(fixed_iv)
                        ext_counter += 1

        session_counter = 0

        for d in drives:
            d_idx = date_to_idx[d.drive_date]
            day_slot_offset = d_idx * slots_per_day

            # Fixed company window in slots
            fixed_start_slot = 0
            fixed_end_slot = slots_per_day
            if d.fixed_window:
                win_start_min = max(0, int((d.fixed_window.start_time - datetime.datetime.combine(d.drive_date, datetime.time(cfg.day_start_hour, 0))).total_seconds() / 60))
                win_end_min = min(slots_per_day * cfg.slot_duration_minutes, int((d.fixed_window.end_time - datetime.datetime.combine(d.drive_date, datetime.time(cfg.day_start_hour, 0))).total_seconds() / 60))
                fixed_start_slot = win_start_min // cfg.slot_duration_minutes
                fixed_end_slot = math.ceil(win_end_min / cfg.slot_duration_minutes)

            prev_round_session_ends: list[Any] = []

            for r in d.rounds:
                dur_slots = max(1, math.ceil(r.duration_minutes / cfg.slot_duration_minutes))
                current_round_session_ends: list[Any] = []

                if r.is_group_round:
                    # Group Test / Assessment
                    batch_size = min(r.max_batch_size, max_room_cap)
                    all_sids = list(d.shortlisted_student_ids)
                    if not all_sids:
                        continue
                    num_batches = math.ceil(len(all_sids) / batch_size)

                    for b_idx in range(num_batches):
                        batch_sids = all_sids[b_idx * batch_size : (b_idx + 1) * batch_size]
                        sess_id = f"sess_{session_counter}"
                        session_counter += 1

                        start_var = model.new_int_var(
                            day_slot_offset + fixed_start_slot,
                            day_slot_offset + fixed_end_slot - dur_slots,
                            f"{sess_id}_start",
                        )
                        end_var = model.new_int_var(
                            day_slot_offset + fixed_start_slot + dur_slots,
                            day_slot_offset + fixed_end_slot,
                            f"{sess_id}_end",
                        )
                        model.add(end_var == start_var + dur_slots)

                        # Prevent lunch overlap
                        b_before = model.new_bool_var(f"{sess_id}_before_lunch")
                        model.add(end_var <= day_slot_offset + lunch_slot_start).only_enforce_if(b_before)
                        model.add(start_var >= day_slot_offset + lunch_slot_end).only_enforce_if(~b_before)

                        # Candidate rooms for group test
                        valid_rooms = [
                            rm for rm in active_rooms
                            if rm.capacity >= len(batch_sids)
                            and (not r.requires_computers or rm.has_computers)
                        ]
                        if r.required_room_type:
                            type_matched = [rm for rm in valid_rooms if rm.room_type == r.required_room_type]
                            if type_matched:
                                valid_rooms = type_matched

                        if not valid_rooms:
                            explanation = self.explainer.explain(drives, rooms, cfg)
                            return ScheduleResult(
                                schedule_id=str(uuid.uuid4()),
                                status=ScheduleStatus.INFEASIBLE,
                                items=[],
                                solver_time_seconds=(datetime.datetime.now() - start_clock).total_seconds(),
                                solver_name="cp-sat",
                                infeasibility_explanation=explanation,
                            )

                        room_literals = []
                        for rm in valid_rooms:
                            lit = model.new_bool_var(f"{sess_id}_in_room_{rm.id}")
                            room_literals.append(lit)
                            rm_interval = model.new_optional_interval_var(
                                start_var, dur_slots, end_var, lit, f"{sess_id}_rm_{rm.id}"
                            )
                            room_intervals[rm.id].append(rm_interval)

                        model.add_exactly_one(room_literals)

                        # Student interval (with transition buffer)
                        dur_with_buffer = dur_slots + buffer_slots
                        for sid in batch_sids:
                            stu_end_var = model.new_int_var(
                                day_slot_offset + fixed_start_slot + dur_with_buffer,
                                day_slot_offset + slots_per_day + buffer_slots,
                                f"{sess_id}_stu_{sid}_end",
                            )
                            model.add(stu_end_var == start_var + dur_with_buffer)
                            stu_interval = model.new_interval_var(
                                start_var, dur_with_buffer, stu_end_var, f"{sess_id}_stu_{sid}"
                            )
                            student_intervals[sid].append(stu_interval)

                        current_round_session_ends.append(end_var)

                        sessions.append({
                            "session_id": sess_id,
                            "drive": d,
                            "round": r,
                            "student_ids": batch_sids,
                            "start_var": start_var,
                            "end_var": end_var,
                            "dur_slots": dur_slots,
                            "room_literals": list(zip(valid_rooms, room_literals, strict=False)),
                            "panel_literals": [],
                            "is_group": True,
                        })

                else:
                    # 1-on-1 Interviews
                    panels = r.panels
                    if not panels:
                        panels = [
                            SchedulerPanel(
                                id=f"{d.id}_p1",
                                drive_id=d.id,
                                round_number=r.round_number,
                                name=f"{d.company_name} Panel 1",
                            )
                        ]
                        panel_room_map[panels[0].id] = cabins_classrooms[0]

                    for sid in d.shortlisted_student_ids:
                        sess_id = f"sess_{session_counter}"
                        session_counter += 1

                        start_var = model.new_int_var(
                            day_slot_offset + fixed_start_slot,
                            day_slot_offset + fixed_end_slot - dur_slots,
                            f"{sess_id}_start",
                        )
                        end_var = model.new_int_var(
                            day_slot_offset + fixed_start_slot + dur_slots,
                            day_slot_offset + fixed_end_slot,
                            f"{sess_id}_end",
                        )
                        model.add(end_var == start_var + dur_slots)

                        # Prevent lunch overlap
                        b_before = model.new_bool_var(f"{sess_id}_before_lunch")
                        model.add(end_var <= day_slot_offset + lunch_slot_start).only_enforce_if(b_before)
                        model.add(start_var >= day_slot_offset + lunch_slot_end).only_enforce_if(~b_before)

                        # Round precedence: Round 2 starts strictly after Round 1 ends
                        if prev_round_session_ends:
                            for prev_end in prev_round_session_ends:
                                model.add(start_var >= prev_end + buffer_slots)

                        # Panel assignment
                        panel_lits = []
                        for p in panels:
                            p_lit = model.new_bool_var(f"{sess_id}_on_panel_{p.id}")
                            panel_lits.append(p_lit)
                            p_interval = model.new_optional_interval_var(
                                start_var, dur_slots, end_var, p_lit, f"{sess_id}_pnl_{p.id}"
                            )
                            panel_intervals[p.id].append(p_interval)

                            # Assign to panel's room
                            p_room = panel_room_map[p.id]
                            r_interval = model.new_optional_interval_var(
                                start_var, dur_slots, end_var, p_lit, f"{sess_id}_rm_{p_room.id}_{p.id}"
                            )
                            room_intervals[p_room.id].append(r_interval)

                        model.add_exactly_one(panel_lits)

                        # Student interval (with transition buffer)
                        dur_with_buffer = dur_slots + buffer_slots
                        stu_end_var = model.new_int_var(
                            day_slot_offset + fixed_start_slot + dur_with_buffer,
                            day_slot_offset + slots_per_day + buffer_slots,
                            f"{sess_id}_stu_{sid}_end",
                        )
                        model.add(stu_end_var == start_var + dur_with_buffer)
                        stu_interval = model.new_interval_var(
                            start_var, dur_with_buffer, stu_end_var, f"{sess_id}_stu_{sid}"
                        )
                        student_intervals[sid].append(stu_interval)

                        current_round_session_ends.append(end_var)

                        sessions.append({
                            "session_id": sess_id,
                            "drive": d,
                            "round": r,
                            "student_ids": [sid],
                            "start_var": start_var,
                            "end_var": end_var,
                            "dur_slots": dur_slots,
                            "room_literals": [],
                            "panel_literals": list(zip(panels, panel_lits, strict=False)),
                            "is_group": False,
                        })

                prev_round_session_ends = current_round_session_ends

        # ---------------------------------------------------------------------
        # Non-Overlap Constraints
        # ---------------------------------------------------------------------
        for _rid, intervals in room_intervals.items():
            if len(intervals) > 1:
                model.add_no_overlap(intervals)

        for _pid, intervals in panel_intervals.items():
            if len(intervals) > 1:
                model.add_no_overlap(intervals)

        for _sid, intervals in student_intervals.items():
            if len(intervals) > 1:
                model.add_no_overlap(intervals)

        # ---------------------------------------------------------------------
        # Soft Objectives: Day Compactness & Earlier Finish
        # ---------------------------------------------------------------------
        objective_terms = [s["start_var"] for s in sessions]
        if objective_terms:
            model.minimize(sum(objective_terms))

        # ---------------------------------------------------------------------
        # Solve
        # ---------------------------------------------------------------------
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = cfg.solver_time_limit_seconds
        solver.parameters.random_seed = cfg.random_seed
        solver.parameters.num_search_workers = cfg.num_workers
        if cfg.stop_after_first_feasible:
            solver.parameters.stop_after_first_solution = True

        status = solver.solve(model)
        elapsed = (datetime.datetime.now() - start_clock).total_seconds()

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            items = []
            schedule_id = str(uuid.uuid4())

            for s in sessions:
                start_slot_val = solver.value(s["start_var"])
                d_idx = start_slot_val // slots_per_day
                slot_in_day = start_slot_val % slots_per_day
                s_date = all_dates[d_idx]

                start_dt = self._slot_to_datetime(s_date, slot_in_day, cfg)
                end_dt = start_dt + datetime.timedelta(minutes=s["dur_slots"] * cfg.slot_duration_minutes)

                if s["is_group"]:
                    assigned_room = None
                    for rm, lit in s["room_literals"]:
                        if solver.value(lit) == 1:
                            assigned_room = rm
                            break
                    assert assigned_room is not None
                    assigned_panel = None
                else:
                    assigned_panel = None
                    for p, lit in s["panel_literals"]:
                        if solver.value(lit) == 1:
                            assigned_panel = p
                            break
                    assert assigned_panel is not None
                    assigned_room = panel_room_map[assigned_panel.id]

                items.append(
                    ScheduledItem(
                        schedule_id=schedule_id,
                        drive_id=s["drive"].id,
                        round_number=s["round"].round_number,
                        round_name=s["round"].name,
                        student_ids=s["student_ids"],
                        room_id=assigned_room.id,
                        room_name=assigned_room.name,
                        panel_id=assigned_panel.id if assigned_panel else None,
                        panel_name=assigned_panel.name if assigned_panel else None,
                        start_time=start_dt,
                        end_time=end_dt,
                        is_group_session=s["is_group"],
                    )
                )

            verification = verify_schedule(items, rooms, drives, cfg)

            return ScheduleResult(
                schedule_id=schedule_id,
                status=ScheduleStatus.OPTIMAL if status == cp_model.OPTIMAL else ScheduleStatus.FEASIBLE,
                items=items,
                solver_time_seconds=round(elapsed, 3),
                solver_name="cp-sat",
                is_optimal=(status == cp_model.OPTIMAL),
                verification=verification,
                metadata={
                    "total_sessions": len(sessions),
                    "branches_or_drives": len(drives),
                },
            )

        elif status == cp_model.INFEASIBLE:
            explanation = self.explainer.explain(drives, rooms, cfg)
            return ScheduleResult(
                schedule_id=str(uuid.uuid4()),
                status=ScheduleStatus.INFEASIBLE,
                items=[],
                solver_time_seconds=round(elapsed, 3),
                solver_name="cp-sat",
                is_optimal=False,
                infeasibility_explanation=explanation,
            )

        else:
            # UNKNOWN / TIMEOUT -> Run fallback heuristic
            if cfg.allow_heuristic_fallback:
                return self.heuristic.schedule(drives, rooms, cfg, existing_slots=existing_slots)

            return ScheduleResult(
                schedule_id=str(uuid.uuid4()),
                status=ScheduleStatus.TIMEOUT,
                items=[],
                solver_time_seconds=round(elapsed, 3),
                solver_name="cp-sat",
                is_optimal=False,
                infeasibility_explanation="CP-SAT time limit reached without finding a feasible solution.",
            )

    def _slot_to_datetime(
        self,
        drive_date: datetime.date,
        slot_index: int,
        config: ScheduleConfig,
    ) -> datetime.datetime:
        minutes_from_start = slot_index * config.slot_duration_minutes
        base_time = datetime.datetime.combine(drive_date, datetime.time(config.day_start_hour, 0))
        return base_time + datetime.timedelta(minutes=minutes_from_start)
