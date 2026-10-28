"""
Document Announcements Library Routes.
Provides full programmatic and user access to the 25 real-format drive announcements
(Anonymised company emails, PDFs, DOCXs, and placement notices).
"""

from __future__ import annotations

import datetime
import json
import os
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.auth.dependencies import require_officer_or_coordinator
from backend.app.extract.document_loader import DocumentLoader
from backend.app.storage.database import get_db
from backend.app.storage.models.entities import CompanyModel, DriveModel, DriveRequirementVersionModel, UserModel

router = APIRouter(prefix="/api/announcements", tags=["25 Announcements Library"])

_loader = DocumentLoader()


def _get_announcements_dir() -> str:
    """Resolves path to fixtures/announcements across development and packaged environments."""
    for cand in [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "fixtures", "announcements")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "fixtures", "announcements")),
        os.path.abspath("fixtures/announcements"),
    ]:
        if os.path.exists(cand):
            return cand
    raise FileNotFoundError("fixtures/announcements directory not found.")


def _get_ground_truth() -> dict[str, Any]:
    """Loads ground truth criteria metadata."""
    try:
        ann_dir = _get_announcements_dir()
        gt_path = os.path.join(ann_dir, "ground_truth_labels.json")
        if os.path.exists(gt_path):
            with open(gt_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


@router.get("")
def list_all_announcements(
    format_filter: str | None = None,
    search: str | None = None,
    current_user: UserModel = Depends(require_officer_or_coordinator),
) -> list[dict[str, Any]]:
    """
    Lists all 25 real-format drive announcements with metadata,
    extracted summaries, and ground-truth recruitment criteria.
    """
    ann_dir = _get_announcements_dir()
    ground_truth = _get_ground_truth()

    files = sorted([f for f in os.listdir(ann_dir) if not f.endswith(".json") and not f.startswith(".")])
    results = []

    format_labels = {
        "EML": "Placement Email Notice (.eml)",
        "PDF": "Company Specification Sheet (.pdf)",
        "DOCX": "Official Job Description (.docx)",
        "TXT": "Campus Placement Notice (.txt)",
    }

    for idx, f in enumerate(files, start=1):
        ext = f.rsplit(".", 1)[1].upper()
        if format_filter and ext != format_filter.upper():
            continue

        name_part = f.split("_", 1)[1].rsplit(".", 1)[0].replace("_", " ").title()
        file_path = os.path.join(ann_dir, f)
        size_bytes = os.path.getsize(file_path) if os.path.exists(file_path) else 0

        gt = ground_truth.get(f, {})
        comp_name = gt.get("company_name", name_part.split()[0])

        if search and search.lower() not in comp_name.lower() and search.lower() not in name_part.lower():
            continue

        # Load preview snippet
        snippet = ""
        try:
            with open(file_path, "rb") as fp:
                full_text = _loader.load_from_bytes(fp.read(), f)
            snippet = full_text[:280].strip().replace("\n", " ") + "..."
        except Exception:
            snippet = f"Real-format {ext} document received by placement cell."

        results.append({
            "index": idx,
            "filename": f,
            "company_name": comp_name,
            "label": f"{comp_name} ({ext})",
            "format": ext,
            "file_type_label": format_labels.get(ext, f"{ext} Document"),
            "size_bytes": size_bytes,
            "ctc_lpa": gt.get("ctc_lpa", 10.0),
            "cgpa_min": gt.get("cgpa_min", 7.0),
            "drive_date": gt.get("drive_date", "2026-11-20"),
            "mode": gt.get("mode", "on_campus"),
            "allowed_branches": gt.get("allowed_branches", ["All Branches"]),
            "active_backlogs_max": gt.get("active_backlogs_max", 0),
            "rounds_count": gt.get("rounds_count", 3),
            "snippet": snippet,
            "download_url": f"/api/announcements/{f}/download",
        })

    return results


@router.get("/{filename}")
def get_announcement_details(
    filename: str,
    current_user: UserModel = Depends(require_officer_or_coordinator),
) -> dict[str, Any]:
    """Returns full extracted text and ground truth labels for a specific announcement."""
    ann_dir = _get_announcements_dir()
    file_path = os.path.join(ann_dir, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Announcement '{filename}' not found.")

    ext = filename.rsplit(".", 1)[1].upper()
    name_part = filename.split("_", 1)[1].rsplit(".", 1)[0].replace("_", " ").title()

    ground_truth = _get_ground_truth()
    gt = ground_truth.get(filename, {})

    with open(file_path, "rb") as fp:
        raw_bytes = fp.read()

    full_text = _loader.load_from_bytes(raw_bytes, filename)

    return {
        "filename": filename,
        "format": ext,
        "company_name": gt.get("company_name", name_part.split()[0]),
        "size_bytes": len(raw_bytes),
        "ground_truth": gt,
        "full_text": full_text,
        "text": full_text,
        "download_url": f"/api/announcements/{filename}/download",
    }


@router.get("/{filename}/download")
def download_announcement_file(
    filename: str,
    current_user: UserModel = Depends(require_officer_or_coordinator),
) -> FileResponse:
    """Downloads the original anonymised company email, PDF, or DOCX document."""
    ann_dir = _get_announcements_dir()
    file_path = os.path.join(ann_dir, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Announcement '{filename}' not found.")

    ext = filename.rsplit(".", 1)[1].lower()
    media_types = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "eml": "message/rfc822",
        "txt": "text/plain",
    }

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media_types.get(ext, "application/octet-stream"),
    )


@router.post("/{filename}/instant-drive")
def create_drive_from_announcement(
    filename: str,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    1-Click converts any of the 25 announcements into an active campus recruitment drive
    pre-populated with ground-truth eligibility criteria.
    """
    ann_dir = _get_announcements_dir()
    file_path = os.path.join(ann_dir, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Announcement '{filename}' not found.")

    ground_truth = _get_ground_truth()
    gt = ground_truth.get(filename, {})

    name_part = filename.split("_", 1)[1].rsplit(".", 1)[0].replace("_", " ").title()
    company_name = gt.get("company_name", name_part.split()[0])
    drive_id = f"drv_{uuid.uuid4().hex[:8]}"

    # Check if drive for this company already exists
    existing = db.execute(select(DriveModel).where(DriveModel.company_name == company_name)).scalars().first()
    if existing:
        return {
            "status": "exists",
            "message": f"Drive for {company_name} already exists in registry.",
            "drive_id": existing.id,
            "company_name": existing.company_name,
            "ctc_lpa": existing.ctc_lpa,
        }

    # Ensure company entity exists
    stmt_comp = select(CompanyModel).where(CompanyModel.name == company_name)
    existing_company = db.execute(stmt_comp).scalars().first()
    if existing_company:
        company_id = existing_company.id
    else:
        company_id = f"comp_{uuid.uuid4().hex[:8]}"
        company = CompanyModel(
            id=company_id,
            name=company_name,
            tier="Dream" if float(gt.get("ctc_lpa", 10.0)) >= 10.0 else "Regular",
        )
        db.add(company)
        db.flush()

    raw_date = gt.get("drive_date", "2026-11-20")
    if isinstance(raw_date, str):
        try:
            drive_date = datetime.date.fromisoformat(raw_date)
        except Exception:
            drive_date = datetime.date(2026, 11, 20)
    elif isinstance(raw_date, datetime.date):
        drive_date = raw_date
    else:
        drive_date = datetime.date(2026, 11, 20)

    drive = DriveModel(
        id=drive_id,
        company_id=company_id,
        company_name=company_name,
        drive_date=drive_date,
        mode=gt.get("mode", "on_campus"),
        ctc_lpa=float(gt.get("ctc_lpa", 12.0)),
        status="published",
    )
    db.add(drive)
    db.flush()

    # Add requirement version
    req_v = DriveRequirementVersionModel(
        id=f"req_{drive.id}",
        drive_id=drive.id,
        version_number=1,
        min_cgpa=float(gt.get("cgpa_min", 7.0)),
        min_tenth_percentage=float(gt.get("tenth_percentage_min", 60.0)),
        min_twelfth_percentage=float(gt.get("twelfth_percentage_min", 60.0)),
        max_active_backlogs=int(gt.get("active_backlogs_max", 0)),
        allowed_branches_json=json.dumps(gt.get("allowed_branches", ["All Branches"])),
        raw_source_text=f"Imported from {filename}",
    )
    db.add(req_v)
    db.commit()

    return {
        "status": "created",
        "message": f"Campus drive for '{company_name}' successfully initialized from {filename}!",
        "drive_id": drive.id,
        "company_name": drive.company_name,
        "ctc_lpa": drive.ctc_lpa,
    }
