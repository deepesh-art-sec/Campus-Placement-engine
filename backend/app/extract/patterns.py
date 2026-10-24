"""
Regex patterns, dictionaries, synonyms, and parsing helpers for deterministic requirement extraction.
"""

from __future__ import annotations

import datetime
import re

from backend.app.domain.models import DriveMode, RoundType

# Canonical branch dictionary and equivalence mapping
BRANCH_ALIASES: dict[str, str] = {
    "cse": "CSE",
    "cs": "CSE",
    "computer science": "CSE",
    "computer science and engineering": "CSE",
    "computer science & engineering": "CSE",
    "it": "IT",
    "information technology": "IT",
    "data science": "Data Science",
    "ds": "Data Science",
    "cs - data science": "Data Science",
    "cse (data science)": "Data Science",
    "ai & ml": "AI & ML",
    "aiml": "AI & ML",
    "artificial intelligence": "AI & ML",
    "artificial intelligence and machine learning": "AI & ML",
    "ece": "ECE",
    "electronics and communication": "ECE",
    "electronics and communication engineering": "ECE",
    "electronics & communication": "ECE",
    "eee": "EEE",
    "electrical and electronics": "EEE",
    "electrical and electronics engineering": "EEE",
    "electrical & electronics": "EEE",
    "electrical": "EEE",
    "mechanical": "Mechanical Engineering",
    "mechanical engineering": "Mechanical Engineering",
    "mech": "Mechanical Engineering",
    "civil": "Civil Engineering",
    "civil engineering": "Civil Engineering",
    "chemical": "Chemical Engineering",
    "chemical engineering": "Chemical Engineering",
    "chem": "Chemical Engineering",
    "biotechnology": "Biotechnology",
    "biotech": "Biotechnology",
    "bio tech": "Biotechnology",
}

CIRCUIT_BRANCHES = ["CSE", "IT", "ECE", "EEE"]
CS_ALLIED_BRANCHES = ["CSE", "IT", "Data Science", "AI & ML"]

COMPOSITE_BRANCH_PHRASES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bcomputer\s+science\s+(?:and|&)\s+engineering\b", re.IGNORECASE), "CSE"),
    (re.compile(r"\belectronics\s+(?:and|&)\s+communication(?:\s+engineering)?\b", re.IGNORECASE), "ECE"),
    (re.compile(r"\belectrical\s+(?:and|&)\s+electronics(?:\s+engineering)?\b", re.IGNORECASE), "EEE"),
    (re.compile(r"\bdata\s+science\b", re.IGNORECASE), "Data Science"),
    (re.compile(r"\bartificial\s+intelligence(?:\s+(?:and|&)\s+machine\s+learning)?\b", re.IGNORECASE), "AI & ML"),
    (re.compile(r"\bai\s+(?:and|&)\s+ml\b", re.IGNORECASE), "AI & ML"),
    (re.compile(r"\bmechanical\s+engineering\b", re.IGNORECASE), "Mechanical Engineering"),
    (re.compile(r"\bcivil\s+engineering\b", re.IGNORECASE), "Civil Engineering"),
    (re.compile(r"\bchemical\s+engineering\b", re.IGNORECASE), "Chemical Engineering"),
]


def normalize_branch_token(token: str) -> str:
    """Normalizes an individual branch token to its canonical name."""
    clean = token.strip().lower().rstrip(".,;")
    # Strip common prefixes like 'b.tech -', 'be -' and trailing suffixes like 'only'
    clean = re.sub(r"^(?:b\.?tech|b\.?e\.?|m\.?tech)\s*[-:]?\s*", "", clean).strip()
    clean = re.sub(r"\b(?:only|students|candidates)\b", "", clean).strip()
    return BRANCH_ALIASES.get(clean, token.strip())


def parse_branches_string(branch_str: str) -> list[str]:
    """Parses a raw branch specification into canonical branch list."""
    clean_lower = branch_str.strip().lower()

    if any(k in clean_lower for k in ("all branches", "any branch", "all disciplines", "open to all")):
        return ["All Branches"]

    if "circuit branches" in clean_lower or "all circuit" in clean_lower:
        return list(CIRCUIT_BRANCHES)

    if "cs-allied" in clean_lower or "cs allied" in clean_lower or "all cs" in clean_lower:
        return list(CS_ALLIED_BRANCHES)

    # Protect composite phrases before splitting
    normalized_text = branch_str
    for pattern, canonical in COMPOSITE_BRANCH_PHRASES:
        normalized_text = pattern.sub(canonical, normalized_text)

    # Split by comma, slash, vertical bar, or standalone 'and' / '&'
    raw_tokens = re.split(r"[,/|]|(?:\s+\band\b\s+)|(?:\s*&\s*)", normalized_text)
    result: list[str] = []
    for token in raw_tokens:
        tok_clean = token.strip()
        if not tok_clean:
            continue
        norm = normalize_branch_token(tok_clean)
        if norm and norm not in result:
            result.append(norm)

    return result if result else ["All Branches"]


# ---------------------------------------------------------
# Regex Pattern Definitions
# ---------------------------------------------------------

# CGPA Patterns
RE_CGPA_EXPLICIT = re.compile(
    r"(?:cgpa(?:\s+cut-?off)?|minimum\s+cgpa)(?:\s+required)?\s*[:=]?\s*(?:of\s+|is\s+)?(?:>=|at\s+least|min)?\s*(\d+(?:\.\d+)?)\s*(?:or\s+above)?(?:\s*(?:in|for)\s*[A-Za-z.]+)?(?:\s*/\s*(\d+(?:\.\d+)?))?",
    re.IGNORECASE,
)
RE_CGPA_INVERTED = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:or\s+above)?\s*(?:cgpa|in\s+b\.?tech)",
    re.IGNORECASE,
)
RE_CGPA_NO_CUTOFF = re.compile(
    r"no\s+(?:cgpa\s+cut-?off|minimum\s+cgpa|cgpa\s+criteria)",
    re.IGNORECASE,
)

# Percentage Patterns
RE_TENTH_AND_TWELFTH = re.compile(
    r"(?:10th\s*(?:&|and)\s*12th|x\s*(?:&|and)\s*xii)\s*(?:percentage)?\s*[:=]?\s*(?:minimum\s+)?(\d+(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)
RE_TENTH_EXPLICIT = re.compile(
    r"(?:10th|class\s+10|ssc|matriculation)\s*(?:percentage)?\s*[:=]?\s*(?:minimum\s+)?(\d+(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)
RE_TWELFTH_EXPLICIT = re.compile(
    r"(?:12th|class\s+12|hsc|intermediate)\s*(?:percentage)?\s*[:=]?\s*(?:minimum\s+)?(\d+(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)
RE_THROUGHOUT_PERCENTAGE = re.compile(
    r"(?:minimum\s+)?(\d+(?:\.\d+)?)\s*%\s*(?:throughout|in\s+academics\s+throughout|aggregate\s+throughout)",
    re.IGNORECASE,
)

# Backlogs Patterns
RE_BACKLOG_LINE = re.compile(
    r"(?:backlog\s+policy|backlogs?|standing\s+arrears?|arrears?)[ \t]*[:=]?[ \t]*([^\r\n]+)",
    re.IGNORECASE,
)

# Gap Years Patterns
RE_GAP_YEARS = re.compile(
    r"(?:education\s+gap|gap\s+years?|gap\s+limit)[ \t]*[:=]?[ \t]*([^\r\n]+)",
    re.IGNORECASE,
)
RE_MAX_GAP_NUM = re.compile(
    r"(?:maximum|max|up\s+to)?\s*(\d+)\s*(?:year[s]?|yr[s]?)\s+(?:education\s+)?gap",
    re.IGNORECASE,
)

# CTC / Package Patterns
RE_CTC_LINE = re.compile(
    r"(?:ctc(?:\s+offered)?|package|salary|stipend)[ \t]*[:=]?[ \t]*([^\r\n]+)",
    re.IGNORECASE,
)
RE_CTC_LPA = re.compile(
    r"(?:inr|rs\.?|₹)?\s*(\d+(?:\.\d+)?)\s*(?:lpa|lakhs?(?:\s+per\s+annum)?|lac)",
    re.IGNORECASE,
)
RE_CTC_NUMERIC_INR = re.compile(
    r"(?:inr|rs\.?|₹)\s*(\d{1,2}(?:,\d{2})*,\d{3})(?:\s*(?:per\s+annum|\/-\s*ctc))?",
    re.IGNORECASE,
)

# Company, Date, Mode
RE_COMPANY = re.compile(
    r"^(?:company(?:\s+name)?|client)[ \t]*[:=][ \t]*([^\r\n]+)",
    re.IGNORECASE | re.MULTILINE,
)
RE_SUBJECT_COMPANY = re.compile(
    r"Subject:\s*(?:Campus\s+Recruitment\s+(?:Announcement|Drive):\s*)?([^(\n]+?)(?:\s*\([^)]*\))?$",
    re.IGNORECASE | re.MULTILINE,
)
RE_DRIVE_DATE = re.compile(
    r"(?:drive\s+date|date\s+of\s+drive)[ \t]*[:=][ \t]*([0-9]{4}-[0-9]{2}-[0-9]{2}|\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+\s+\d{4})",
    re.IGNORECASE,
)
RE_DRIVE_MODE = re.compile(
    r"(?:mode(?:\s+of\s+drive)?)[ \t]*[:=][ \t]*([^\r\n]+)",
    re.IGNORECASE,
)

# Degree & Batch
RE_DEGREE = re.compile(
    r"(?:degree|program|course|qualification)[ \t]*[:=][ \t]*([^\r\n]+)",
    re.IGNORECASE,
)
RE_BATCH = re.compile(
    r"(?:batch\s+of\s+|batch\s*[:=]?\s*|graduating\s+in\s+)(\d{4})",
    re.IGNORECASE,
)

# Selection Process & Rounds
RE_ROUND_LINE = re.compile(
    r"Round\s*(\d+)[ \t]*[:\-][ \t]*([^\r\n]+)",
    re.IGNORECASE,
)
RE_DURATION_MINS = re.compile(
    r"(\d+)\s*(?:mins|min|minutes)",
    re.IGNORECASE,
)

# Bond / Service Agreement
RE_BOND = re.compile(
    r"(?:service\s+agreement|bond(?:\s+period)?)[ \t]*[:=][ \t]*([^\r\n]+)",
    re.IGNORECASE,
)


def parse_date_string(date_str: str) -> datetime.date | None:
    """Parses ISO date or verbal date (e.g. '2026-11-01' or '1st Nov 2026')."""
    clean = date_str.strip()
    # Try ISO
    try:
        return datetime.date.fromisoformat(clean)
    except ValueError:
        pass

    # Try common formats
    clean_verbal = re.sub(r"(st|nd|rd|th)", "", clean)
    for fmt in ("%d %b %Y", "%d %B %Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.datetime.strptime(clean_verbal, fmt).date()
        except ValueError:
            pass

    return None


def parse_mode_string(mode_str: str) -> DriveMode:
    """Parses drive mode string into DriveMode enum."""
    clean = mode_str.strip().lower()
    if "hybrid" in clean:
        return DriveMode.HYBRID
    elif "virtual" in clean or "online" in clean or "remote" in clean:
        return DriveMode.VIRTUAL
    else:
        return DriveMode.ON_CAMPUS


def classify_round_type(round_name: str) -> RoundType:
    """Classifies round text into canonical RoundType."""
    rn = round_name.lower()
    if any(k in rn for k in ("coding", "online test", "assessment", "cognitive", "written", "aptitude")):
        return RoundType.ONLINE_TEST
    elif any(k in rn for k in ("technical", "system design", "tech interview", "coding interview")):
        return RoundType.TECHNICAL_INTERVIEW
    elif any(k in rn for k in ("hr", "leadership", "behavioral", "cultural", "managerial")):
        return RoundType.HR_INTERVIEW
    elif any(k in rn for k in ("gd", "group discussion")):
        return RoundType.GROUP_DISCUSSION
    return RoundType.TECHNICAL_INTERVIEW
