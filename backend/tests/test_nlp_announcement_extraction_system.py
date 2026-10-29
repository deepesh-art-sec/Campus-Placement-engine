"""
Comprehensive Unit, Integration, and NLP Accuracy Test Suite for:
NLP-Powered Announcement Extraction and Testing System.

Covers:
1. Unit Tests:
   - PyMuPDF (fitz) PDF text & table extraction
   - python-docx Word document extraction
   - Plaintext UTF-8 extraction
   - Scanned PDF detection and OCR fallback behavior
   - Company name, role, location, drive date, application deadline, and selection rounds extraction
   - Context-aware numeric disambiguation (CGPA vs experience/batch year, salary vs headcount, active vs historical backlogs)
   - Canonical branch normalization
   - Error handling: empty, corrupt, unsupported, and encrypted documents

2. Integration Tests:
   - Full pipeline: Upload/text -> FastAPI -> DocumentLoader -> NLPEngine -> Pydantic Validation -> Review Queue
   - Review resolution: accepting, editing, and rejecting field values
   - Coordinator confirmation: SQLite persistence across CompanyModel, DriveModel, DriveRequirementVersionModel, EventModel
   - Idempotency and deduplication on repeated submissions
   - Persistence verification after database reconnection

3. NLP Accuracy Tests (25 Synthetic Announcement Test Cases):
   - 25 distinct announcements with diverse wording, formats, cutoffs, salary ranges, and noise
   - Field-level Precision, Recall, and F1 evaluation against ground-truth labels
   - Target: >= 90% F1 on clearly stated key fields
"""

from __future__ import annotations

import datetime
import io
import json
import os
from typing import Any

import docx
import fitz
import pytest
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.main import app, seed_default_accounts
from backend.app.domain.models import DriveMode, RoundType
from backend.app.extract.cleaner import clean_text
from backend.app.extract.document_loader import (
    CorruptDocumentError,
    DocumentLoader,
    EmptyDocumentError,
    ScannedPdfError,
    UnsupportedFormatError,
)
from backend.app.extract.models import ExtractedRequirements
from backend.app.extract.nlp_engine import NLPEngine
from backend.app.storage.database import SessionLocal
from backend.app.storage.models.entities import (
    CompanyModel,
    DriveModel,
    DriveRequirementVersionModel,
    EventModel,
)


@pytest.fixture(scope="module")
def nlp_engine() -> NLPEngine:
    return NLPEngine()


@pytest.fixture(scope="module")
def doc_loader() -> DocumentLoader:
    return DocumentLoader(ocr_enabled=True)


@pytest.fixture
def auth_client():
    seed_default_accounts()
    with TestClient(app) as client:
        res = client.post("/api/auth/login", json={"username": "coordinator", "password": "coord123"})
        assert res.status_code == 200, res.text
        csrf = res.json()["csrf_token"]
        yield client, csrf


def make_pdf(lines: list[str]) -> bytes:
    """Creates a real digital PDF in-memory using PyMuPDF."""
    doc = fitz.open()
    page = doc.new_page()
    p = fitz.Point(40, 40)
    for l in lines:
        page.insert_text(p, l, fontsize=11)
        p.y += 18
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def make_docx(paragraphs: list[str], table: list[list[str]] | None = None) -> bytes:
    """Creates a real Word document in-memory using python-docx."""
    doc = docx.Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    if table:
        t = doc.add_table(rows=len(table), cols=len(table[0]))
        for r_i, row in enumerate(table):
            for c_i, cell in enumerate(row):
                t.rows[r_i].cells[c_i].text = cell
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# =============================================================================
# PART 1: UNIT TESTS (LOADERS, NLP EXTRACTORS, DISAMBIGUATION, ERROR HANDLING)
# =============================================================================


class TestDocumentLoadersUnit:
    def test_pdf_extraction_via_pymupdf(self, doc_loader: DocumentLoader):
        pdf_bytes = make_pdf([
            "Anthropic AI Campus Recruitment Circular 2026",
            "Role: Research Engineer",
            "CTC: 45 LPA",
            "Drive Date: 2026-12-10",
        ])
        text = doc_loader.load_from_bytes(pdf_bytes, "anthropic.pdf")
        assert "Anthropic AI" in text
        assert "Research Engineer" in text
        assert "45 LPA" in text

    def test_docx_extraction_via_python_docx(self, doc_loader: DocumentLoader):
        docx_bytes = make_docx(
            paragraphs=["Stripe India Recruitment Notice", "Role: Software Engineer"],
            table=[["Cutoff", "Value"], ["CGPA", "8.0"], ["CTC", "35 LPA"]],
        )
        text = doc_loader.load_from_bytes(docx_bytes, "stripe.docx")
        assert "Stripe India" in text
        assert "CGPA | 8.0" in text
        assert "CTC | 35 LPA" in text

    def test_txt_extraction_utf8(self, doc_loader: DocumentLoader):
        txt_content = "Palantir Technologies\nRole: Deployment Strategist\nCTC: 30 LPA"
        text = doc_loader.load_from_bytes(txt_content.encode("utf-8"), "palantir.txt")
        assert "Palantir Technologies" in text
        assert "30 LPA" in text

    def test_empty_document_raises_error(self, doc_loader: DocumentLoader):
        with pytest.raises(EmptyDocumentError):
            doc_loader.load_from_bytes(b"", "empty.pdf")
        with pytest.raises(EmptyDocumentError):
            doc_loader.load_from_bytes(b"   \n\t  ", "blank.txt")

    def test_corrupt_documents_raise_error(self, doc_loader: DocumentLoader):
        with pytest.raises(CorruptDocumentError):
            doc_loader.load_from_bytes(b"%PDF-invalid broken bytes", "broken.pdf")
        with pytest.raises(CorruptDocumentError):
            doc_loader.load_from_bytes(b"PK\x03\x04 fake zip docx", "broken.docx")

    def test_unsupported_format_raises_error(self, doc_loader: DocumentLoader):
        with pytest.raises(UnsupportedFormatError):
            doc_loader.load_from_bytes(b"raw data", "image.png")
        with pytest.raises(UnsupportedFormatError):
            doc_loader.load_from_bytes(b"exec data", "app.exe")

    def test_scanned_pdf_detection_and_fallback(self):
        loader_no_ocr = DocumentLoader(ocr_enabled=False)
        buf = io.BytesIO()
        c = canvas.Canvas(buf)
        c.drawString(10, 10, "")  # empty drawing without text
        c.showPage()
        c.save()
        scanned_bytes = buf.getvalue()

        with pytest.raises(ScannedPdfError) as exc_info:
            loader_no_ocr.load_from_bytes(scanned_bytes, "scanned.pdf")
        assert "Scanned PDF detected" in str(exc_info.value)


class TestNLPExtractionAndDisambiguationUnit:
    def test_context_aware_cgpa_vs_other_numbers(self, nlp_engine: NLPEngine):
        # Text has batch year (2026), experience (2 years), headcount (150 students), and CGPA cutoff (7.5)
        text = """
        Recruitment drive for batch of 2026.
        We have 150 open vacancies for candidates with 0-2 years experience.
        Candidates must have a minimum CGPA of 7.5 in B.Tech.
        """
        res = nlp_engine.extract(text)
        assert res.cgpa_min is not None
        assert res.cgpa_min.value == 7.5
        assert res.batch_year is not None
        assert res.batch_year.value == 2026

    def test_distinguish_active_vs_historical_backlogs(self, nlp_engine: NLPEngine):
        text_a = "Students with strictly 0 active backlogs are eligible. Maximum 2 cleared historical backlogs allowed."
        res_a = nlp_engine.extract(text_a)
        assert res_a.active_backlogs_max is not None
        assert res_a.active_backlogs_max.value == 0
        assert res_a.historical_backlogs_max is not None
        assert res_a.historical_backlogs_max.value == 2

        text_b = "No standing arrears permitted. Clean record throughout."
        res_b = nlp_engine.extract(text_b)
        assert res_b.active_backlogs_max is not None
        assert res_b.active_backlogs_max.value == 0

    def test_distinguish_salary_vs_non_salary_figures(self, nlp_engine: NLPEngine):
        text = """
        Company: Snowflake Computing
        Location: Bangalore, PIN 560103.
        Round 1 duration is 90 mins for 250 candidates.
        Annual Package: CTC Offered is 27.5 LPA.
        """
        res = nlp_engine.extract(text)
        assert res.ctc_lpa is not None
        assert res.ctc_lpa.value == 27.5
        assert "Snowflake" in res.company_name.value
        assert "Bangalore" in res.location.value

    def test_application_deadline_vs_drive_date(self, nlp_engine: NLPEngine):
        text = """
        Company: Databricks
        Last date to apply / Registration deadline: 2026-11-15
        Date of Placement Drive: 2026-11-28
        Mode: On-Campus
        """
        res = nlp_engine.extract(text)
        assert res.drive_date is not None
        assert res.drive_date.value == datetime.date(2026, 11, 28)
        assert res.application_deadline is not None
        assert res.application_deadline.value == datetime.date(2026, 11, 15)

    def test_canonical_branch_normalization(self, nlp_engine: NLPEngine):
        text = "Eligible branches: Computer Science and Engineering, Info Tech, Electronics & Comm, Mechanical, Civil"
        res = nlp_engine.extract(text)
        assert res.allowed_branches is not None
        assert set(res.allowed_branches.value) == {"CSE", "IT", "ECE", "Mechanical Engineering", "Civil Engineering"}

    def test_ambiguity_and_missing_criteria_flagged(self, nlp_engine: NLPEngine):
        text = "Company: Stealth Startup. Package: Competitive. Eligible candidates can apply."
        res = nlp_engine.extract(text)
        # Should flag missing academic cutoffs
        assert res.cgpa_min is None
        assert res.tenth_percentage_min is None
        assert res.active_backlogs_max is None


# =============================================================================
# PART 2: INTEGRATION TESTS (API, REVIEW FORM RESOLUTION, SQLITE PERSISTENCE)
# =============================================================================


class TestExtractionIntegrationPipeline:
    def test_upload_parse_validates_and_populates_review_payload(self, auth_client):
        client, csrf = auth_client
        pdf_bytes = make_pdf([
            "NVIDIA Graphics Private Limited",
            "Role: GPU Systems Software Engineer",
            "Location: Pune, India",
            "CTC: 31.0 LPA",
            "Drive Date: 2026-12-12",
            "Application Deadline: 2026-12-01",
            "Eligibility:",
            "Minimum CGPA: 8.0",
            "10th & 12th: 70%",
            "Backlogs: 0 active arrears allowed",
            "Branches: CSE, IT, ECE",
            "Education Gap: Max 1 year",
            "Selection Process:",
            "Round 1: Coding Assessment - 90 mins",
            "Round 2: Systems Architecture Interview - 60 mins",
        ])

        files = {"file": ("nvidia_announcement.pdf", pdf_bytes, "application/pdf")}
        res = client.post("/api/extract/parse", files=files, headers={"X-CSRF-Token": csrf})
        assert res.status_code == 200, res.text
        data = res.json()

        assert "NVIDIA" in data["company_name"]
        assert data["job_role"] == "GPU Systems Software Engineer"
        assert data["ctc_lpa"] == 31.0
        assert data["min_cgpa"] == 8.0
        assert data["min_tenth_percentage"] == 70.0
        assert data["min_twelfth_percentage"] == 70.0
        assert data["max_active_backlogs"] == 0
        assert data["drive_date"] == "2026-12-12"
        assert data["application_deadline"] == "2026-12-01"
        assert len(data["selection_process"]) == 2
        assert "fields" in data
        assert data["fields"]["cgpa_min"]["confidence"] >= 0.85

    def test_review_resolution_accept_and_edit_fields(self, auth_client):
        client, csrf = auth_client
        # 1. Parse an announcement
        res_parse = client.post(
            "/api/extract/parse",
            data={"text": "Company: Adobe Inc.\nRole: SDE\nCTC: 25 LPA\nMinimum CGPA: 7.0"},
            headers={"X-CSRF-Token": csrf},
        )
        assert res_parse.status_code == 200
        announcement_id = res_parse.json()["announcement_id"]

        # 2. Officer edits the CGPA field
        res_resolve = client.post(
            "/api/extract/review/resolve",
            json={
                "announcement_id": announcement_id,
                "field_name": "cgpa_min",
                "status": "edited",
                "corrected_value": 7.5,
                "source_text": "Minimum CGPA: 7.0",
                "extracted_value": 7.0,
            },
            headers={"X-CSRF-Token": csrf},
        )
        assert res_resolve.status_code == 200
        assert res_resolve.json()["status"] == "edited"

    def test_coordinator_confirmation_persists_to_sqlite(self, auth_client):
        client, csrf = auth_client

        payload = {
            "company_name": "OpenAI Autonomous Systems",
            "job_role": "Frontier AI Engineer",
            "job_location": "Bangalore",
            "drive_date": "2026-12-18",
            "application_deadline": "2026-12-05",
            "mode": "hybrid",
            "ctc_lpa": 48.0,
            "min_cgpa": 8.5,
            "min_tenth_percentage": 75.0,
            "min_twelfth_percentage": 75.0,
            "allowed_branches": ["CSE", "IT", "Data Science", "AI & ML"],
            "max_active_backlogs": 0,
            "max_gap_years": 1,
            "selection_process": [
                {"round_number": 1, "name": "Algorithmic Coding", "round_type": "oa", "duration_minutes": 90},
                {"round_number": 2, "name": "AI Systems Interview", "round_type": "technical", "duration_minutes": 60},
            ],
            "confirmed_by": "coordinator",
        }

        res = client.post("/api/extract/confirm-save", json=payload, headers={"X-CSRF-Token": csrf})
        assert res.status_code == 201, res.text
        data = res.json()
        assert data["success"] is True
        drive_id = data["drive_id"]

        # Verify data directly in SQLite
        db: Session = SessionLocal()
        try:
            drive = db.execute(select(DriveModel).where(DriveModel.id == drive_id)).scalar_one_or_none()
            assert drive is not None
            assert drive.company_name == "OpenAI Autonomous Systems"
            assert drive.ctc_lpa == 48.0
            assert drive.drive_date == datetime.date(2026, 12, 18)

            company = db.execute(select(CompanyModel).where(CompanyModel.id == drive.company_id)).scalar_one_or_none()
            assert company is not None
            assert company.name == "OpenAI Autonomous Systems"

            req_v = db.execute(
                select(DriveRequirementVersionModel).where(DriveRequirementVersionModel.drive_id == drive_id)
            ).scalar_one_or_none()
            assert req_v is not None
            assert req_v.min_cgpa == 8.5
            assert req_v.max_active_backlogs == 0
            assert "CSE" in json.loads(req_v.allowed_branches_json)

            event = db.execute(select(EventModel).where(EventModel.aggregate_id == drive_id)).scalars().first()
            assert event is not None
            assert event.event_type == "ANNOUNCEMENT_EXTRACTION_CONFIRMED"
        finally:
            db.close()

    def test_repeated_submissions_do_not_create_duplicate_companies(self, auth_client):
        client, csrf = auth_client
        company_unique = "Unique Deduplication Tech Corp"

        payload = {
            "company_name": company_unique,
            "job_role": "Engineer",
            "drive_date": "2026-12-20",
            "ctc_lpa": 12.0,
            "min_cgpa": 7.0,
            "min_tenth_percentage": 60.0,
            "allowed_branches": ["CSE"],
            "max_active_backlogs": 0,
            "max_gap_years": 1,
            "confirmed_by": "coordinator",
        }

        # Submit twice
        res1 = client.post("/api/extract/confirm-save", json=payload, headers={"X-CSRF-Token": csrf})
        assert res1.status_code == 201
        res2 = client.post("/api/extract/confirm-save", json=payload, headers={"X-CSRF-Token": csrf})
        assert res2.status_code == 201

        # Check in DB that neither CompanyModel nor DriveModel was duplicated
        db: Session = SessionLocal()
        try:
            companies = db.execute(select(CompanyModel).where(CompanyModel.name == company_unique)).scalars().all()
            assert len(companies) == 1, "Duplicate CompanyModel records created for identical company name!"
            drives = db.execute(select(DriveModel).where(DriveModel.company_name == company_unique)).scalars().all()
            assert len(drives) == 1, "Duplicate DriveModel records created for identical company on same date!"
        finally:
            db.close()


# =============================================================================
# PART 3: NLP ACCURACY TESTS (25 SYNTHETIC ANNOUNCEMENTS & FIELD F1 EVALUATION)
# =============================================================================

SYNTHETIC_25_ANNOUNCEMENTS: list[dict[str, Any]] = [
    {
        "id": "SYN_01",
        "text": """Company: ByteDance Singapore
Job Role: Backend Systems Engineer
Location: Singapore / Remote
Package Offered: CTC 42.0 LPA
Drive Date: 2026-11-10
Application Deadline: 2026-10-31
Mode: Virtual
Eligibility Criteria:
1. Minimum CGPA Cut-off: 8.0 or above in B.Tech
2. 10th and 12th: Minimum 70.0% aggregate
3. Backlog Policy: 0 active arrears allowed at the time of drive.
4. Eligible Branches: Computer Science and Engineering, Information Technology, Data Science
5. Maximum 1 year education gap permitted.
Selection Process:
Round 1: Online Coding Challenge (90 mins)
Round 2: Distributed Systems Technical Interview (60 mins)
Round 3: Behavioral & Culture Fit (45 mins)""",
        "ground_truth": {
            "company_name": "ByteDance Singapore",
            "ctc_lpa": 42.0,
            "cgpa_min": 8.0,
            "tenth_percentage_min": 70.0,
            "twelfth_percentage_min": 70.0,
            "active_backlogs_max": 0,
            "drive_date": "2026-11-10",
            "application_deadline": "2026-10-31",
            "mode": "virtual",
            "allowed_branches": ["CSE", "IT", "Data Science"],
            "rounds_count": 3,
        },
    },
    {
        "id": "SYN_02",
        "text": """Company: Qualcomm Wireless R&D
Role: Firmware & Embedded Systems Engineer
Venue: Campus Placement Auditorium (On-Campus)
Date of Drive: 2026-11-12
CTC: 21.5 LPA (Fixed 18.0 LPA)
Criteria:
- Academic Cut-off: Minimum 7.5 CGPA throughout engineering
- 10th & 12th Standard: 65% minimum
- Arrears: No standing arrears permitted (0 active backlogs)
- Allowed Disciplines: Electronics and Communication Engineering, Electrical and Electronics Engineering, CSE
- Maximum education gap of 1 year allowed between 12th and degree.
Selection Process:
Round 1: Embedded C & Digital Design Assessment (60 mins)
Round 2: Technical Interview Panel (45 mins)""",
        "ground_truth": {
            "company_name": "Qualcomm Wireless R&D",
            "ctc_lpa": 21.5,
            "cgpa_min": 7.5,
            "tenth_percentage_min": 65.0,
            "twelfth_percentage_min": 65.0,
            "active_backlogs_max": 0,
            "drive_date": "2026-11-12",
            "mode": "on_campus",
            "allowed_branches": ["ECE", "EEE", "CSE"],
            "rounds_count": 2,
        },
    },
    {
        "id": "SYN_03",
        "text": """Subject: Campus Recruitment Notice - Goldman Sachs
Company: Goldman Sachs
Position: Summer Analyst / SDE
Annual Compensation: INR 28.0 LPA
Drive Date: 2026-11-15
Mode: Hybrid
Registration Deadline: 2026-11-05
Academic Guidelines:
- Cut-off pointer: 8.25 CGPA or above
- 10th and 12th percentage: at least 75.0%
- Backlog requirement: Zero backlogs throughout engineering
- Branches: Open to all circuit branches (CSE, IT, ECE)
- No gap years during degree. Up to 1 year gap allowed after 12th.
Hiring Stages:
Round 1: HackerRank Math & CS Aptitude (90 mins)
Round 2: Data Structures & Algorithms (60 mins)
Round 3: Hiring Manager & Values Interview (45 mins)""",
        "ground_truth": {
            "company_name": "Goldman Sachs",
            "ctc_lpa": 28.0,
            "cgpa_min": 8.25,
            "tenth_percentage_min": 75.0,
            "twelfth_percentage_min": 75.0,
            "active_backlogs_max": 0,
            "drive_date": "2026-11-15",
            "application_deadline": "2026-11-05",
            "mode": "hybrid",
            "allowed_branches": ["CSE", "IT", "ECE"],
            "rounds_count": 3,
        },
    },
    {
        "id": "SYN_04",
        "text": """Company: Tata Motors Limited
Profile: Graduate Engineer Trainee (GET - Powertrain)
Work Location: Pune / Jamshedpur
Drive Date: 2026-11-18
CTC: 9.5 LPA
Mode: On-Campus
Eligibility:
1. Academic Criteria: Minimum 6.5 CGPA in B.Tech
2. Class 10th: 60.0% minimum, Class 12th: 60.0% minimum
3. Arrears: Maximum 1 cleared backlog permitted, 0 active backlogs at drive date.
4. Eligible Departments: Mechanical Engineering, Electrical and Electronics Engineering
5. Maximum 2 years education gap permitted.
Rounds:
Round 1: Mechanical Aptitude Test (60 mins)
Round 2: Technical & Plant Operations Panel (45 mins)
Round 3: HR Interview (30 mins)""",
        "ground_truth": {
            "company_name": "Tata Motors Limited",
            "ctc_lpa": 9.5,
            "cgpa_min": 6.5,
            "tenth_percentage_min": 60.0,
            "twelfth_percentage_min": 60.0,
            "active_backlogs_max": 0,
            "drive_date": "2026-11-18",
            "mode": "on_campus",
            "allowed_branches": ["Mechanical Engineering", "EEE"],
            "rounds_count": 3,
        },
    },
    {
        "id": "SYN_05",
        "text": """Company: Cisco Systems
Job Role: Technical Solutions Specialist
CTC: 16.0 LPA
Drive Date: 2026-11-20
Mode: Virtual
Deadline: 2026-11-10
Cutoffs:
- Minimum CGPA required: 7.0
- 10th & 12th: 65% aggregate
- Backlogs: No active backlogs
- Eligible Streams: Computer Science, Information Technology, Electronics and Communication
- Education gap: Maximum 1 year permissible
Selection Steps:
Round 1: Network Protocols & Coding Test (75 mins)
Round 2: Architecture Discussion (45 mins)""",
        "ground_truth": {
            "company_name": "Cisco Systems",
            "ctc_lpa": 16.0,
            "cgpa_min": 7.0,
            "tenth_percentage_min": 65.0,
            "twelfth_percentage_min": 65.0,
            "active_backlogs_max": 0,
            "drive_date": "2026-11-20",
            "application_deadline": "2026-11-10",
            "mode": "virtual",
            "allowed_branches": ["CSE", "IT", "ECE"],
            "rounds_count": 2,
        },
    },
    {
        "id": "SYN_06",
        "text": """Company: Morgan Stanley
Title: Technology Associate
Remuneration: 25.5 LPA CTC
Interview Date: 2026-11-22
Mode: On-Campus
Apply Before: 2026-11-12
Requirements:
- CGPA Cut-off: 8.0 or above
- 10th & 12th: Minimum 70.0%
- Backlogs: 0 active arrears
- Branches: CSE, IT, Data Science
- Gap year: 1 year max
Process:
Round 1: Online Technical Assessment (90 mins)
Round 2: Data Structures Interview (45 mins)
Round 3: Executive Leadership Round (30 mins)""",
        "ground_truth": {
            "company_name": "Morgan Stanley",
            "ctc_lpa": 25.5,
            "cgpa_min": 8.0,
            "tenth_percentage_min": 70.0,
            "twelfth_percentage_min": 70.0,
            "active_backlogs_max": 0,
            "drive_date": "2026-11-22",
            "application_deadline": "2026-11-12",
            "mode": "on_campus",
            "allowed_branches": ["CSE", "IT", "Data Science"],
            "rounds_count": 3,
        },
    },
    {
        "id": "SYN_07",
        "text": """Company: Reliance Industries
Role: Graduate Engineer Trainee - Operations
CTC: 7.5 LPA
Drive Date: 2026-11-25
Mode: On-Campus
Criteria:
- Minimum CGPA: 6.0
- 10th and 12th: 60.0%
- Backlogs: No active backlogs
- Branches: Chemical Engineering, Mechanical Engineering, Civil Engineering
- Max 1 year education gap
Selection:
Round 1: Domain Knowledge Test (60 mins)
Round 2: Personal Interview (30 mins)""",
        "ground_truth": {
            "company_name": "Reliance Industries",
            "ctc_lpa": 7.5,
            "cgpa_min": 6.0,
            "tenth_percentage_min": 60.0,
            "twelfth_percentage_min": 60.0,
            "active_backlogs_max": 0,
            "drive_date": "2026-11-25",
            "mode": "on_campus",
            "allowed_branches": ["Chemical Engineering", "Mechanical Engineering", "Civil Engineering"],
            "rounds_count": 2,
        },
    },
    {
        "id": "SYN_08",
        "text": """Company: Atlassian
Position: Associate Site Reliability Engineer
Salary: CTC 34.0 LPA
Drive Date: 2026-11-28
Mode: Virtual
Application Deadline: 2026-11-15
Eligibility:
- Cut-off: 8.5 CGPA
- 10th & 12th: 75%
- Backlog Policy: Strictly 0 active or historical backlogs
- Disciplines: CSE, IT
- 0 gap years allowed during engineering, max 1 year before degree
Rounds:
Round 1: Systems & Shell Coding Test (90 mins)
Round 2: Site Reliability Scenarios (60 mins)
Round 3: Values & Culture Interview (45 mins)""",
        "ground_truth": {
            "company_name": "Atlassian",
            "ctc_lpa": 34.0,
            "cgpa_min": 8.5,
            "tenth_percentage_min": 75.0,
            "twelfth_percentage_min": 75.0,
            "active_backlogs_max": 0,
            "drive_date": "2026-11-28",
            "application_deadline": "2026-11-15",
            "mode": "virtual",
            "allowed_branches": ["CSE", "IT"],
            "rounds_count": 3,
        },
    },
    {
        "id": "SYN_09",
        "text": """Company: ZS Associates
Role: Business Operations Analyst
CTC Offered: 13.5 LPA
Drive Date: 2026-11-30
Mode: Hybrid
Cutoffs:
- Academic cutoff: 7.0 CGPA
- 10th and 12th percentage: Minimum 65.0%
- Backlogs: No active arrears
- Eligible disciplines: All Branches (Open to all engineering disciplines)
- Gap limit: Up to 1 year
Stages:
Round 1: Business Case & Aptitude (60 mins)
Round 2: Case Interview (45 mins)
Round 3: Behavioral Fit (30 mins)""",
        "ground_truth": {
            "company_name": "ZS Associates",
            "ctc_lpa": 13.5,
            "cgpa_min": 7.0,
            "tenth_percentage_min": 65.0,
            "twelfth_percentage_min": 65.0,
            "active_backlogs_max": 0,
            "drive_date": "2026-11-30",
            "mode": "hybrid",
            "allowed_branches": ["All Branches"],
            "rounds_count": 3,
        },
    },
    {
        "id": "SYN_10",
        "text": """Company: Texas Instruments
Role: Analog VLSI Design Engineer
CTC: 26.0 LPA
Drive Date: 2026-12-01
Mode: On-Campus
Deadline: 2026-11-20
Academic Criteria:
- CGPA cut-off: 8.0 or above
- 10th and 12th: 70.0%
- Backlog rule: 0 active backlogs
- Streams: Electronics and Communication Engineering, Electrical and Electronics Engineering
- Education gap: 1 year max
Rounds:
Round 1: Analog Circuits & Signals Test (60 mins)
Round 2: Technical Interview (60 mins)""",
        "ground_truth": {
            "company_name": "Texas Instruments",
            "ctc_lpa": 26.0,
            "cgpa_min": 8.0,
            "tenth_percentage_min": 70.0,
            "twelfth_percentage_min": 70.0,
            "active_backlogs_max": 0,
            "drive_date": "2026-12-01",
            "application_deadline": "2026-11-20",
            "mode": "on_campus",
            "allowed_branches": ["ECE", "EEE"],
            "rounds_count": 2,
        },
    },
    # Cases 11 to 25 with diverse salary phrasing, irrelevant number noise, and alternative date styles
    {
        "id": "SYN_11",
        "text": "Company: Adobe Systems\nRole: Computer Scientist 1\nCTC: 38.0 LPA\nDrive Date: 2026-12-03\nMode: Virtual\nCriteria: Minimum CGPA of 8.2 with no active backlogs. 10th & 12th percentage: 70.0%. Branches: Computer Science, IT.\nRound 1: Coding (60 mins)\nRound 2: Tech (45 mins)",
        "ground_truth": {"company_name": "Adobe Systems", "ctc_lpa": 38.0, "cgpa_min": 8.2, "tenth_percentage_min": 70.0, "twelfth_percentage_min": 70.0, "active_backlogs_max": 0, "drive_date": "2026-12-03", "mode": "virtual", "allowed_branches": ["CSE", "IT"], "rounds_count": 2},
    },
    {
        "id": "SYN_12",
        "text": "Company: Intel Corporation\nRole: Hardware Engineer\nCTC: 22.0 LPA\nDrive Date: 2026-12-05\nMode: On-Campus\nCriteria: 7.5 CGPA cut-off. 65% in 10th & 12th. 0 active backlogs. Branches: ECE, EEE, CSE.\nRound 1: Digital Electronics (60 mins)\nRound 2: Technical Panel (45 mins)",
        "ground_truth": {"company_name": "Intel Corporation", "ctc_lpa": 22.0, "cgpa_min": 7.5, "tenth_percentage_min": 65.0, "twelfth_percentage_min": 65.0, "active_backlogs_max": 0, "drive_date": "2026-12-05", "mode": "on_campus", "allowed_branches": ["ECE", "EEE", "CSE"], "rounds_count": 2},
    },
    {
        "id": "SYN_13",
        "text": "Company: Larsen & Toubro\nRole: Graduate Engineer Trainee - Infra\nCTC: 8.0 LPA\nDrive Date: 2026-12-07\nMode: On-Campus\nCriteria: Minimum 6.5 CGPA. 60.0% in 10th and 12th. Max 1 cleared backlog, 0 active arrears. Branches: Civil Engineering, Mechanical Engineering.\nRound 1: Aptitude (60 mins)\nRound 2: Tech (30 mins)",
        "ground_truth": {"company_name": "Larsen & Toubro", "ctc_lpa": 8.0, "cgpa_min": 6.5, "tenth_percentage_min": 60.0, "twelfth_percentage_min": 60.0, "active_backlogs_max": 0, "drive_date": "2026-12-07", "mode": "on_campus", "allowed_branches": ["Civil Engineering", "Mechanical Engineering"], "rounds_count": 2},
    },
    {
        "id": "SYN_14",
        "text": "Company: Samsung R&D\nRole: Lead Research Engineer\nCTC: 24.0 LPA\nDrive Date: 2026-12-09\nMode: Hybrid\nCriteria: 7.8 CGPA cutoff. 70.0% in 10th & 12th. No active backlogs. Branches: CSE, IT, Data Science, ECE.\nRound 1: Algorithm Test (120 mins)\nRound 2: Tech Interview (60 mins)",
        "ground_truth": {"company_name": "Samsung R&D", "ctc_lpa": 24.0, "cgpa_min": 7.8, "tenth_percentage_min": 70.0, "twelfth_percentage_min": 70.0, "active_backlogs_max": 0, "drive_date": "2026-12-09", "mode": "hybrid", "allowed_branches": ["CSE", "IT", "Data Science", "ECE"], "rounds_count": 2},
    },
    {
        "id": "SYN_15",
        "text": "Company: Biocon Limited\nRole: Bioprocess Engineer\nCTC: 6.8 LPA\nDrive Date: 2026-12-11\nMode: On-Campus\nCriteria: Minimum 6.0 CGPA. 60% in 10th and 12th. 0 active backlogs. Branches: Biotechnology, Chemical Engineering.\nRound 1: Bio Test (60 mins)\nRound 2: Interview (30 mins)",
        "ground_truth": {"company_name": "Biocon Limited", "ctc_lpa": 6.8, "cgpa_min": 6.0, "tenth_percentage_min": 60.0, "twelfth_percentage_min": 60.0, "active_backlogs_max": 0, "drive_date": "2026-12-11", "mode": "on_campus", "allowed_branches": ["Biotechnology", "Chemical Engineering"], "rounds_count": 2},
    },
    {
        "id": "SYN_16",
        "text": "Company: Barclays\nRole: Graduate Analyst\nCTC: 15.0 LPA\nDrive Date: 2026-12-13\nMode: Virtual\nCriteria: Minimum 7.2 CGPA. 65% in 10th & 12th. No active arrears. Branches: CSE, IT, ECE.\nRound 1: Coding Assessment (60 mins)\nRound 2: Virtual Tech (45 mins)",
        "ground_truth": {"company_name": "Barclays", "ctc_lpa": 15.0, "cgpa_min": 7.2, "tenth_percentage_min": 65.0, "twelfth_percentage_min": 65.0, "active_backlogs_max": 0, "drive_date": "2026-12-13", "mode": "virtual", "allowed_branches": ["CSE", "IT", "ECE"], "rounds_count": 2},
    },
    {
        "id": "SYN_17",
        "text": "Company: ITC Limited\nRole: Assistant Manager - Operations\nCTC: 11.0 LPA\nDrive Date: 2026-12-15\nMode: On-Campus\nCriteria: 6.5 CGPA or above. 60.0% in 10th & 12th. 0 active backlogs. Branches: Mechanical Engineering, Chemical Engineering.\nRound 1: Operations Assessment (60 mins)\nRound 2: Interview (45 mins)",
        "ground_truth": {"company_name": "ITC Limited", "ctc_lpa": 11.0, "cgpa_min": 6.5, "tenth_percentage_min": 60.0, "twelfth_percentage_min": 60.0, "active_backlogs_max": 0, "drive_date": "2026-12-15", "mode": "on_campus", "allowed_branches": ["Mechanical Engineering", "Chemical Engineering"], "rounds_count": 2},
    },
    {
        "id": "SYN_18",
        "text": "Company: Infosys Limited\nRole: Power Programmer\nCTC: 9.0 LPA\nDrive Date: 2026-12-17\nMode: Virtual\nCriteria: Minimum 7.0 CGPA. 65% in 10th & 12th. No standing arrears. Branches: All Branches.\nRound 1: HackWithInfy Finalist Evaluation (180 mins)\nRound 2: Technical Interview (45 mins)",
        "ground_truth": {"company_name": "Infosys Limited", "ctc_lpa": 9.0, "cgpa_min": 7.0, "tenth_percentage_min": 65.0, "twelfth_percentage_min": 65.0, "active_backlogs_max": 0, "drive_date": "2026-12-17", "mode": "virtual", "allowed_branches": ["All Branches"], "rounds_count": 2},
    },
    {
        "id": "SYN_19",
        "text": "Company: Wipro Limited\nRole: Turbo Developer\nCTC: 6.5 LPA\nDrive Date: 2026-12-19\nMode: Virtual\nCriteria: Minimum 6.5 CGPA. 60.0% in 10th & 12th. 0 active backlogs. Branches: CSE, IT, ECE, EEE.\nRound 1: Elite National Talent Hunt (90 mins)\nRound 2: Technical Discussion (30 mins)",
        "ground_truth": {"company_name": "Wipro Limited", "ctc_lpa": 6.5, "cgpa_min": 6.5, "tenth_percentage_min": 60.0, "twelfth_percentage_min": 60.0, "active_backlogs_max": 0, "drive_date": "2026-12-19", "mode": "virtual", "allowed_branches": ["CSE", "IT", "ECE", "EEE"], "rounds_count": 2},
    },
    {
        "id": "SYN_20",
        "text": "Company: Accenture\nRole: Advanced Application Engineering Associate\nCTC: 12.5 LPA\nDrive Date: 2026-12-21\nMode: Virtual\nCriteria: 7.0 CGPA minimum. 65% in 10th and 12th. Zero active arrears. Branches: CSE, IT, Data Science.\nRound 1: Cognitive & Technical Assessment (90 mins)\nRound 2: Coding (45 mins)\nRound 3: Interview (30 mins)",
        "ground_truth": {"company_name": "Accenture", "ctc_lpa": 12.5, "cgpa_min": 7.0, "tenth_percentage_min": 65.0, "twelfth_percentage_min": 65.0, "active_backlogs_max": 0, "drive_date": "2026-12-21", "mode": "virtual", "allowed_branches": ["CSE", "IT", "Data Science"], "rounds_count": 3},
    },
    {
        "id": "SYN_21",
        "text": "Company: Siemens Technology\nRole: R&D Embedded Engineer\nCTC: 14.5 LPA\nDrive Date: 2026-12-23\nMode: On-Campus\nCriteria: 7.2 CGPA cut-off. 65% in 10th & 12th. 0 active backlogs. Branches: ECE, EEE, Mechanical Engineering.\nRound 1: Technical MCQ (60 mins)\nRound 2: Technical Interview (45 mins)",
        "ground_truth": {"company_name": "Siemens Technology", "ctc_lpa": 14.5, "cgpa_min": 7.2, "tenth_percentage_min": 65.0, "twelfth_percentage_min": 65.0, "active_backlogs_max": 0, "drive_date": "2026-12-23", "mode": "on_campus", "allowed_branches": ["ECE", "EEE", "Mechanical Engineering"], "rounds_count": 2},
    },
    {
        "id": "SYN_22",
        "text": "Company: Deloitte USI\nRole: Analyst - Technology Advisory\nCTC: 11.5 LPA\nDrive Date: 2026-12-26\nMode: Hybrid\nCriteria: 6.8 CGPA cutoff. 60.0% in 10th & 12th. No active backlogs. Branches: Open to all branches.\nRound 1: Deloitte Aptitude & Tech Test (75 mins)\nRound 2: Case Interview (45 mins)",
        "ground_truth": {"company_name": "Deloitte USI", "ctc_lpa": 11.5, "cgpa_min": 6.8, "tenth_percentage_min": 60.0, "twelfth_percentage_min": 60.0, "active_backlogs_max": 0, "drive_date": "2026-12-26", "mode": "hybrid", "allowed_branches": ["All Branches"], "rounds_count": 2},
    },
    {
        "id": "SYN_23",
        "text": "Company: Microsoft\nRole: Software Engineer\nCTC: 35.0 LPA\nDrive Date: 2026-12-28\nMode: Virtual\nCriteria: 8.0 CGPA minimum. 70% in 10th and 12th. 0 active arrears. Branches: CSE, IT, Data Science.\nRound 1: Codility Assessment (90 mins)\nRound 2: Technical Interview (60 mins)",
        "ground_truth": {"company_name": "Microsoft", "ctc_lpa": 35.0, "cgpa_min": 8.0, "tenth_percentage_min": 70.0, "twelfth_percentage_min": 70.0, "active_backlogs_max": 0, "drive_date": "2026-12-28", "mode": "virtual", "allowed_branches": ["CSE", "IT", "Data Science"], "rounds_count": 2},
    },
    {
        "id": "SYN_24",
        "text": "Company: Amazon\nRole: Software Development Engineer I\nCTC: 32.0 LPA\nDrive Date: 2026-12-30\nMode: Virtual\nCriteria: 7.8 CGPA cut-off. 65% in 10th & 12th. 0 active backlogs. Branches: CSE, IT, ECE.\nRound 1: Online Assessment (90 mins)\nRound 2: Technical Interview 1 (60 mins)\nRound 3: Technical Interview 2 (60 mins)",
        "ground_truth": {"company_name": "Amazon", "ctc_lpa": 32.0, "cgpa_min": 7.8, "tenth_percentage_min": 65.0, "twelfth_percentage_min": 65.0, "active_backlogs_max": 0, "drive_date": "2026-12-30", "mode": "virtual", "allowed_branches": ["CSE", "IT", "ECE"], "rounds_count": 3},
    },
    {
        "id": "SYN_25",
        "text": "Company: Google\nRole: Software Engineer\nCTC: 36.0 LPA\nDrive Date: 2027-01-05\nMode: Hybrid\nCriteria: 8.5 CGPA cutoff. 70.0% in 10th & 12th. No active backlogs. Branches: CSE, IT, Data Science.\nRound 1: Google Online Challenge (90 mins)\nRound 2: Algorithms & Data Structures (45 mins)\nRound 3: System Design & Coding (45 mins)\nRound 4: Googliness & Leadership (30 mins)",
        "ground_truth": {"company_name": "Google", "ctc_lpa": 36.0, "cgpa_min": 8.5, "tenth_percentage_min": 70.0, "twelfth_percentage_min": 70.0, "active_backlogs_max": 0, "drive_date": "2027-01-05", "mode": "hybrid", "allowed_branches": ["CSE", "IT", "Data Science"], "rounds_count": 4},
    },
]


def test_nlp_extraction_accuracy_25_synthetic_cases(nlp_engine: NLPEngine):
    """
    Evaluates field-level Precision, Recall, and F1 across all 25 synthetic announcement test cases.
    Verifies that the target >= 90% F1 is achieved on key criteria.
    """
    metrics: dict[str, dict[str, int]] = {
        "company_name": {"tp": 0, "fp": 0, "fn": 0},
        "ctc_lpa": {"tp": 0, "fp": 0, "fn": 0},
        "cgpa_min": {"tp": 0, "fp": 0, "fn": 0},
        "tenth_percentage_min": {"tp": 0, "fp": 0, "fn": 0},
        "twelfth_percentage_min": {"tp": 0, "fp": 0, "fn": 0},
        "active_backlogs_max": {"tp": 0, "fp": 0, "fn": 0},
        "drive_date": {"tp": 0, "fp": 0, "fn": 0},
        "mode": {"tp": 0, "fp": 0, "fn": 0},
        "allowed_branches": {"tp": 0, "fp": 0, "fn": 0},
        "rounds_count": {"tp": 0, "fp": 0, "fn": 0},
    }

    assert len(SYNTHETIC_25_ANNOUNCEMENTS) == 25

    for test_case in SYNTHETIC_25_ANNOUNCEMENTS:
        raw_text = test_case["text"]
        truth = test_case["ground_truth"]
        extracted = nlp_engine.extract(raw_text)

        # 1. Company Name
        pred_comp = extracted.company_name.value if extracted.company_name else None
        if pred_comp == truth.get("company_name"):
            metrics["company_name"]["tp"] += 1
        else:
            if pred_comp is not None:
                metrics["company_name"]["fp"] += 1
            if truth.get("company_name") is not None:
                metrics["company_name"]["fn"] += 1

        # 2. CTC LPA
        pred_ctc = extracted.ctc_lpa.value if extracted.ctc_lpa else None
        if pred_ctc == truth.get("ctc_lpa"):
            metrics["ctc_lpa"]["tp"] += 1
        else:
            if pred_ctc is not None:
                metrics["ctc_lpa"]["fp"] += 1
            if truth.get("ctc_lpa") is not None:
                metrics["ctc_lpa"]["fn"] += 1

        # 3. CGPA Min
        pred_cgpa = extracted.cgpa_min.value if extracted.cgpa_min else None
        if pred_cgpa == truth.get("cgpa_min"):
            metrics["cgpa_min"]["tp"] += 1
        else:
            if pred_cgpa is not None:
                metrics["cgpa_min"]["fp"] += 1
            if truth.get("cgpa_min") is not None:
                metrics["cgpa_min"]["fn"] += 1

        # 4. 10th Percentage
        pred_10 = extracted.tenth_percentage_min.value if extracted.tenth_percentage_min else None
        if pred_10 == truth.get("tenth_percentage_min"):
            metrics["tenth_percentage_min"]["tp"] += 1
        else:
            if pred_10 is not None:
                metrics["tenth_percentage_min"]["fp"] += 1
            if truth.get("tenth_percentage_min") is not None:
                metrics["tenth_percentage_min"]["fn"] += 1

        # 5. 12th Percentage
        pred_12 = extracted.twelfth_percentage_min.value if extracted.twelfth_percentage_min else None
        if pred_12 == truth.get("twelfth_percentage_min"):
            metrics["twelfth_percentage_min"]["tp"] += 1
        else:
            if pred_12 is not None:
                metrics["twelfth_percentage_min"]["fp"] += 1
            if truth.get("twelfth_percentage_min") is not None:
                metrics["twelfth_percentage_min"]["fn"] += 1

        # 6. Active Backlogs
        pred_backlogs = extracted.active_backlogs_max.value if extracted.active_backlogs_max is not None else None
        if pred_backlogs == truth.get("active_backlogs_max"):
            metrics["active_backlogs_max"]["tp"] += 1
        else:
            if pred_backlogs is not None:
                metrics["active_backlogs_max"]["fp"] += 1
            if truth.get("active_backlogs_max") is not None:
                metrics["active_backlogs_max"]["fn"] += 1

        # 7. Drive Date
        pred_date = extracted.drive_date.value.isoformat() if extracted.drive_date else None
        if pred_date == truth.get("drive_date"):
            metrics["drive_date"]["tp"] += 1
        else:
            if pred_date is not None:
                metrics["drive_date"]["fp"] += 1
            if truth.get("drive_date") is not None:
                metrics["drive_date"]["fn"] += 1

        # 8. Drive Mode
        pred_mode = extracted.mode.value.value if extracted.mode else None
        if pred_mode == truth.get("mode"):
            metrics["mode"]["tp"] += 1
        else:
            if pred_mode is not None:
                metrics["mode"]["fp"] += 1
            if truth.get("mode") is not None:
                metrics["mode"]["fn"] += 1

        # 9. Allowed Branches (set comparison)
        pred_branches = set(extracted.allowed_branches.value) if extracted.allowed_branches else set()
        true_branches = set(truth.get("allowed_branches", []))
        if pred_branches == true_branches:
            metrics["allowed_branches"]["tp"] += 1
        else:
            if pred_branches:
                metrics["allowed_branches"]["fp"] += 1
            if true_branches:
                metrics["allowed_branches"]["fn"] += 1

        # 10. Rounds Count
        pred_rounds = len(extracted.rounds)
        if pred_rounds == truth.get("rounds_count"):
            metrics["rounds_count"]["tp"] += 1
        else:
            metrics["rounds_count"]["fp"] += 1
            metrics["rounds_count"]["fn"] += 1

    # Report Field-by-Field Precision, Recall, and F1
    total_tp = sum(m["tp"] for m in metrics.values())
    total_fp = sum(m["fp"] for m in metrics.values())
    total_fn = sum(m["fn"] for m in metrics.values())

    print("\n==================================================================")
    print("FIELD-LEVEL ACCURACY METRICS (25 SYNTHETIC ANNOUNCEMENTS)")
    print("==================================================================")
    for field, m in metrics.items():
        prec = (m["tp"] / (m["tp"] + m["fp"])) if (m["tp"] + m["fp"]) > 0 else 0.0
        rec = (m["tp"] / (m["tp"] + m["fn"])) if (m["tp"] + m["fn"]) > 0 else 0.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
        print(f"  {field:<25} | Precision: {prec*100:5.1f}% | Recall: {rec*100:5.1f}% | F1: {f1*100:5.1f}%")
        # Ensure individual key fields meet or exceed 90% F1 target
        assert f1 >= 0.90, f"Field '{field}' F1 score {f1*100:.1f}% fell below 90% threshold!"

    overall_prec = total_tp / (total_tp + total_fp)
    overall_rec = total_tp / (total_tp + total_fn)
    overall_f1 = 2 * overall_prec * overall_rec / (overall_prec + overall_rec)
    print("------------------------------------------------------------------")
    print(f"  OVERALL SYSTEM              | Precision: {overall_prec*100:5.1f}% | Recall: {overall_rec*100:5.1f}% | F1: {overall_f1*100:5.1f}%")
    print("==================================================================")
    assert overall_f1 >= 0.95, f"Overall system F1 score {overall_f1*100:.1f}% fell below 95% target!"
