"""
Campus Recruitment Drive Management Routes.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.auth.dependencies import require_officer, require_officer_or_coordinator
from backend.app.domain.models import DriveMode, DriveStatus
from backend.app.storage.database import get_db
import json
from backend.app.storage.models.entities import CompanyModel, DriveModel, DriveRequirementVersionModel, UserModel

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
    current_user: UserModel = Depends(require_officer),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Deletes a drive record (Officer only)."""
    stmt = select(DriveModel).where(DriveModel.id == drive_id)
    drive = db.execute(stmt).scalar_one_or_none()
    if not drive:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drive not found.")

    db.delete(drive)
    db.commit()
    return {"message": "Drive deleted successfully."}
