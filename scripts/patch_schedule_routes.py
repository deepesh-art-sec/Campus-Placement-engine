with open("backend/app/api/routes/schedule_routes.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace cabin allocation and generate call
target = """    # Ensure enough individual cabins for requested parallel panels
    effective_num_panels = max(req.num_panels, (len(shortlist_ids) + 13) // 14) if shortlist_ids else req.num_panels
    cabins = [r for r in room_entities if r.capacity < 50]
    existing_ids = {r.id for r in room_entities}
    existing_names = {r.name for r in room_entities}
    c_num = 1
    while len(cabins) < effective_num_panels:
        cabin_id = f"cabin_auto_{c_num}"
        cabin_name = f"Interview Cabin Auto {c_num}"
        while cabin_id in existing_ids or cabin_name in existing_names:
            c_num += 1
            cabin_id = f"cabin_auto_{c_num}"
            cabin_name = f"Interview Cabin Auto {c_num}"
        new_c = RoomModel(id=cabin_id, name=cabin_name, building="Placement", capacity=5)
        db.add(new_c)
        db.flush()
        existing_ids.add(cabin_id)
        existing_names.add(cabin_name)
        room_entities.append(new_c)
        cabins.append(new_c)
        c_num += 1
    db.commit()

    rooms = [
        SchedulerRoom(
            id=r.id,
            name=r.name,
            building=r.building,
            room_type=RoomType.HALL if r.capacity >= 50 else RoomType.CABIN,
            capacity=r.capacity,
            has_computers=r.has_computers,
            is_active=r.is_active,
        )
        for r in room_entities
    ]

    panels = [
        SchedulerPanel(
            id=f"panel_{i+1}",
            drive_id=drive_entity.id,
            round_number=1,
            name=f"Technical Panel {i+1}",
            preferred_room_id=cabins[i].id,
        )
        for i in range(effective_num_panels)
    ]

    drive = SchedulerDrive(
        id=drive_entity.id,
        company_name=drive_entity.company_name,
        drive_date=drive_entity.drive_date,
        shortlisted_student_ids=shortlist_ids,
        rounds=[
            SchedulerRound(
                round_number=1,
                name="Technical Interview",
                round_type=RoundType.TECHNICAL_INTERVIEW,
                duration_minutes=req.round_duration_minutes,
                is_group_round=False,
                panels=panels,
            )
        ],
    )

    config = ScheduleConfig(
        solver_time_limit_seconds=float(req.time_limit_seconds),
        stop_after_first_feasible=True,
    )
    res = _scheduler.generate_schedule(drives=[drive], rooms=rooms, config=config)"""

replacement = """    # Ensure enough individual cabins for requested parallel panels
    effective_num_panels = max(req.num_panels, (len(shortlist_ids) + 13) // 14) if shortlist_ids else req.num_panels

    # Prioritize cabins that are not booked on this date for other drives
    day_start = datetime.datetime.combine(drive_entity.drive_date, datetime.time.min)
    day_end = datetime.datetime.combine(drive_entity.drive_date, datetime.time.max)
    busy_room_ids = set(
        db.execute(
            select(SlotModel.room_id)
            .where(
                SlotModel.drive_id != drive_entity.id,
                SlotModel.start_time >= day_start,
                SlotModel.start_time <= day_end,
            )
            .distinct()
        ).scalars().all()
    )

    all_cabins = [r for r in room_entities if r.capacity < 50]
    avail_cabins = [r for r in all_cabins if r.id not in busy_room_ids]
    occupied_cabins = [r for r in all_cabins if r.id in busy_room_ids]
    cabins = avail_cabins + occupied_cabins

    existing_ids = {r.id for r in room_entities}
    existing_names = {r.name for r in room_entities}
    c_num = 1
    while len(avail_cabins) < effective_num_panels:
        cabin_id = f"cabin_auto_{c_num}"
        cabin_name = f"Interview Cabin Auto {c_num}"
        while cabin_id in existing_ids or cabin_name in existing_names:
            c_num += 1
            cabin_id = f"cabin_auto_{c_num}"
            cabin_name = f"Interview Cabin Auto {c_num}"
        new_c = RoomModel(id=cabin_id, name=cabin_name, building="Placement", capacity=5)
        db.add(new_c)
        db.flush()
        existing_ids.add(cabin_id)
        existing_names.add(cabin_name)
        room_entities.append(new_c)
        cabins.insert(len(avail_cabins), new_c)
        avail_cabins.append(new_c)
        c_num += 1
    db.commit()

    rooms = [
        SchedulerRoom(
            id=r.id,
            name=r.name,
            building=r.building,
            room_type=RoomType.HALL if r.capacity >= 50 else RoomType.CABIN,
            capacity=r.capacity,
            has_computers=r.has_computers,
            is_active=r.is_active,
        )
        for r in room_entities
    ]

    panels = [
        SchedulerPanel(
            id=f"panel_{i+1}",
            drive_id=drive_entity.id,
            round_number=1,
            name=f"Technical Panel {i+1}",
            preferred_room_id=cabins[i].id,
        )
        for i in range(effective_num_panels)
    ]

    drive = SchedulerDrive(
        id=drive_entity.id,
        company_name=drive_entity.company_name,
        drive_date=drive_entity.drive_date,
        shortlisted_student_ids=shortlist_ids,
        rounds=[
            SchedulerRound(
                round_number=1,
                name="Technical Interview",
                round_type=RoundType.TECHNICAL_INTERVIEW,
                duration_minutes=req.round_duration_minutes,
                is_group_round=False,
                panels=panels,
            )
        ],
    )

    # Fetch existing scheduled slots for published drives on this date to guarantee zero cross-drive clashes
    existing_slots_stmt = (
        select(SlotModel)
        .join(DriveModel, SlotModel.drive_id == DriveModel.id)
        .where(
            SlotModel.drive_id != drive_entity.id,
            DriveModel.status == "published",
            SlotModel.start_time >= day_start,
            SlotModel.start_time <= day_end,
        )
    )
    existing_slots_entities = db.execute(existing_slots_stmt).scalars().all()
    existing_slots = [
        {
            "student_id": s.student_id,
            "room_id": s.room_id,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "drive_id": s.drive_id,
        }
        for s in existing_slots_entities
    ]

    config = ScheduleConfig(
        solver_time_limit_seconds=float(req.time_limit_seconds),
        stop_after_first_feasible=True,
    )
    res = _scheduler.generate_schedule(
        drives=[drive],
        rooms=rooms,
        config=config,
        existing_slots=existing_slots,
    )

    is_feasible = res.status in (ScheduleStatus.OPTIMAL, ScheduleStatus.FEASIBLE, ScheduleStatus.FEASIBLE_HEURISTIC)
    if not is_feasible or len(res.items) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=res.infeasibility_explanation or "No clash-free solution exists under current room, panel, and student commitments.",
        )"""

assert target in content, "target not found"
content = content.replace(target, replacement, 1)

# Also update the return dict and get_drive_schedule clash matching
target_ret = """    is_feasible = res.status in (ScheduleStatus.OPTIMAL, ScheduleStatus.FEASIBLE, ScheduleStatus.FEASIBLE_HEURISTIC)
    is_valid = res.verification.is_valid if res.verification else False
    clash_count = res.verification.clash_count if res.verification else 0

    return {
        "is_feasible": is_feasible,
        "solver_status": res.status.value,
        "solve_time_seconds": res.solver_time_seconds,
        "scheduled_items_count": len(res.items),
        "total_slots": len(res.items),
        "students_scheduled": len(shortlist_ids),
        "zero_clashes_verified": is_valid,
        "clash_count": clash_count,
    }"""

replacement_ret = """    # Independently audit the database schedule to calculate true clash count
    actual_db_clashes = detect_db_slot_clashes(db, drive_id=drive_entity.id)
    actual_unresolved = sum(1 for c in actual_db_clashes if c.get("status") == "unresolved")
    is_valid = actual_unresolved == 0

    return {
        "is_feasible": is_feasible,
        "solver_status": res.status.value,
        "solve_time_seconds": res.solver_time_seconds,
        "scheduled_items_count": len(res.items),
        "total_slots": len(res.items),
        "students_scheduled": len(shortlist_ids),
        "zero_clashes_verified": is_valid,
        "clash_count": actual_unresolved,
        "infeasibility_explanation": res.infeasibility_explanation,
    }"""

assert target_ret in content, "target_ret not found"
content = content.replace(target_ret, replacement_ret, 1)

# In get_drive_schedule:
target_get = """    all_clashes = detect_db_slot_clashes(db)

    clash_map: dict[str, str] = {}
    for c in all_clashes:
        if c.get("status") == "unresolved":
            if c.get("drive_a_id") == drive_id:
                clash_map[c["student_roll"]] = f"Conflicts with {c['drive_b_company']} ({c['drive_b_time']})"
            elif c.get("drive_b_id") == drive_id:
                clash_map[c["student_roll"]] = f"Conflicts with {c['drive_a_company']} ({c['drive_a_time']})"

    return [
        {
            "id": s.id,
            "student_id": s.student_id,
            "student_name": s.student.name if s.student else "Student",
            "roll_no": s.student.roll_no if s.student else "",
            "round_name": f"Round {s.round_number}",
            "room_id": s.room_id,
            "room_name": s.room.name if s.room else "Venue",
            "time_slot": s.start_time.strftime("%H:%M"),
            "start_time": s.start_time.strftime("%d-%b-%Y %H:%M"),
            "end_time": s.end_time.strftime("%H:%M"),
            "has_clash": (s.student and s.student.roll_no in clash_map) or False,
            "clash_detail": clash_map.get(s.student.roll_no) if s.student else None,
        }
        for s in slots
    ]"""

replacement_get = """    all_clashes = detect_db_slot_clashes(db, drive_id=drive_id)

    clash_map: dict[str, str] = {}
    room_clash_map: dict[tuple[str, str], str] = {}

    for c in all_clashes:
        if c.get("status") == "unresolved":
            other_company = c['drive_b_company'] if c.get("drive_a_id") == drive_id else c['drive_a_company']
            other_time = c['drive_b_time'] if c.get("drive_a_id") == drive_id else c['drive_a_time']
            msg = f"{c.get('conflict_type', 'Conflict')}: Conflicts with {other_company} ({other_time})"
            if c.get("student_roll"):
                clash_map[c["student_roll"]] = msg
            if c.get("room_name"):
                room_clash_map[(c["room_name"], c.get("date", ""))] = msg

    return [
        {
            "id": s.id,
            "student_id": s.student_id,
            "student_name": s.student.name if s.student else "Student",
            "roll_no": s.student.roll_no if s.student else "",
            "round_name": f"Round {s.round_number}",
            "room_id": s.room_id,
            "room_name": s.room.name if s.room else "Venue",
            "time_slot": s.start_time.strftime("%H:%M"),
            "start_time": s.start_time.strftime("%d-%b-%Y %H:%M"),
            "end_time": s.end_time.strftime("%H:%M"),
            "has_clash": (s.student and s.student.roll_no in clash_map) or (s.room and (s.room.name, s.start_time.strftime("%Y-%m-%d")) in room_clash_map),
            "clash_detail": clash_map.get(s.student.roll_no) if (s.student and s.student.roll_no in clash_map) else room_clash_map.get((s.room.name if s.room else "", s.start_time.strftime("%Y-%m-%d"))),
        }
        for s in slots
    ]"""

assert target_get in content, "target_get not found"
content = content.replace(target_get, replacement_get, 1)

with open("backend/app/api/routes/schedule_routes.py", "w", encoding="utf-8") as f:
    f.write(content)
print("schedule_routes.py patched successfully")
