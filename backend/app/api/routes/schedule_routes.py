"""
Clash-Free Placement Scheduler Routes.
"""

from __future__ import annotations

import datetime
import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.app.api.auth.dependencies import require_officer_or_coordinator
from backend.app.domain.models import RoundType
from backend.app.scheduler.engine import PlacementSchedulerEngine
from backend.app.scheduler.models import (
    RoomType,
    ScheduleConfig,
    SchedulerDrive,
    SchedulerPanel,
    SchedulerRoom,
    SchedulerRound,
    ScheduleStatus,
)
from backend.app.scheduler.clash_service import detect_db_slot_clashes
from backend.app.storage.database import get_db
from backend.app.storage.models.entities import (
    DriveModel,
    EligibilityDecisionModel,
    PanelModel,
    RoomModel,
    ScheduleModel,
    SlotModel,
    UserModel,
)

router = APIRouter(prefix="/api/schedules", tags=["Scheduler Engine"])

_scheduler = PlacementSchedulerEngine()


class ScheduleGenerateRequest(BaseModel):
    drive_id: str
    num_panels: int = 2
    round_duration_minutes: int = 30
    time_limit_seconds: float = 10.0
    student_ids: list[str] | None = None


@router.post("/generate")
def generate_schedule(
    req: ScheduleGenerateRequest,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Generates an optimal, clash-free schedule using discrete constraint engine."""
    drive_stmt = select(DriveModel).where(DriveModel.id == req.drive_id)
    drive_entity = db.execute(drive_stmt).scalar_one_or_none()
    if not drive_entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drive not found.")

    # Fetch eligible students or use explicit candidate shortlist
    if req.student_ids:
        shortlist_ids = req.student_ids
    else:
        dec_stmt = select(EligibilityDecisionModel).where(
            EligibilityDecisionModel.drive_id == req.drive_id,
            EligibilityDecisionModel.status == "eligible",
        )
        eligible_decisions = db.execute(dec_stmt).scalars().all()
        shortlist_ids = [d.student_id for d in eligible_decisions]

    if not shortlist_ids:
        # Fallback to sample student if no decisions saved yet
        shortlist_ids = [d.student_id for d in db.execute(select(EligibilityDecisionModel).limit(5)).scalars().all()]

    if not shortlist_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot schedule: No eligible shortlisted candidates found for this drive.",
        )

    # Fetch rooms or create defaults if none
    room_entities = list(db.execute(select(RoomModel)).scalars().all())
    if not room_entities:
        r1 = RoomModel(id="hall_auditorium", name="Main Auditorium", building="Main", capacity=150)
        r2 = RoomModel(id="cabin_101", name="Interview Cabin 101", building="Placement", capacity=5)
        r3 = RoomModel(id="cabin_102", name="Interview Cabin 102", building="Placement", capacity=5)
        db.add_all([r1, r2, r3])
        db.commit()
        room_entities = [r1, r2, r3]

    # Ensure enough individual cabins for requested parallel panels
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
        )

    # Persist panels
    for p in panels:
        p_entity = db.execute(select(PanelModel).where(PanelModel.id == p.id)).scalar_one_or_none()
        if not p_entity:
            p_entity = PanelModel(
                id=p.id,
                drive_id=drive_entity.id,
                name=p.name,
                room_id=p.preferred_room_id,
                interviewers_json="[]",
            )
            db.add(p_entity)
    db.flush()

    # Persist schedule and slots
    sched_id = f"sched_{drive_entity.id}"
    # Clear existing slots for this drive to prevent duplicate accumulation
    db.execute(delete(SlotModel).where(SlotModel.drive_id == drive_entity.id))
    db.flush()

    sched_entity = db.execute(select(ScheduleModel).where(ScheduleModel.id == sched_id)).scalar_one_or_none()
    if not sched_entity:
        sched_entity = ScheduleModel(
            id=sched_id,
            name=f"Schedule - {drive_entity.company_name}",
            version=1,
            status="draft",
            drive_ids_json=json.dumps([drive_entity.id]),
        )
        db.add(sched_entity)
        db.flush()

    for it in res.items:
        for sid in it.student_ids:
            slot_id = f"slot_{uuid.uuid4().hex[:10]}"
            slot_entity = SlotModel(
                id=slot_id,
                schedule_id=sched_entity.id,
                drive_id=drive_entity.id,
                student_id=sid,
                room_id=it.room_id,
                panel_id=it.panel_id,
                round_number=it.round_number,
                start_time=it.start_time,
                end_time=it.end_time,
            )
            db.merge(slot_entity)
    db.commit()

    # Independently audit the database schedule to calculate true clash count
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
    }


@router.get("/{drive_id}")
def get_drive_schedule(
    drive_id: str,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieves schedule slots for a drive with cross-drive conflict detection."""
    stmt = select(SlotModel).where(SlotModel.drive_id == drive_id).order_by(SlotModel.start_time.asc())
    slots = db.execute(stmt).scalars().all()
    all_clashes = detect_db_slot_clashes(db, drive_id=drive_id)

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
    ]
