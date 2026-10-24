"""
What-If Change Impact Preview Routes.
Zero-persistence in-memory simulation of cut-offs, backlogs, branches, and overrides.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.auth.dependencies import require_officer_or_coordinator
from backend.app.domain.impact.models import ChangeRequest, ImpactReport
from backend.app.domain.impact.what_if import WhatIfEngine
from backend.app.domain.models import Drive, RequirementSet
from backend.app.domain.policy.catalog import STRICT_ONE_OFFER_POLICY
from backend.app.scheduler.models import RoomType, SchedulerRoom
from backend.app.storage.database import get_db
from backend.app.storage.models.entities import (
    DriveModel,
    EligibilityDecisionModel,
    RoomModel,
    StudentModel,
    UserModel,
)
from backend.app.storage.repositories.mappers import student_entity_to_domain

router = APIRouter(prefix="/api/what-if", tags=["What-If Simulation"])

_what_if_engine = WhatIfEngine()


@router.post("/simulate", response_model=ImpactReport)
def simulate_change(
    change: ChangeRequest,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> ImpactReport:
    """
    Applies proposed placement changes in-memory without persistence.
    Computes exact student deltas, schedule collisions, and second-order causal effects.
    """
    # 1. Fetch current drive
    drive_stmt = select(DriveModel).where(DriveModel.id == change.drive_id)
    drive_entity = db.execute(drive_stmt).scalar_one_or_none()
    if not drive_entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target drive not found.")

    latest_req = drive_entity.requirement_versions[0] if drive_entity.requirement_versions else None
    branches = ["CSE", "IT", "ECE"]
    if latest_req and latest_req.allowed_branches_json:
        if isinstance(latest_req.allowed_branches_json, str):
            try:
                branches = json.loads(latest_req.allowed_branches_json)
            except Exception:
                branches = [b.strip() for b in latest_req.allowed_branches_json.split(",") if b.strip()]
        elif isinstance(latest_req.allowed_branches_json, list):
            branches = latest_req.allowed_branches_json

    req_domain = RequirementSet(
        id=latest_req.id if latest_req else "req_def",
        drive_id=drive_entity.id,
        min_cgpa=latest_req.min_cgpa if latest_req else 6.0,
        min_tenth_percentage=latest_req.min_tenth_percentage if latest_req else 60.0,
        min_twelfth_percentage=latest_req.min_twelfth_percentage if latest_req else None,
        allowed_branches=branches,
        max_active_backlogs=latest_req.max_active_backlogs if latest_req else 0,
        max_gap_years=latest_req.max_gap_years if latest_req else 1,
    )

    drive_domain = Drive(
        id=drive_entity.id,
        company_id=drive_entity.company_id,
        company_name=drive_entity.company_name,
        drive_date=drive_entity.drive_date,
        ctc_lpa=drive_entity.ctc_lpa,
        requirements=req_domain,
        version=drive_entity.version,
    )

    # 2. Fetch all drives for second-order tracing
    all_drives = [
        Drive(
            id=d.id,
            company_id=d.company_id,
            company_name=d.company_name,
            drive_date=d.drive_date,
            ctc_lpa=d.ctc_lpa,
        )
        for d in db.execute(select(DriveModel)).scalars().all()
    ]

    # 3. Fetch candidates
    students = [student_entity_to_domain(s) for s in db.execute(select(StudentModel)).scalars().all()]

    # 4. Fetch current shortlist
    dec_stmt = select(EligibilityDecisionModel).where(
        EligibilityDecisionModel.drive_id == change.drive_id,
        EligibilityDecisionModel.status == "eligible",
    )
    current_shortlist = [d.student_id for d in db.execute(dec_stmt).scalars().all()]

    # 5. Rooms
    rooms = [
        SchedulerRoom(
            id=r.id,
            name=r.name,
            building=r.building,
            room_type=RoomType.HALL if r.capacity >= 50 else RoomType.CABIN,
            capacity=r.capacity,
        )
        for r in db.execute(select(RoomModel)).scalars().all()
    ]

    report = _what_if_engine.apply_change(
        current_drive=drive_domain,
        all_drives=all_drives,
        students=students,
        rooms=rooms,
        policy=STRICT_ONE_OFFER_POLICY,
        current_shortlist=current_shortlist,
        current_schedule_items=[],
        change=change,
    )

    return report
