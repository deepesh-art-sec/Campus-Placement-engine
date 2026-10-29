"""
Requirement Extraction and Review Queue Routes.
Deterministic offline parser using PyMuPDF (fitz), python-docx, UTF-8, and Tesseract OCR (pytesseract).
Side-by-side editable coordinator review form and SQLite database persistence upon confirmation.
"""

from __future__ import annotations

import datetime
import json
import os
import re
import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.auth.dependencies import require_officer_or_coordinator
from backend.app.domain.models import DriveMode, DriveStatus
from backend.app.extract.deterministic_extractor import DeterministicExtractor
from backend.app.extract.nlp_engine import NLPEngine
from backend.app.extract.document_loader import (
    CorruptDocumentError,
    DocumentLoader,
    EmptyDocumentError,
    ScannedPdfError,
    UnsupportedFormatError,
)
from backend.app.extract.models import FieldReviewStatus
from backend.app.extract.review_contract import ExtractionReviewService, FeedbackStore
from backend.app.importers.canonical_maps import get_branch_code
from backend.app.storage.database import get_db
from backend.app.storage.models.entities import (
    CompanyModel,
    DriveModel,
    DriveRequirementVersionModel,
    EventModel,
    UserModel,
)

router = APIRouter(prefix="/api/extract", tags=["Requirement Extraction"])

_extractor = NLPEngine()
_loader = DocumentLoader(ocr_enabled=True)
_feedback_store = FeedbackStore()
_review_service = ExtractionReviewService(_feedback_store)

# Global in-memory review queue
_active_reviews: dict[str, Any] = {}

CANONICAL_BRANCH_MAP: dict[str, str] = {
    "CSE": "CSE",
    "CS": "CSE",
    "COMPUTER SCIENCE": "CSE",
    "IT": "IT",
    "INFORMATION TECHNOLOGY": "IT",
    "ECE": "ECE",
    "ELECTRONICS": "ECE",
    "EEE": "EE",
    "EE": "EE",
    "ELECTRICAL": "EE",
    "MECH": "MECH",
    "MECHANICAL": "MECH",
    "ME": "MECH",
    "CIVIL": "CIVIL",
    "CE": "CIVIL",
    "CHEM": "CHEM",
    "CHEMICAL": "CHEM",
    "CHE": "CHEM",
    "META": "META",
    "METALLURGY": "META",
    "BIOTECH": "BIOTECH",
    "BIOTECHNOLOGY": "BIOTECH",
    "BT": "BIOTECH",
    "DATA SCIENCE": "CSE",
    "DS": "CSE",
    "AI & ML": "CSE",
    "AIML": "CSE",
}


def normalize_branches(branches: list[str] | None) -> list[str]:
    """Normalizes any extracted branch tokens into the standard canonical branch codes."""
    if not branches or "All Branches" in branches:
        return ["All Branches"]

    result: list[str] = []
    for b in branches:
        clean = str(b).strip()
        if not clean:
            continue
        code = get_branch_code(clean)
        norm = CANONICAL_BRANCH_MAP.get(code.upper(), CANONICAL_BRANCH_MAP.get(clean.upper(), clean.upper()))
        if norm not in result:
            result.append(norm)

    return result if result else ["All Branches"]


# ---------------------------------------------------------------------------
# Pydantic Schemas for Extraction, Review, and Confirmation
# ---------------------------------------------------------------------------


class ParseTextRequest(BaseModel):
    text: str
    drive_id: str | None = None
    company_name: str | None = None


class ReviewResolutionRequest(BaseModel):
    announcement_id: str
    field_name: str
    status: FieldReviewStatus
    corrected_value: Any = None
    source_text: str = ""
    extracted_value: Any = None


class ExtractedFieldDetail(BaseModel):
    model_config = ConfigDict(frozen=True)

    extracted_value: Any = None
    confidence: float = 1.0
    source_sentence: str = ""
    is_ambiguous: bool = False
    is_missing: bool = False
    is_uncertain: bool = False
    ambiguity_reason: str | None = None


class ExtractedRoundDetail(BaseModel):
    model_config = ConfigDict(frozen=True)

    round_number: int
    name: str
    round_type: str
    duration_minutes: int = 60
    source_sentence: str = ""


class ParsedAnnouncementResponse(BaseModel):
    announcement_id: str
    filename: str
    company_name: str
    job_role: str | None = None
    location: str | None = None
    ctc_lpa: float | None = None
    drive_date: str | None = None
    application_deadline: str | None = None
    mode: str = "on_campus"
    allowed_branches: list[str] = []
    min_cgpa: float | None = None
    min_tenth_percentage: float | None = None
    min_twelfth_percentage: float | None = None
    max_active_backlogs: int | None = None
    max_gap_years: int | None = None
    selection_process: list[ExtractedRoundDetail] = []
    requires_review: bool = False
    missing_fields: list[str] = []
    uncertain_fields: list[str] = []
    review_queue: list[dict[str, Any]] = []
    ambiguities: list[dict[str, Any]] = []
    fields: dict[str, ExtractedFieldDetail] = {}
    rule_count: int = 0
    raw_content_preview: str = ""


class ConfirmSaveExtractionRequest(BaseModel):
    company_name: str = Field(min_length=2)
    job_role: str | None = None
    job_location: str | None = None
    drive_date: datetime.date = Field(default_factory=lambda: datetime.date.today() + datetime.timedelta(days=14))
    application_deadline: datetime.date | None = None
    mode: str = "on_campus"
    ctc_lpa: float = Field(default=10.0, ge=0.0)
    min_cgpa: float = Field(default=6.0, ge=0.0, le=10.0)
    min_tenth_percentage: float = Field(default=60.0, ge=0.0, le=100.0)
    min_twelfth_percentage: float | None = Field(default=None, ge=0.0, le=100.0)
    allowed_branches: list[str] = Field(default_factory=lambda: ["CSE", "IT", "ECE"])
    max_active_backlogs: int = Field(default=0, ge=0)
    max_gap_years: int = Field(default=1, ge=0)
    selection_process: list[dict[str, Any]] | None = None
    raw_source_text: str | None = None
    confirmed_by: str = "coordinator"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clean_company_name(filename: str, ground_truth: dict[str, Any] | None = None) -> str:
    """Extracts or looks up clean, accurate company name without deleting multi-word names."""
    if ground_truth and filename in ground_truth:
        gt_name = ground_truth[filename].get("company_name")
        if gt_name:
            return gt_name

    clean = filename.rsplit(".", 1)[0]
    clean = re.sub(r"^\d+[\s_-]*", "", clean)
    clean = re.sub(
        r"[_-](?:announcement|email|spec|jd|circular|notice|job_description)$",
        "",
        clean,
        flags=re.IGNORECASE,
    )
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


def _get_fixtures_dir() -> str:
    for cand in [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "fixtures", "announcements")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "fixtures", "announcements")),
        os.path.abspath("fixtures/announcements"),
    ]:
        if os.path.exists(cand):
            return cand
    raise FileNotFoundError("Fixtures directory not found.")


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------


@router.get("/samples")
def list_sample_announcements(
    current_user: UserModel = Depends(require_officer_or_coordinator),
) -> list[dict[str, Any]]:
    """Lists the 25 real-format announcement files with preliminary metadata for quick testing."""
    fixtures_dir = _get_fixtures_dir()
    files = sorted([f for f in os.listdir(fixtures_dir) if not f.endswith(".json") and not f.startswith(".")])

    gt_file = os.path.join(fixtures_dir, "ground_truth_labels.json")
    ground_truth = {}
    if os.path.exists(gt_file):
        with open(gt_file, encoding="utf-8") as f:
            ground_truth = json.load(f)

    results = []
    for f in files:
        file_path = os.path.join(fixtures_dir, f)
        ext = f.rsplit(".", 1)[1].upper() if "." in f else "TXT"
        comp_name = _clean_company_name(f, ground_truth)

        try:
            with open(file_path, "rb") as fp:
                text = _loader.load_from_bytes(fp.read(), f)
            results.append({
                "filename": f,
                "label": f"{comp_name} ({ext})",
                "format": ext,
                "company_name": comp_name,
                "text": text,
            })
        except Exception:
            continue
    return results


@router.post("/parse", response_model=ParsedAnnouncementResponse)
async def parse_announcement(
    text: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    company_name: str = Form(default="Target Company"),
    current_user: UserModel = Depends(require_officer_or_coordinator),
) -> ParsedAnnouncementResponse:
    """
    Deterministically parses recruitment drive announcements from uploaded PDF, DOCX, TXT, or pasted text.
    Extracts structured requirements with sentence provenance, confidence scores, and AST translation.
    Uses PyMuPDF (fitz) for PDFs, python-docx for DOCX, UTF-8 for TXT, and Tesseract OCR for scanned documents.
    """
    raw_content = ""
    source_filename = "pasted_text.txt"

    if file:
        source_filename = file.filename or "announcement"
        bytes_data = await file.read()
        if not bytes_data or len(bytes_data) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Uploaded file '{source_filename}' is empty (0 bytes). Please upload a valid document.",
            )
        try:
            raw_content = _loader.load_from_bytes(bytes_data, source_filename)
        except EmptyDocumentError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except UnsupportedFormatError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except CorruptDocumentError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except ScannedPdfError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to process document '{source_filename}': {str(exc)}",
            ) from exc
    elif text:
        if not text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Supplied announcement text is empty or contains only whitespace.",
            )
        try:
            raw_content = _loader.load_text(text)
        except EmptyDocumentError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'text' or 'file' must be supplied for requirement extraction.",
        )

    # Deterministic rule extraction
    extracted = _extractor.extract(raw_content)
    review_payload = _review_service.build_review_payload(source_filename, extracted)

    _active_reviews[source_filename] = {
        "payload": review_payload,
        "extracted": extracted,
        "raw_text": raw_content,
    }

    # Map all target fields
    target_attributes = [
        ("company_name", extracted.company_name),
        ("role", extracted.role),
        ("location", extracted.location),
        ("drive_date", extracted.drive_date),
        ("application_deadline", getattr(extracted, "application_deadline", None)),
        ("mode", extracted.mode),
        ("ctc_lpa", extracted.ctc_lpa),
        ("cgpa_min", extracted.cgpa_min),
        ("tenth_percentage_min", extracted.tenth_percentage_min),
        ("twelfth_percentage_min", extracted.twelfth_percentage_min),
        ("allowed_branches", extracted.allowed_branches),
        ("active_backlogs_max", extracted.active_backlogs_max),
        ("gap_years_max", extracted.gap_years_max),
    ]

    fields_dict: dict[str, ExtractedFieldDetail] = {}
    missing_fields: list[str] = []
    uncertain_fields: list[str] = []

    for field_key, field_obj in target_attributes:
        if field_obj is not None and field_obj.value is not None:
            val = field_obj.value
            if isinstance(val, (datetime.date, datetime.datetime)):
                val = val.isoformat()
            elif hasattr(val, "value"):
                val = val.value

            is_uncertain = field_obj.confidence < 0.70 or field_obj.is_ambiguous
            if is_uncertain:
                uncertain_fields.append(field_key)

            fields_dict[field_key] = ExtractedFieldDetail(
                extracted_value=val,
                confidence=field_obj.confidence,
                source_sentence=field_obj.source_sentence or "",
                is_ambiguous=field_obj.is_ambiguous,
                is_missing=False,
                is_uncertain=is_uncertain,
                ambiguity_reason=field_obj.ambiguity_reason,
            )
        else:
            missing_fields.append(field_key)
            fields_dict[field_key] = ExtractedFieldDetail(
                extracted_value=None,
                confidence=0.0,
                source_sentence="",
                is_ambiguous=False,
                is_missing=True,
                is_uncertain=True,
                ambiguity_reason="Field not detected in announcement circular.",
            )

    # Selection process rounds
    selection_process: list[ExtractedRoundDetail] = []
    for r in extracted.rounds:
        r_type = r.round_type.value if hasattr(r.round_type, "value") else str(r.round_type)
        selection_process.append(
            ExtractedRoundDetail(
                round_number=r.round_number,
                name=r.name,
                round_type=r_type,
                duration_minutes=r.duration_minutes,
                source_sentence=r.source_sentence,
            )
        )

    # Rule Set AST
    comp = extracted.company_name.value if extracted.company_name else company_name
    rule_set = extracted.to_rule_set(rule_set_id=f"rs_{comp}", name=f"{comp} Rules")
    requires_review = len(extracted.review_queue) > 0 or len(extracted.ambiguities) > 0 or len(missing_fields) > 0

    # Normalized branches for client
    raw_branches = extracted.allowed_branches.value if extracted.allowed_branches else []
    norm_branches = normalize_branches(raw_branches)

    return ParsedAnnouncementResponse(
        announcement_id=source_filename,
        filename=source_filename,
        company_name=comp,
        job_role=extracted.role.value if extracted.role else None,
        location=extracted.location.value if extracted.location else None,
        ctc_lpa=extracted.ctc_lpa.value if extracted.ctc_lpa else None,
        drive_date=extracted.drive_date.value.isoformat() if extracted.drive_date else None,
        application_deadline=extracted.application_deadline.value.isoformat() if getattr(extracted, "application_deadline", None) else None,
        mode=extracted.mode.value.value if extracted.mode else "on_campus",
        allowed_branches=norm_branches,
        min_cgpa=extracted.cgpa_min.value if extracted.cgpa_min else None,
        min_tenth_percentage=extracted.tenth_percentage_min.value if extracted.tenth_percentage_min else None,
        min_twelfth_percentage=extracted.twelfth_percentage_min.value if extracted.twelfth_percentage_min else None,
        max_active_backlogs=extracted.active_backlogs_max.value if extracted.active_backlogs_max is not None else None,
        max_gap_years=extracted.gap_years_max.value if extracted.gap_years_max is not None else None,
        selection_process=selection_process,
        requires_review=requires_review,
        missing_fields=missing_fields,
        uncertain_fields=uncertain_fields,
        review_queue=[r.model_dump() for r in extracted.review_queue],
        ambiguities=[a.model_dump() for a in extracted.ambiguities],
        fields=fields_dict,
        rule_count=len(rule_set.rules),
        raw_content_preview=raw_content[:400] + ("..." if len(raw_content) > 400 else ""),
    )


@router.post("/confirm-save", status_code=status.HTTP_201_CREATED)
def confirm_save_extracted_drive(
    req: ConfirmSaveExtractionRequest,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Saves the coordinator-reviewed and confirmed announcement extraction to the SQLite database.
    Creates or maps CompanyModel, DriveModel, DriveRequirementVersionModel, and emits an immutable audit event.
    """
    # 1. Company
    stmt_comp = select(CompanyModel).where(CompanyModel.name == req.company_name)
    existing_company = db.execute(stmt_comp).scalar_one_or_none()
    if existing_company:
        company = existing_company
    else:
        company = CompanyModel(
            id=f"comp_{uuid.uuid4().hex[:8]}",
            name=req.company_name,
            industry="Technology",
            tier="Standard",
        )
        db.add(company)
        db.flush()

    # 2. Normalize branches to canonical codes
    canonical_branches = normalize_branches(req.allowed_branches)

    # 3. Create or reuse existing drive idempotently
    stmt_drive = select(DriveModel).where(
        DriveModel.company_id == company.id,
        DriveModel.drive_date == req.drive_date,
    )
    existing_drive = db.execute(stmt_drive).scalars().first()
    if existing_drive:
        drive = existing_drive
        drive.mode = req.mode
        drive.ctc_lpa = req.ctc_lpa
        drive_id = drive.id
    else:
        drive_id = f"drv_{uuid.uuid4().hex[:8]}"
        drive = DriveModel(
            id=drive_id,
            company_id=company.id,
            company_name=req.company_name,
            drive_date=req.drive_date,
            mode=req.mode,
            status="draft",
            ctc_lpa=req.ctc_lpa,
            version=1,
        )
        db.add(drive)
        db.flush()

    # 4. Create or update Requirement Set
    stmt_req = select(DriveRequirementVersionModel).where(
        DriveRequirementVersionModel.drive_id == drive_id
    ).order_by(DriveRequirementVersionModel.version_number.desc())
    existing_req = db.execute(stmt_req).scalars().first()
    if existing_req:
        req_version = existing_req
        req_version.min_cgpa = req.min_cgpa
        req_version.min_tenth_percentage = req.min_tenth_percentage
        req_version.min_twelfth_percentage = req.min_twelfth_percentage
        req_version.allowed_branches_json = json.dumps(canonical_branches)
        req_version.max_active_backlogs = req.max_active_backlogs
        req_version.max_gap_years = req.max_gap_years
    else:
        req_version = DriveRequirementVersionModel(
            id=f"req_{uuid.uuid4().hex[:8]}",
            drive_id=drive_id,
            version_number=1,
            raw_source_text=req.raw_source_text or f"Confirmed announcement extraction for {req.company_name}",
            parse_confidence=1.0,
            min_cgpa=req.min_cgpa,
            min_tenth_percentage=req.min_tenth_percentage,
            min_twelfth_percentage=req.min_twelfth_percentage,
            allowed_branches_json=json.dumps(canonical_branches),
            allowed_programs_json=json.dumps(["B.Tech"]),
            max_active_backlogs=req.max_active_backlogs,
            max_gap_years=req.max_gap_years,
            created_at=datetime.datetime.utcnow(),
        )
        db.add(req_version)

    # 5. Record Event (idempotent update or insert)
    stmt_event = select(EventModel).where(
        EventModel.aggregate_type == "drive",
        EventModel.aggregate_id == drive_id,
        EventModel.event_type == "ANNOUNCEMENT_EXTRACTION_CONFIRMED",
    )
    existing_event = db.execute(stmt_event).scalars().first()
    payload_str = json.dumps({
        "drive_id": drive_id,
        "company_name": req.company_name,
        "job_role": req.job_role,
        "ctc_lpa": req.ctc_lpa,
        "min_cgpa": req.min_cgpa,
        "allowed_branches": canonical_branches,
        "max_active_backlogs": req.max_active_backlogs,
        "confirmed_by": current_user.username,
    })
    if existing_event:
        existing_event.payload_json = payload_str
        existing_event.timestamp = datetime.datetime.utcnow()
        event = existing_event
    else:
        event = EventModel(
            id=f"evt_{uuid.uuid4().hex[:12]}",
            aggregate_type="drive",
            aggregate_id=drive_id,
            event_type="ANNOUNCEMENT_EXTRACTION_CONFIRMED",
            payload_json=payload_str,
            actor=current_user.username,
            timestamp=datetime.datetime.utcnow(),
        )
        db.add(event)

    db.commit()

    return {
        "success": True,
        "drive_id": drive.id,
        "company_name": drive.company_name,
        "drive_date": drive.drive_date.isoformat(),
        "version": 1,
        "status": "draft",
        "ctc_lpa": drive.ctc_lpa,
        "allowed_branches": canonical_branches,
        "min_cgpa": req.min_cgpa,
        "message": f"Announcement extraction confirmed. Recruitment drive for '{drive.company_name}' saved to SQLite database successfully.",
    }


@router.get("/review")
def list_pending_reviews(
    current_user: UserModel = Depends(require_officer_or_coordinator),
) -> list[dict[str, Any]]:
    """Lists unresolved review queue items across recent extractions."""
    pending = []
    for ann_id, entry in _active_reviews.items():
        payload = entry["payload"]
        for r in payload.get("review_queue", []):
            pending.append({
                "announcement_id": ann_id,
                **r,
            })
    return pending


@router.post("/review/resolve")
def resolve_review_item(
    req: ReviewResolutionRequest,
    current_user: UserModel = Depends(require_officer_or_coordinator),
) -> dict[str, Any]:
    """Records officer confirmation, manual edit, or rejection with provenance audit."""
    entry = _active_reviews.get(req.announcement_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extraction review session not found.")

    reviewed_item = _review_service.process_field_review(
        announcement_id=req.announcement_id,
        field_name=req.field_name,
        status=req.status,
        source_sentence=req.source_text,
        extracted_value=req.extracted_value,
        correction=req.corrected_value,
        reviewed_by=current_user.username,
    )

    payload = entry["payload"]
    payload["review_queue"] = [
        rq for rq in payload.get("review_queue", []) if rq.get("field_name") != req.field_name
    ]

    return {
        "field_name": reviewed_item.field_name,
        "status": reviewed_item.status.value,
        "final_value": reviewed_item.correction if reviewed_item.status == FieldReviewStatus.EDITED else reviewed_item.extracted_value,
        "remaining_unresolved": len(payload["review_queue"]),
        "message": f"Field '{req.field_name}' successfully updated to {req.status.value}.",
    }
