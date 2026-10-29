"""
What-If Change Impact Preview and Direct Apply/Publish Routes.
Zero-persistence in-memory simulation of cut-offs, backlogs, branches, and overrides,
with one-click atomic publication of simulated What-If adjustments.
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
from backend.app.domain.impact.models import ChangeRequest, ChangeType, ImpactReport
from backend.app.domain.impact.what_if import WhatIfEngine
from backend.app.domain.models import Drive, RequirementSet
from backend.app.domain.policy.catalog import STRICT_ONE_OFFER_POLICY
from backend.app.events.event_service import EventService
from backend.app.importers.canonical_maps import parse_allowed_branches
from backend.app.scheduler.models import RoomType, SchedulerRoom
from backend.app.storage.database import get_db
from backend.app.storage.models.entities import (
    DriveModel,
    DriveRequirementVersionModel,
    EligibilityDecisionModel,
    EligibilityRunModel,
    EventModel,
    RoomModel,
    StudentModel,
    UserModel,
)
from backend.app.storage.repositories.mappers import student_entity_to_domain
from backend.app.storage.repositories.sqlalchemy_repo import SqlAlchemyUnitOfWork

router = APIRouter(prefix="/api/what-if", tags=["What-If Simulation"])

_what_if_engine = WhatIfEngine()


class ApplyWhatIfRequest(BaseModel):
    drive_id: str
    change: ChangeRequest
    reason: str = "Applied and published What-If simulated criteria adjustment"


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

    latest_req = (
        sorted(drive_entity.requirement_versions, key=lambda r: r.version_number, reverse=True)[0]
        if drive_entity.requirement_versions
        else None
    )
    raw_branches = latest_req.allowed_branches_json if latest_req else None
    branches = parse_allowed_branches(raw_branches) if raw_branches else ["CSE", "IT", "ECE"]

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


@router.post("/apply")
def apply_what_if_and_publish(
    req: ApplyWhatIfRequest,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Atomically applies a simulated What-If adjustment to the drive, persists a new
    requirement version, re-evaluates student eligibility, advances the drive version,
    marks it published, and appends an audit event.
    """
    drive_stmt = select(DriveModel).where(DriveModel.id == req.drive_id)
    drive_entity = db.execute(drive_stmt).scalar_one_or_none()
    if not drive_entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target drive not found.")

    latest_req = (
        sorted(drive_entity.requirement_versions, key=lambda r: r.version_number, reverse=True)[0]
        if drive_entity.requirement_versions
        else None
    )

    old_branches = parse_allowed_branches(latest_req.allowed_branches_json) if latest_req else ["CSE", "IT", "ECE"]
    min_cgpa = latest_req.min_cgpa if latest_req else 6.0
    min_tenth = latest_req.min_tenth_percentage if latest_req else 60.0
    min_twelfth = latest_req.min_twelfth_percentage if latest_req else None
    max_active_backlogs = latest_req.max_active_backlogs if latest_req else 0
    max_gap_years = latest_req.max_gap_years if latest_req else 1
    branches = list(old_branches)

    ch = req.change
    if ch.change_type == ChangeType.CGPA_CUTOFF:
        min_cgpa = float(ch.new_value)
    elif ch.change_type == ChangeType.BACKLOG_RULE:
        max_active_backlogs = int(ch.new_value)
    elif ch.change_type == ChangeType.BRANCH_ADDED:
        b_name = ch.branch_name or str(ch.new_value)
        if b_name not in branches:
            branches.append(b_name)
    elif ch.change_type == ChangeType.BRANCH_REMOVED:
        b_name = ch.branch_name or str(ch.new_value)
        branches = [b for b in branches if b != b_name]
    elif ch.change_type == ChangeType.DRIVE_DATE_SHIFT:
        if isinstance(ch.new_value, str):
            drive_entity.drive_date = datetime.date.fromisoformat(ch.new_value)
        elif isinstance(ch.new_value, datetime.date):
            drive_entity.drive_date = ch.new_value
    elif ch.change_type == ChangeType.PERCENTAGE_CUTOFF:
        if ch.target_field == "10th":
            min_tenth = float(ch.new_value)
        elif ch.target_field == "12th":
            min_twelfth = float(ch.new_value)
    elif ch.change_type == ChangeType.GAP_YEAR:
        max_gap_years = int(ch.new_value)

    new_version = drive_entity.version + 1

    # Create new requirement version
    new_req_model = DriveRequirementVersionModel(
        id=f"req_{drive_entity.id}_v{new_version}_{uuid.uuid4().hex[:6]}",
        drive_id=drive_entity.id,
        version_number=new_version,
        min_cgpa=min_cgpa,
        min_tenth_percentage=min_tenth,
        min_twelfth_percentage=min_twelfth,
        allowed_branches_json=json.dumps(branches),
        max_active_backlogs=max_active_backlogs,
        max_gap_years=max_gap_years,
        raw_source_text=f"Updated via What-If: {ch.change_type.value}",
    )
    db.add(new_req_model)

    # Re-evaluate eligibility for all students
    req_domain = RequirementSet(
        id=new_req_model.id,
        drive_id=drive_entity.id,
        min_cgpa=min_cgpa,
        min_tenth_percentage=min_tenth,
        min_twelfth_percentage=min_twelfth,
        allowed_branches=branches,
        max_active_backlogs=max_active_backlogs,
        max_gap_years=max_gap_years,
    )
    ruleset = _what_if_engine._build_ruleset_from_requirements(req_domain)
    students = [student_entity_to_domain(s) for s in db.execute(select(StudentModel)).scalars().all()]

    # Clear previous eligibility decisions for this drive
    db.execute(delete(EligibilityDecisionModel).where(EligibilityDecisionModel.drive_id == drive_entity.id))

    run_id = f"run_what_if_{drive_entity.id}_v{new_version}_{uuid.uuid4().hex[:6]}"
    decisions_to_add = []
    newly_shortlisted = 0
    now = datetime.datetime.utcnow()

    for stu in students:
        eval_res = _what_if_engine.evaluator.evaluate(stu, ruleset, drive_id=drive_entity.id)
        if eval_res.status.value == "eligible":
            newly_shortlisted += 1
            dec = EligibilityDecisionModel(
                id=f"dec_{drive_entity.id}_{stu.id}_{uuid.uuid4().hex[:6]}",
                run_id=run_id,
                drive_id=drive_entity.id,
                student_id=stu.id,
                status="eligible",
                reasons_json=json.dumps([eval_res.overall_student_reason or f"Eligible for {drive_entity.company_name} v{new_version}"]),
                rule_ids_json="[]",
                evaluated_at=now,
            )
            decisions_to_add.append(dec)

    run_model = EligibilityRunModel(
        id=run_id,
        drive_id=drive_entity.id,
        requirement_version_id=new_req_model.id,
        policy_id="pol_default_active",
        executed_at=now,
        total_evaluated=len(students),
        total_eligible=newly_shortlisted,
        total_ineligible=len(students) - newly_shortlisted,
        executed_by=current_user.username,
    )
    db.add(run_model)
    db.flush()

    for dec in decisions_to_add:
        db.add(dec)

    # Update drive
    old_version = drive_entity.version
    drive_entity.version = new_version
    drive_entity.status = "published"

    # Audit logging using the same active database session
    event = EventModel(
        id=str(uuid.uuid4()),
        aggregate_type="DRIVE_WHAT_IF_PUBLISH",
        aggregate_id=drive_entity.id,
        event_type="DRIVE_WHAT_IF_APPLIED_AND_PUBLISHED",
        actor=current_user.username,
        timestamp=datetime.datetime.utcnow(),
        payload_json=json.dumps({
            "before": {"version": old_version, "status": "draft"},
            "after": {
                "version": new_version,
                "status": "published",
                "shortlist_count": newly_shortlisted,
                "change": ch.model_dump(mode="json"),
            },
            "reason": req.reason,
        }),
    )
    db.add(event)
    db.commit()

    return {
        "success": True,
        "drive_id": drive_entity.id,
        "version": new_version,
        "status": "published",
        "shortlist_count": newly_shortlisted,
        "message": f"Successfully applied {ch.change_type.value} and published v{new_version} for {drive_entity.company_name}!",
    }
