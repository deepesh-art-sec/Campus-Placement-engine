"""
Requirement extraction module for placement announcements (pasted text, emails, PDFs, DOCX).
Deterministic parsing, provenance tracking, review queue, and AST generation.
"""

from backend.app.extract.cleaner import clean_text, extract_sentences
from backend.app.extract.deterministic_extractor import DeterministicExtractor
from backend.app.extract.document_loader import DocumentLoader, ScannedPdfError
from backend.app.extract.llm_adapter import HybridExtractionEngine, ILlmExtractor, MockLlmExtractor
from backend.app.extract.models import (
    AmbiguityItem,
    ExtractedField,
    ExtractedFieldReview,
    ExtractedRequirements,
    ExtractedRound,
    ExtractionFeedback,
    FieldReviewStatus,
)
from backend.app.extract.review_contract import ExtractionReviewService, FeedbackStore

__all__ = [
    "clean_text",
    "extract_sentences",
    "DocumentLoader",
    "ScannedPdfError",
    "DeterministicExtractor",
    "ExtractedRequirements",
    "ExtractedField",
    "ExtractedRound",
    "AmbiguityItem",
    "FieldReviewStatus",
    "ExtractedFieldReview",
    "ExtractionFeedback",
    "ExtractionReviewService",
    "FeedbackStore",
    "ILlmExtractor",
    "MockLlmExtractor",
    "HybridExtractionEngine",
]
