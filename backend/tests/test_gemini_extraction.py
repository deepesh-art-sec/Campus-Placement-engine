import datetime
from unittest.mock import MagicMock

import pytest

from backend.app.domain.models import DriveMode, RoundType
from backend.app.extract.deterministic_extractor import DeterministicExtractor
from backend.app.extract.llm_adapter import GeminiExtractor, HybridExtractionEngine, MockLlmExtractor
from backend.app.extract.models import ExtractedRequirements


def test_gemini_extractor_is_configured_and_enabled():
    extractor = GeminiExtractor()
    assert extractor.is_enabled() is True
    assert extractor.model == "gemini-3.5-flash-lite"


def test_circuit_breaker_guarantees_zero_failures_on_error():
    """
    Ensures that if the LLM extractor raises any exception (network down, rate limit, timeout),
    HybridExtractionEngine catches it and safely returns the deterministic output with zero crashes.
    """
    failing_llm = MagicMock()
    failing_llm.is_enabled.return_value = True
    failing_llm.extract.side_effect = TimeoutError("Simulated LLM Gateway Timeout 504")

    engine = HybridExtractionEngine(
        deterministic_extractor=DeterministicExtractor(),
        llm_extractor=failing_llm,
    )

    text = "Company: Infosys\nRole: Systems Engineer\nPackage: 9.5 LPA\nCGPA: 7.0"
    result = engine.extract(text)

    # Must NOT raise exception! Must return valid ExtractedRequirements from deterministic baseline
    assert isinstance(result, ExtractedRequirements)
    assert result.company_name is not None
    assert "Infosys" in result.company_name.value
    assert result.ctc_lpa is not None
    assert result.ctc_lpa.value == 9.5


def test_gemini_live_extraction_accuracy():
    """
    Tests live Gemini API extraction on a multi-attribute announcement.
    """
    extractor = GeminiExtractor()
    sample = """
    CAMPUS PLACEMENT DRIVE 2026
    Company: Cisco Systems
    Role: Network Software Engineer
    Location: Bangalore
    Mode: On-Campus
    Drive Date: 2026-11-20
    Deadline: 2026-11-10
    Salary: 18.0 LPA with 40,000 monthly stipend for 6 months.
    Eligibility:
    - B.Tech in CSE, IT, or ECE with minimum 7.5 CGPA.
    - No active backlogs allowed. Max 1 historical backlog.
    - Maximum 1 year education gap.
    Selection Stages:
    1. Online Coding Round
    2. Technical Interview
    3. Managerial & HR Round
    """

    res = extractor.extract(sample)
    assert res.company_name is not None
    assert "Cisco" in res.company_name.value
    assert res.role is not None
    assert "Network" in res.role.value
    assert res.ctc_lpa is not None
    assert res.ctc_lpa.value == 18.0
    assert res.stipend_monthly is not None
    assert res.stipend_monthly.value == 40000.0
    assert res.cgpa_min is not None
    assert res.cgpa_min.value == 7.5
    assert res.active_backlogs_max is not None
    assert res.active_backlogs_max.value == 0
    assert res.allowed_branches is not None
    assert any("CSE" in b for b in res.allowed_branches.value)
    assert len(res.rounds) == 3
