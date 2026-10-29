file_path = "backend/app/api/routes/schedule_routes.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Add import
import_target = "from backend.app.storage.database import get_db"
import_replacement = "from backend.app.scheduler.clash_service import detect_db_slot_clashes\nfrom backend.app.storage.database import get_db"
assert import_target in content, "import target not found"
content = content.replace(import_target, import_replacement, 1)

# Update get_drive_schedule
old_get = '''@router.get("/{drive_id}")
def get_drive_schedule(
    drive_id: str,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieves schedule slots for a drive."""
    stmt = select(SlotModel).where(SlotModel.drive_id == drive_id).order_by(SlotModel.start_time.asc())
    slots = db.execute(stmt).scalars().all()
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
        }
        for s in slots
    ]'''

new_get = '''@router.get("/{drive_id}")
def get_drive_schedule(
    drive_id: str,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieves schedule slots for a drive with cross-drive conflict detection."""
    stmt = select(SlotModel).where(SlotModel.drive_id == drive_id).order_by(SlotModel.start_time.asc())
    slots = db.execute(stmt).scalars().all()
    all_clashes = detect_db_slot_clashes(db)

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
    ]'''

assert old_get in content, "old_get target not found"
content = content.replace(old_get, new_get, 1)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("schedule_routes.py updated successfully!")
