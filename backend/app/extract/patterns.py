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
    "info tech": "IT",
    "electronics & comm": "ECE",
    "electronics and comm": "ECE",
    "comm": "ECE",
    "electronics": "ECE",
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
    (re.compile(r"\belectronics\s*(?:and|&)\s*comm(?:unication)?(?:\s+engineering)?\b", re.IGNORECASE), "ECE"),
    (re.compile(r"\belectronics\s+(?:and|&)\s+communication(?:\s+engineering)?\b", re.IGNORECASE), "ECE"),
    (re.compile(r"\binfo(?:rmation)?\s+tech(?:nology)?\b", re.IGNORECASE), "IT"),
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

    # Check for explicit parenthetical list e.g. "(CSE, IT, ECE)"
    m_paren = re.search(r"\(([^)]+)\)", branch_str)
    if m_paren:
        inside = m_paren.group(1).strip()
        if any(k in inside.upper() for k in ("CSE", "ECE", "EEE", "MECH", "IT", "CIVIL", "CHEM")):
            # Parse inside explicitly
            inside_tokens = re.split(r"[,/|]|(?:\s+\band\b\s+)|(?:\s*&\s*)", inside)
            res = [normalize_branch_token(t.strip()) for t in inside_tokens if t.strip()]
            res = [r for r in res if r]
            if res:
                return res

    if "circuit branches" in clean_lower or "all circuit" in clean_lower:
        return list(CIRCUIT_BRANCHES)

    if "cs-allied" in clean_lower or "cs allied" in clean_lower or "all cs" in clean_lower:
        return list(CS_ALLIED_BRANCHES)

    if any(k in clean_lower for k in ("all branches", "any branch", "all disciplines", "open to all branches", "open to all disciplines", "all engineering disciplines")):
        return ["All Branches"]

    # Protect composite phrases and protect 'AI & ML' from splitting on '&'
    normalized_text = branch_str
    # Replace AI & ML variants with safe non-splitting token
    normalized_text = re.sub(r"\bai\s*(?:and|&)\s*ml\b", "__AIML_TOKEN__", normalized_text, flags=re.IGNORECASE)
    normalized_text = re.sub(r"\bartificial\s+intelligence(?:\s*(?:and|&)\s*machine\s+learning)?\b", "__AIML_TOKEN__", normalized_text, flags=re.IGNORECASE)

    for pattern, canonical in COMPOSITE_BRANCH_PHRASES:
        normalized_text = pattern.sub(canonical, normalized_text)

    # Split by comma, slash, vertical bar, whitespace if no punctuation, or standalone 'and' / '&'
    if not re.search(r"[,/|]", normalized_text) and " and " not in normalized_text and " & " not in normalized_text:
        # Check if space-separated branch codes e.g. 'CSE IT ECE EEE'
        raw_tokens = re.split(r"[,/|]|(?:\s+\band\b\s+)|(?:\s*&\s*)|\s+", normalized_text)
    else:
        raw_tokens = re.split(r"[,/|]|(?:\s+\band\b\s+)|(?:\s*&\s*)", normalized_text)

    result: list[str] = []
    # Expand tokens that contain multiple concatenated acronyms e.g. 'CSE IT' or 'ECE EEE'
    expanded_tokens = []
    for token in raw_tokens:
        sub_words = token.strip().split()
        if len(sub_words) > 1 and all(w.upper() in ("CSE", "CS", "IT", "ECE", "EEE", "MECH", "CIVIL", "CHEM", "BT") for w in sub_words):
            expanded_tokens.extend(sub_words)
        else:
            expanded_tokens.append(token)

    for token in expanded_tokens:
        tok_clean = token.strip()
        if not tok_clean:
            continue
        if tok_clean == "__AIML_TOKEN__":
            tok_clean = "AI & ML"
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
RE_PERCENT_BEFORE_TENTH_AND_TWELFTH = re.compile(
    r"(?:minimum\s+|min\s+|at\s+least\s+)?(\d+(?:\.\d+)?)\s*%\s*(?:in|aggregate\s+in|across|in\s+both)?\s*(?:10th|x|class\s+10|ssc)\s*(?:&|and|,)\s*(?:12th|xii|class\s+12|hsc|intermediate)",
    re.IGNORECASE,
)
RE_PERCENT_BEFORE_TENTH = re.compile(
    r"(?:minimum\s+|min\s+|at\s+least\s+)?(\d+(?:\.\d+)?)\s*%\s*(?:in|for)?\s*(?:10th|x|class\s+10|ssc)",
    re.IGNORECASE,
)
RE_PERCENT_BEFORE_TWELFTH = re.compile(
    r"(?:minimum\s+|min\s+|at\s+least\s+)?(\d+(?:\.\d+)?)\s*%\s*(?:in|for)?\s*(?:12th|xii|class\s+12|hsc|intermediate)",
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
RE_CTC_RANGE = re.compile(
    r"(?:inr|rs\.?|₹)?\s*(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*(?:lpa|lakhs?(?:\s+per\s+annum)?|lac)",
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
RE_STIPEND_MONTHLY = re.compile(
    r"(?:stipend|internship\s+stipend)[ \t]*[:=]?[ \t]*(?:inr|rs\.?|₹)?\s*(\d{1,2}(?:,\d{2})*,\d{3}|\d{4,6})\s*(?:\/|\s*per\s*)?(?:month|pm|mo)?",
    re.IGNORECASE,
)
RE_DRIVE_TIME = re.compile(
    r"(?:drive\s+time|interview\s+time|reporting\s+time|time)\s*[:=]\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm)(?:\s*(?:to|-)\s*\d{1,2}(?::\d{2})?\s*(?:am|pm))?)",
    re.IGNORECASE,
)
RE_CGPA_RANGE = re.compile(
    r"(?:cgpa|gpa|pointer)\s*(?:between|range)?\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)

# Company, Date, Mode, Role, Location
RE_COMPANY = re.compile(
    r"^[ \t]*(?:[-*•]|\d+\.|\*\*)*[ \t]*(?:company(?:\s+name)?|client|organization|employer|recruiter|corporate)\*?[ \t]*[:=][ \t]*([^\r\n]+)",
    re.IGNORECASE | re.MULTILINE,
)
RE_ROLE = re.compile(
    r"(?:^[ \t]*(?:[-*•]|\d+\.|\*\*)*[ \t]*)?(?:job\s+role|role|position|profile|designation|job\s+title|title)\*?[ \t]*[:=\-][ \t]*([^\r\n]+)",
    re.IGNORECASE | re.MULTILINE,
)
RE_ROLE_CONTEXTUAL = re.compile(
    r"(?:hiring|recruiting|inviting\s+applications\s+for|role\s+of|profile\s+of|position\s+of)\s+([A-Za-z0-9&/\s\-]{3,40}?)(?:\s+(?:interns?|roles?|positions?|engineers?|profile|freshers|for|at|\.|\n))",
    re.IGNORECASE,
)
COMMON_PLACEMENT_ROLES = [
    "Software Development Engineer",
    "Software Engineer",
    "Associate Software Engineer",
    "Graduate Engineer Trainee",
    "Associate Consultant",
    "Systems Engineer",
    "Technology Analyst",
    "Member Technical Staff",
    "Full Stack Developer",
    "Frontend Developer",
    "Backend Developer",
    "Data Analyst",
    "Data Scientist",
    "Machine Learning Engineer",
    "DevOps Engineer",
    "Cloud Engineer",
    "QA Engineer",
    "Site Reliability Engineer",
    "Analyst",
    "Consultant",
]

RE_LOCATION = re.compile(
    r"(?:^[ \t]*(?:[-*•]|\d+\.|\*\*)*[ \t]*)?(?:job\s+location|location|posting\s+location|work\s+location|venue|base\s+location)\*?[ \t]*[:=\-][ \t]*([^\r\n]+)",
    re.IGNORECASE | re.MULTILINE,
)
COMMON_LOCATIONS = [
    "Bengaluru", "Bangalore", "Hyderabad", "Pune", "Gurgaon", "Gurugram",
    "Noida", "Mumbai", "Chennai", "Delhi", "Delhi NCR", "Kolkata", "Ahmedabad",
    "Pan India", "Work from Home", "Remote", "Hybrid",
]

RE_SUBJECT_COMPANY = re.compile(
    r"Subject:\s*(?:Campus\s+Recruitment\s+(?:Announcement|Drive):\s*)?([^(\n]+?)(?:\s*\([^)]*\))?$",
    re.IGNORECASE | re.MULTILINE,
)
RE_DRIVE_DATE = re.compile(
    r"(?:^[ \t]*(?:[-*•]|\d+\.|\*\*)*[ \t]*)?(?:drive\s+date|date\s+of\s+placement\s+drive|date\s+of\s+drive|interview\s+date|placement\s+date|drive\s+scheduled\s+date|drive\s+schedule|date)\*?[ \t]*[:=][ \t]*([^\r\n,;]+)",
    re.IGNORECASE | re.MULTILINE,
)
RE_DRIVE_MODE = re.compile(
    r"(?:^[ \t]*(?:[-*•]|\d+\.|\*\*)*[ \t]*)?(?:mode(?:\s+of\s+drive)?|drive\s+mode)\*?[ \t]*[:=][ \t]*([^\r\n]+)",
    re.IGNORECASE | re.MULTILINE,
)

# Degree & Batch
RE_DEGREE = re.compile(
    r"(?:^[ \t]*(?:[-*•]|\d+\.|\*\*)*[ \t]*)?(?:degree|program|course|qualification)\*?[ \t]*[:=][ \t]*([^\r\n]+)",
    re.IGNORECASE | re.MULTILINE,
)
RE_BATCH = re.compile(
    r"(?:batch\s+of\s+|batch\s*[:=]?\s*|graduating\s+in\s+)(\d{4})",
    re.IGNORECASE,
)

# Selection Process & Rounds
RE_ROUND_LINE = re.compile(
    r"^[ \t]*(?:[-*\u2022]|\*\*)*[ \t]*(?:Round|Phase|Stage)\s*(\d+|[IVXLCDM]+)[ \t]*[:\-][ \t]*([^\r\n]+)",
    re.IGNORECASE | re.MULTILINE,
)
RE_DURATION_MINS = re.compile(
    r"(\d+)\s*(?:mins|min|minutes|hr|hours)",
    re.IGNORECASE,
)

def roman_to_int(roman: str) -> int:
    roman_map = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    try:
        val = 0
        prev = 0
        for ch in reversed(roman.upper()):
            curr = roman_map.get(ch, 0)
            if curr < prev:
                val -= curr
            else:
                val += curr
            prev = curr
        return val if val > 0 else 1
    except Exception:
        return 1

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
    clean_verbal = re.sub(r"(st|nd|rd|th)", "", clean).replace(",", " ").strip()
    clean_verbal = re.sub(r"\s+", " ", clean_verbal)
    for fmt in (
        "%d %b %Y", "%d %B %Y",
        "%d-%b-%Y", "%d-%B-%Y",
        "%d/%m/%Y", "%d-%m-%Y",
        "%Y/%m/%d", "%Y-%m-%d",
        "%B %d %Y", "%b %d %Y",
        "%m/%d/%Y", "%m-%d-%Y",
    ):
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
