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

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from backend.app.extract.nlp_engine import NLPEngine
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.auth.dependencies import require_officer_or_coordinator
from backend.app.extract.document_loader import DocumentLoader
from backend.app.storage.database import get_db
from backend.app.storage.models.entities import CompanyModel, DriveModel, DriveRequirementVersionModel, UserModel

router = APIRouter(prefix="/api/announcements", tags=["25 Announcements Library"])

_loader = DocumentLoader()
_extractor = NLPEngine()


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


def _clean_company_name(filename: str, ground_truth: dict[str, Any] | None = None) -> str:
    """Extracts or looks up clean, accurate company name without deleting multi-word names."""
    if ground_truth and filename in ground_truth:
        gt_name = ground_truth[filename].get("company_name")
        if gt_name:
            return gt_name

    clean = filename.rsplit(".", 1)[0]
    clean = re.sub(r"^\d+[\s_-]*", "", clean)
    clean = re.sub(r"[_-](?:announcement|email|spec|jd|circular|notice|job_description)$", "", clean, flags=re.IGNORECASE)
    clean = clean.replace("_", " ").replace("-", " ").strip()

    lower = clean.lower()
    if "goldman" in lower and "sachs" in lower:
        return "Goldman Sachs"
    if "deloitte" in lower:
        return "Deloitte USI" if "usi" in lower else "Deloitte"
    if "tata" in lower and "consultancy" in lower:
        return "Tata Consultancy Services"
    if "tata" in lower and "motors" in lower:
        return "Tata Motors"
    if "larsen" in lower or "toubro" in lower:
        return "Larsen & Toubro"
    if "texas" in lower and "instruments" in lower:
        return "Texas Instruments"
    if "morgan" in lower and "stanley" in lower:
        return "Morgan Stanley"
    if "samsung" in lower:
        return "Samsung R&D"
    if "reliance" in lower:
        return "Reliance Industries"
    if "itc" in lower:
        return "ITC Limited"
    if "zs" in lower or "associates" in lower:
        return "ZS Associates"
    if "infosys" in lower:
        return "Infosys Power Programmer" if "power" in lower else "Infosys"
    if "wipro" in lower:
        return "Wipro Turbo" if "turbo" in lower else "Wipro"
    if "accenture" in lower:
        return "Accenture Advanced Tech" if ("tech" in lower or "advanced" in lower) else "Accenture"

    words = []
    for w in clean.split():
        up = w.upper()
        if up in ("USI", "ITC", "ZS", "TCS", "R&D", "AI", "ML"):
            words.append(up)
        elif up == "AND":
            words.append("&")
        else:
            words.append(w.capitalize())
    return " ".join(words) or clean.title()


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

        name_part = (f.split("_", 1)[1] if "_" in f else f).rsplit(".", 1)[0].replace("_", " ").title()
        file_path = os.path.join(ann_dir, f)
        size_bytes = os.path.getsize(file_path) if os.path.exists(file_path) else 0

        gt = ground_truth.get(f, {})
        comp_name = gt.get("company_name") or _clean_company_name(f, ground_truth)

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

        role = gt.get("role") or "Software Development Engineer"
        location = gt.get("location") or "Bengaluru / Hyderabad"
        deadline = gt.get("application_deadline") or "2026-10-25"

        results.append({
            "index": idx,
            "filename": f,
            "company_name": comp_name,
            "role": role,
            "location": location,
            "application_deadline": deadline,
            "label": f"{comp_name} - {role} ({ext})",
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
    name_part = (filename.split("_", 1)[1] if "_" in filename else filename).rsplit(".", 1)[0].replace("_", " ").title()

    ground_truth = _get_ground_truth()
    gt = ground_truth.get(filename, {})

    with open(file_path, "rb") as fp:
        raw_bytes = fp.read()

    full_text = _loader.load_from_bytes(raw_bytes, filename)

    return {
        "filename": filename,
        "format": ext,
        "company_name": gt.get("company_name") or _clean_company_name(filename, ground_truth),
        "role": gt.get("role", "Software Development Engineer"),
        "location": gt.get("location", "Bengaluru / Hyderabad"),
        "application_deadline": gt.get("application_deadline", "2026-10-25"),
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


@router.post("/upload")
async def upload_announcement(
    file: UploadFile = File(...),
    current_user: UserModel = Depends(require_officer_or_coordinator),
) -> dict[str, Any]:
    """Uploads, validates, stores, and deterministically parses a new announcement document."""
    orig_name = file.filename or "announcement.txt"
    ext = orig_name.rsplit(".", 1)[-1].lower() if "." in orig_name else "txt"
    if ext not in ("pdf", "docx", "eml", "txt"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format '.{ext}'. Supported formats: PDF, DOCX, EML, TXT.",
        )

    ann_dir = _get_announcements_dir()
    safe_name = os.path.basename(orig_name).replace(" ", "_")
    dest_path = os.path.join(ann_dir, safe_name)

    contents = await file.read()
    with open(dest_path, "wb") as f_out:
        f_out.write(contents)

    full_text = _loader.load_from_bytes(contents, safe_name)
    extracted = _extractor.extract(full_text)

    name_part = safe_name.rsplit(".", 1)[0].replace("_", " ").title()
    company_name = extracted.company_name.value if extracted.company_name else name_part

    gt = _get_ground_truth()
    gt_entry = {
        "company_name": company_name,
        "ctc_lpa": extracted.ctc_lpa.value if extracted.ctc_lpa else 10.0,
        "cgpa_min": extracted.cgpa_min.value if extracted.cgpa_min else 6.0,
        "drive_date": extracted.drive_date.value.isoformat() if extracted.drive_date else "2026-11-20",
        "mode": extracted.mode.value if extracted.mode else "on_campus",
        "allowed_branches": extracted.allowed_branches.value if extracted.allowed_branches else ["All Branches"],
        "active_backlogs_max": extracted.active_backlogs_max.value if extracted.active_backlogs_max is not None else 0,
        "tenth_percentage_min": extracted.tenth_percentage_min.value if extracted.tenth_percentage_min else 60.0,
        "twelfth_percentage_min": extracted.twelfth_percentage_min.value if extracted.twelfth_percentage_min else 60.0,
        "rounds_count": len(extracted.rounds) if extracted.rounds else 3,
    }
    gt[safe_name] = gt_entry
    gt_path = os.path.join(ann_dir, "ground_truth_labels.json")
    try:
        with open(gt_path, "w", encoding="utf-8") as f_gt:
            json.dump(gt, f_gt, indent=2)
    except Exception:
        pass

    return {
        "filename": safe_name,
        "company_name": company_name,
        "format": ext.upper(),
        "size_bytes": len(contents),
        "text": full_text,
        "extracted": gt_entry,
        "message": f"Announcement '{safe_name}' successfully ingested and parsed!",
    }


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

    name_part = filename.split("_", 1)[-1].rsplit(".", 1)[0].replace("_", " ").title()
    if not gt or "company_name" not in gt:
        with open(file_path, "rb") as fp:
            dyn_text = _loader.load_from_bytes(fp.read(), filename)
        dyn_ext = _extractor.extract(dyn_text)
        gt = {
            "company_name": dyn_ext.company_name.value if dyn_ext.company_name else name_part,
            "ctc_lpa": dyn_ext.ctc_lpa.value if dyn_ext.ctc_lpa else 12.0,
            "cgpa_min": dyn_ext.cgpa_min.value if dyn_ext.cgpa_min else 6.0,
            "drive_date": dyn_ext.drive_date.value.isoformat() if dyn_ext.drive_date else "2026-11-20",
            "mode": dyn_ext.mode.value if dyn_ext.mode else "on_campus",
            "allowed_branches": dyn_ext.allowed_branches.value if dyn_ext.allowed_branches else ["All Branches"],
            "active_backlogs_max": dyn_ext.active_backlogs_max.value if dyn_ext.active_backlogs_max is not None else 0,
            "tenth_percentage_min": dyn_ext.tenth_percentage_min.value if dyn_ext.tenth_percentage_min else 60.0,
            "twelfth_percentage_min": dyn_ext.twelfth_percentage_min.value if dyn_ext.twelfth_percentage_min else 60.0,
        }
    company_name = gt.get("company_name") or _clean_company_name(filename, ground_truth)
    drive_id = f"drv_{uuid.uuid4().hex[:8]}"

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

    # Check if drive for this company already exists: update in place without duplicate
    existing = db.execute(select(DriveModel).where(DriveModel.company_name == company_name)).scalars().first()
    if existing:
        existing.drive_date = drive_date
        existing.mode = gt.get("mode", existing.mode or "on_campus")
        existing.ctc_lpa = float(gt.get("ctc_lpa", existing.ctc_lpa or 12.0))
        existing.version += 1

        req_v = db.execute(
            select(DriveRequirementVersionModel)
            .where(DriveRequirementVersionModel.drive_id == existing.id)
            .order_by(DriveRequirementVersionModel.version_number.desc())
        ).scalars().first()
        if req_v:
            req_v.min_cgpa = float(gt.get("cgpa_min", req_v.min_cgpa))
            req_v.min_tenth_percentage = float(gt.get("tenth_percentage_min", req_v.min_tenth_percentage))
            req_v.min_twelfth_percentage = float(gt.get("twelfth_percentage_min", req_v.min_twelfth_percentage))
            req_v.max_active_backlogs = int(gt.get("active_backlogs_max", req_v.max_active_backlogs))
            req_v.allowed_branches_json = json.dumps(gt.get("allowed_branches", ["All Branches"]))
            req_v.version_number = existing.version
            req_v.raw_source_text = f"Imported from {filename}"
        db.commit()
        return {
            "status": "updated",
            "message": f"Drive for {company_name} updated with announcement criteria.",
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
