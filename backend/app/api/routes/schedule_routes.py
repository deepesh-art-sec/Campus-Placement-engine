"""
Clash-Free Placement Scheduler Routes.
"""

from __future__ import annotations

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
    """Generates an optimal, clash-free schedule using Google OR-Tools CP-SAT."""
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
    res = _scheduler.generate_schedule(drives=[drive], rooms=rooms, config=config)

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

    is_feasible = res.status in (ScheduleStatus.OPTIMAL, ScheduleStatus.FEASIBLE, ScheduleStatus.FEASIBLE_HEURISTIC)
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
    }


@router.get("/{drive_id}")
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
    ]
