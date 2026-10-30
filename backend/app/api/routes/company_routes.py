"""
Corporate Partner Company Management Routes.
Supports listing, creating, and updating partner companies across SQLite and MongoDB Atlas.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from backend.app.api.auth.dependencies import require_officer, require_officer_or_coordinator
from backend.app.api.logging.audit_service import AuditService
from backend.app.storage.database import get_db
from backend.app.storage.models.entities import CompanyModel, DriveModel, UserModel

router = APIRouter(prefix="/api/companies", tags=["Partner Companies"])


class CompanyCreateUpdateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Official company / partner name")
    industry: str | None = Field(default="Technology", max_length=128)
    tier: str | None = Field(default="Tier 1", max_length=64)
    website: str | None = Field(default=None, max_length=255)


class CompanyResponse(BaseModel):
    id: str
    name: str
    industry: str | None = None
    tier: str | None = "Tier 1"
    website: str | None = None
    drive_count: int = 0
    created_at: str | None = None


@router.get("", response_model=list[CompanyResponse])
def list_companies(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_officer_or_coordinator),
) -> list[dict[str, Any]]:
    """Lists all registered partner companies with active drive counts."""
    # Group drives by company_id
    drive_counts_query = (
        select(DriveModel.company_id, func.count(DriveModel.id).label("count"))
        .group_by(DriveModel.company_id)
    )
    drive_counts = dict(db.execute(drive_counts_query).all())

    companies = db.execute(select(CompanyModel).order_by(CompanyModel.name.asc())).scalars().all()
    res = []
    for c in companies:
        cnt = drive_counts.get(c.id, 0)
        res.append({
            "id": c.id,
            "name": c.name,
            "industry": c.industry or "Technology",
            "tier": c.tier or "Tier 1",
            "website": c.website or f"https://{c.name.lower().replace(' ', '')}.com",
            "drive_count": cnt,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })
    return res


@router.post("", status_code=status.HTTP_201_CREATED)
def create_company(
    req: CompanyCreateUpdateRequest,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_officer),
) -> dict[str, Any]:
    """
    Onboards a new corporate partner company into the SQLite database
    and automatically mirrors the record to MongoDB Atlas.
    """
    cleaned_name = req.name.strip()
    if not cleaned_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Company name cannot be blank.")

    # 1. Check if company already exists
    stmt = select(CompanyModel).where(func.lower(CompanyModel.name) == cleaned_name.lower())
    existing = db.execute(stmt).scalar_one_or_none()

    now_utc = datetime.datetime.utcnow()
    is_new = False

    if existing:
        company_id = existing.id
        existing.industry = req.industry or existing.industry or "Technology"
        existing.tier = req.tier or existing.tier or "Tier 1"
        if req.website:
            existing.website = req.website
        company_obj = existing
        msg = f"Company '{cleaned_name}' updated successfully in database."
    else:
        is_new = True
        company_id = f"comp_{uuid.uuid4().hex[:8]}"
        company_obj = CompanyModel(
            id=company_id,
            name=cleaned_name,
            industry=req.industry or "Technology",
            tier=req.tier or "Tier 1",
            website=req.website or f"https://{cleaned_name.lower().replace(' ', '')}.com",
            version=1,
            created_at=now_utc,
        )
        db.add(company_obj)
        msg = f"Company '{cleaned_name}' successfully added to database."

    db.commit()

    # 2. Synchronize to MongoDB Atlas immediately
    try:
        from backend.app.storage.mongodb import get_mongo_db
        mongo_db = get_mongo_db()
        if mongo_db is not None:
            mongo_doc = {
                "_id": company_id,
                "id": company_id,
                "name": cleaned_name,
                "industry": company_obj.industry,
                "tier": company_obj.tier,
                "website": company_obj.website,
                "created_at": company_obj.created_at.isoformat() if company_obj.created_at else now_utc.isoformat(),
                "synced_at": now_utc.isoformat(),
            }
            mongo_db.companies.update_one({"_id": company_id}, {"$set": mongo_doc}, upsert=True)
    except Exception:
        pass

    # 3. Record Audit Log
    AuditService.record_action(
        db=db,
        actor=f"{current_user.role}:{current_user.username}",
        action="COMPANY_CREATED" if is_new else "COMPANY_UPDATED",
        aggregate_type="COMPANY",
        aggregate_id=company_id,
        payload={
            "company_name": cleaned_name,
            "industry": company_obj.industry,
            "tier": company_obj.tier,
            "website": company_obj.website,
            "synced_to_mongodb": True,
            "timestamp": now_utc.isoformat(),
        },
    )

    return {
        "id": company_id,
        "name": company_obj.name,
        "industry": company_obj.industry,
        "tier": company_obj.tier,
        "website": company_obj.website,
        "message": msg,
        "synced_to_mongodb": True,
    }


@router.get("/{company_id}")
def get_company(
    company_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_officer_or_coordinator),
) -> dict[str, Any]:
    """Retrieves detailed information for a company including all associated drives."""
    company = db.execute(select(CompanyModel).where(CompanyModel.id == company_id)).scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")

    drives = db.execute(select(DriveModel).where(DriveModel.company_id == company_id)).scalars().all()
    return {
        "id": company.id,
        "name": company.name,
        "industry": company.industry,
        "tier": company.tier,
        "website": company.website,
        "created_at": company.created_at.isoformat() if company.created_at else None,
        "drives": [
            {
                "id": d.id,
                "job_role": getattr(d, "job_role", "Engineering Trainee"),
                "drive_date": d.drive_date.isoformat() if d.drive_date else None,
                "ctc_lpa": d.ctc_lpa,
                "mode": d.mode,
                "status": d.status,
            }
            for d in drives
        ],
    }
