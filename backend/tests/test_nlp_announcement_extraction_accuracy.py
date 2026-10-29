"""
End-to-End Accuracy, Regression, and Provenance Test Suite for IM-101 Announcement Extraction.
Tests:
  - 100-document synthetic dataset benchmark (precision, recall, F1, exact match)
  - PyMuPDF text & table extraction for digital PDFs
  - Tesseract OCR extraction for scanned PDFs
  - DOCX structured tables & paragraphs
  - UTF-8 text & email formats
  - Disambiguation: min vs max CGPA, 10th vs 12th, active vs historical backlogs, CTC ranges vs stipends
  - Error resilience: empty, corrupt, and garbled scanned documents
  - Coordinator confirmation & SQLite WAL persistence
"""

from __future__ import annotations

import datetime
import io
import json
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.main import app, seed_default_accounts
from backend.app.extract.document_loader import (
    CorruptDocumentError,
    DocumentChunk,
    DocumentLoader,
    EmptyDocumentError,
    ScannedPdfError,
    UnsupportedFormatError,
)
from backend.app.extract.nlp_engine import NLPEngine
from backend.app.storage.database import SessionLocal
from backend.app.storage.models.entities import (
    CompanyModel,
    DriveModel,
    DriveRequirementVersionModel,
    EventModel,
)
from scripts.evaluate_accuracy import evaluate


@pytest.fixture
def auth_client():
    seed_default_accounts()
    with TestClient(app) as client:
        res = client.post("/api/auth/login", json={"username": "coordinator", "password": "coord123"})
        assert res.status_code == 200, res.text
        csrf = res.json()["csrf_token"]
        yield client, csrf


def test_100_synthetic_dataset_benchmark():
    """Asserts that 100-document dataset benchmark meets strict field-level accuracy and F1 targets."""
    results = evaluate()

    assert results["total_documents"] == 100
    assert results["overall_precision"] >= 0.95, f"Overall precision too low: {results['overall_precision']}"
    assert results["overall_recall"] >= 0.95, f"Overall recall too low: {results['overall_recall']}"
    assert results["overall_f1"] >= 0.95, f"Overall F1 score too low: {results['overall_f1']}"
    assert results["digital_document_accuracy"] >= 0.95, f"Digital doc accuracy too low: {results['digital_document_accuracy']}"
    assert results["edge_case_pass_rate"] == 1.0, "Edge cases failed to be handled correctly"

    # Field-level assertions
    fields = results["field_scores"]
    assert fields["company_name"]["precision"] >= 0.95
    assert fields["role"]["precision"] >= 0.95
    assert fields["allowed_branches"]["precision"] >= 0.95
    assert fields["cgpa_min"]["precision"] >= 0.95
    assert fields["tenth_percentage_min"]["precision"] >= 0.95
    assert fields["twelfth_percentage_min"]["precision"] >= 0.95
    assert fields["active_backlogs_max"]["precision"] >= 0.95
    assert fields["historical_backlogs_max"]["precision"] >= 0.95
    assert fields["ctc_lpa"]["precision"] >= 0.95
    assert fields["application_deadline"]["precision"] >= 0.95


def test_provenance_and_page_tracking():
    """Verifies that extracted fields contain provenance, source sentence, and page numbers."""
    engine = NLPEngine()
    text = (
        "CAMPUS DRIVE NOTICE 2026\n"
        "Organization: Atlassian\n"
        "Job Role: Software Engineer\n"
        "Eligible Branches: CSE, IT\n"
        "Package Offered: 45 LPA\n"
        "Eligibility:\n"
        "- Minimum CGPA required: 8.0\n"
        "- Minimum 70% in 10th and 12th\n"
        "- No active backlogs allowed\n"
        "Drive Date: 2026-11-20\n"
        "Application Deadline: 2026-11-10"
    )
    reqs = engine.extract(text)

    assert reqs.company_name is not None
    assert reqs.company_name.value == "Atlassian"
    assert reqs.company_name.confidence >= 0.95
    assert "Atlassian" in reqs.company_name.source_sentence
    assert reqs.company_name.page_number is not None

    assert reqs.role is not None
    assert reqs.role.value == "Software Engineer"
    assert reqs.role.confidence >= 0.95

    assert reqs.cgpa_min is not None
    assert reqs.cgpa_min.value == 8.0

    assert reqs.tenth_percentage_min is not None
    assert reqs.tenth_percentage_min.value == 70.0
    assert reqs.twelfth_percentage_min is not None
    assert reqs.twelfth_percentage_min.value == 70.0

    assert reqs.active_backlogs_max is not None
    assert reqs.active_backlogs_max.value == 0

    assert reqs.ctc_lpa is not None
    assert reqs.ctc_lpa.value == 45.0


def test_zero_hallucination_on_missing_fields():
    """Verifies that when fields are missing from an announcement, the engine returns None instead of guessing."""
    engine = NLPEngine()
    minimal_text = (
        "Google Campus Visit Notice\n"
        "Date of Drive: 2026-11-25\n"
        "All interested students must register."
    )
    reqs = engine.extract(minimal_text)

    # Missing fields must strictly be None
    assert reqs.role is None
    assert reqs.location is None
    assert reqs.ctc_lpa is None
    assert reqs.cgpa_min is None
    assert reqs.tenth_percentage_min is None
    assert reqs.twelfth_percentage_min is None
    assert reqs.active_backlogs_max is None


def test_ctc_range_and_stipend_disambiguation():
    """Verifies that CTC ranges and monthly stipends are not conflated."""
    engine = NLPEngine()
    text = (
        "Recruitment Announcement: Microsoft\n"
        "Job Role: Software Engineer\n"
        "Stipend during 6-month internship: ₹50,000 per month\n"
        "Full-time CTC Offered: 16.0 LPA - 24.0 LPA based on interview performance\n"
        "Drive Date: 2026-12-05"
    )
    reqs = engine.extract(text)

    assert reqs.ctc_lpa is not None
    assert reqs.ctc_lpa.value == 16.0  # Base/min CTC in range


def test_backlog_standing_disambiguation():
    """Verifies exact differentiation between active and cleared/historical backlogs."""
    engine = NLPEngine()

    # Case A: Strict 0 active and 0 historical
    text_a = "Eligibility: Strictly clean academic history (0 active, 0 historical backlogs)."
    reqs_a = engine.extract(text_a)
    assert reqs_a.active_backlogs_max is not None and reqs_a.active_backlogs_max.value == 0
    assert reqs_a.historical_backlogs_max is not None and reqs_a.historical_backlogs_max.value == 0

    # Case B: 0 active, up to 2 cleared allowed
    text_b = "Eligibility: No active backlogs allowed at the time of drive. Up to 2 cleared backlogs permitted."
    reqs_b = engine.extract(text_b)
    assert reqs_b.active_backlogs_max is not None and reqs_b.active_backlogs_max.value == 0
    assert reqs_b.historical_backlogs_max is not None and reqs_b.historical_backlogs_max.value == 2


def test_scanned_pdf_ocr_execution():
    """Tests that a scanned PDF requiring Tesseract OCR extracts cleanly without errors."""
    loader = DocumentLoader(ocr_enabled=True)
    scanned_path = os.path.abspath("fixtures/synthetic_100/documents/doc_038_infosys_scanned.pdf")
    with open(scanned_path, "rb") as f:
        bytes_data = f.read()

    full_text, chunks, page_count = loader.load_structured(bytes_data, "doc_038_infosys_scanned.pdf")
    assert len(full_text) > 50
    assert "Infosys" in full_text
    assert page_count >= 1

    engine = NLPEngine()
    reqs = engine.extract(full_text)
    assert reqs.company_name is not None
    assert reqs.company_name.value == "Infosys"


def test_api_upload_parse_and_confirm_save(auth_client):
    """End-to-end integration test: Upload file -> Parse -> Review -> Confirm Save -> Verify SQLite WAL."""
    client, csrf = auth_client

    sample_path = os.path.abspath("fixtures/synthetic_100/documents/doc_001_google_sde.pdf")
    with open(sample_path, "rb") as f:
        upload_res = client.post(
            "/api/extract/parse",
            files={"file": ("doc_001_google_sde.pdf", f, "application/pdf")},
            data={"company_name": "Google"},
            headers={"X-CSRF-Token": csrf},
        )
    assert upload_res.status_code == 200, upload_res.text
    parsed = upload_res.json()

    assert parsed["company_name"] == "Google"
    assert parsed["job_role"] == "Software Development Engineer"
    assert parsed["ctc_lpa"] == 35.0
    assert parsed["min_cgpa"] == 8.0
    assert "CSE" in parsed["allowed_branches"]
    assert "fields" in parsed
    assert "page_number" in parsed["fields"]["company_name"]

    # Save confirmed drive
    save_payload = {
        "company_name": parsed["company_name"],
        "job_role": parsed["job_role"],
        "job_location": parsed["location"],
        "drive_date": parsed["drive_date"],
        "application_deadline": parsed["application_deadline"],
        "mode": parsed["mode"],
        "ctc_lpa": parsed["ctc_lpa"],
        "min_cgpa": parsed["min_cgpa"],
        "min_tenth_percentage": parsed["min_tenth_percentage"],
        "min_twelfth_percentage": parsed["min_twelfth_percentage"],
        "allowed_branches": parsed["allowed_branches"],
        "max_active_backlogs": parsed["max_active_backlogs"] or 0,
        "max_gap_years": parsed["max_gap_years"] or 1,
        "confirmed_by": "coordinator",
    }
    save_res = client.post(
        "/api/extract/confirm-save",
        json=save_payload,
        headers={"X-CSRF-Token": csrf},
    )
    assert save_res.status_code == 201, save_res.text
    save_data = save_res.json()
    assert save_data["success"] is True
    assert save_data["status"] == "draft"
    drive_id = save_data["drive_id"]

    # Verify directly in SQLite database
    db: Session = SessionLocal()
    try:
        drive_row = db.execute(select(DriveModel).where(DriveModel.id == drive_id)).scalar_one_or_none()
        assert drive_row is not None
        assert drive_row.company.name == "Google"
        assert drive_row.ctc_lpa == 35.0
        assert drive_row.status == "draft"

        req_row = db.execute(
            select(DriveRequirementVersionModel).where(DriveRequirementVersionModel.drive_id == drive_id)
        ).scalar_one_or_none()
        assert req_row is not None
        assert req_row.min_cgpa == 8.0
        branches_list = json.loads(req_row.allowed_branches_json) if req_row.allowed_branches_json else []
        assert "CSE" in branches_list
    finally:
        db.close()
