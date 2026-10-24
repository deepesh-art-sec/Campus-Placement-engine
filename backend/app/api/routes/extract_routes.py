"""
Requirement Extraction and Review Queue Routes.
Deterministic offline parser with side-by-side officer review.
"""

from __future__ import annotations

import os
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

    results = []
    files = sorted([f for f in os.listdir(ann_dir) if not f.endswith(".json") and not f.startswith(".")])
    for f in files:
        path = os.path.join(ann_dir, f)
        ext = f.rsplit(".", 1)[1].upper()
        name_part = f.split("_", 1)[1].rsplit(".", 1)[0].replace("_", " ").title()
        try:
            with open(path, "rb") as fp:
                text = _loader.load_from_bytes(fp.read(), f)
            results.append({
                "filename": f,
                "label": f"{name_part} ({ext})",
                "format": ext,
                "company_name": name_part.split()[0],
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
