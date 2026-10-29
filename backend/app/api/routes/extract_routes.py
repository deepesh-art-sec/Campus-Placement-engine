"""
Requirement Extraction and Review Queue Routes.
Deterministic offline parser with side-by-side officer review.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from backend.app.api.auth.dependencies import require_officer_or_coordinator
from backend.app.extract.deterministic_extractor import DeterministicExtractor
from backend.app.extract.document_loader import DocumentLoader
from backend.app.extract.models import FieldReviewStatus
from backend.app.extract.review_contract import ExtractionReviewService, FeedbackStore
from backend.app.storage.models.entities import UserModel

router = APIRouter(prefix="/api/extract", tags=["Requirement Extraction"])

_extractor = DeterministicExtractor()
_loader = DocumentLoader()
_feedback_store = FeedbackStore()
_review_service = ExtractionReviewService(_feedback_store)

# Global in-memory review queue
_active_reviews: dict[str, Any] = {}


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


@router.get("/samples")
def list_sample_announcements(
    current_user: UserModel = Depends(require_officer_or_coordinator),
) -> list[dict[str, Any]]:
    """Returns the 25 real-format drive announcements with extracted content and metadata."""
    ann_dir = None
    for cand in [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "fixtures", "announcements")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "fixtures", "announcements")),
        os.path.abspath("fixtures/announcements"),
    ]:
        if os.path.exists(cand):
            ann_dir = cand
            break
    if not os.path.exists(ann_dir):
        return []

    ground_truth = {}
    gt_path = os.path.join(ann_dir, "ground_truth_labels.json")
    if os.path.exists(gt_path):
        try:
            with open(gt_path, "r", encoding="utf-8") as fp:
                ground_truth = json.load(fp)
        except Exception:
            pass

    results = []
    files = sorted([f for f in os.listdir(ann_dir) if not f.endswith(".json") and not f.startswith(".")])
    for f in files:
        path = os.path.join(ann_dir, f)
        ext = f.rsplit(".", 1)[1].upper()
        comp_name = _clean_company_name(f, ground_truth)
        try:
            with open(path, "rb") as fp:
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


@router.post("/parse")
async def parse_announcement(
    text: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    company_name: str = Form(default="Target Company"),
    current_user: UserModel = Depends(require_officer_or_coordinator),
) -> dict[str, Any]:
    """
    Parses drive announcements from pasted text, PDF, DOCX, EML, or TXT offline.
    Extracts structured requirements into Rule AST with per-field confidence and provenance.
    """
    raw_content = ""
    source_filename = "pasted_text.txt"

    if file:
        source_filename = file.filename or "announcement"
        bytes_data = await file.read()
        try:
            raw_content = _loader.load_from_bytes(bytes_data, source_filename)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    elif text:
        raw_content = text
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'text' or 'file' must be supplied for extraction.",
        )

    extracted = _extractor.extract(raw_content)
    review_payload = _review_service.build_review_payload(source_filename, extracted)

    # Cache active review session
    _active_reviews[source_filename] = {
        "payload": review_payload,
        "extracted": extracted,
    }

    fields_dict: dict[str, Any] = {}
    for attr in [
        "company_name", "drive_date", "mode", "ctc_lpa", "role", "location",
        "cgpa_min", "tenth_percentage_min", "twelfth_percentage_min",
        "allowed_branches", "active_backlogs_max", "gap_years_max"
    ]:
        val = getattr(extracted, attr, None)
        if val is not None:
            fields_dict[attr] = {
                "extracted_value": val.value,
                "confidence": val.confidence,
                "source_sentence": val.source_sentence,
                "is_ambiguous": val.is_ambiguous,
            }

    rule_set = extracted.to_rule_set(rule_set_id=f"rs_{company_name}", name=f"{company_name} Rules")
    requires_review = len(extracted.review_queue) > 0 or len(extracted.ambiguities) > 0

    return {
        "announcement_id": source_filename,
        "filename": source_filename,
        "company_name": extracted.company_name.value if extracted.company_name else company_name,
        "job_role": extracted.role.value if extracted.role else None,
        "ctc_lpa": extracted.ctc_lpa.value if extracted.ctc_lpa else None,
        "requires_review": requires_review,
        "review_queue": [r.model_dump() for r in extracted.review_queue],
        "ambiguities": [a.model_dump() for a in extracted.ambiguities],
        "fields": fields_dict,
        "rule_count": len(rule_set.rules),
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
