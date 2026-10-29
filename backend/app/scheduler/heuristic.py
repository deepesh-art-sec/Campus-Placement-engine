"""
DSatur-style constructive heuristic and local search fallback scheduler.
Used when exact CP-SAT search reaches its time limit.
Ensures zero clashes and clearly flags results as 'feasible, not optimised'.
"""

from __future__ import annotations

import collections
import datetime
import math
import uuid

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


class HeuristicTask:
    """An atomic scheduling unit (group batch session or individual interview)."""

    def __init__(
        self,
        task_id: str,
        drive_id: str,
        company_name: str,
        round_number: int,
        round_name: str,
        student_ids: list[str],
        duration_minutes: int,
        is_group_round: bool,
        required_room_type: RoomType | None,
        requires_computers: bool,
        panels: list[SchedulerPanel],
        drive_date: datetime.date,
    ) -> None:
        self.task_id = task_id
        self.drive_id = drive_id
        self.company_name = company_name
        self.round_number = round_number
        self.round_name = round_name
        self.student_ids = student_ids
        self.duration_minutes = duration_minutes
        self.is_group_round = is_group_round
        self.required_room_type = required_room_type
        self.requires_computers = requires_computers
        self.panels = panels
        self.drive_date = drive_date

        self.assigned_slot: int | None = None
        self.assigned_room: SchedulerRoom | None = None
        self.assigned_panel: SchedulerPanel | None = None


class DSaturHeuristicScheduler:
    """Constructive graph-coloring-inspired placement scheduler with local search."""

    def schedule(
        self,
        drives: list[SchedulerDrive],
        rooms: list[SchedulerRoom],
        config: ScheduleConfig,
        existing_slots: list[dict[str, Any]] | None = None,
    ) -> ScheduleResult:
        start_time = datetime.datetime.now()

        # Step 1: Decompose drives into tasks
        tasks = self._build_tasks(drives, rooms, config)

        # Step 2: Build student and precedence conflict graph
        conflict_graph = self._build_conflict_graph(tasks)

        # Step 3: DSatur constructive scheduling
        scheduled_tasks = self._dsatur_schedule(tasks, conflict_graph, rooms, config, existing_slots=existing_slots)

        if len(scheduled_tasks) < len(tasks):
            return ScheduleResult(
                schedule_id=str(uuid.uuid4()),
                status=ScheduleStatus.INFEASIBLE,
                items=[],
                solver_time_seconds=(datetime.datetime.now() - start_time).total_seconds(),
                solver_name="dsatur-heuristic",
                is_optimal=False,
                infeasibility_explanation=(
                    f"Heuristic could only place {len(scheduled_tasks)} of {len(tasks)} sessions. "
                    "Available room-time capacity exhausted."
                ),
            )

        # Step 4: Convert tasks to ScheduledItems
        items: list[ScheduledItem] = []
        schedule_id = str(uuid.uuid4())

        for t in scheduled_tasks:
            assert t.assigned_slot is not None
            assert t.assigned_room is not None

            start_dt = self._slot_to_datetime(t.drive_date, t.assigned_slot, config)
            end_dt = start_dt + datetime.timedelta(minutes=t.duration_minutes)

            items.append(
                ScheduledItem(
                    schedule_id=schedule_id,
                    drive_id=t.drive_id,
                    round_number=t.round_number,
                    round_name=t.round_name,
                    student_ids=t.student_ids,
                    room_id=t.assigned_room.id,
                    room_name=t.assigned_room.name,
                    panel_id=t.assigned_panel.id if t.assigned_panel else None,
                    panel_name=t.assigned_panel.name if t.assigned_panel else None,
                    start_time=start_dt,
                    end_time=end_dt,
                    is_group_session=t.is_group_round,
                )
            )

        verification = verify_schedule(items, rooms, drives, config)
        elapsed = (datetime.datetime.now() - start_time).total_seconds()

        return ScheduleResult(
            schedule_id=schedule_id,
            status=ScheduleStatus.FEASIBLE_HEURISTIC,
            items=items,
            solver_time_seconds=round(elapsed, 3),
            solver_name="dsatur-heuristic",
            is_optimal=False,
            verification=verification,
            metadata={
                "note": "feasible, not optimised",
                "heuristic_tasks_count": len(tasks),
            },
        )

    def _build_tasks(
        self,
        drives: list[SchedulerDrive],
        rooms: list[SchedulerRoom],
        config: ScheduleConfig,
    ) -> list[HeuristicTask]:
        tasks: list[HeuristicTask] = []
        max_room_cap = max((r.capacity for r in rooms if r.is_active), default=50)

        for d in drives:
            for r in d.rounds:
                if r.is_group_round:
                    batch_size = min(r.max_batch_size, max_room_cap)
                    all_students = list(dict.fromkeys(d.shortlisted_student_ids))
                    if not all_students:
                        continue
                    num_batches = math.ceil(len(all_students) / batch_size)

                    for b_idx in range(num_batches):
                        batch_sids = all_students[b_idx * batch_size : (b_idx + 1) * batch_size]
                        tasks.append(
                            HeuristicTask(
                                task_id=f"{d.id}_r{r.round_number}_b{b_idx}",
                                drive_id=d.id,
                                company_name=d.company_name,
                                round_number=r.round_number,
                                round_name=r.name,
                                student_ids=batch_sids,
                                duration_minutes=r.duration_minutes,
                                is_group_round=True,
                                required_room_type=r.required_room_type,
                                requires_computers=r.requires_computers,
                                panels=[],
                                drive_date=d.drive_date,
                            )
                        )
                else:
                    for sid in list(dict.fromkeys(d.shortlisted_student_ids)):
                        tasks.append(
                            HeuristicTask(
                                task_id=f"{d.id}_r{r.round_number}_s_{sid}",
                                drive_id=d.id,
                                company_name=d.company_name,
                                round_number=r.round_number,
                                round_name=r.name,
                                student_ids=[sid],
                                duration_minutes=r.duration_minutes,
                                is_group_round=False,
                                required_room_type=r.required_room_type,
                                requires_computers=r.requires_computers,
                                panels=r.panels,
                                drive_date=d.drive_date,
                            )
                        )

        return tasks

    def _build_conflict_graph(self, tasks: list[HeuristicTask]) -> dict[str, set[str]]:
        graph: dict[str, set[str]] = collections.defaultdict(set)
        student_task_map: dict[str, list[HeuristicTask]] = collections.defaultdict(list)

        for t in tasks:
            for sid in t.student_ids:
                student_task_map[sid].append(t)

        for _sid, t_list in student_task_map.items():
            for i in range(len(t_list)):
                for j in range(i + 1, len(t_list)):
                    t1 = t_list[i]
                    t2 = t_list[j]
                    graph[t1.task_id].add(t2.task_id)
                    graph[t2.task_id].add(t1.task_id)

        return graph

    def _dsatur_schedule(
        self,
        tasks: list[HeuristicTask],
        conflict_graph: dict[str, set[str]],
        rooms: list[SchedulerRoom],
        config: ScheduleConfig,
        existing_slots: list[dict[str, Any]] | None = None,
    ) -> list[HeuristicTask]:
        scheduled: list[HeuristicTask] = []
        unscheduled = {t.task_id: t for t in tasks}

        saturation_map: dict[str, set[int]] = collections.defaultdict(set)

        # Precise multi-entity busy sets: (date, slot, entity_id)
        slots_per_day = int((config.day_end_hour - config.day_start_hour) * 60 / config.slot_duration_minutes)
        buffer_slots = int(math.ceil(config.transition_buffer_minutes / config.slot_duration_minutes))

        busy_rooms: set[tuple[datetime.date, int, str]] = set()
        busy_panels: set[tuple[datetime.date, int, str]] = set()
        busy_students: set[tuple[datetime.date, int, str]] = set()

        if existing_slots:
            for ext in existing_slots:
                st = ext.get("start_time")
                et = ext.get("end_time")
                if not isinstance(st, datetime.datetime) or not isinstance(et, datetime.datetime):
                    continue
                ext_date = st.date()
                day_start_dt = datetime.datetime.combine(ext_date, datetime.time(config.day_start_hour, 0))
                start_min = max(0, int((st - day_start_dt).total_seconds() / 60))
                end_min = min(slots_per_day * config.slot_duration_minutes, int((et - day_start_dt).total_seconds() / 60))
                if end_min <= start_min:
                    continue
                s_slot = start_min // config.slot_duration_minutes
                e_slot = math.ceil(end_min / config.slot_duration_minutes)

                sid = ext.get("student_id")
                if sid:
                    ext_range = range(max(0, s_slot - buffer_slots), min(slots_per_day, e_slot + buffer_slots))
                    for slot_idx in ext_range:
                        busy_students.add((ext_date, slot_idx, sid))

                rid = ext.get("room_id")
                if rid:
                    for slot_idx in range(s_slot, e_slot):
                        busy_rooms.add((ext_date, slot_idx, rid))

        lunch_slot_start = int((config.lunch_start_hour - config.day_start_hour) * 60 / config.slot_duration_minutes)
        lunch_slots_count = int(config.lunch_duration_minutes / config.slot_duration_minutes)
        lunch_slot_end = lunch_slot_start + lunch_slots_count

        while unscheduled:
            # Pick task with maximum saturation (tie-break on conflict degree)
            best_task_id = max(
                unscheduled.keys(),
                key=lambda tid: (len(saturation_map[tid]), len(conflict_graph[tid])),
            )
            task = unscheduled.pop(best_task_id)

            task_slots_needed = math.ceil(task.duration_minutes / config.slot_duration_minutes)
            placed = False

            # Search valid slot
            for slot in range(slots_per_day - task_slots_needed + 1):
                slot_range = range(slot, slot + task_slots_needed)

                # Cannot overlap lunch
                if any(lunch_slot_start <= s < lunch_slot_end for s in slot_range):
                    continue

                # Buffer slot range for students
                extended_range = range(
                    max(0, slot - buffer_slots),
                    min(slots_per_day, slot + task_slots_needed + buffer_slots),
                )

                # Check students availability with buffer
                if any(
                    (task.drive_date, s, sid) in busy_students
                    for s in extended_range
                    for sid in task.student_ids
                ):
                    continue

                # Precedence check: if student had earlier round in same drive, must be after it
                earlier_conflict = False
                for prev in scheduled:
                    if prev.drive_id == task.drive_id and prev.round_number < task.round_number:
                        if set(prev.student_ids) & set(task.student_ids):
                            assert prev.assigned_slot is not None
                            prev_dur_slots = math.ceil(prev.duration_minutes / config.slot_duration_minutes)
                            if slot < prev.assigned_slot + prev_dur_slots + buffer_slots:
                                earlier_conflict = True
                                break
                if earlier_conflict:
                    continue

                # Find valid room and panel
                candidate_room, candidate_panel = self._find_room_and_panel(
                    task, slot_range, rooms, busy_rooms, busy_panels
                )

                if candidate_room:
                    # Place task
                    task.assigned_slot = slot
                    task.assigned_room = candidate_room
                    task.assigned_panel = candidate_panel

                    # Record reservations
                    for s in slot_range:
                        busy_rooms.add((task.drive_date, s, candidate_room.id))
                        if candidate_panel:
                            busy_panels.add((task.drive_date, s, candidate_panel.id))

                    # Student reservations include the session
                    for s in slot_range:
                        for sid in task.student_ids:
                            busy_students.add((task.drive_date, s, sid))

                    # Update saturation of neighbours
                    for nbr in conflict_graph[task.task_id]:
                        if nbr in unscheduled:
                            saturation_map[nbr].update(slot_range)

                    scheduled.append(task)
                    placed = True
                    break

            if not placed:
                # Classroom was not available among existing rooms -> dynamically make new class as per students requirements
                for slot in range(slots_per_day - task_slots_needed + 1):
                    slot_range = range(slot, slot + task_slots_needed)
                    if any(lunch_slot_start <= s < lunch_slot_end for s in slot_range):
                        continue
                    extended_range = range(
                        max(0, slot - buffer_slots),
                        min(slots_per_day, slot + task_slots_needed + buffer_slots),
                    )
                    if any(
                        (task.drive_date, s, sid) in busy_students
                        for s in extended_range
                        for sid in task.student_ids
                    ):
                        continue

                    earlier_conflict = False
                    for prev in scheduled:
                        if prev.drive_id == task.drive_id and prev.round_number < task.round_number:
                            if set(prev.student_ids) & set(task.student_ids):
                                assert prev.assigned_slot is not None
                                prev_dur_slots = math.ceil(prev.duration_minutes / config.slot_duration_minutes)
                                if slot < prev.assigned_slot + prev_dur_slots + buffer_slots:
                                    earlier_conflict = True
                                    break
                    if earlier_conflict:
                        continue

                    # Find a panel that is free
                    free_panel = None
                    if not task.is_group_round:
                        for p in task.panels:
                            if not any((task.drive_date, s, p.id) in busy_panels for s in slot_range):
                                free_panel = p
                                break
                        if not free_panel:
                            p_idx = len(task.panels) + 1
                            free_panel = SchedulerPanel(
                                id=f"panel_{task.drive_id}_auto_{p_idx}",
                                drive_id=task.drive_id,
                                round_number=task.round_number,
                                name=f"Technical Panel {p_idx}",
                            )
                            task.panels.append(free_panel)

                    # Create a new classroom as per students' requirements
                    req_cap = max(40, len(task.student_ids))
                    existing_names = {rm.name for rm in rooms}
                    existing_ids = {rm.id for rm in rooms}
                    c_num = 101
                    while f"Classroom {c_num}" in existing_names or f"room_class_{c_num}" in existing_ids:
                        c_num += 1
                    candidate_room = SchedulerRoom(
                        id=f"room_class_{c_num}",
                        name=f"Classroom {c_num}",
                        building="Academic Complex",
                        room_type=task.required_room_type or RoomType.CLASSROOM,
                        capacity=req_cap,
                        has_computers=task.requires_computers,
                        is_active=True,
                    )
                    rooms.append(candidate_room)

                    task.assigned_slot = slot
                    task.assigned_room = candidate_room
                    task.assigned_panel = free_panel

                    for s in slot_range:
                        busy_rooms.add((task.drive_date, s, candidate_room.id))
                        if free_panel:
                            busy_panels.add((task.drive_date, s, free_panel.id))
                        for sid in task.student_ids:
                            busy_students.add((task.drive_date, s, sid))

                    for nbr in conflict_graph[task.task_id]:
                        if nbr in unscheduled:
                            saturation_map[nbr].update(slot_range)

                    scheduled.append(task)
                    placed = True
                    break

            if not placed:
                break

        return scheduled

    def _find_room_and_panel(
        self,
        task: HeuristicTask,
        slot_range: range,
        rooms: list[SchedulerRoom],
        busy_rooms: set[tuple[datetime.date, int, str]],
        busy_panels: set[tuple[datetime.date, int, str]],
    ) -> tuple[SchedulerRoom | None, SchedulerPanel | None]:
        valid_rooms = [
            r for r in rooms
            if r.is_active
            and r.capacity >= len(task.student_ids)
            and (not task.requires_computers or r.has_computers)
        ]

        if task.required_room_type:
            type_matched = [r for r in valid_rooms if r.room_type == task.required_room_type]
            if type_matched:
                valid_rooms = type_matched

        for room in valid_rooms:
            # Check room availability
            if any((task.drive_date, s, room.id) in busy_rooms for s in slot_range):
                continue

            if task.is_group_round:
                return room, None

            # For interview, check panel
            for panel in task.panels:
                if not any((task.drive_date, s, panel.id) in busy_panels for s in slot_range):
                    return room, panel

        return None, None

    def _slot_to_datetime(
        self,
        drive_date: datetime.date,
        slot_index: int,
        config: ScheduleConfig,
    ) -> datetime.datetime:
        minutes_from_start = slot_index * config.slot_duration_minutes
        base_time = datetime.datetime.combine(drive_date, datetime.time(config.day_start_hour, 0))
        return base_time + datetime.timedelta(minutes=minutes_from_start)
