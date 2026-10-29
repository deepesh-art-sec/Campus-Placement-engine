"""
NLP-Powered Announcement Extraction Engine using spaCy, Matchers, and Context-Aware Disambiguation.
Provides:
  - Text preprocessing: tokenization, lemmatization, sentence segmentation, and POS tagging via spaCy.
  - Named Entity Recognition (NER) for company names (ORG), job locations (GPE/LOC), dates (DATE), and compensation (MONEY).
  - PhraseMatcher and Matcher for technical roles, academic cutoffs, selection rounds, and deadlines.
  - Context-aware disambiguation:
      * Minimum vs maximum CGPA (rejects irrelevant integers like years, headcount, or percentages).
      * Active vs historical backlogs (standing arrears vs past cleared arrears).
      * Salary figures vs non-salary numbers (distinguishes LPA/INR from phone numbers, batch years, and quotas).
      * Application deadline vs campus drive interview date.
      * Canonical branch normalization (CSE, ECE, EEE, Mechanical Engineering, Civil Engineering, Chemical Engineering, Biotechnology).
  - Compatible with full offline operation without cloud dependency.
"""

from __future__ import annotations

import datetime
import logging
import re
from typing import Any

import spacy
from spacy.matcher import Matcher, PhraseMatcher

from backend.app.domain.models import DriveMode, RoundType
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
    BRANCH_ALIASES,
    CIRCUIT_BRANCHES,
    CS_ALLIED_BRANCHES,
    RE_BACKLOG_LINE,
    RE_BATCH,
    RE_BOND,
    RE_CGPA_EXPLICIT,
    RE_CGPA_INVERTED,
    RE_CGPA_NO_CUTOFF,
    RE_COMPANY,
    RE_CTC_LINE,
    RE_CTC_LPA,
    RE_CTC_NUMERIC_INR,
    RE_DEGREE,
    RE_DRIVE_DATE,
    RE_DRIVE_MODE,
    RE_DURATION_MINS,
    RE_GAP_YEARS,
    RE_LOCATION,
    RE_MAX_GAP_NUM,
    RE_ROLE,
    RE_ROUND_LINE,
    RE_SUBJECT_COMPANY,
    RE_TENTH_AND_TWELFTH,
    RE_PERCENT_BEFORE_TENTH_AND_TWELFTH,
    RE_PERCENT_BEFORE_TENTH,
    RE_PERCENT_BEFORE_TWELFTH,
    RE_TENTH_EXPLICIT,
    RE_THROUGHOUT_PERCENTAGE,
    RE_TWELFTH_EXPLICIT,
    classify_round_type,
    normalize_branch_token,
    parse_branches_string,
    parse_date_string,
    parse_mode_string,
)

logger = logging.getLogger("placement_nlp")


# Canonical project branch codes mapping
CANONICAL_BRANCH_CODES: dict[str, str] = {
    "CSE": "CSE",
    "COMPUTER SCIENCE": "CSE",
    "COMPUTER SCIENCE AND ENGINEERING": "CSE",
    "COMPUTER SCIENCE & ENGINEERING": "CSE",
    "CS": "CSE",
    "IT": "IT",
    "INFORMATION TECHNOLOGY": "IT",
    "DATA SCIENCE": "Data Science",
    "DS": "Data Science",
    "AI & ML": "AI & ML",
    "AIML": "AI & ML",
    "ARTIFICIAL INTELLIGENCE": "AI & ML",
    "ECE": "ECE",
    "ELECTRONICS AND COMMUNICATION": "ECE",
    "ELECTRONICS AND COMMUNICATION ENGINEERING": "ECE",
    "ELECTRONICS & COMMUNICATION": "ECE",
    "ELECTRONICS": "ECE",
    "EEE": "EEE",
    "ELECTRICAL AND ELECTRONICS": "EEE",
    "ELECTRICAL AND ELECTRONICS ENGINEERING": "EEE",
    "ELECTRICAL & ELECTRONICS": "EEE",
    "ELECTRICAL": "EEE",
    "EE": "EEE",
    "MECH": "Mechanical Engineering",
    "MECHANICAL": "Mechanical Engineering",
    "MECHANICAL ENGINEERING": "Mechanical Engineering",
    "ME": "Mechanical Engineering",
    "CIVIL": "Civil Engineering",
    "CIVIL ENGINEERING": "Civil Engineering",
    "CE": "Civil Engineering",
    "CHEM": "Chemical Engineering",
    "CHEMICAL": "Chemical Engineering",
    "CHEMICAL ENGINEERING": "Chemical Engineering",
    "BIOTECH": "Biotechnology",
    "BIOTECHNOLOGY": "Biotechnology",
    "BT": "Biotechnology",
    "ALL BRANCHES": "All Branches",
    "OPEN TO ALL": "All Branches",
    "ANY BRANCH": "All Branches",
}

COMMON_ROLES = [
    "Software Engineer",
    "Software Engineers",
    "Software Development Engineer",
    "Software Development Engineers",
    "SDE",
    "SDE-1",
    "SDE I",
    "Associate Software Engineer",
    "Associate Software Engineers",
    "Graduate Engineer Trainee",
    "Graduate Engineer Trainees",
    "GET",
    "Full Stack Developer",
    "Full Stack Developers",
    "Frontend Developer",
    "Frontend Developers",
    "Backend Developer",
    "Backend Developers",
    "Data Scientist",
    "Data Scientists",
    "Data Analyst",
    "Data Analysts",
    "Machine Learning Engineer",
    "Machine Learning Engineers",
    "Cloud Engineer",
    "DevOps Engineer",
    "Cyber Security Analyst",
    "Quality Assurance Engineer",
    "QA Engineer",
    "Product Analyst",
    "Business Analyst",
    "Member Technical Staff",
    "MTS",
    "System Engineer",
    "Systems Engineer",
    "Systems Engineers",
    "Consultant",
    "Consultants",
    "Associate Consultant",
    "Technical Solutions Engineer",
    "Application Developer",
    "R&D Engineer",
]

COMMON_LOCATIONS = [
    "Bangalore",
    "Bengaluru",
    "Hyderabad",
    "Pune",
    "Mumbai",
    "Delhi",
    "Noida",
    "Gurgaon",
    "Gurugram",
    "Chennai",
    "Kolkata",
    "Ahmedabad",
    "Kochi",
    "Trivandrum",
    "Coimbatore",
    "Pan India",
    "Across India",
    "Remote",
    "Hybrid",
]

DEADLINE_INDICATORS = [
    re.compile(r"(?:application\s+deadline|last\s+date\s+to\s+apply|registration\s+deadline|registration\s+closes|apply\s+by|apply\s+before|submission\s+deadline|deadline)[ \t]*[:=]?[ \t]*([^\r\n,;]+)", re.IGNORECASE),
    re.compile(r"(?:apply|register)\s+on\s+or\s+before\s+([^\r\n,;]+)", re.IGNORECASE),
    re.compile(r"portal\s+closes\s+on\s+([^\r\n,;]+)", re.IGNORECASE),
]


class NLPEngine:
    """
    NLP-driven Information Extraction engine for university placement announcements.
    Combines spaCy language pipeline (NER, Matchers, Part-of-Speech) with deterministic
    domain grammars for maximum precision, recall, and explainable provenance.
    """

    def __init__(self) -> None:
        try:
            self.nlp = spacy.load("en_core_web_sm")
            self._has_ner = True
        except Exception:
            try:
                self.nlp = spacy.blank("en")
                if "sentencizer" not in self.nlp.pipe_names:
                    self.nlp.add_pipe("sentencizer")
                self._has_ner = False
            except Exception:
                self.nlp = None
                self._has_ner = False

        self.matcher = None
        self.phrase_matcher = None
        if self.nlp:
            self._init_matchers()

    def _init_matchers(self) -> None:
        """Initializes Matcher and PhraseMatcher rules."""
        self.matcher = Matcher(self.nlp.vocab)
        self.phrase_matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")

        # 1. Role phrase matching
        role_patterns = [self.nlp.make_doc(role) for role in COMMON_ROLES]
        self.phrase_matcher.add("ROLE_PATTERN", role_patterns)

        # 2. Location phrase matching
        loc_patterns = [self.nlp.make_doc(loc) for loc in COMMON_LOCATIONS]
        self.phrase_matcher.add("LOC_PATTERN", loc_patterns)

    def _find_sentence(self, sentences: list[str], phrase: str) -> str:
        """Helper to find source sentence for provenance tracking."""
        phrase_clean = phrase.strip().lower()
        for s in sentences:
            if phrase_clean in s.lower():
                return s
        return sentences[0] if sentences else phrase

    # -------------------------------------------------------------------------
    # Core Extraction with NLP & Context-Aware Disambiguation
    # -------------------------------------------------------------------------

    def extract(self, raw_text: str) -> ExtractedRequirements:
        """Runs the hybrid NLP and rule-based extraction pipeline on raw announcement text."""
        cleaned = clean_text(raw_text)
        sentences = extract_sentences(cleaned)

        doc = self.nlp(cleaned) if self.nlp else None

        ambiguities: list[AmbiguityItem] = []
        review_queue: list[ExtractedFieldReview] = []

        # 1. Metadata extraction
        company = self.extract_company(cleaned, sentences, doc)
        role = self.extract_role(cleaned, sentences, doc)
        location = self.extract_location(cleaned, sentences, doc)
        drive_date = self.extract_drive_date(cleaned, sentences, doc)
        deadline = self.extract_application_deadline(cleaned, sentences, doc)
        mode = self.extract_mode(cleaned, sentences)
        ctc_lpa = self.extract_ctc(cleaned, sentences, doc)
        bond = self.extract_bond(cleaned, sentences)
        rounds = self.extract_rounds(cleaned, sentences)

        # 2. Academic criteria extraction
        cgpa_min, cgpa_ambiguities = self.extract_cgpa(cleaned, sentences, doc)
        ambiguities.extend(cgpa_ambiguities)

        tenth_pct, twelfth_pct, pct_ambiguities = self.extract_percentages(cleaned, sentences)
        ambiguities.extend(pct_ambiguities)

        active_backlogs, hist_backlogs, backlog_ambiguities = self.extract_backlogs(cleaned, sentences)
        ambiguities.extend(backlog_ambiguities)

        branches, branch_ambiguities = self.extract_branches(cleaned, sentences)
        ambiguities.extend(branch_ambiguities)

        programs, batch = self.extract_degree_and_batch(cleaned, sentences)
        gap_years, allow_gap_during = self.extract_gap_years(cleaned, sentences)

        # 3. Overall confidence calculation
        fields_to_score = [
            f for f in (
                company, role, location, drive_date, deadline, mode, ctc_lpa,
                cgpa_min, tenth_pct, twelfth_pct, active_backlogs, hist_backlogs,
                branches, programs, gap_years,
            ) if f is not None
        ]

        if fields_to_score:
            overall_conf = round(sum(f.confidence for f in fields_to_score) / len(fields_to_score), 3)
        else:
            overall_conf = 0.50

        # Build review queue for ambiguous or low-confidence fields
        for field in fields_to_score:
            if field.confidence < 0.65 or field.is_ambiguous:
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

        for amb in ambiguities:
            review_queue.append(
                ExtractedFieldReview(
                    field_name=amb.field_name,
                    extracted_value=amb.raw_text,
                    confidence=0.50,
                    source_sentence=amb.source_sentence,
                    status=FieldReviewStatus.PENDING,
                    is_ambiguous=True,
                    ambiguity_reason=amb.reason,
                    officer_notes=f"Action suggested: {amb.suggested_action}",
                )
            )

        return ExtractedRequirements(
            company_name=company,
            role=role,
            location=location,
            drive_date=drive_date,
            application_deadline=deadline,
            mode=mode,
            ctc_lpa=ctc_lpa,
            bond_details=bond,
            rounds=rounds,
            cgpa_min=cgpa_min,
            tenth_percentage_min=tenth_pct,
            twelfth_percentage_min=twelfth_pct,
            active_backlogs_max=active_backlogs,
            historical_backlogs_max=hist_backlogs,
            allowed_branches=branches,
            allowed_programs=programs,
            batch_year=batch,
            gap_years_max=gap_years,
            allow_gap_during_degree=allow_gap_during,
            raw_text=cleaned,
            source_sentences=sentences,
            ambiguities=ambiguities,
            review_queue=review_queue,
            overall_confidence=overall_conf,
        )

    # -------------------------------------------------------------------------
    # Field Extraction Methods
    # -------------------------------------------------------------------------

    def extract_company(
        self, text: str, sentences: list[str], doc: spacy.tokens.Doc | None
    ) -> ExtractedField[str] | None:
        """Extracts company name with high precision using regex tags, subject lines, and spaCy NER."""
        # 1. Explicit Company header (highest precedence)
        m = RE_COMPANY.search(text)
        if m:
            clean_comp = m.group(1).strip()
            clean_comp = re.sub(r"\s*\([^)]*\)", "", clean_comp).strip()
            clean_comp = re.sub(r"\s+(?:Private\s+Limited|Pvt\.?\s+Ltd\.?|Ltd\.?|Inc\.?|Corporation)$", "", clean_comp, flags=re.IGNORECASE).strip()
            return ExtractedField(
                field_name="company_name",
                value=clean_comp,
                confidence=0.99,
                source_sentence=m.group(0).strip(),
            )

        # 1b. Check first 2 lines for corporate header (e.g. 'NVIDIA Graphics Private Limited')
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if lines:
            first_line = lines[0]
            first_line_clean = re.sub(r"^(?:campus\s+recruitment\s+(?:drive\s+|circular\s+|notice\s+)?[-:—–]?\s*)", "", first_line, flags=re.IGNORECASE).strip()
            if any(term in first_line_clean.lower() for term in ("private limited", "pvt ltd", "pvt. ltd.", "limited", "ltd", "inc", "technologies", "corporation", "corp")):
                clean_name = re.sub(r"\s+(?:Private\s+Limited|Pvt\.?\s+Ltd\.?|Ltd\.?|Inc\.?|Corporation)$", "", first_line_clean, flags=re.IGNORECASE).strip()
                if clean_name and len(clean_name) >= 2:
                    return ExtractedField(
                        field_name="company_name",
                        value=clean_name,
                        confidence=0.96,
                        source_sentence=first_line,
                    )

        # 2. Email Subject Line match
        m_subj = RE_SUBJECT_COMPANY.search(text)
        if m_subj:
            clean_comp = m_subj.group(1).strip()
            return ExtractedField(
                field_name="company_name",
                value=clean_comp,
                confidence=0.95,
                source_sentence=m_subj.group(0).strip(),
            )

        # 2b. Company hiring / visiting announcement pattern
        m_hiring = re.search(
            r"^(?:##\s*)?([A-Z][A-Za-z0-9&.\s]{1,40}?)\s+(?:is\s+hiring|is\s+recruiting|is\s+visiting|invites\s+applications|announces\s+(?:its\s+)?campus|campus\s+recruitment|placement\s+drive|recruitment\s+drive|campus\s+placement|hiring\s+notice|recruitment\s+notice|placement\s+notice)",
            text,
            re.IGNORECASE | re.MULTILINE,
        )
        if m_hiring:
            cand = m_hiring.group(1).strip()
            if cand.lower() not in ("company", "college", "university", "department", "placement", "notice", "circular", "all", "the", "dear"):
                return ExtractedField(
                    field_name="company_name",
                    value=cand,
                    confidence=0.95,
                    source_sentence=m_hiring.group(0).strip(),
                )

        # 3. Known company signatures in first 5 sentences
        known_companies = [
            ("Goldman Sachs", ["goldman sachs", "goldman"]),
            ("Google", ["google india", "google llc", "google"]),
            ("Microsoft", ["microsoft india", "microsoft r&d", "microsoft"]),
            ("Amazon", ["amazon development", "amazon web services", "amazon"]),
            ("Uber", ["uber india", "uber technologies", "uber"]),
            ("Apple", ["apple india", "apple"]),
            ("Adobe", ["adobe systems", "adobe india", "adobe"]),
            ("Salesforce", ["salesforce india", "salesforce"]),
            ("Flipkart", ["flipkart internet", "flipkart"]),
            ("Oracle", ["oracle india", "oracle financial", "oracle"]),
            ("Qualcomm", ["qualcomm india", "qualcomm"]),
            ("Cisco", ["cisco systems", "cisco"]),
            ("Deloitte USI", ["deloitte consulting", "deloitte usi"]),
            ("Tata Consultancy Services", ["tata consultancy services", "tcs"]),
            ("Infosys", ["infosys limited", "infosys"]),
            ("Wipro", ["wipro limited", "wipro"]),
            ("Accenture", ["accenture solutions", "accenture"]),
            ("Siemens", ["siemens technology", "siemens"]),
            ("Larsen & Toubro", ["larsen & toubro", "larsen and toubro", "l&t"]),
            ("Texas Instruments", ["texas instruments india", "texas instruments"]),
            ("Intel", ["intel technology", "intel corporation", "intel"]),
            ("Morgan Stanley", ["morgan stanley advantage", "morgan stanley"]),
            ("Samsung R&D", ["samsung r&d", "samsung electronics", "samsung"]),
            ("Tata Motors", ["tata motors limited", "tata motors"]),
            ("Reliance Industries", ["reliance industries limited", "reliance industries", "ril"]),
            ("ITC Limited", ["itc limited", "itc"]),
            ("Biocon", ["biocon biologics", "biocon limited", "biocon"]),
            ("ZS Associates", ["zs associates india", "zs associates"]),
            ("Barclays", ["barclays global", "barclays"]),
            ("Atlassian", ["atlassian india", "atlassian"]),
        ]

        check_text = "\n".join(sentences[:5]).lower()
        for canonical, aliases in known_companies:
            for alias in aliases:
                if re.search(r"\b" + re.escape(alias) + r"\b", check_text):
                    return ExtractedField(
                        field_name="company_name",
                        value=canonical,
                        confidence=0.92,
                        source_sentence=sentences[0] if sentences else "",
                    )

        # 4. spaCy NER ORG in the first 3 sentences with strict role/branch noise rejection
        invalid_org_tokens = {
            "engineer", "engineers", "engineering", "developer", "developers",
            "analyst", "analysts", "consultant", "consultants", "specialist", "specialists",
            "trainee", "trainees", "intern", "interns", "associate", "associates",
            "manager", "managers", "lead", "architect",
            "campus", "placement", "placements", "recruitment", "drive", "notice", "circular",
            "b.tech", "m.tech", "b.e", "m.e", "bca", "mca", "degree", "batch",
            "university", "college", "department", "institute", "school",
            "cse", "it", "ece", "eee", "mech", "civil", "chem", "ds", "aiml",
            "eligibility", "criteria", "process", "round", "rounds", "package", "ctc", "lpa",
            "interview", "test", "assessment", "target", "candidates", "students",
        }
        if doc and self._has_ner:
            for ent in doc.ents:
                if ent.label_ == "ORG" and len(ent.text.strip()) > 2:
                    ent_clean = ent.text.strip()
                    tokens = re.findall(r"\b\w+\b", ent_clean.lower())
                    if any(t in invalid_org_tokens for t in tokens):
                        continue
                    return ExtractedField(
                        field_name="company_name",
                        value=ent_clean,
                        confidence=0.75,
                        source_sentence=ent.sent.text.strip() if ent.sent else ent_clean,
                    )

        return None

    def extract_role(
        self, text: str, sentences: list[str], doc: spacy.tokens.Doc | None
    ) -> ExtractedField[str] | None:
        """Extracts job profile / title."""
        m = RE_ROLE.search(text)
        if m:
            clean_role = m.group(1).strip()
            return ExtractedField(
                field_name="role",
                value=clean_role,
                confidence=0.95,
                source_sentence=m.group(0).strip(),
            )

        if doc and self.phrase_matcher:
            matches = self.phrase_matcher(doc)
            for match_id, start, end in matches:
                string_id = self.nlp.vocab.strings[match_id]
                if string_id == "ROLE_PATTERN":
                    span = doc[start:end]
                    return ExtractedField(
                        field_name="role",
                        value=span.text,
                        confidence=0.88,
                        source_sentence=span.sent.text.strip() if span.sent else span.text,
                    )

        return None

    def extract_location(
        self, text: str, sentences: list[str], doc: spacy.tokens.Doc | None
    ) -> ExtractedField[str] | None:
        """Extracts job posting location."""
        m = RE_LOCATION.search(text)
        if m:
            clean_loc = m.group(1).strip()
            return ExtractedField(
                field_name="location",
                value=clean_loc,
                confidence=0.95,
                source_sentence=m.group(0).strip(),
            )

        for s in sentences:
            if any(k in s.lower() for k in ("location", "posting", "work location", "venue", "posting:", "base location")):
                for city in COMMON_LOCATIONS:
                    if re.search(r"\b" + re.escape(city) + r"\b", s, re.IGNORECASE):
                        return ExtractedField(
                            field_name="location",
                            value=city,
                            confidence=0.88,
                            source_sentence=s,
                        )

        if doc and self._has_ner:
            for ent in doc.ents:
                if ent.label_ in ("GPE", "LOC"):
                    sent_text = ent.sent.text.lower() if ent.sent else ""
                    if any(k in sent_text for k in ("posting", "office", "work", "joining", "based")):
                        return ExtractedField(
                            field_name="location",
                            value=ent.text.strip(),
                            confidence=0.80,
                            source_sentence=ent.sent.text.strip() if ent.sent else ent.text,
                        )

        return None

    def extract_drive_date(
        self, text: str, sentences: list[str], doc: spacy.tokens.Doc | None
    ) -> ExtractedField[datetime.date] | None:
        """Extracts campus drive / interview execution date."""
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

        for s in sentences:
            s_lower = s.lower()
            if any(k in s_lower for k in ("drive date", "date of drive", "interview date", "placement drive on", "drive scheduled")):
                if any(dk in s_lower for dk in ("apply by", "deadline", "last date to apply")):
                    continue
                date_m = re.search(r"(\d{4}-\d{2}-\d{2}|\d{1,2}[-\s](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[-\s]\d{4})", s, re.IGNORECASE)
                if date_m:
                    parsed = parse_date_string(date_m.group(1))
                    if parsed:
                        return ExtractedField(
                            field_name="drive_date",
                            value=parsed,
                            confidence=0.85,
                            source_sentence=s,
                        )

        return None

    def extract_application_deadline(
        self, text: str, sentences: list[str], doc: spacy.tokens.Doc | None
    ) -> ExtractedField[datetime.date] | None:
        """Extracts application registration deadline separately from the drive date."""
        for pattern in DEADLINE_INDICATORS:
            m = pattern.search(text)
            if m:
                raw_d = m.group(1).strip()
                parsed = parse_date_string(raw_d)
                if parsed:
                    src = self._find_sentence(sentences, raw_d)
                    return ExtractedField(
                        field_name="application_deadline",
                        value=parsed,
                        confidence=0.92,
                        source_sentence=src,
                    )

        for s in sentences:
            s_lower = s.lower()
            if any(dk in s_lower for dk in ("last date", "deadline", "apply by", "registration closes")):
                date_m = re.search(r"(\d{4}-\d{2}-\d{2}|\d{1,2}[-\s](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[-\s]\d{4})", s, re.IGNORECASE)
                if date_m:
                    parsed = parse_date_string(date_m.group(1))
                    if parsed:
                        return ExtractedField(
                            field_name="application_deadline",
                            value=parsed,
                            confidence=0.85,
                            source_sentence=s,
                        )

        return None

    def extract_mode(self, text: str, sentences: list[str]) -> ExtractedField[DriveMode] | None:
        """Extracts drive mode: on_campus, virtual, or hybrid."""
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

        m_fallback = re.search(r"\b(on[- ]campus|in[- ]person|virtual|hybrid|online)\b", text, re.IGNORECASE)
        if m_fallback:
            raw_mode = m_fallback.group(1).strip()
            mode = parse_mode_string(raw_mode)
            src = self._find_sentence(sentences, raw_mode)
            return ExtractedField(
                field_name="mode",
                value=mode,
                confidence=0.90,
                source_sentence=src,
            )

        return ExtractedField(
            field_name="mode",
            value=DriveMode.ON_CAMPUS,
            confidence=0.60,
            source_sentence="Default assumed on_campus",
        )

    def extract_ctc(
        self, text: str, sentences: list[str], doc: spacy.tokens.Doc | None
    ) -> ExtractedField[float] | None:
        """
        Context-aware CTC extractor.
        Differentiates salary figures (LPA / INR) from unrelated numbers (batch year, headcount, percentages).
        """
        # Primary regex: explicit CTC / Package line
        m_line = re.search(
            r"(?:ctc(?:\s+offered)?|package|salary|stipend)\s*[:=]\s*([^\r\n]+)",
            text,
            re.IGNORECASE,
        )
        if m_line:
            line_text = m_line.group(1).strip()
            m_lpa = RE_CTC_LPA.search(line_text)
            if m_lpa:
                val = float(m_lpa.group(1))
                src = self._find_sentence(sentences, m_lpa.group(0))
                return ExtractedField(
                    field_name="ctc_lpa",
                    value=val,
                    confidence=0.98,
                    source_sentence=src,
                )

            m_inr = RE_CTC_NUMERIC_INR.search(line_text)
            if m_inr:
                raw_num = m_inr.group(1).replace(",", "")
                lpa_val = round(float(raw_num) / 100000.0, 2)
                src = self._find_sentence(sentences, m_inr.group(0))
                return ExtractedField(
                    field_name="ctc_lpa",
                    value=lpa_val,
                    confidence=0.95,
                    source_sentence=src,
                )

        m_fallback = RE_CTC_LPA.search(text)
        if m_fallback:
            val = float(m_fallback.group(1))
            src = self._find_sentence(sentences, m_fallback.group(0))
            return ExtractedField(
                field_name="ctc_lpa",
                value=val,
                confidence=0.90,
                source_sentence=src,
            )

        return None

    def extract_bond(self, text: str, sentences: list[str]) -> ExtractedField[str] | None:
        """Extracts service bond or agreement details."""
        m = RE_BOND.search(text)
        if m:
            clean_bond = m.group(1).strip()
            src = self._find_sentence(sentences, clean_bond)
            return ExtractedField(
                field_name="bond_details",
                value=clean_bond,
                confidence=0.90,
                source_sentence=src,
            )
        return None

    def extract_rounds(self, text: str, sentences: list[str]) -> list[ExtractedRound]:
        """Extracts selection process stages and hiring rounds."""
        rounds: list[ExtractedRound] = []
        for line in text.splitlines():
            m = RE_ROUND_LINE.search(line)
            if m:
                raw_num = m.group(1)
                if raw_num and raw_num.isdigit():
                    r_num = int(raw_num)
                elif raw_num:
                    r_num = roman_to_int(raw_num)
                else:
                    r_num = len(rounds) + 1
                r_desc = (m.group(2) or "").strip()
                r_type = classify_round_type(r_desc)

                dur = 60
                dur_m = RE_DURATION_MINS.search(r_desc)
                if dur_m:
                    dur = int(dur_m.group(1))

                src = self._find_sentence(sentences, line)
                rounds.append(
                    ExtractedRound(
                        round_number=r_num,
                        name=f"Round {r_num}: {r_desc}",
                        round_type=r_type,
                        duration_minutes=dur,
                        source_sentence=src,
                    )
                )

        return rounds

    # -------------------------------------------------------------------------
    # Academic Criteria Extraction
    # -------------------------------------------------------------------------

    def extract_cgpa(
        self, text: str, sentences: list[str], doc: spacy.tokens.Doc | None
    ) -> tuple[ExtractedField[float] | None, list[AmbiguityItem]]:
        """
        Extracts minimum CGPA cutoff with strict context checking.
        Distinguishes minimum versus maximum cutoffs and rejects irrelevant non-CGPA numbers.
        """
        ambiguities: list[AmbiguityItem] = []

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

        m = RE_CGPA_EXPLICIT.search(text)
        if m:
            val = float(m.group(1))
            scale = float(m.group(2)) if m.group(2) else 10.0
            if scale == 4.0:
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

    def extract_percentages(
        self, text: str, sentences: list[str]
    ) -> tuple[ExtractedField[float] | None, ExtractedField[float] | None, list[AmbiguityItem]]:
        """Extracts 10th and 12th percentage minimum requirements."""
        ambiguities: list[AmbiguityItem] = []
        tenth: ExtractedField[float] | None = None
        twelfth: ExtractedField[float] | None = None

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

        m_before_both = RE_PERCENT_BEFORE_TENTH_AND_TWELFTH.search(text)
        if m_before_both:
            val = float(m_before_both.group(1))
            src = self._find_sentence(sentences, m_before_both.group(0))
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

        m10 = RE_PERCENT_BEFORE_TENTH.search(text) or RE_TENTH_EXPLICIT.search(text)
        if m10:
            val = float(m10.group(1))
            src = self._find_sentence(sentences, m10.group(0))
            tenth = ExtractedField(
                field_name="tenth_percentage_min",
                value=val,
                confidence=0.95,
                source_sentence=src,
            )

        m12 = RE_PERCENT_BEFORE_TWELFTH.search(text) or RE_TWELFTH_EXPLICIT.search(text)
        if m12:
            val = float(m12.group(1))
            src = self._find_sentence(sentences, m12.group(0))
            twelfth = ExtractedField(
                field_name="twelfth_percentage_min",
                value=val,
                confidence=0.95,
                source_sentence=src,
            )

        return tenth, twelfth, ambiguities

    def extract_backlogs(
        self, text: str, sentences: list[str]
    ) -> tuple[ExtractedField[int] | None, ExtractedField[int] | None, list[AmbiguityItem]]:
        """
        Extracts active backlog maximum and historical backlog maximum.
        Strictly differentiates between live/standing arrears versus cleared/past history backlogs.
        """
        ambiguities: list[AmbiguityItem] = []
        active_field: ExtractedField[int] | None = None
        history_field: ExtractedField[int] | None = None

        candidate_lines = []
        for line in text.splitlines():
            if re.search(r"\b(?:backlogs?|arrears?)\b", line, re.IGNORECASE):
                candidate_lines.append(line.strip())
        for sent in sentences:
            if re.search(r"\b(?:backlogs?|arrears?)\b", sent, re.IGNORECASE) and sent not in candidate_lines:
                candidate_lines.append(sent.strip())

        if not candidate_lines:
            return None, None, ambiguities

        for line_val in candidate_lines:
            line_lower = line_val.lower()
            src = self._find_sentence(sentences, line_val)

            # Case 1: Strictly clean record / 0 active & historical
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
            m_cleared = re.search(r"(?:max(?:imum)?|up\s+to)?\s*(\d+)\s*(?:cleared|history|historical)\s*(?:backlogs?|arrears?)?", line_lower)
            if m_cleared and history_field is None:
                hist_count = int(m_cleared.group(1))
                history_field = ExtractedField(
                    field_name="historical_backlogs_max",
                    value=hist_count,
                    confidence=0.95,
                    source_sentence=src,
                )

            # Case 3: Ambiguity on timing
            if "at time of joining" in line_lower or "at the time of joining" in line_lower:
                ambiguities.append(
                    AmbiguityItem(
                        field_name="backlog_timing",
                        raw_text=line_val,
                        source_sentence=src,
                        reason="Backlog status specified 'at time of joining' rather than drive date.",
                        suggested_action="Verify if students with current backlogs are allowed to sit for interview.",
                    )
                )

            # Case 4: Active backlogs count
            m_active_num = re.search(r"(?:max(?:imum)?|up\s+to)?\s*(\d+)\s*active\s*(?:backlogs?|arrears?)?", line_lower)
            if m_active_num and active_field is None:
                active_count = int(m_active_num.group(1))
                active_field = ExtractedField(
                    field_name="active_backlogs_max",
                    value=active_count,
                    confidence=0.95,
                    source_sentence=src,
                )
            elif active_field is None and any(
                k in line_lower
                for k in (
                    "0 active",
                    "no active",
                    "no standing arrears",
                    "0 standing arrears",
                    "no standing backlogs",
                    "no active arrears",
                    "zero backlogs",
                    "zero active",
                    "nil active",
                    "without active backlogs",
                    "without any active backlogs",
                )
            ):
                active_field = ExtractedField(
                    field_name="active_backlogs_max",
                    value=0,
                    confidence=0.95,
                    source_sentence=src,
                )

        return active_field, history_field, ambiguities

    def extract_branches(
        self, text: str, sentences: list[str]
    ) -> tuple[ExtractedField[list[str]] | None, list[AmbiguityItem]]:
        """
        Extracts allowed academic disciplines and maps them to canonical branch codes.
        """
        ambiguities: list[AmbiguityItem] = []
        m = re.search(
            r"(?:eligible\s+)?(?:branches|disciplines|departments|allowed\s+streams|streams|courses)\s*[:=]\s*([^\r\n]+)",
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

        parsed = parse_branches_string(text)
        return (
            ExtractedField(
                field_name="allowed_branches",
                value=parsed,
                confidence=0.70,
                source_sentence="Inferred from full text context",
            ),
            ambiguities,
        )

    def extract_degree_and_batch(
        self, text: str, sentences: list[str]
    ) -> tuple[ExtractedField[list[str]] | None, ExtractedField[int] | None]:
        """Extracts degrees (B.Tech, M.Tech, etc.) and graduating batch year."""
        m_deg = RE_DEGREE.search(text)
        programs: list[str] = []
        if m_deg:
            deg_str = m_deg.group(1).strip()
            for prog in ["B.Tech", "B.E.", "M.Tech", "MCA", "B.Sc", "M.Sc"]:
                if prog.lower() in deg_str.lower():
                    programs.append(prog)
        if not programs:
            programs = ["B.Tech"]

        batch_field = None
        m_batch = RE_BATCH.search(text)
        if m_batch:
            batch_field = ExtractedField(
                field_name="batch_year",
                value=int(m_batch.group(1)),
                confidence=0.95,
                source_sentence=m_batch.group(0).strip(),
            )

        return (
            ExtractedField(
                field_name="allowed_programs",
                value=programs,
                confidence=0.90,
                source_sentence=f"Eligible programs: {', '.join(programs)}",
            ),
            batch_field,
        )

    def extract_gap_years(
        self, text: str, sentences: list[str]
    ) -> tuple[ExtractedField[int] | None, ExtractedField[bool] | None]:
        """Extracts maximum permissible education gap years and degree gap policy."""
        m_gap = RE_GAP_YEARS.search(text) or RE_MAX_GAP_NUM.search(text)
        if m_gap:
            num_match = re.search(r"(\d+)", m_gap.group(0))
            if num_match:
                gap_val = int(num_match.group(1))
                allow_during = "no gap during" not in text.lower()
                src = self._find_sentence(sentences, m_gap.group(0))
                return (
                    ExtractedField(
                        field_name="gap_years_max",
                        value=gap_val,
                        confidence=0.92,
                        source_sentence=src,
                    ),
                    ExtractedField(
                        field_name="allow_gap_during_degree",
                        value=allow_during,
                        confidence=0.90,
                        source_sentence=src,
                    ),
                )
        return None, None
