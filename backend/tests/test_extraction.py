"""
Comprehensive test suite for recruitment requirement extraction (Part 4).
Tests:
  - Dirty text handling (messy whitespace, odd bullets, fractions, smart quotes)
  - Multi-format document loading (.txt, .eml, .pdf, .docx, scanned PDF error)
  - Golden-file evaluation against all 25 announcements
  - Hard criterion test: fails if fewer than 20 announcements are fully extracted
  - Ambiguity detection and review queue routing
  - Translation to Part 2 RuleSet AST and end-to-end evaluation
  - Review contract and officer feedback audit store
  - Optional LLM adapter default-off and lower priority merge logic
"""

from __future__ import annotations

import datetime
import json
import os

import pytest

from backend.app.domain.eligibility.ast import (
    ActiveBacklogsMaxRule,
    BranchInRule,
    CGPAMinRule,
    GapYearsMaxRule,
    HistoricalBacklogsMaxRule,
    PercentageMinRule,
    RuleSet,
)
from backend.app.domain.eligibility.evaluator import EligibilityEvaluator, EligibilityStatus
from backend.app.domain.models import DriveMode, Student
from backend.app.extract.deterministic_extractor import DeterministicExtractor
from backend.app.extract.document_loader import DocumentLoader, ScannedPdfError
from backend.app.extract.llm_adapter import HybridExtractionEngine, MockLlmExtractor
from backend.app.extract.models import FieldReviewStatus
from backend.app.extract.review_contract import ExtractionReviewService, FeedbackStore

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FIXTURES_DIR = os.path.join(PROJECT_ROOT, "fixtures", "announcements")
GROUND_TRUTH_PATH = os.path.join(FIXTURES_DIR, "ground_truth_labels.json")


@pytest.fixture
def extractor() -> DeterministicExtractor:
    return DeterministicExtractor()


@pytest.fixture
def loader() -> DocumentLoader:
    return DocumentLoader()


# -----------------------------------------------------------------------------
# 1. Dirty Text, Bullets, and Fractions Tests
# -----------------------------------------------------------------------------

def test_dirty_input_text_messy_spacing_and_bullets(extractor: DeterministicExtractor) -> None:
    dirty_text = """
    \u2022\u2022\u2022 CAMPUS RECRUITMENT DRIVE \u2014 Cisco Systems \u2022\u2022\u2022
    Company : Cisco Systems
    Drive Date : 2026-11-20
    Mode of Drive : Hybrid
    CTC Offered : 18.5 LPA

    ELIGIBILITY CRITERIA:
    \u25cf Minimum CGPA Cut-off: 7.5 or above in B.Tech
    \u25cb 10th & 12th Percentage: Minimum 65.0% aggregate
    \u25aa Backlog Policy: Maximum 1 cleared backlog permitted, 0 active
    * Allowed Disciplines / Branches: CSE, IT, ECE
    * Education Gap: Maximum 1 year education gap permissible between 12th and degree. No gaps during engineering.

    SELECTION PROCESS:
    Round 1: Online Assessment - 60 mins
    Round 2: Technical Interview - 45 mins
    """

    res = extractor.extract(dirty_text)

    assert res.company_name is not None
    assert "Cisco" in res.company_name.value
    assert res.drive_date is not None
    assert res.drive_date.value == datetime.date(2026, 11, 20)
    assert res.mode is not None
    assert res.mode.value == DriveMode.HYBRID
    assert res.ctc_lpa is not None
    assert res.ctc_lpa.value == 18.5
    assert res.cgpa_min is not None
    assert res.cgpa_min.value == 7.5
    assert res.tenth_percentage_min is not None
    assert res.tenth_percentage_min.value == 65.0
    assert res.twelfth_percentage_min is not None
    assert res.twelfth_percentage_min.value == 65.0
    assert res.active_backlogs_max is not None
    assert res.active_backlogs_max.value == 0
    assert res.historical_backlogs_max is not None
    assert res.historical_backlogs_max.value == 1
    assert res.allowed_branches is not None
    assert res.allowed_branches.value == ["CSE", "IT", "ECE"]
    assert res.gap_years_max is not None
    assert res.gap_years_max.value == 1
    assert len(res.rounds) == 2


def test_fraction_and_scale_conversion(extractor: DeterministicExtractor) -> None:
    text_4_scale = """
    Company: Global Corp
    Drive Date: 2026-12-01
    Mode: On Campus
    CTC: 12.0 LPA
    Eligibility:
    Minimum CGPA: 3.2 / 4.0
    10th & 12th Percentage: 60%
    Backlogs: 0 active backlogs
    Branches: All Branches
    """
    res = extractor.extract(text_4_scale)
    assert res.cgpa_min is not None
    # 3.2 on 4.0 scale converts to 8.0 on 10.0 scale
    assert res.cgpa_min.value == 8.0


# -----------------------------------------------------------------------------
# 2. Document Loading & Scanned PDF Error
# -----------------------------------------------------------------------------

def test_document_loader_eml(loader: DocumentLoader) -> None:
    eml_path = os.path.join(FIXTURES_DIR, "08_deloitte_usi_email.eml")
    with open(eml_path, "rb") as f:
        content = f.read()
    txt = loader.load_from_bytes(content, "08.eml")
    assert "Deloitte USI" in txt
    assert "9.0 LPA" in txt


def test_document_loader_pdf(loader: DocumentLoader) -> None:
    pdf_path = os.path.join(FIXTURES_DIR, "14_larsen_and_toubro_spec.pdf")
    with open(pdf_path, "rb") as f:
        content = f.read()
    txt = loader.load_from_bytes(content, "14.pdf")
    assert "Larsen & Toubro" in txt
    assert "6.5 LPA" in txt


def test_document_loader_docx(loader: DocumentLoader) -> None:
    docx_path = os.path.join(FIXTURES_DIR, "20_reliance_industries_jd.docx")
    with open(docx_path, "rb") as f:
        content = f.read()
    txt = loader.load_from_bytes(content, "20.docx")
    assert "Reliance Industries" in txt
    assert "7.5 LPA" in txt


def test_scanned_pdf_error_when_ocr_disabled(loader: DocumentLoader) -> None:
    loader.ocr_enabled = False
    # A dummy PDF without text layer
    import io

    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    # Draw empty page without text
    c.showPage()
    c.save()
    pdf_bytes = buf.getvalue()

    with pytest.raises(ScannedPdfError) as exc_info:
        loader.load_from_bytes(pdf_bytes, "scanned.pdf")

    assert "Scanned PDF detected without embedded text layer" in str(exc_info.value)


# -----------------------------------------------------------------------------
# 3. Golden-File Benchmark Against All 25 Announcements
# -----------------------------------------------------------------------------

def test_golden_file_all_25_announcements(extractor: DeterministicExtractor, loader: DocumentLoader) -> None:
    with open(GROUND_TRUTH_PATH, encoding="utf-8") as f:
        ground_truth: dict = json.load(f)

    fully_extracted_count = 0

    for filename, truth in ground_truth.items():
        file_path = os.path.join(FIXTURES_DIR, filename)
        assert os.path.exists(file_path), f"Fixture file missing: {filename}"

        with open(file_path, "rb") as f:
            content = f.read()

        txt = loader.load_from_bytes(content, filename)
        extracted = extractor.extract(txt)

        # Field-by-field assertions
        assert extracted.company_name is not None
        assert extracted.company_name.value == truth["company_name"]

        assert extracted.drive_date is not None
        assert extracted.drive_date.value.isoformat() == truth["drive_date"]

        assert extracted.mode is not None
        assert extracted.mode.value.value == truth["mode"]

        assert extracted.ctc_lpa is not None
        assert extracted.ctc_lpa.value == truth["ctc_lpa"]

        assert extracted.cgpa_min is not None
        assert extracted.cgpa_min.value == truth["cgpa_min"]

        assert extracted.tenth_percentage_min is not None
        assert extracted.tenth_percentage_min.value == truth["tenth_percentage_min"]

        assert extracted.twelfth_percentage_min is not None
        assert extracted.twelfth_percentage_min.value == truth["twelfth_percentage_min"]

        assert extracted.active_backlogs_max is not None
        assert extracted.active_backlogs_max.value == truth["active_backlogs_max"]

        if truth["historical_backlogs_max"] is not None:
            assert extracted.historical_backlogs_max is not None
            assert extracted.historical_backlogs_max.value == truth["historical_backlogs_max"]
        else:
            assert extracted.historical_backlogs_max is None

        assert extracted.allowed_branches is not None
        if truth["allowed_branches"] == ["All Branches"]:
            assert extracted.allowed_branches.value == ["All Branches"]
        else:
            assert set(extracted.allowed_branches.value) == set(truth["allowed_branches"])

        assert extracted.gap_years_max is not None
        assert extracted.gap_years_max.value == truth["gap_years_max"]

        assert len(extracted.rounds) == truth["rounds_count"]

        fully_extracted_count += 1

    assert fully_extracted_count == 25


def test_extraction_threshold_fails_if_fewer_than_20_extracted(
    extractor: DeterministicExtractor, loader: DocumentLoader
) -> None:
    """
    CRITERION 3: Must extract structured requirements from at least 20 of 25 announcements
    WITHOUT manual re-typing, fully offline.
    """
    with open(GROUND_TRUTH_PATH, encoding="utf-8") as f:
        ground_truth: dict = json.load(f)

    successful = 0
    for filename, truth in ground_truth.items():
        file_path = os.path.join(FIXTURES_DIR, filename)
        txt = loader.load_from_bytes(open(file_path, "rb").read(), filename)
        extracted = extractor.extract(txt)

        # Confirm all critical fields are extracted accurately
        if (
            extracted.company_name and extracted.company_name.value == truth["company_name"]
            and extracted.cgpa_min and extracted.cgpa_min.value == truth["cgpa_min"]
            and extracted.ctc_lpa and extracted.ctc_lpa.value == truth["ctc_lpa"]
            and extracted.drive_date and extracted.drive_date.value.isoformat() == truth["drive_date"]
            and extracted.active_backlogs_max is not None
            and extracted.allowed_branches is not None
        ):
            successful += 1

    # Strict assertion: must be at least 20 out of 25
    assert successful >= 20, f"Extraction failed to meet threshold: only {successful}/25 succeeded."
    assert successful == 25, f"Expected 25/25 perfect extractions, got {successful}"


# -----------------------------------------------------------------------------
# 4. Ambiguity Detection & Review Queue Routing
# -----------------------------------------------------------------------------

def test_ambiguity_throughout_percentage_flagged(extractor: DeterministicExtractor) -> None:
    raw_announcement = """
    Company: Apex Financial
    Drive Date: 2026-11-15
    Mode: On Campus
    CTC Offered: 15.0 LPA
    Eligibility:
    Minimum 65% throughout in all exams.
    Backlogs: No active backlogs
    Branches: CSE, IT
    """
    res = extractor.extract(raw_announcement)

    # Must flag ambiguity item
    assert len(res.ambiguities) == 1
    amb = res.ambiguities[0]
    assert amb.field_name == "percentage_throughout"
    assert "throughout" in amb.reason.lower()

    # Must add to review queue
    flagged = [item for item in res.review_queue if item.is_ambiguous]
    assert len(flagged) >= 1
    assert any("throughout" in f.ambiguity_reason.lower() for f in flagged if f.ambiguity_reason)


def test_ambiguity_backlog_timing_flagged(extractor: DeterministicExtractor) -> None:
    raw_announcement = """
    Company: Wipro
    Drive Date: 2026-11-15
    Mode: On Campus
    CTC: 6.5 LPA
    Backlog Policy: No active backlogs at time of joining
    Allowed Branches: All Branches
    """
    res = extractor.extract(raw_announcement)

    assert len(res.ambiguities) == 1
    assert res.ambiguities[0].field_name == "backlog_timing"
    assert "at time of joining" in res.ambiguities[0].reason


# -----------------------------------------------------------------------------
# 5. AST RuleSet Translation & Pure Domain Evaluation Integration
# -----------------------------------------------------------------------------

def test_ast_ruleset_translation_and_evaluation(extractor: DeterministicExtractor) -> None:
    announcement = """
    Company: Google
    Drive Date: 2026-11-01
    Mode: Hybrid
    CTC Offered: 36.0 LPA
    Eligibility Criteria:
    Minimum CGPA Cut-off: 8.5 or above in B.Tech
    10th & 12th Percentage: Minimum 60.0% aggregate
    Backlog Policy: Strictly 0 (No active or historical backlogs)
    Allowed Disciplines: CSE, IT, Data Science
    Education Gap: Maximum 1 year education gap permissible between 12th and degree. No gaps during engineering.
    """

    res = extractor.extract(announcement)
    rule_set: RuleSet = res.to_rule_set("google_drive_2026", "Google Campus Drive Requirements")

    assert rule_set.id == "google_drive_2026"
    assert len(rule_set.rules) == 7

    rule_types = {type(r) for r in rule_set.rules}
    assert CGPAMinRule in rule_types
    assert PercentageMinRule in rule_types
    assert BranchInRule in rule_types
    assert ActiveBacklogsMaxRule in rule_types
    assert HistoricalBacklogsMaxRule in rule_types
    assert GapYearsMaxRule in rule_types

    # End-to-end evaluation with Part 2 evaluator
    evaluator_engine = EligibilityEvaluator()
    eligible_student = Student(
        id="stu_001",
        roll_no="CS101",
        name="Alice Kumar",
        email="alice@college.edu",
        date_of_birth=datetime.date(2004, 5, 10),
        branch="CSE",
        program="B.Tech",
        cgpa=8.8,
        tenth_percentage=92.0,
        twelfth_percentage=89.0,
        gap_years=[],
        backlogs=[],
    )
    decision = evaluator_engine.evaluate(eligible_student, rule_set, drive_id="google_drive_2026")
    assert decision.status == EligibilityStatus.ELIGIBLE

    ineligible_student = Student(
        id="stu_002",
        roll_no="ME101",
        name="Bob Singh",
        email="bob@college.edu",
        date_of_birth=datetime.date(2004, 6, 15),
        branch="Mechanical Engineering",
        program="B.Tech",
        cgpa=7.2,
        tenth_percentage=80.0,
        twelfth_percentage=75.0,
        gap_years=[],
        backlogs=[],
    )
    decision2 = evaluator_engine.evaluate(ineligible_student, rule_set, drive_id="google_drive_2026")
    assert decision2.status == EligibilityStatus.INELIGIBLE
    assert len(decision2.failed_rules) >= 2  # Fails CGPA and Branch


# -----------------------------------------------------------------------------
# 6. Review Contract and Officer Feedback Audit Store
# -----------------------------------------------------------------------------

def test_review_contract_and_feedback_storage(extractor: DeterministicExtractor) -> None:
    raw_announcement = """
    Company: Test Corp
    Drive Date: 2026-12-15
    Mode: On Campus
    CTC Offered: 10.0 LPA
    Minimum CGPA: 7.0
    Branches: CSE, IT
    """
    res = extractor.extract(raw_announcement)

    store = FeedbackStore()
    review_service = ExtractionReviewService(feedback_store=store)

    payload = review_service.build_review_payload("announcement_101", res)
    assert payload["announcement_id"] == "announcement_101"
    assert len(payload["fields"]) >= 4

    # Officer edits CGPA from 7.0 to 7.5
    reviewed = review_service.process_field_review(
        announcement_id="announcement_101",
        field_name="cgpa_min",
        status=FieldReviewStatus.EDITED,
        source_sentence="Minimum CGPA: 7.0",
        extracted_value=7.0,
        correction=7.5,
        reviewed_by="TPO_HEAD",
    )

    assert reviewed.status == FieldReviewStatus.EDITED
    assert reviewed.correction == 7.5

    # Check feedback store
    feedbacks = store.list_feedback("announcement_101")
    assert len(feedbacks) == 1
    assert feedbacks[0].field_name == "cgpa_min"
    assert feedbacks[0].extracted_value == 7.0
    assert feedbacks[0].corrected_value == 7.5
    assert feedbacks[0].reviewed_by == "TPO_HEAD"

    stats = store.feedback_stats()
    assert stats[FieldReviewStatus.EDITED] == 1


# -----------------------------------------------------------------------------
# 7. LLM Adapter Default OFF & Hybrid Merger
# -----------------------------------------------------------------------------

def test_llm_adapter_disabled_by_default() -> None:
    llm = MockLlmExtractor()
    assert llm.is_enabled() is False

    with pytest.raises(RuntimeError):
        llm.extract("Sample announcement")


def test_hybrid_engine_prioritizes_deterministic(extractor: DeterministicExtractor) -> None:
    llm = MockLlmExtractor(enabled=True)
    engine = HybridExtractionEngine(deterministic_extractor=extractor, llm_extractor=llm)

    text = """
    Company: Amazon
    Drive Date: 2026-11-07
    Mode: On Campus
    CTC Offered: 32.0 LPA
    Minimum CGPA: 7.5
    Backlogs: 0 active backlogs
    Allowed Branches: CSE, IT, ECE, EEE
    """
    merged = engine.extract(text)

    # Primary fields come from deterministic extractor
    assert merged.company_name is not None
    assert merged.company_name.value == "Amazon"
    assert merged.ctc_lpa is not None
    assert merged.ctc_lpa.value == 32.0
    assert merged.cgpa_min is not None
    assert merged.cgpa_min.value == 7.5
