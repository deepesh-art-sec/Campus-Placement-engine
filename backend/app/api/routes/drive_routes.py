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
from backend.app.importers.canonical_maps import parse_allowed_branches
from backend.app.scheduler.clash_service import count_unresolved_clashes
from backend.app.storage.models.entities import (
    AttendanceRecordModel,
    CompanyExportMappingModel,
    CompanyModel,
    CoordinatorRequestModel,
    DriveAttendanceModel,
    DriveModel,
    DriveRequirementVersionModel,
    EligibilityDecisionModel,
    EligibilityRunModel,
    NotificationModel,
    OfferModel,
    PanelModel,
    PendingResultModel,
    PlacementRequestModel,
    SlotModel,
    StudentApplicationModel,
    StudentModel,
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
    results = []
    for d in drives:
        latest_req = sorted(d.requirement_versions, key=lambda r: r.version_number, reverse=True)[0] if d.requirement_versions else None
        results.append({
            "id": d.id,
            "company_name": d.company_name,
            "drive_date": d.drive_date.isoformat(),
            "mode": d.mode,
            "status": d.status,
            "ctc_lpa": d.ctc_lpa,
            "version": d.version,
            "applied_count": len([a for a in d.applications if a.status == "applied"]),
            "requirements": {
                "min_cgpa": latest_req.min_cgpa if latest_req else 6.0,
                "min_tenth_percentage": latest_req.min_tenth_percentage if latest_req else 60.0,
                "min_twelfth_percentage": latest_req.min_twelfth_percentage if latest_req else None,
                "allowed_branches": parse_allowed_branches(latest_req.allowed_branches_json) if latest_req else ["CSE", "IT", "ECE"],
                "max_active_backlogs": latest_req.max_active_backlogs if latest_req else 0,
                "max_gap_years": latest_req.max_gap_years if latest_req else 1,
            } if latest_req else None,
        })
    return results


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

    # Unresolved clashes across published drive slots (deduplicated & filtered)
    clashes_count = count_unresolved_clashes(db)

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
        "applied_count": len([a for a in drive.applications if a.status == "applied"]),
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
    """Creates a new campus recruitment drive with deduplication guardrails (idempotent upsert)."""
    clean_company = req.company_name.strip()
    stmt_existing = select(DriveModel).where(
        (DriveModel.company_name.ilike(clean_company))
        & (DriveModel.status != "cancelled")
    )
    existing_drive = db.execute(stmt_existing).scalars().first()
    branches_json = json.dumps(req.allowed_branches) if isinstance(req.allowed_branches, list) else str(req.allowed_branches)

    if existing_drive:
        # Update existing drive in place so user changes are saved reliably without creating duplicates
        existing_drive.drive_date = req.drive_date
        existing_drive.mode = req.mode.value
        existing_drive.status = req.status.value
        existing_drive.ctc_lpa = req.ctc_lpa
        existing_drive.version += 1

        if existing_drive.company_id:
            comp = db.execute(select(CompanyModel).where(CompanyModel.id == existing_drive.company_id)).scalar_one_or_none()
            if comp:
                comp.name = req.company_name

        stmt_req = (
            select(DriveRequirementVersionModel)
            .where(DriveRequirementVersionModel.drive_id == existing_drive.id)
            .order_by(DriveRequirementVersionModel.version_number.desc())
        )
        req_version = db.execute(stmt_req).scalars().first()
        if req_version:
            req_version.min_cgpa = req.min_cgpa
            req_version.min_tenth_percentage = req.min_tenth_percentage
            req_version.min_twelfth_percentage = req.min_twelfth_percentage
            req_version.allowed_branches_json = branches_json
            req_version.max_active_backlogs = req.max_active_backlogs
            req_version.max_history_backlogs = req.max_history_backlogs
            req_version.max_gap_years = req.max_gap_years
            req_version.min_diploma_percentage = req.min_diploma_percentage
            req_version.allow_gap_during_degree = req.allow_gap_during_degree
            req_version.version_number = existing_drive.version
        else:
            req_version = DriveRequirementVersionModel(
                id=f"req_{uuid.uuid4().hex[:8]}",
                drive_id=existing_drive.id,
                version_number=existing_drive.version,
                min_cgpa=req.min_cgpa,
                min_tenth_percentage=req.min_tenth_percentage,
                min_twelfth_percentage=req.min_twelfth_percentage,
                allowed_branches_json=branches_json,
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
        return {
            "id": existing_drive.id,
            "company_name": existing_drive.company_name,
            "version": existing_drive.version,
            "message": "Drive criteria updated successfully (no duplicate created).",
        }

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
        allowed_branches_json=branches_json,
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

    # Automatically save & mirror company and drive into MongoDB Atlas
    try:
        from backend.app.storage.mongodb import get_mongo_db
        mongo_db = get_mongo_db()
        if mongo_db is not None:
            now_iso = datetime.datetime.utcnow().isoformat()
            mongo_db.companies.update_one(
                {"_id": company_id},
                {
                    "$set": {
                        "_id": company_id,
                        "id": company_id,
                        "name": req.company_name,
                        "tier": "Tier 1",
                        "industry": "Technology",
                        "website": f"https://{req.company_name.lower().replace(' ', '')}.com",
                        "synced_at": now_iso,
                    }
                },
                upsert=True,
            )
            mongo_db.drives.update_one(
                {"_id": drive_id},
                {
                    "$set": {
                        "_id": drive_id,
                        "id": drive_id,
                        "company_id": company_id,
                        "company_name": req.company_name,
                        "job_role": req.job_role or "Engineering Trainee",
                        "drive_date": req.drive_date.isoformat() if req.drive_date else None,
                        "mode": req.mode.value if hasattr(req.mode, "value") else str(req.mode),
                        "status": req.status.value if hasattr(req.status, "value") else str(req.status),
                        "ctc_lpa": req.ctc_lpa,
                        "version": 1,
                        "requirements": [
                            {
                                "min_cgpa": req.min_cgpa,
                                "min_tenth_percentage": req.min_tenth_percentage,
                                "min_twelfth_percentage": req.min_twelfth_percentage,
                                "allowed_branches": parse_allowed_branches(req.allowed_branches),
                                "max_active_backlogs": req.max_active_backlogs,
                            }
                        ],
                        "synced_at": now_iso,
                    }
                },
                upsert=True,
            )
    except Exception:
        pass

    return {"id": drive_id, "company_name": req.company_name, "version": 1, "message": "Drive registered successfully."}


@router.put("/{drive_id}")
def update_drive(
    drive_id: str,
    req: DriveCreateUpdateRequest,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Updates drive date, mode, package, status, and academic requirement criteria."""
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

    # Synchronize company entity name
    if drive.company_id:
        comp = db.execute(select(CompanyModel).where(CompanyModel.id == drive.company_id)).scalar_one_or_none()
        if comp:
            comp.name = req.company_name

    # Synchronize requirement version criteria
    stmt_req = (
        select(DriveRequirementVersionModel)
        .where(DriveRequirementVersionModel.drive_id == drive_id)
        .order_by(DriveRequirementVersionModel.version_number.desc())
    )
    req_version = db.execute(stmt_req).scalars().first()
    branches_json = json.dumps(req.allowed_branches) if isinstance(req.allowed_branches, list) else str(req.allowed_branches)

    if req_version:
        req_version.min_cgpa = req.min_cgpa
        req_version.min_tenth_percentage = req.min_tenth_percentage
        req_version.min_twelfth_percentage = req.min_twelfth_percentage
        req_version.allowed_branches_json = branches_json
        req_version.max_active_backlogs = req.max_active_backlogs
        req_version.max_history_backlogs = req.max_history_backlogs
        req_version.max_gap_years = req.max_gap_years
        req_version.min_diploma_percentage = req.min_diploma_percentage
        req_version.allow_gap_during_degree = req.allow_gap_during_degree
        req_version.version_number = drive.version
    else:
        req_version = DriveRequirementVersionModel(
            id=f"req_{uuid.uuid4().hex[:8]}",
            drive_id=drive_id,
            version_number=drive.version,
            min_cgpa=req.min_cgpa,
            min_tenth_percentage=req.min_tenth_percentage,
            min_twelfth_percentage=req.min_twelfth_percentage,
            allowed_branches_json=branches_json,
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
    return {"id": drive_id, "version": drive.version, "message": "Drive and criteria updated successfully."}


@router.delete("/{drive_id}")
def delete_drive(
    drive_id: str,
    reason: str = "Drive removed by placement officer",
    current_user: UserModel = Depends(require_officer),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Permanently purges a company and its drive across all dashboards (Officer only)."""
    stmt = select(DriveModel).where(DriveModel.id == drive_id)
    drive = db.execute(stmt).scalar_one_or_none()
    if not drive:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drive not found.")

    company_name = drive.company_name
    company_id = drive.company_id

    # 1. Identify all drives associated with this company
    company_drives = db.execute(
        select(DriveModel).where(
            (DriveModel.company_id == company_id) | (DriveModel.company_name == company_name)
        )
    ).scalars().all()
    all_drive_ids = list({d.id for d in company_drives} | {drive_id})

    # 2. Cleanly purge dependent records for all target drive IDs
    for did in all_drive_ids:
        db.execute(delete(DriveAttendanceModel).where(DriveAttendanceModel.drive_id == did))
        db.execute(delete(AttendanceRecordModel).where(AttendanceRecordModel.drive_id == did))
        db.execute(delete(PendingResultModel).where(PendingResultModel.drive_id == did))
        db.execute(delete(SlotModel).where(SlotModel.drive_id == did))
        db.execute(delete(EligibilityDecisionModel).where(EligibilityDecisionModel.drive_id == did))
        db.execute(delete(EligibilityRunModel).where(EligibilityRunModel.drive_id == did))
        db.execute(delete(PanelModel).where(PanelModel.drive_id == did))
        db.execute(delete(StudentApplicationModel).where(StudentApplicationModel.drive_id == did))
        db.execute(delete(DriveRequirementVersionModel).where(DriveRequirementVersionModel.drive_id == did))
        db.execute(delete(CoordinatorRequestModel).where(CoordinatorRequestModel.target_id == did))
        db.execute(delete(PlacementRequestModel).where(PlacementRequestModel.drive_id == did))

    # 3. Cleanly remove offers associated with this company & recalculate affected students' versions
    offers = db.execute(select(OfferModel).where(OfferModel.company == company_name)).scalars().all()
    affected_student_ids = {off.student_id for off in offers if off.student_id}
    db.execute(delete(OfferModel).where(OfferModel.company == company_name))
    for stu_id in affected_student_ids:
        stu = db.execute(select(StudentModel).where(StudentModel.id == stu_id)).scalar_one_or_none()
        if stu:
            stu.version += 1

    # 4. Clean up any coordinator requests referencing company
    db.execute(
        delete(CoordinatorRequestModel).where(
            (CoordinatorRequestModel.target_id == company_id)
            | (CoordinatorRequestModel.title.like(f"%{company_name}%"))
            | (CoordinatorRequestModel.description.like(f"%{company_name}%"))
        )
    )

    # 5. Clean up any placement requests referencing company
    db.execute(
        delete(PlacementRequestModel).where(
            PlacementRequestModel.subject.like(f"%{company_name}%")
        )
    )

    # 6. Clean up notifications referencing this company or drive
    for did in all_drive_ids:
        db.execute(delete(NotificationModel).where(NotificationModel.metadata_json.like(f"%{did}%")))
    db.execute(
        delete(NotificationModel).where(
            (NotificationModel.title.like(f"%{company_name}%"))
            | (NotificationModel.message.like(f"%{company_name}%"))
        )
    )

    # 7. Clean up company export mappings
    if company_id:
        db.execute(delete(CompanyExportMappingModel).where(CompanyExportMappingModel.company_id == company_id))
    db.execute(delete(CompanyExportMappingModel).where(CompanyExportMappingModel.company_name == company_name))

    # 8. Deactivate or unlink recruiter accounts tied to this company
    recruiter_users = db.execute(
        select(UserModel).where(
            (UserModel.company_id == company_id)
            | (UserModel.username == f"recruiter_{company_name.lower().replace(' ', '_')}")
        )
    ).scalars().all()
    for ru in recruiter_users:
        ru.company_id = None
        ru.is_active = False

    # 9. Delete all drives for this company
    db.execute(delete(DriveModel).where(DriveModel.id.in_(all_drive_ids)))

    # 10. Delete company completely from companies table
    if company_id:
        db.execute(delete(CompanyModel).where(CompanyModel.id == company_id))
    db.execute(delete(CompanyModel).where(CompanyModel.name == company_name))

    # 11. Record immutable audit log
    AuditService.record_action(
        db=db,
        actor=f"{current_user.role}:{current_user.username}",
        action="COMPANY_AND_DRIVE_PURGED_COMPLETELY",
        aggregate_type="DRIVE",
        aggregate_id=drive_id,
        payload={
            "company_name": company_name,
            "company_id": company_id,
            "deleted_drive_ids": all_drive_ids,
            "reason": reason,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        },
    )

    db.commit()

    # Synchronize deletion with MongoDB Atlas
    try:
        from backend.app.storage.mongodb import get_mongo_db
        mongo_db = get_mongo_db()
        if mongo_db is not None:
            for did in all_drive_ids:
                mongo_db.drives.delete_one({"_id": did})
                mongo_db.drive_requirements.delete_many({"drive_id": did})
                mongo_db.attendance.delete_many({"drive_id": did})
                mongo_db.eligibility_decisions.delete_many({"drive_id": did})
            if company_id:
                mongo_db.companies.delete_one({"_id": company_id})
            mongo_db.companies.delete_many({"name": company_name})
            mongo_db.offers.delete_many({"company_name": company_name})
    except Exception:
        pass

    return {"message": f"Company '{company_name}' and all associated drive data removed completely across all dashboards."}


@router.delete("/company/{company_id}")
def delete_company_by_id(
    company_id: str,
    reason: str = "Company removed by placement officer",
    current_user: UserModel = Depends(require_officer),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Permanently purges a company by its company_id across all dashboards (Officer only)."""
    company = db.execute(select(CompanyModel).where(CompanyModel.id == company_id)).scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")

    company_name = company.name

    # Identify all drives
    company_drives = db.execute(
        select(DriveModel).where(
            (DriveModel.company_id == company_id) | (DriveModel.company_name == company_name)
        )
    ).scalars().all()
    all_drive_ids = [d.id for d in company_drives]

    for did in all_drive_ids:
        db.execute(delete(DriveAttendanceModel).where(DriveAttendanceModel.drive_id == did))
        db.execute(delete(AttendanceRecordModel).where(AttendanceRecordModel.drive_id == did))
        db.execute(delete(PendingResultModel).where(PendingResultModel.drive_id == did))
        db.execute(delete(SlotModel).where(SlotModel.drive_id == did))
        db.execute(delete(EligibilityDecisionModel).where(EligibilityDecisionModel.drive_id == did))
        db.execute(delete(EligibilityRunModel).where(EligibilityRunModel.drive_id == did))
        db.execute(delete(PanelModel).where(PanelModel.drive_id == did))
        db.execute(delete(StudentApplicationModel).where(StudentApplicationModel.drive_id == did))
        db.execute(delete(DriveRequirementVersionModel).where(DriveRequirementVersionModel.drive_id == did))
        db.execute(delete(CoordinatorRequestModel).where(CoordinatorRequestModel.target_id == did))
        db.execute(delete(PlacementRequestModel).where(PlacementRequestModel.drive_id == did))

    offers = db.execute(select(OfferModel).where(OfferModel.company == company_name)).scalars().all()
    affected_student_ids = {off.student_id for off in offers if off.student_id}
    db.execute(delete(OfferModel).where(OfferModel.company == company_name))
    for stu_id in affected_student_ids:
        stu = db.execute(select(StudentModel).where(StudentModel.id == stu_id)).scalar_one_or_none()
        if stu:
            stu.version += 1

    db.execute(
        delete(CoordinatorRequestModel).where(
            (CoordinatorRequestModel.target_id == company_id)
            | (CoordinatorRequestModel.title.like(f"%{company_name}%"))
            | (CoordinatorRequestModel.description.like(f"%{company_name}%"))
        )
    )
    db.execute(
        delete(PlacementRequestModel).where(
            PlacementRequestModel.subject.like(f"%{company_name}%")
        )
    )

    for did in all_drive_ids:
        db.execute(delete(NotificationModel).where(NotificationModel.metadata_json.like(f"%{did}%")))
    db.execute(
        delete(NotificationModel).where(
            (NotificationModel.title.like(f"%{company_name}%"))
            | (NotificationModel.message.like(f"%{company_name}%"))
        )
    )

    db.execute(delete(CompanyExportMappingModel).where(CompanyExportMappingModel.company_id == company_id))
    db.execute(delete(CompanyExportMappingModel).where(CompanyExportMappingModel.company_name == company_name))

    recruiter_users = db.execute(
        select(UserModel).where(
            (UserModel.company_id == company_id)
            | (UserModel.username == f"recruiter_{company_name.lower().replace(' ', '_')}")
        )
    ).scalars().all()
    for ru in recruiter_users:
        ru.company_id = None
        ru.is_active = False

    if all_drive_ids:
        db.execute(delete(DriveModel).where(DriveModel.id.in_(all_drive_ids)))

    db.delete(company)

    AuditService.record_action(
        db=db,
        actor=f"{current_user.role}:{current_user.username}",
        action="COMPANY_PURGED_COMPLETELY",
        aggregate_type="COMPANY",
        aggregate_id=company_id,
        payload={
            "company_name": company_name,
            "deleted_drive_ids": all_drive_ids,
            "reason": reason,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        },
    )

    db.commit()
    return {"message": f"Company '{company_name}' and all associated records permanently removed across all dashboards."}


@router.post("/{drive_id}/duplicate")
def duplicate_drive(
    drive_id: str,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Disallows duplicate drive creation to protect database integrity."""
    drive = db.execute(select(DriveModel).where(DriveModel.id == drive_id)).scalar_one_or_none()
    if not drive:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drive not found.")
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Duplicate drives for '{drive.company_name}' are disabled to keep database records clean and unique.",
    )


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
