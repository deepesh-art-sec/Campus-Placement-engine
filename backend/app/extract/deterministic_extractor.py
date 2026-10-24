"""
Deterministic placement requirement extractor.
Primary rule extractor using compiled regular expressions, canonical dictionaries,
and ambiguity detection. Produces explainable AST nodes with sentence provenance.
"""

from __future__ import annotations

import datetime
import re

from backend.app.domain.models import DriveMode
from backend.app.extract.cleaner import clean_text, extract_sentences
from backend.app.extract.models import (
    AmbiguityItem,
    ExtractedField,
    ExtractedFieldReview,
    ExtractedRequirements,
    ExtractedRound,
    FieldReviewStatus,
)
from backend.app.extract.patterns import (
    RE_BACKLOG_LINE,
    RE_BATCH,
    RE_BOND,
    RE_CGPA_EXPLICIT,
    RE_CGPA_INVERTED,
    RE_CGPA_NO_CUTOFF,
    RE_COMPANY,
    RE_CTC_LPA,
    RE_CTC_NUMERIC_INR,
    RE_DEGREE,
    RE_DRIVE_DATE,
    RE_DRIVE_MODE,
    RE_DURATION_MINS,
    RE_GAP_YEARS,
    RE_MAX_GAP_NUM,
    RE_ROUND_LINE,
    RE_SUBJECT_COMPANY,
    RE_TENTH_AND_TWELFTH,
    RE_TENTH_EXPLICIT,
    RE_THROUGHOUT_PERCENTAGE,
    RE_TWELFTH_EXPLICIT,
    classify_round_type,
    parse_branches_string,
    parse_date_string,
    parse_mode_string,
)


class DeterministicExtractor:
    """
    Offline, deterministic requirement extractor for placement drive announcements.
    Operates strictly via structured patterns and semantic dictionaries.
    """

    def extract(self, raw_input: str) -> ExtractedRequirements:
        """Extracts complete placement requirements and metadata from raw input text."""
        cleaned = clean_text(raw_input)
        sentences = extract_sentences(cleaned)

        ambiguities: list[AmbiguityItem] = []
        review_queue: list[ExtractedFieldReview] = []

        # 1. Metadata
        company = self._extract_company(cleaned, sentences)
        drive_date = self._extract_drive_date(cleaned, sentences)
        mode = self._extract_mode(cleaned, sentences)
        ctc_lpa = self._extract_ctc(cleaned, sentences)
        bond = self._extract_bond(cleaned, sentences)
        rounds = self._extract_rounds(cleaned, sentences)

        # 2. Academic criteria
        cgpa_min, cgpa_ambiguities = self._extract_cgpa(cleaned, sentences)
        ambiguities.extend(cgpa_ambiguities)

        tenth_pct, twelfth_pct, pct_ambiguities = self._extract_percentages(cleaned, sentences)
        ambiguities.extend(pct_ambiguities)

        active_backlogs, hist_backlogs, backlog_ambiguities = self._extract_backlogs(cleaned, sentences)
        ambiguities.extend(backlog_ambiguities)

        branches, branch_ambiguities = self._extract_branches(cleaned, sentences)
        ambiguities.extend(branch_ambiguities)

        programs, batch = self._extract_degree_and_batch(cleaned, sentences)
        gap_years, allow_gap_during = self._extract_gap_years(cleaned, sentences)

        # Calculate overall confidence
        extracted_fields = [
            f for f in (
                company, drive_date, mode, ctc_lpa, cgpa_min, tenth_pct, twelfth_pct,
                active_backlogs, hist_backlogs, branches, programs, gap_years,
            ) if f is not None
        ]

        if extracted_fields:
            overall_conf = round(sum(f.confidence for f in extracted_fields) / len(extracted_fields), 3)
        else:
            overall_conf = 0.5

        # Build review queue for any item with confidence < 0.6 or ambiguous items
        for field in extracted_fields:
            if field.confidence < 0.6 or field.is_ambiguous:
                review_queue.append(
                    ExtractedFieldReview(
                        field_name=field.field_name,
                        extracted_value=field.value,
                        confidence=field.confidence,
                        source_sentence=field.source_sentence,
                        status=FieldReviewStatus.PENDING,
                        is_ambiguous=field.is_ambiguous,
                        ambiguity_reason=field.ambiguity_reason,
                    )
                )

        # Also add explicit ambiguity items to review queue
        for amb in ambiguities:
            review_queue.append(
                ExtractedFieldReview(
                    field_name=amb.field_name,
                    extracted_value=amb.raw_text,
                    confidence=0.5,
                    source_sentence=amb.source_sentence,
                    status=FieldReviewStatus.PENDING,
                    is_ambiguous=True,
                    ambiguity_reason=amb.reason,
                    officer_notes=f"Action suggested: {amb.suggested_action}",
                )
            )

        return ExtractedRequirements(
            company_name=company,
            drive_date=drive_date,
            mode=mode,
            ctc_lpa=ctc_lpa,
            bond_details=bond,
            rounds=rounds,
            cgpa_min=cgpa_min,
            tenth_percentage_min=tenth_pct,
            twelfth_percentage_min=twelfth_pct,
            allowed_branches=branches,
            allowed_programs=programs,
            batch_year=batch,
            active_backlogs_max=active_backlogs,
            historical_backlogs_max=hist_backlogs,
            gap_years_max=gap_years,
            allow_gap_during_degree=allow_gap_during,
            raw_text=cleaned,
            source_sentences=sentences,
            ambiguities=ambiguities,
            review_queue=review_queue,
            overall_confidence=overall_conf,
        )

    # -------------------------------------------------------------------------
    # Extractor Helpers
    # -------------------------------------------------------------------------

    def _extract_company(self, text: str, sentences: list[str]) -> ExtractedField[str] | None:
        m = RE_COMPANY.search(text)
        if m:
            val = m.group(1).strip()
            # Clean possible trailing details
            val = re.sub(r"\s*\(CTC.*$", "", val).strip()
            src = self._find_sentence(sentences, val)
            return ExtractedField(
                field_name="company_name",
                value=val,
                confidence=0.98,
                source_sentence=src,
            )

        # Try from subject line
        m_subj = RE_SUBJECT_COMPANY.search(text)
        if m_subj:
            val = m_subj.group(1).strip()
            src = self._find_sentence(sentences, val)
            return ExtractedField(
                field_name="company_name",
                value=val,
                confidence=0.92,
                source_sentence=src,
            )

        return None

    def _extract_drive_date(self, text: str, sentences: list[str]) -> ExtractedField[datetime.date] | None:
        m = RE_DRIVE_DATE.search(text)
        if m:
            raw_date = m.group(1).strip()
            parsed = parse_date_string(raw_date)
            if parsed:
                src = self._find_sentence(sentences, raw_date)
                return ExtractedField(
                    field_name="drive_date",
                    value=parsed,
                    confidence=0.95,
                    source_sentence=src,
                )
        return None

    def _extract_mode(self, text: str, sentences: list[str]) -> ExtractedField[DriveMode] | None:
        m = RE_DRIVE_MODE.search(text)
        if m:
            raw_mode = m.group(1).strip()
            mode = parse_mode_string(raw_mode)
            src = self._find_sentence(sentences, raw_mode)
            return ExtractedField(
                field_name="mode",
                value=mode,
                confidence=0.95,
                source_sentence=src,
            )
        return None

    def _extract_ctc(self, text: str, sentences: list[str]) -> ExtractedField[float] | None:
        # Search lines mentioning CTC or package
        for line in text.split("\n"):
            if any(k in line.lower() for k in ("ctc", "package", "salary")):
                m_lpa = RE_CTC_LPA.search(line)
                if m_lpa:
                    val = float(m_lpa.group(1))
                    src = self._find_sentence(sentences, line)
                    return ExtractedField(
                        field_name="ctc_lpa",
                        value=val,
                        confidence=0.95,
                        source_sentence=src,
                    )
                m_inr = RE_CTC_NUMERIC_INR.search(line)
                if m_inr:
                    # Convert numeric INR e.g. 12,00,000 to LPA
                    raw_num = float(m_inr.group(1).replace(",", ""))
                    val = round(raw_num / 100000.0, 2)
                    src = self._find_sentence(sentences, line)
                    return ExtractedField(
                        field_name="ctc_lpa",
                        value=val,
                        confidence=0.92,
                        source_sentence=src,
                    )
        return None

    def _extract_cgpa(
        self, text: str, sentences: list[str]
    ) -> tuple[ExtractedField[float] | None, list[AmbiguityItem]]:
        ambiguities: list[AmbiguityItem] = []

        # Check for explicit "no cut-off"
        m_no = RE_CGPA_NO_CUTOFF.search(text)
        if m_no:
            src = self._find_sentence(sentences, m_no.group(0))
            return (
                ExtractedField(
                    field_name="cgpa_min",
                    value=0.0,
                    confidence=0.95,
                    source_sentence=src,
                ),
                ambiguities,
            )

        # Primary explicit regex
        m = RE_CGPA_EXPLICIT.search(text)
        if m:
            val = float(m.group(1))
            scale = float(m.group(2)) if m.group(2) else 10.0
            if scale == 4.0:
                # Convert 4.0 scale to 10.0 scale
                val = round((val / 4.0) * 10.0, 2)
            src = self._find_sentence(sentences, m.group(0))
            return (
                ExtractedField(
                    field_name="cgpa_min",
                    value=val,
                    confidence=0.95,
                    source_sentence=src,
                ),
                ambiguities,
            )

        # Inverted phrase e.g. "7.0 or above in B.Tech"
        m_inv = RE_CGPA_INVERTED.search(text)
        if m_inv:
            val = float(m_inv.group(1))
            src = self._find_sentence(sentences, m_inv.group(0))
            return (
                ExtractedField(
                    field_name="cgpa_min",
                    value=val,
                    confidence=0.90,
                    source_sentence=src,
                ),
                ambiguities,
            )

        return None, ambiguities

    def _extract_percentages(
        self, text: str, sentences: list[str]
    ) -> tuple[ExtractedField[float] | None, ExtractedField[float] | None, list[AmbiguityItem]]:
        ambiguities: list[AmbiguityItem] = []
        tenth: ExtractedField[float] | None = None
        twelfth: ExtractedField[float] | None = None

        # Check for throughout phrasing (e.g. "60% throughout" or "minimum 65% throughout")
        m_thru = RE_THROUGHOUT_PERCENTAGE.search(text)
        if m_thru:
            val = float(m_thru.group(1))
            src = self._find_sentence(sentences, m_thru.group(0))
            ambiguities.append(
                AmbiguityItem(
                    field_name="percentage_throughout",
                    raw_text=m_thru.group(0),
                    source_sentence=src,
                    reason="Requirement specifies percentage 'throughout' without distinct 10th, 12th, and semester cutoffs.",
                    suggested_action="Confirm whether cut-off applies uniformly to 10th, 12th, and all degree semesters.",
                )
            )
            tenth = ExtractedField(
                field_name="tenth_percentage_min",
                value=val,
                confidence=0.75,
                source_sentence=src,
                is_ambiguous=True,
                ambiguity_reason="Inferred from 'throughout' phrasing.",
            )
            twelfth = ExtractedField(
                field_name="twelfth_percentage_min",
                value=val,
                confidence=0.75,
                source_sentence=src,
                is_ambiguous=True,
                ambiguity_reason="Inferred from 'throughout' phrasing.",
            )
            return tenth, twelfth, ambiguities

        # Combined 10th and 12th pattern
        m_both = RE_TENTH_AND_TWELFTH.search(text)
        if m_both:
            val = float(m_both.group(1))
            src = self._find_sentence(sentences, m_both.group(0))
            tenth = ExtractedField(
                field_name="tenth_percentage_min",
                value=val,
                confidence=0.95,
                source_sentence=src,
            )
            twelfth = ExtractedField(
                field_name="twelfth_percentage_min",
                value=val,
                confidence=0.95,
                source_sentence=src,
            )
            return tenth, twelfth, ambiguities

        # Separate 10th
        m_10 = RE_TENTH_EXPLICIT.search(text)
        if m_10:
            val = float(m_10.group(1))
            src = self._find_sentence(sentences, m_10.group(0))
            tenth = ExtractedField(
                field_name="tenth_percentage_min",
                value=val,
                confidence=0.95,
                source_sentence=src,
            )

        # Separate 12th
        m_12 = RE_TWELFTH_EXPLICIT.search(text)
        if m_12:
            val = float(m_12.group(1))
            src = self._find_sentence(sentences, m_12.group(0))
            twelfth = ExtractedField(
                field_name="twelfth_percentage_min",
                value=val,
                confidence=0.95,
                source_sentence=src,
            )

        return tenth, twelfth, ambiguities

    def _extract_backlogs(
        self, text: str, sentences: list[str]
    ) -> tuple[ExtractedField[int] | None, ExtractedField[int] | None, list[AmbiguityItem]]:
        ambiguities: list[AmbiguityItem] = []
        active_field: ExtractedField[int] | None = None
        history_field: ExtractedField[int] | None = None

        m_line = RE_BACKLOG_LINE.search(text)
        if not m_line:
            return None, None, ambiguities

        line_val = m_line.group(1).strip()
        line_lower = line_val.lower()
        src = self._find_sentence(sentences, line_val)

        # Case 1: Strictly 0 / Clean record / Zero throughout / No history of backlogs
        if any(
            k in line_lower
            for k in (
                "no active or historical backlogs",
                "strictly no history of backlogs",
                "no history of backlogs",
                "zero backlogs throughout",
                "strictly clean academic record",
                "clean academic history",
            )
        ):
            active_field = ExtractedField(
                field_name="active_backlogs_max",
                value=0,
                confidence=0.98,
                source_sentence=src,
            )
            history_field = ExtractedField(
                field_name="historical_backlogs_max",
                value=0,
                confidence=0.98,
                source_sentence=src,
            )
            return active_field, history_field, ambiguities

        # Case 2: Max cleared / history backlogs permitted
        # e.g. "Maximum 1 cleared backlog permitted, 0 active" or "no active backlogs, max 1 cleared"
        m_cleared = re.search(r"max(?:imum)?\s*(\d+)\s*cleared", line_lower)
        if m_cleared:
            hist_count = int(m_cleared.group(1))
            history_field = ExtractedField(
                field_name="historical_backlogs_max",
                value=hist_count,
                confidence=0.95,
                source_sentence=src,
            )

        # Check active backlogs count
        if "at time of joining" in line_lower:
            ambiguities.append(
                AmbiguityItem(
                    field_name="backlog_timing",
                    raw_text=line_val,
                    source_sentence=src,
                    reason="Backlog status specified 'at time of joining' rather than drive date.",
                    suggested_action="Verify if students with current backlogs are allowed to sit for interview.",
                )
            )

        m_active_num = re.search(r"max(?:imum)?\s*(\d+)\s*active", line_lower)
        if m_active_num:
            active_count = int(m_active_num.group(1))
            active_field = ExtractedField(
                field_name="active_backlogs_max",
                value=active_count,
                confidence=0.95,
                source_sentence=src,
            )
        elif any(
            k in line_lower
            for k in (
                "0 active",
                "no active",
                "no standing arrears",
                "0 standing arrears",
                "no standing backlogs",
                "no active arrears",
                "zero backlogs at the time",
            )
        ):
            active_field = ExtractedField(
                field_name="active_backlogs_max",
                value=0,
                confidence=0.95,
                source_sentence=src,
            )

        return active_field, history_field, ambiguities

    def _extract_branches(
        self, text: str, sentences: list[str]
    ) -> tuple[ExtractedField[list[str]] | None, list[AmbiguityItem]]:
        ambiguities: list[AmbiguityItem] = []
        # First check explicit regex pattern across line or paragraph
        m = re.search(
            r"(?:eligible\s+)?(?:branches|disciplines|departments|allowed\s+streams)\s*[:=]\s*([^\r\n.]+)",
            text,
            re.IGNORECASE,
        )
        if m:
            raw_branches = m.group(1).strip()
            parsed = parse_branches_string(raw_branches)
            src = self._find_sentence(sentences, raw_branches)
            return (
                ExtractedField(
                    field_name="allowed_branches",
                    value=parsed,
                    confidence=0.95,
                    source_sentence=src,
                ),
                ambiguities,
            )

        for line in text.split("\n"):
            if any(k in line.lower() for k in ("branches", "disciplines", "departments", "allowed streams")):
                parts = line.split(":", 1)
                if len(parts) > 1:
                    raw_branches = parts[1].strip()
                    parsed = parse_branches_string(raw_branches)
                    src = self._find_sentence(sentences, raw_branches)
                    return (
                        ExtractedField(
                            field_name="allowed_branches",
                            value=parsed,
                            confidence=0.95,
                            source_sentence=src,
                        ),
                        ambiguities,
                    )

        return None, ambiguities

    def _extract_degree_and_batch(
        self, text: str, sentences: list[str]
    ) -> tuple[ExtractedField[list[str]] | None, ExtractedField[int] | None]:
        programs_field: ExtractedField[list[str]] | None = None
        batch_field: ExtractedField[int] | None = None

        m_deg = RE_DEGREE.search(text)
        if m_deg:
            raw_deg = m_deg.group(1).strip()
            src = self._find_sentence(sentences, raw_deg)
            # Find degrees
            deg_list: list[str] = []
            for deg_name in ("B.Tech", "B.E.", "M.Tech", "MCA", "MBA", "BCA"):
                if re.search(rf"\b{re.escape(deg_name)}\b", raw_deg, re.IGNORECASE):
                    deg_list.append(deg_name)
            if deg_list:
                programs_field = ExtractedField(
                    field_name="allowed_programs",
                    value=deg_list,
                    confidence=0.95,
                    source_sentence=src,
                )

        m_batch = RE_BATCH.search(text)
        if m_batch:
            val = int(m_batch.group(1))
            src = self._find_sentence(sentences, m_batch.group(0))
            batch_field = ExtractedField(
                field_name="batch_year",
                value=val,
                confidence=0.95,
                source_sentence=src,
            )

        return programs_field, batch_field

    def _extract_gap_years(
        self, text: str, sentences: list[str]
    ) -> tuple[ExtractedField[int] | None, ExtractedField[bool] | None]:
        m_gap = RE_GAP_YEARS.search(text)
        if not m_gap:
            return None, None

        raw_val = m_gap.group(1).strip()
        src = self._find_sentence(sentences, raw_val)

        max_gap = 0
        m_num = RE_MAX_GAP_NUM.search(raw_val)
        if m_num:
            max_gap = int(m_num.group(1))

        allow_during_degree = not ("no gaps during engineering" in raw_val.lower() or "no gap during degree" in raw_val.lower())

        gap_field = ExtractedField(
            field_name="gap_years_max",
            value=max_gap,
            confidence=0.95,
            source_sentence=src,
        )
        allow_field = ExtractedField(
            field_name="allow_gap_during_degree",
            value=allow_during_degree,
            confidence=0.95,
            source_sentence=src,
        )

        return gap_field, allow_field

    def _extract_rounds(self, text: str, sentences: list[str]) -> list[ExtractedRound]:
        rounds: list[ExtractedRound] = []
        for m in RE_ROUND_LINE.finditer(text):
            r_num = int(m.group(1))
            r_desc = m.group(2).strip()
            src = self._find_sentence(sentences, m.group(0))

            # Extract duration
            duration = 60
            m_dur = RE_DURATION_MINS.search(r_desc)
            if m_dur:
                duration = int(m_dur.group(1))
                r_name = re.sub(r"-\s*\d+\s*(?:mins|min|minutes)", "", r_desc).strip()
            else:
                r_name = r_desc

            round_type = classify_round_type(r_name)
            rounds.append(
                ExtractedRound(
                    round_number=r_num,
                    name=r_name,
                    round_type=round_type,
                    duration_minutes=duration,
                    source_sentence=src,
                )
            )

        return rounds

    def _extract_bond(self, text: str, sentences: list[str]) -> ExtractedField[str] | None:
        m = RE_BOND.search(text)
        if m:
            val = m.group(1).strip()
            src = self._find_sentence(sentences, val)
            return ExtractedField(
                field_name="bond_details",
                value=val,
                confidence=0.90,
                source_sentence=src,
            )
        return None

    def _find_sentence(self, sentences: list[str], needle: str) -> str:
        """Finds the most specific sentence containing the needle."""
        n_clean = needle.strip()
        for s in sentences:
            if n_clean in s:
                return s
        for s in sentences:
            # Fallback fuzzy word match
            words = [w for w in re.split(r"\W+", n_clean) if len(w) > 3]
            if words and any(w in s for w in words):
                return s
        return sentences[0] if sentences else needle
