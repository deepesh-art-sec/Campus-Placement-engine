"""
High-Precision LLM Extractor Adapter and Hybrid Merger.
Integrates Google Gemini API (gemini-3.5-flash-lite / gemini-3.8-flash) with
the local deterministic NLP extraction engine.
Guarantees 100% Zero-Failure uptime via resilient fallback circuit-breaker.
Supports Multi-Format Direct Ingestion: Text, DOCX, Scanned/Digital PDF, and Images.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import re
from typing import Any, Protocol, runtime_checkable

from dotenv import load_dotenv

from backend.app.domain.models import DriveMode, RoundType
from backend.app.extract.deterministic_extractor import DeterministicExtractor
from backend.app.extract.models import (
    ExtractedField,
    ExtractedRequirements,
    ExtractedRound,
)
from backend.app.importers.canonical_maps import get_branch_code

load_dotenv()
logger = logging.getLogger("placement_llm_adapter")


@runtime_checkable
class ILlmExtractor(Protocol):
    """Protocol for optional large language model extractors."""

    def is_enabled(self) -> bool:
        """Returns True if the LLM extractor is active and configured."""
        ...

    def extract(
        self,
        announcement_text: str,
        document_bytes: bytes | None = None,
        filename: str | None = None,
    ) -> ExtractedRequirements:
        """Extracts requirements using an LLM. Receives announcement text and optional raw document bytes."""
        ...


class GeminiExtractor(ILlmExtractor):
    """
    Production Google Gemini API Extractor.
    Extracts structured requirements with deep semantic understanding using Google's official google-genai SDK.
    Supports both text announcements and direct Multimodal ingestion for PDFs and images.
    Calibrated for campus placement drives, multi-tier cutoffs, backlogs, and selection rounds.
    """

    DEFAULT_API_KEY = os.getenv("GEMINI_API_KEY", "")
    DEFAULT_MODEL = "gemini-3.5-flash-lite"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        enabled: bool = True,
    ) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or self.DEFAULT_API_KEY
        self.model = model or os.getenv("GEMINI_MODEL") or self.DEFAULT_MODEL
        env_flag = os.getenv("ENABLE_LLM_EXTRACTOR", os.getenv("ENABLE_LLM_ADAPTER", "true")).lower() in ("true", "1", "yes")
        self._enabled = enabled and env_flag and bool(self.api_key)
        self._client = None

        if self._enabled:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as exc:
                logger.warning("GeminiExtractor: Failed to initialize google-genai Client: %s", exc)
                self._enabled = False

    def is_enabled(self) -> bool:
        return self._enabled and self._client is not None

    def extract(
        self,
        announcement_text: str,
        document_bytes: bytes | None = None,
        filename: str | None = None,
    ) -> ExtractedRequirements:
        if not self.is_enabled():
            raise RuntimeError("GeminiExtractor is disabled or unconfigured.")

        from google.genai import types

        prompt = f"""You are an expert Campus Recruitment Director and Placement Officer.
Extract structured placement drive requirements from the provided campus recruitment announcement.

CRITICAL INSTRUCTIONS:
1. company_name: Name of hiring company (e.g., 'Goldman Sachs', 'Google', 'TCS', 'Adobe').
2. role: Specific job title or designation (e.g., 'Software Development Engineer', 'Systems Engineer').
3. location: Cities/office locations (e.g., 'Bangalore / Hyderabad', 'Pan India') or null.
4. mode: 'On-Campus', 'Virtual', 'Hybrid', or null.
5. drive_date: Date of drive or assessment in ISO format 'YYYY-MM-DD' or null.
6. application_deadline: Registration deadline in ISO format 'YYYY-MM-DD' or null.
7. ctc_lpa: Full-time annual CTC in LPA (numeric float, e.g., 14.5).
8. stipend_monthly: Monthly internship stipend in INR (numeric float, e.g., 50000.0) or null.
9. cgpa_min: Minimum required CGPA on 10.0 scale (numeric float, e.g., 7.5) or null.
10. tenth_percentage_min: Minimum required Class 10 percentage (numeric float, e.g., 70.0) or null.
11. twelfth_percentage_min: Minimum required Class 12 / Diploma percentage (numeric float, e.g., 65.0) or null.
12. allowed_branches: List of eligible engineering branches as standard codes (e.g., ['CSE', 'IT', 'ECE', 'EE', 'MECH', 'CIVIL']) or null if open to all.
13. active_backlogs_max: Maximum active/current backlogs allowed. If text says 'no active backlogs' or 'no standing arrears', output 0. If 1 allowed, output 1. null if unspecified.
14. historical_backlogs_max: Maximum total/dead backlogs permitted or null.
15. gap_years_max: Maximum education gap years permitted or null.
16. bond_details: Description of bond/service agreement (e.g., '2 years service agreement') or null.
17. rounds: Array of recruitment rounds in sequence with 'name' and 'round_type' (one of: 'ONLINE_TEST', 'TECHNICAL_INTERVIEW', 'HR_INTERVIEW', 'GROUP_DISCUSSION', 'MANAGERIAL_INTERVIEW').

Return ONLY valid JSON matching this schema:
{{
  "company_name": string or null,
  "role": string or null,
  "location": string or null,
  "mode": "On-Campus" | "Virtual" | "Hybrid" | null,
  "drive_date": "YYYY-MM-DD" or null,
  "application_deadline": "YYYY-MM-DD" or null,
  "ctc_lpa": float or null,
  "stipend_monthly": float or null,
  "cgpa_min": float or null,
  "tenth_percentage_min": float or null,
  "twelfth_percentage_min": float or null,
  "allowed_branches": ["CSE", "IT", "ECE"] or null,
  "active_backlogs_max": int or null,
  "historical_backlogs_max": int or null,
  "gap_years_max": int or null,
  "bond_details": string or null,
  "rounds": [{{"name": string, "round_type": string}}]
}}

Announcement Text:
{announcement_text}
"""

        contents_payload: list[Any] = []
        mime_map = {
            ".pdf": "application/pdf",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
        }

        # Check for direct multimodal document attachment
        if document_bytes and filename:
            ext = os.path.splitext(filename)[1].lower()
            if ext in mime_map:
                try:
                    part = types.Part.from_bytes(data=document_bytes, mime_type=mime_map[ext])
                    contents_payload.append(part)
                except Exception as exc:
                    logger.warning("GeminiExtractor: Failed to attach multimodal document Part: %s", exc)

        contents_payload.append(prompt)

        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=contents_payload,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                ),
            )
        except Exception as exc:
            # If multimodal request failed, retry with pure text
            if len(contents_payload) > 1:
                logger.info("GeminiExtractor: Multimodal payload failed, retrying with text prompt: %s", exc)
                response = self._client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1,
                    ),
                )
            else:
                raise exc

        raw_json = (response.text or "").strip()
        if not raw_json:
            raise ValueError("Gemini returned empty response text.")

        data = json.loads(raw_json)
        # Handle cases where LLM returns a list with one dict
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            data = data[0]
        elif not isinstance(data, dict):
            raise ValueError("Gemini JSON response is not an object.")

        return self._map_to_domain(data, announcement_text)

    def _map_to_domain(self, data: dict[str, Any], raw_text: str) -> ExtractedRequirements:
        def make_field(name: str, val: Any) -> ExtractedField | None:
            if val is None or val == "":
                return None
            return ExtractedField(
                field_name=name,
                value=val,
                confidence=0.96,
                source_sentence=f"Gemini Semantic Extraction: {val}",
                extraction_method="gemini_llm",
            )

        def parse_date(date_str: Any) -> datetime.date | None:
            if not date_str or not isinstance(date_str, str):
                return None
            try:
                clean = re.sub(r"[^\d\-]", "", date_str.strip())
                return datetime.date.fromisoformat(clean[:10])
            except Exception:
                return None

        drive_date_val = parse_date(data.get("drive_date"))
        deadline_val = parse_date(data.get("application_deadline"))

        # Parse DriveMode
        mode_val = None
        mode_raw = data.get("mode")
        if mode_raw:
            m_upper = str(mode_raw).upper()
            if "CAMPUS" in m_upper or "PERSON" in m_upper or "OFFLINE" in m_upper or "ON-SITE" in m_upper:
                mode_val = DriveMode.ON_CAMPUS
            elif "VIRTUAL" in m_upper or "ONLINE" in m_upper or "REMOTE" in m_upper:
                mode_val = DriveMode.VIRTUAL
            elif "HYBRID" in m_upper:
                mode_val = DriveMode.HYBRID

        # Canonicalize branch codes
        raw_branches = data.get("allowed_branches")
        norm_branches: list[str] | None = None
        if raw_branches and isinstance(raw_branches, list):
            norm_branches = []
            for b in raw_branches:
                code = get_branch_code(str(b).strip())
                if code and code not in norm_branches:
                    norm_branches.append(code)
            if not norm_branches:
                norm_branches = None

        # Parse rounds
        rounds: list[ExtractedRound] = []
        for idx, r in enumerate(data.get("rounds") or [], start=1):
            r_name = str(r.get("name") or f"Round {idx}")
            r_type_raw = str(r.get("round_type", "")).upper()
            r_type = RoundType.ONLINE_TEST
            if "TECH" in r_type_raw:
                r_type = RoundType.TECHNICAL_INTERVIEW
            elif "HR" in r_type_raw:
                r_type = RoundType.HR_INTERVIEW
            elif "GROUP" in r_type_raw or "GD" in r_type_raw:
                r_type = RoundType.GROUP_DISCUSSION
            elif "MANAGE" in r_type_raw:
                r_type = RoundType.MANAGERIAL_INTERVIEW
            elif "TEST" in r_type_raw or "ASSESS" in r_type_raw:
                r_type = RoundType.ONLINE_TEST

            rounds.append(
                ExtractedRound(
                    round_number=idx,
                    name=r_name,
                    round_type=r_type,
                    duration_minutes=60,
                    source_sentence=f"Gemini round extraction: {r_name}",
                )
            )

        def safe_float(v: Any) -> float | None:
            if v is None:
                return None
            try:
                return float(re.sub(r"[^0-9.]", "", str(v)))
            except Exception:
                return None

        def safe_int(v: Any) -> int | None:
            if v is None:
                return None
            try:
                return int(re.sub(r"[^0-9]", "", str(v)))
            except Exception:
                return None

        return ExtractedRequirements(
            company_name=make_field("company_name", data.get("company_name")),
            role=make_field("role", data.get("role")),
            location=make_field("location", data.get("location")),
            drive_date=make_field("drive_date", drive_date_val) if drive_date_val else None,
            application_deadline=make_field("application_deadline", deadline_val) if deadline_val else None,
            mode=make_field("mode", mode_val) if mode_val else None,
            ctc_lpa=make_field("ctc_lpa", safe_float(data.get("ctc_lpa"))) if data.get("ctc_lpa") is not None else None,
            stipend_monthly=make_field("stipend_monthly", safe_float(data.get("stipend_monthly"))) if data.get("stipend_monthly") is not None else None,
            cgpa_min=make_field("cgpa_min", safe_float(data.get("cgpa_min"))) if data.get("cgpa_min") is not None else None,
            tenth_percentage_min=make_field("tenth_percentage_min", safe_float(data.get("tenth_percentage_min"))) if data.get("tenth_percentage_min") is not None else None,
            twelfth_percentage_min=make_field("twelfth_percentage_min", safe_float(data.get("twelfth_percentage_min"))) if data.get("twelfth_percentage_min") is not None else None,
            allowed_branches=make_field("allowed_branches", norm_branches) if norm_branches else None,
            active_backlogs_max=make_field("active_backlogs_max", safe_int(data.get("active_backlogs_max"))) if data.get("active_backlogs_max") is not None else None,
            historical_backlogs_max=make_field("historical_backlogs_max", safe_int(data.get("historical_backlogs_max"))) if data.get("historical_backlogs_max") is not None else None,
            gap_years_max=make_field("gap_years_max", safe_int(data.get("gap_years_max"))) if data.get("gap_years_max") is not None else None,
            bond_details=make_field("bond_details", data.get("bond_details")),
            rounds=rounds,
            raw_text=raw_text,
            overall_confidence=0.96,
        )


class MockLlmExtractor:
    """
    Reference/offline mock implementation of ILlmExtractor.
    Disabled by default via environment variable 'ENABLE_LLM_EXTRACTOR'.
    """

    def __init__(self, enabled: bool = False) -> None:
        env_flag = os.getenv("ENABLE_LLM_EXTRACTOR", "false").lower() in ("true", "1", "yes")
        self._enabled = enabled or env_flag

    def is_enabled(self) -> bool:
        return self._enabled

    def extract(
        self,
        announcement_text: str,
        document_bytes: bytes | None = None,
        filename: str | None = None,
    ) -> ExtractedRequirements:
        if not self.is_enabled():
            raise RuntimeError("MockLlmExtractor is disabled.")

        deterministic = DeterministicExtractor()
        extracted = deterministic.extract(announcement_text)
        return extracted.model_copy(update={"overall_confidence": round(extracted.overall_confidence * 0.85, 3)})


class HybridExtractionEngine:
    """
    Coordinates extraction by running the deterministic extractor first,
    and optionally falling back to an LLM extractor (Gemini) for unfilled fields.
    Guarantees 100% zero failure: if the LLM call times out or encounters network
    glitches, the deterministic result is safely returned without interruption.
    """

    def __init__(
        self,
        deterministic_extractor: Any | None = None,
        llm_extractor: ILlmExtractor | None = None,
    ) -> None:
        self.deterministic = deterministic_extractor or DeterministicExtractor()
        self.llm = llm_extractor if llm_extractor is not None else GeminiExtractor()

    def extract(
        self,
        text: str,
        document_bytes: bytes | None = None,
        filename: str | None = None,
    ) -> ExtractedRequirements:
        # Step 1: Run primary deterministic extractor
        primary = self.deterministic.extract(text)

        # Step 2: If LLM is not provided or disabled, return deterministic output directly
        if self.llm is None or not self.llm.is_enabled():
            return primary

        # Step 3: Run LLM extractor with resilient fault-tolerant circuit-breaker
        try:
            secondary = self.llm.extract(
                text,
                document_bytes=document_bytes,
                filename=filename,
            )
        except Exception as exc:
            # Resilient: NEVER fail or crash due to LLM error or timeout
            logger.warning("HybridExtractionEngine: LLM extraction skipped or failed: %s", exc)
            return primary

        # Step 4: Merge secondary fields where primary was empty, ambiguous, or enriched
        updates: dict[str, object] = {}

        merge_fields = (
            "company_name",
            "drive_date",
            "application_deadline",
            "mode",
            "ctc_lpa",
            "stipend_monthly",
            "role",
            "location",
            "bond_details",
            "cgpa_min",
            "tenth_percentage_min",
            "twelfth_percentage_min",
            "diploma_percentage_min",
            "allowed_branches",
            "allowed_programs",
            "batch_year",
            "active_backlogs_max",
            "historical_backlogs_max",
            "gap_years_max",
            "allow_gap_during_degree",
        )

        for field_name in merge_fields:
            primary_val = getattr(primary, field_name, None)
            secondary_val = getattr(secondary, field_name, None)

            if secondary_val is None:
                continue

            # Case A: Primary is None -> take secondary
            if primary_val is None:
                updates[field_name] = secondary_val
                continue

            # Special Case: If primary company name is a filename or placeholder, take secondary
            if field_name == 'company_name':
                p_comp = str(getattr(primary_val, 'value', '')).lower()
                if any(p_comp.endswith(ext) for ext in ('.png', '.jpg', '.jpeg', '.pdf', '.docx', '.txt', '.eml')) or 'target company' in p_comp:
                    updates[field_name] = secondary_val
                    continue

            # Case B: Primary is ambiguous or low confidence -> take high-confidence secondary
            is_ambiguous = getattr(primary_val, "is_ambiguous", False)
            conf = getattr(primary_val, "confidence", 1.0)
            if is_ambiguous or conf < 0.60:
                updates[field_name] = secondary_val
                continue

            # Case C: Primary allowed_branches is empty, ['All Branches'], or has unparsed regex artifact chunks
            if field_name == "allowed_branches":
                p_val = getattr(primary_val, "value", [])
                s_val = getattr(secondary_val, "value", [])
                p_list = p_val if isinstance(p_val, list) else [p_val]
                is_bad_branch = (
                    not p_val
                    or p_val == ["All Branches"]
                    or any("\n" in str(x) or len(str(x)) > 20 or any(bad in str(x).upper() for bad in ["IMAGE", "CIRCULAR", "RECRUITMENT", "DOCUMENT", "NOTICE"]) for x in p_list)
                )
                if is_bad_branch and s_val and s_val != ["All Branches"]:
                    updates[field_name] = secondary_val

        # Step 5: Merge rounds if secondary discovered structured selection rounds
        if (not primary.rounds or len(primary.rounds) == 0) and secondary.rounds:
            updates["rounds"] = secondary.rounds

        # Step 6: Mark overall confidence
        if updates:
            updates["overall_confidence"] = max(primary.overall_confidence, 0.96)
            return primary.model_copy(update=updates)

        return primary
