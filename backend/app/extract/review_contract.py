"""
Review contract service and feedback storage for placement requirement extraction.
Facilitates side-by-side officer review (accept, edit, reject) and stores corrections for continuous feedback.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any

from backend.app.extract.models import (
    ExtractedFieldReview,
    ExtractedRequirements,
    ExtractionFeedback,
    FieldReviewStatus,
)


class FeedbackStore:
    """Stores extraction feedback and officer corrections."""

    def __init__(self) -> None:
        self._feedback: list[ExtractionFeedback] = []

    def record_feedback(
        self,
        announcement_id: str,
        field_name: str,
        source_text: str,
        extracted_value: Any,
        corrected_value: Any,
        status: FieldReviewStatus,
        reviewed_by: str = "TPO_OFFICER",
    ) -> ExtractionFeedback:
        record = ExtractionFeedback(
            id=str(uuid.uuid4()),
            announcement_id=announcement_id,
            field_name=field_name,
            source_text=source_text,
            extracted_value=extracted_value,
            corrected_value=corrected_value,
            status=status,
            reviewed_by=reviewed_by,
            reviewed_at=datetime.datetime.utcnow(),
        )
        self._feedback.append(record)
        return record

    def list_feedback(self, announcement_id: str | None = None) -> list[ExtractionFeedback]:
        if announcement_id is None:
            return list(self._feedback)
        return [f for f in self._feedback if f.announcement_id == announcement_id]

    def feedback_stats(self) -> dict[str, int]:
        stats: dict[str, int] = {
            FieldReviewStatus.ACCEPTED: 0,
            FieldReviewStatus.EDITED: 0,
            FieldReviewStatus.REJECTED: 0,
            FieldReviewStatus.PENDING: 0,
        }
        for f in self._feedback:
            stats[f.status] += 1
        return stats

    def clear(self) -> None:
        self._feedback.clear()


class ExtractionReviewService:
    """Provides side-by-side review payloads and processes officer decisions."""

    def __init__(self, feedback_store: FeedbackStore | None = None) -> None:
        self.feedback_store = feedback_store or FeedbackStore()

    def build_review_payload(self, announcement_id: str, extracted: ExtractedRequirements) -> dict[str, Any]:
        """Constructs UI payload showing original text alongside extracted fields."""
        items: list[dict[str, Any]] = []

        field_mapping: list[tuple[str, Any]] = [
            ("company_name", extracted.company_name),
            ("drive_date", extracted.drive_date),
            ("mode", extracted.mode),
            ("ctc_lpa", extracted.ctc_lpa),
            ("cgpa_min", extracted.cgpa_min),
            ("tenth_percentage_min", extracted.tenth_percentage_min),
            ("twelfth_percentage_min", extracted.twelfth_percentage_min),
            ("allowed_branches", extracted.allowed_branches),
            ("allowed_programs", extracted.allowed_programs),
            ("batch_year", extracted.batch_year),
            ("active_backlogs_max", extracted.active_backlogs_max),
            ("historical_backlogs_max", extracted.historical_backlogs_max),
            ("gap_years_max", extracted.gap_years_max),
            ("allow_gap_during_degree", extracted.allow_gap_during_degree),
        ]

        for fname, fval in field_mapping:
            if fval is not None:
                items.append({
                    "field_name": fname,
                    "extracted_value": fval.value,
                    "confidence": fval.confidence,
                    "source_sentence": fval.source_sentence,
                    "is_ambiguous": fval.is_ambiguous,
                    "ambiguity_reason": fval.ambiguity_reason,
                    "status": FieldReviewStatus.PENDING,
                })

        return {
            "announcement_id": announcement_id,
            "raw_text": extracted.raw_text,
            "overall_confidence": extracted.overall_confidence,
            "fields": items,
            "ambiguities": [a.model_dump() for a in extracted.ambiguities],
            "review_queue": [rq.model_dump() for rq in extracted.review_queue],
        }

    def process_field_review(
        self,
        announcement_id: str,
        field_name: str,
        status: FieldReviewStatus,
        source_sentence: str,
        extracted_value: Any,
        correction: Any | None = None,
        reviewed_by: str = "TPO_OFFICER",
    ) -> ExtractedFieldReview:
        """Processes officer decision (accept, edit, reject) and stores feedback."""
        effective_value = correction if status == FieldReviewStatus.EDITED else (
            None if status == FieldReviewStatus.REJECTED else extracted_value
        )

        self.feedback_store.record_feedback(
            announcement_id=announcement_id,
            field_name=field_name,
            source_text=source_sentence,
            extracted_value=extracted_value,
            corrected_value=effective_value,
            status=status,
            reviewed_by=reviewed_by,
        )

        return ExtractedFieldReview(
            field_name=field_name,
            extracted_value=extracted_value,
            confidence=1.0 if status == FieldReviewStatus.ACCEPTED else 0.5,
            source_sentence=source_sentence,
            status=status,
            correction=effective_value,
        )
