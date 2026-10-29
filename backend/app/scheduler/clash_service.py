import collections
import json
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from backend.app.storage.models.entities import (
    DriveModel,
    SlotModel,
    StudentModel,
    CoordinatorRequestModel,
    RoomModel,
    PanelModel,
)


def detect_db_slot_clashes(db: Session, drive_id: str | None = None) -> list[dict[str, Any]]:
    """
    Identifies all cross-drive student, room, and panel conflicts for published drives.
    Cross-references open/approved coordinator preferences to reflect true resolution state.
    Strictly respects datetime boundaries (back-to-back interviews do not clash).
    """
    # 1. Fetch published drive IDs
    published_drive_ids = set(
        db.execute(select(DriveModel.id).where(DriveModel.status == "published")).scalars().all()
    )
    if not published_drive_ids:
        return []

    # 2. Fetch all slots for published drives
    slots_query = (
        select(SlotModel)
        .where(SlotModel.drive_id.in_(published_drive_ids))
        .options(
            joinedload(SlotModel.student),
            joinedload(SlotModel.drive),
            joinedload(SlotModel.room),
            joinedload(SlotModel.panel),
        )
        .order_by(SlotModel.start_time.asc())
    )
    slots = db.execute(slots_query).scalars().all()

    # 3. Fetch clash preference requests to check resolution status
    coord_requests = (
        db.execute(
            select(CoordinatorRequestModel).where(
                CoordinatorRequestModel.request_type == "clash_preference"
            )
        )
        .scalars()
        .all()
    )

    prefs_by_target: dict[str, list[CoordinatorRequestModel]] = collections.defaultdict(list)
    for req in coord_requests:
        if req.target_id:
            prefs_by_target[req.target_id].append(req)

    clashes: list[dict[str, Any]] = []
    seen_pairs = set()

    # 4. Student Conflicts
    student_slots: dict[str, list[SlotModel]] = collections.defaultdict(list)
    for s in slots:
        student_slots[s.student_id].append(s)

    for student_id, s_list in student_slots.items():
        if len(s_list) < 2:
            continue
        for i in range(len(s_list)):
            for j in range(i + 1, len(s_list)):
                s1 = s_list[i]
                s2 = s_list[j]
                if s1.drive_id == s2.drive_id:
                    continue

                # Back-to-back check: strictly max(start) < min(end)
                if max(s1.start_time, s2.start_time) < min(s1.end_time, s2.end_time):
                    pair_key = ("student", tuple(sorted([s1.id, s2.id])))
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)

                    student: StudentModel | None = s1.student
                    roll_no = student.roll_no if student else ""
                    student_name = student.name if student else f"Student {student_id}"
                    branch = student.branch if student else "N/A"

                    d1: DriveModel | None = s1.drive
                    d2: DriveModel | None = s2.drive
                    d1_name = d1.company_name if d1 else s1.drive_id
                    d2_name = d2.company_name if d2 else s2.drive_id

                    status_val = "unresolved"
                    recorded_pref = None

                    student_prefs = prefs_by_target.get(student_id, []) + prefs_by_target.get(roll_no, [])
                    for pr in student_prefs:
                        try:
                            payload = json.loads(pr.payload_json or "{}")
                            pref_id = payload.get("preferred_drive_id")
                            conf_id = payload.get("conflicting_drive_id")
                            if {pref_id, conf_id} == {s1.drive_id, s2.drive_id}:
                                if pr.status in ("approved", "resolved"):
                                    status_val = "resolved"
                                    recorded_pref = d1_name if pref_id == s1.drive_id else d2_name
                                    break
                                elif pr.status == "open":
                                    status_val = "preference_recorded"
                                    recorded_pref = d1_name if pref_id == s1.drive_id else d2_name
                        except Exception:
                            continue

                    clashes.append({
                        "id": f"clash_stu_{min(s1.id, s2.id)}_{max(s1.id, s2.id)}",
                        "conflict_type": "student_double_booking",
                        "student_roll": roll_no,
                        "student_name": student_name,
                        "branch": branch,
                        "drive_a_id": s1.drive_id,
                        "drive_a_company": d1_name,
                        "drive_a_time": f"{s1.start_time.strftime('%I:%M %p')} - {s1.end_time.strftime('%I:%M %p')}",
                        "drive_b_id": s2.drive_id,
                        "drive_b_company": d2_name,
                        "drive_b_time": f"{s2.start_time.strftime('%I:%M %p')} - {s2.end_time.strftime('%I:%M %p')}",
                        "date": s1.start_time.strftime("%Y-%m-%d"),
                        "room_name": s1.room.name if s1.room else s1.room_id,
                        "status": status_val,
                        "recorded_preference": recorded_pref,
                    })

    # 5. Room Conflicts
    room_slots: dict[str, list[SlotModel]] = collections.defaultdict(list)
    for s in slots:
        room_slots[s.room_id].append(s)

    for room_id, r_list in room_slots.items():
        if len(r_list) < 2:
            continue
        for i in range(len(r_list)):
            for j in range(i + 1, len(r_list)):
                s1 = r_list[i]
                s2 = r_list[j]
                if s1.drive_id == s2.drive_id and s1.student_id == s2.student_id:
                    continue

                if max(s1.start_time, s2.start_time) < min(s1.end_time, s2.end_time):
                    pair_key = ("room", tuple(sorted([s1.id, s2.id])))
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)

                    r_name = s1.room.name if s1.room else room_id
                    d1_name = s1.drive.company_name if s1.drive else s1.drive_id
                    d2_name = s2.drive.company_name if s2.drive else s2.drive_id
                    stu1 = s1.student.name if s1.student else s1.student_id
                    stu2 = s2.student.name if s2.student else s2.student_id

                    clashes.append({
                        "id": f"clash_rm_{min(s1.id, s2.id)}_{max(s1.id, s2.id)}",
                        "conflict_type": "room_double_booking",
                        "student_roll": s1.student.roll_no if s1.student else "",
                        "student_name": f"{stu1} / {stu2}",
                        "branch": s1.student.branch if s1.student else "N/A",
                        "drive_a_id": s1.drive_id,
                        "drive_a_company": d1_name,
                        "drive_a_time": f"{s1.start_time.strftime('%I:%M %p')} - {s1.end_time.strftime('%I:%M %p')}",
                        "drive_b_id": s2.drive_id,
                        "drive_b_company": d2_name,
                        "drive_b_time": f"{s2.start_time.strftime('%I:%M %p')} - {s2.end_time.strftime('%I:%M %p')}",
                        "date": s1.start_time.strftime("%Y-%m-%d"),
                        "room_name": r_name,
                        "status": "unresolved",
                        "recorded_preference": None,
                    })

    # 6. Panel Conflicts
    panel_slots: dict[str, list[SlotModel]] = collections.defaultdict(list)
    for s in slots:
        if s.panel_id:
            panel_slots[s.panel_id].append(s)

    for panel_id, p_list in panel_slots.items():
        if len(p_list) < 2:
            continue
        for i in range(len(p_list)):
            for j in range(i + 1, len(p_list)):
                s1 = p_list[i]
                s2 = p_list[j]
                if max(s1.start_time, s2.start_time) < min(s1.end_time, s2.end_time):
                    pair_key = ("panel", tuple(sorted([s1.id, s2.id])))
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)

                    p_name = s1.panel.name if s1.panel else panel_id
                    d1_name = s1.drive.company_name if s1.drive else s1.drive_id
                    d2_name = s2.drive.company_name if s2.drive else s2.drive_id

                    clashes.append({
                        "id": f"clash_pnl_{min(s1.id, s2.id)}_{max(s1.id, s2.id)}",
                        "conflict_type": "panel_double_booking",
                        "student_roll": s1.student.roll_no if s1.student else "",
                        "student_name": f"Panel {p_name}",
                        "branch": "N/A",
                        "drive_a_id": s1.drive_id,
                        "drive_a_company": d1_name,
                        "drive_a_time": f"{s1.start_time.strftime('%I:%M %p')} - {s1.end_time.strftime('%I:%M %p')}",
                        "drive_b_id": s2.drive_id,
                        "drive_b_company": d2_name,
                        "drive_b_time": f"{s2.start_time.strftime('%I:%M %p')} - {s2.end_time.strftime('%I:%M %p')}",
                        "date": s1.start_time.strftime("%Y-%m-%d"),
                        "room_name": s1.room.name if s1.room else s1.room_id,
                        "status": "unresolved",
                        "recorded_preference": None,
                    })

    if drive_id:
        return [c for c in clashes if c["drive_a_id"] == drive_id or c["drive_b_id"] == drive_id]

    return clashes


def count_unresolved_clashes(db: Session, drive_id: str | None = None) -> int:
    """Returns the count of active schedule clashes that remain unresolved."""
    all_clashes = detect_db_slot_clashes(db, drive_id=drive_id)
    return sum(1 for c in all_clashes if c["status"] == "unresolved")
