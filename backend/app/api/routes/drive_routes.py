"""
Campus Recruitment Drive Management Routes.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from backend.app.api.auth.dependencies import require_officer, require_officer_or_coordinator
from backend.app.api.logging.audit_service import AuditService
from backend.app.domain.models import DriveMode, DriveStatus
from backend.app.storage.database import get_db
import json
from backend.app.storage.models.entities import (
    CompanyModel,
    DriveModel,
    DriveRequirementVersionModel,
    EligibilityDecisionModel,
    EligibilityRunModel,
    PanelModel,
    SlotModel,
    DriveAttendanceModel,
    PendingResultModel,
    UserModel,
)

router = APIRouter(prefix="/api/drives", tags=["Recruitment Drives"])


class DriveCreateUpdateRequest(BaseModel):
    company_name: str
    drive_date: datetime.date
    mode: DriveMode = DriveMode.ON_CAMPUS
    status: DriveStatus = DriveStatus.DRAFT
    ctc_lpa: float = Field(ge=0.0)
    fixed_pay_lpa: float | None = Field(default=None, ge=0.0)
    job_role: str | None = None
    job_location: str | None = None
    min_cgpa: float = Field(default=6.0, ge=0.0, le=10.0)
    min_tenth_percentage: float = Field(default=60.0, ge=0.0, le=100.0)
    min_twelfth_percentage: float | None = Field(default=None, ge=0.0, le=100.0)
    allowed_branches: list[str] = Field(default_factory=lambda: ["CSE", "IT", "ECE"])
    max_active_backlogs: int = 0
    max_history_backlogs: int | None = None
    max_gap_years: int | None = 1
    min_diploma_percentage: float | None = Field(default=None, ge=0.0, le=100.0)
    allow_gap_during_degree: bool = False


@router.get("")
def list_drives(
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Lists all recruitment drives."""
    stmt = select(DriveModel).order_by(DriveModel.drive_date.asc())
    drives = db.execute(stmt).scalars().all()
    return [
        {
            "id": d.id,
            "company_name": d.company_name,
            "drive_date": d.drive_date.isoformat(),
            "mode": d.mode,
            "status": d.status,
            "ctc_lpa": d.ctc_lpa,
            "version": d.version,
        }
        for d in drives
    ]


@router.get("/overview-metrics")
def get_overview_metrics(
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Computes summary metrics for Home/Overview module (Module 1)."""
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)
    week_ahead = today + datetime.timedelta(days=7)

    all_drives = db.execute(select(DriveModel)).scalars().all()

    today_drives = [d for d in all_drives if d.drive_date == today]
    tomorrow_drives = [d for d in all_drives if d.drive_date == tomorrow]
    this_week_drives = [d for d in all_drives if today <= d.drive_date <= week_ahead]

    # Total shortlisted students (eligible status)
    shortlisted_decisions = db.execute(
        select(EligibilityDecisionModel).where(EligibilityDecisionModel.status == "eligible")
    ).scalars().all()
    unique_shortlisted = len({d.student_id for d in shortlisted_decisions})

    # Needs review decisions
    needs_review_count = len(
        db.execute(
            select(EligibilityDecisionModel).where(EligibilityDecisionModel.status == "needs_review")
        ).scalars().all()
    )

    # Unresolved clashes across all slots
    slots = db.execute(select(SlotModel)).scalars().all()
    clashes_count = 0
    for i in range(len(slots)):
        for j in range(i + 1, len(slots)):
            if (
                slots[i].student_id == slots[j].student_id
                and slots[i].start_time == slots[j].start_time
            ):
                clashes_count += 1

    # Stale versions (drives where requirements were never locked or versions > 1)
    stale_versions = len([d for d in all_drives if d.version > 1 and d.status != "published"])

    return {
        "upcoming": {
            "today": len(today_drives),
            "tomorrow": len(tomorrow_drives),
            "this_week": len(this_week_drives),
        },
        "total_drives": len(all_drives),
        "total_shortlisted_students": unique_shortlisted,
        "unresolved_clashes": clashes_count,
        "needs_review_count": needs_review_count,
        "pending_coordinator_requests": 0,
        "stale_versions_count": stale_versions,
    }


@router.get("/{drive_id}")
def get_drive(
    drive_id: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retrieves recruitment drive details and requirement configuration."""
    stmt = select(DriveModel).where(DriveModel.id == drive_id)
    drive = db.execute(stmt).scalar_one_or_none()
    if not drive:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drive not found.")

    latest_req = drive.requirement_versions[0] if drive.requirement_versions else None

    return {
        "id": drive.id,
        "company_name": drive.company_name,
        "drive_date": drive.drive_date.isoformat(),
        "mode": drive.mode,
        "status": drive.status,
        "ctc_lpa": drive.ctc_lpa,
        "version": drive.version,
        "requirements": {
            "min_cgpa": latest_req.min_cgpa if latest_req else 6.0,
            "min_tenth_percentage": latest_req.min_tenth_percentage if latest_req else 60.0,
            "min_twelfth_percentage": latest_req.min_twelfth_percentage if latest_req else None,
            "allowed_branches": latest_req.allowed_branches_json if latest_req else [],
            "max_active_backlogs": latest_req.max_active_backlogs if latest_req else 0,
            "max_gap_years": latest_req.max_gap_years if latest_req else 1,
        } if latest_req else None,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_drive(
    req: DriveCreateUpdateRequest,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Creates a new campus recruitment drive with default requirements."""
    stmt_comp = select(CompanyModel).where(CompanyModel.name == req.company_name)
    existing_company = db.execute(stmt_comp).scalar_one_or_none()
    if existing_company:
        company_id = existing_company.id
    else:
        company_id = f"comp_{uuid.uuid4().hex[:8]}"
        company = CompanyModel(
            id=company_id,
            name=req.company_name,
            tier="Tier 1",
        )
        db.add(company)
        db.flush()

    drive_id = f"drv_{uuid.uuid4().hex[:8]}"
    drive = DriveModel(
        id=drive_id,
        company_id=company_id,
        company_name=req.company_name,
        drive_date=req.drive_date,
        mode=req.mode.value,
        status=req.status.value,
        ctc_lpa=req.ctc_lpa,
        version=1,
    )
    db.add(drive)
    db.flush()

    req_version = DriveRequirementVersionModel(
        id=f"req_{uuid.uuid4().hex[:8]}",
        drive_id=drive_id,
        version_number=1,
        min_cgpa=req.min_cgpa,
        min_tenth_percentage=req.min_tenth_percentage,
        min_twelfth_percentage=req.min_twelfth_percentage,
        allowed_branches_json=json.dumps(req.allowed_branches) if isinstance(req.allowed_branches, list) else str(req.allowed_branches),
        allowed_programs_json=json.dumps(["B.Tech", "M.Tech"]),
        max_active_backlogs=req.max_active_backlogs,
        max_history_backlogs=req.max_history_backlogs,
        max_gap_years=req.max_gap_years,
        min_diploma_percentage=req.min_diploma_percentage,
        allow_gap_during_degree=req.allow_gap_during_degree,
        created_at=datetime.datetime.utcnow(),
    )
    db.add(req_version)
    db.commit()

    return {"id": drive_id, "company_name": req.company_name, "message": "Drive registered successfully."}


@router.put("/{drive_id}")
def update_drive(
    drive_id: str,
    req: DriveCreateUpdateRequest,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Updates drive date, mode, package, or status."""
    stmt = select(DriveModel).where(DriveModel.id == drive_id)
    drive = db.execute(stmt).scalar_one_or_none()
    if not drive:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drive not found.")

    drive.company_name = req.company_name
    drive.drive_date = req.drive_date
    drive.mode = req.mode.value
    drive.status = req.status.value
    drive.ctc_lpa = req.ctc_lpa
    drive.version += 1

    db.commit()
    return {"id": drive_id, "version": drive.version, "message": "Drive updated successfully."}


@router.delete("/{drive_id}")
def delete_drive(
    drive_id: str,
    reason: str = "Drive removed by placement officer",
    current_user: UserModel = Depends(require_officer),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Permanently removes a drive record with audit justification (Officer only)."""
    stmt = select(DriveModel).where(DriveModel.id == drive_id)
    drive = db.execute(stmt).scalar_one_or_none()
    if not drive:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drive not found.")

    company_name = drive.company_name

    # Cleanly remove associated records across all dependent tables
    db.execute(delete(DriveAttendanceModel).where(DriveAttendanceModel.drive_id == drive_id))
    db.execute(delete(PendingResultModel).where(PendingResultModel.drive_id == drive_id))
    db.execute(delete(SlotModel).where(SlotModel.drive_id == drive_id))
    db.execute(delete(EligibilityDecisionModel).where(EligibilityDecisionModel.drive_id == drive_id))
    db.execute(delete(EligibilityRunModel).where(EligibilityRunModel.drive_id == drive_id))
    db.execute(delete(PanelModel).where(PanelModel.drive_id == drive_id))
    db.execute(delete(DriveRequirementVersionModel).where(DriveRequirementVersionModel.drive_id == drive_id))

    db.delete(drive)

    AuditService.record_action(
        db=db,
        actor=f"{current_user.role}:{current_user.username}",
        action="DRIVE_REMOVED",
        aggregate_type="DRIVE",
        aggregate_id=drive_id,
        payload={
            "company_name": company_name,
            "reason": reason,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        },
    )

    db.commit()
    return {"message": f"Drive '{company_name}' removed permanently. Reason: {reason}"}


@router.post("/{drive_id}/duplicate")
def duplicate_drive(
    drive_id: str,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Duplicates an existing drive with its full requirement criteria (Module 4)."""
    drive = db.execute(select(DriveModel).where(DriveModel.id == drive_id)).scalar_one_or_none()
    if not drive:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drive not found.")

    new_id = f"drv_{uuid.uuid4().hex[:8]}"
    new_drive = DriveModel(
        id=new_id,
        company_id=drive.company_id,
        company_name=f"{drive.company_name} (Copy)",
        drive_date=drive.drive_date,
        mode=drive.mode,
        status="draft",
        ctc_lpa=drive.ctc_lpa,
        version=1,
    )
    db.add(new_drive)
    db.flush()

    latest_req = drive.requirement_versions[0] if drive.requirement_versions else None
    if latest_req:
        new_req = DriveRequirementVersionModel(
            id=f"req_{uuid.uuid4().hex[:8]}",
            drive_id=new_id,
            version_number=1,
            min_cgpa=latest_req.min_cgpa,
            min_tenth_percentage=latest_req.min_tenth_percentage,
            min_twelfth_percentage=latest_req.min_twelfth_percentage,
            allowed_branches_json=latest_req.allowed_branches_json,
            allowed_programs_json=latest_req.allowed_programs_json,
            max_active_backlogs=latest_req.max_active_backlogs,
            max_history_backlogs=latest_req.max_history_backlogs,
            max_gap_years=latest_req.max_gap_years,
            min_diploma_percentage=latest_req.min_diploma_percentage,
            allow_gap_during_degree=latest_req.allow_gap_during_degree,
            created_at=datetime.datetime.utcnow(),
        )
        db.add(new_req)

    db.commit()
    return {
        "id": new_id,
        "company_name": new_drive.company_name,
        "message": f"Drive successfully duplicated as '{new_drive.company_name}'.",
    }


class CancelDriveRequest(BaseModel):
    reason: str = Field(min_length=3)


@router.post("/{drive_id}/cancel")
def cancel_drive(
    drive_id: str,
    req: CancelDriveRequest,
    current_user: UserModel = Depends(require_officer),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Cancels a drive with mandatory audit reason (Module 1)."""
    drive = db.execute(select(DriveModel).where(DriveModel.id == drive_id)).scalar_one_or_none()
    if not drive:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drive not found.")

    drive.status = "cancelled"
    drive.version += 1
    db.commit()

    return {
        "id": drive_id,
        "status": "cancelled",
        "message": f"Drive '{drive.company_name}' marked as cancelled. Reason: {req.reason}",
    }
