"""
Service for detecting, auditing, and synchronizing schedule clashes across drives.
"""

from __future__ import annotations

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
)


def detect_db_slot_clashes(db: Session) -> list[dict[str, Any]]:
    """
    Identifies all cross-drive slot conflicts for published drives.
    Cross-references open/approved coordinator preferences to reflect true resolution state.
    """
    # 1. Fetch all published drive IDs
    published_drive_ids = set(
        db.execute(select(DriveModel.id).where(DriveModel.status == "published")).scalars().all()
    )
    if not published_drive_ids:
        return []

    # 2. Fetch slots with student and drive preloaded
    slots = (
        db.execute(
            select(SlotModel)
            .where(SlotModel.drive_id.in_(published_drive_ids))
            .options(joinedload(SlotModel.student), joinedload(SlotModel.drive))
            .order_by(SlotModel.student_id, SlotModel.start_time.asc())
        )
        .scalars()
        .all()
    )

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

    # Index coordinator preferences by (target_id, drive_pair)
    # target_id could be student_id or roll_no
    prefs_by_target: dict[str, list[CoordinatorRequestModel]] = collections.defaultdict(list)
    for req in coord_requests:
        if req.target_id:
            prefs_by_target[req.target_id].append(req)

    # 4. Group slots by student
    student_slots: dict[str, list[SlotModel]] = collections.defaultdict(list)
    for s in slots:
        student_slots[s.student_id].append(s)

    clashes: list[dict[str, Any]] = []
    seen_clash_keys = set()

    for student_id, s_list in student_slots.items():
        if len(s_list) < 2:
            continue

        for i in range(len(s_list)):
            for j in range(i + 1, len(s_list)):
                s1 = s_list[i]
                s2 = s_list[j]

                # Only cross-drive collisions
                if s1.drive_id == s2.drive_id:
                    continue

                # Check temporal overlap
                if max(s1.start_time, s2.start_time) < min(s1.end_time, s2.end_time):
                    pair_key = tuple(sorted([s1.id, s2.id]))
                    if pair_key in seen_clash_keys:
                        continue
                    seen_clash_keys.add(pair_key)

                    student: StudentModel | None = s1.student
                    roll_no = student.roll_no if student else ""
                    student_name = student.name if student else f"Student {student_id}"
                    branch = student.branch if student else "N/A"

                    d1: DriveModel | None = s1.drive
                    d2: DriveModel | None = s2.drive
                    d1_name = d1.company_name if d1 else s1.drive_id
                    d2_name = d2.company_name if d2 else s2.drive_id

                    # Check for coordinator preference resolution
                    status_val = "unresolved"
                    recorded_pref = None

                    # Check requests by student_id or roll_no
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
                        "id": f"clash_{min(s1.id, s2.id)}_{max(s1.id, s2.id)}",
                        "student_roll": roll_no,
                        "student_name": student_name,
                        "branch": branch,
                        "drive_a_id": s1.drive_id,
                        "drive_a_company": d1_name,
                        "drive_a_time": f"{s1.start_time.strftime('%I:%M %p')} - {s1.end_time.strftime('%I:%M %p')}",
                        "drive_b_id": s2.drive_id,
                        "drive_b_company": d2_name,
                        "drive_b_time": f"{s2.start_time.strftime('%I:%M %p')} - {s2.end_time.strftime('%I:%M %p')}",
                        "status": status_val,
                        "recorded_preference": recorded_pref,
                    })

    return clashes


def count_unresolved_clashes(db: Session) -> int:
    """Returns the count of active schedule clashes that remain unresolved."""
    all_clashes = detect_db_slot_clashes(db)
    return sum(1 for c in all_clashes if c["status"] == "unresolved")
