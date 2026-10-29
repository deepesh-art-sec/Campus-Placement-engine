"""
Campus Classroom & Venue Management API.
Supports listing, creating, and auto-provisioning classrooms according to students' requirements.
"""

from __future__ import annotations

import datetime
import math
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.auth.dependencies import require_officer_or_coordinator
from backend.app.storage.database import get_db
from backend.app.storage.models.entities import RoomModel, SlotModel, UserModel

router = APIRouter(prefix="/api/rooms", tags=["Classroom Inventory & Allocation"])


def _infer_room_type(capacity: int, name: str) -> str:
    n_lower = name.lower()
    if "auditorium" in n_lower or "hall" in n_lower or capacity >= 80:
        return "hall"
    if "cabin" in n_lower or capacity <= 10:
        return "cabin"
    return "classroom"


class CreateRoomRequest(BaseModel):
    name: str = Field(..., description="Classroom name e.g. Classroom 305")
    building: str = Field("Academic Complex", description="Campus building or block")
    capacity: int = Field(40, ge=1, le=1000, description="Seating capacity according to students requirements")
    has_computers: bool = Field(False, description="Whether room is equipped with lab computers")
    is_active: bool = Field(True, description="Whether room is available for scheduling")


class AutoProvisionRequest(BaseModel):
    students_count: int = Field(..., ge=1, description="Number of students needing classrooms")
    round_type: str = Field("interview", description="interview or test")
    target_date: datetime.date | None = Field(None, description="Date for scheduling (checks existing room bookings)")
    preferred_building: str = Field("Academic Complex", description="Campus complex/building")
    capacity_per_room: int = Field(40, ge=5, le=500, description="Required capacity per classroom")


@router.get("")
def list_rooms(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    """Lists all active and configured campus classrooms and venues."""
    rooms = db.execute(select(RoomModel)).scalars().all()
    # Sort with auditorium/halls first, then numeric classrooms
    sorted_rooms = sorted(
        rooms,
        key=lambda r: (
            0 if "auditorium" in (r.name or "").lower() else 1,
            r.building or "",
            r.name or "",
        ),
    )
    return [
        {
            "id": r.id,
            "name": r.name,
            "building": r.building,
            "capacity": r.capacity,
            "has_computers": r.has_computers,
            "room_type": _infer_room_type(r.capacity, r.name),
            "is_active": r.is_active,
        }
        for r in sorted_rooms
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_room(
    req: CreateRoomRequest,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Manually creates a new classroom configured according to student/drive requirements."""
    # Check if room name already exists
    existing = db.execute(select(RoomModel).where(RoomModel.name == req.name)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A room or classroom with the name '{req.name}' already exists.",
        )

    # Generate clean room id
    r_id = req.name.lower().strip().replace(" ", "_").replace("-", "_")
    check_id = db.execute(select(RoomModel).where(RoomModel.id == r_id)).scalar_one_or_none()
    if check_id:
        r_id = f"{r_id}_{int(datetime.datetime.now().timestamp())}"

    new_room = RoomModel(
        id=r_id,
        name=req.name,
        building=req.building,
        capacity=req.capacity,
        has_computers=req.has_computers,
        is_active=req.is_active,
    )
    db.add(new_room)
    db.commit()
    db.refresh(new_room)

    return {
        "status": "created",
        "room": {
            "id": new_room.id,
            "name": new_room.name,
            "building": new_room.building,
            "capacity": new_room.capacity,
            "has_computers": new_room.has_computers,
            "room_type": _infer_room_type(new_room.capacity, new_room.name),
            "is_active": new_room.is_active,
        },
    }


@router.post("/provision-for-students")
def provision_classrooms_for_students(
    req: AutoProvisionRequest,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Automatically provisions new classrooms when existing inventory is insufficient
    for the required number of students and panels.
    """
    all_rooms = list(db.execute(select(RoomModel)).scalars().all())
    existing_ids = {r.id for r in all_rooms}
    existing_names = {r.name for r in all_rooms}

    busy_room_ids: set[str] = set()
    if req.target_date:
        day_start = datetime.datetime.combine(req.target_date, datetime.time.min)
        day_end = datetime.datetime.combine(req.target_date, datetime.time.max)
        busy_room_ids = set(
            db.execute(
                select(SlotModel.room_id)
                .where(
                    SlotModel.start_time >= day_start,
                    SlotModel.start_time <= day_end,
                )
                .distinct()
            ).scalars().all()
        )

    # Calculate classrooms needed based on round type and students count
    if req.round_type.lower() == "test":
        # Group exam / test round
        needed_classrooms = max(1, math.ceil(req.students_count / req.capacity_per_room))
        available_rooms = [
            r for r in all_rooms
            if r.is_active and r.id not in busy_room_ids and r.capacity >= req.capacity_per_room
        ]
    else:
        # Interview round: 14 sessions per panel in an 8h day
        needed_classrooms = max(1, math.ceil(req.students_count / 14))
        available_rooms = [
            r for r in all_rooms
            if r.is_active and r.id not in busy_room_ids and r.capacity <= 60
        ]

    deficit = max(0, needed_classrooms - len(available_rooms))
    provisioned: list[dict[str, Any]] = []

    c_num = 101
    while len(provisioned) < deficit:
        class_id = f"room_class_{c_num}"
        class_name = f"Classroom {c_num}"
        while class_id in existing_ids or class_name in existing_names:
            c_num += 1
            class_id = f"room_class_{c_num}"
            class_name = f"Classroom {c_num}"

        new_c = RoomModel(
            id=class_id,
            name=class_name,
            building=req.preferred_building,
            capacity=req.capacity_per_room,
            has_computers=False,
            is_active=True,
        )
        db.add(new_c)
        db.flush()
        existing_ids.add(class_id)
        existing_names.add(class_name)
        provisioned.append({
            "id": new_c.id,
            "name": new_c.name,
            "building": new_c.building,
            "capacity": new_c.capacity,
        })
        c_num += 1

    db.commit()

    return {
        "status": "success",
        "round_type": req.round_type,
        "students_count": req.students_count,
        "needed_classrooms": needed_classrooms,
        "previously_available": len(available_rooms),
        "newly_provisioned_count": len(provisioned),
        "provisioned_rooms": provisioned,
        "total_active_rooms": len(all_rooms) + len(provisioned),
    }
