"""
Canonical maps and alias definitions for Placement Engine Importers.
"""

from __future__ import annotations

import json
import re
from typing import Any

# Canonical Branch Mapping (Lowercase normalized alias -> Canonical Name)
CANONICAL_BRANCHES: dict[str, str] = {
    # Computer Science
    "cse": "Computer Science and Engineering",
    "cs": "Computer Science and Engineering",
    "c s e": "Computer Science and Engineering",
    "c s": "Computer Science and Engineering",
    "computer science": "Computer Science and Engineering",
    "computer science and engineering": "Computer Science and Engineering",
    "computer science & engineering": "Computer Science and Engineering",
    "comp sci": "Computer Science and Engineering",
    "comp sci and engg": "Computer Science and Engineering",
    "comp sci & engg": "Computer Science and Engineering",
    "comp engg": "Computer Science and Engineering",
    "computer engineering": "Computer Science and Engineering",
    "b tech cse": "Computer Science and Engineering",
    "b tech - cse": "Computer Science and Engineering",
    "btech cse": "Computer Science and Engineering",
    "b tech cs": "Computer Science and Engineering",
    "btech cs": "Computer Science and Engineering",
    "be cse": "Computer Science and Engineering",
    "b e cse": "Computer Science and Engineering",

    # Information Technology
    "it": "Information Technology",
    "i t": "Information Technology",
    "infotech": "Information Technology",
    "information technology": "Information Technology",
    "info tech": "Information Technology",
    "info-tech": "Information Technology",
    "b tech it": "Information Technology",
    "btech it": "Information Technology",
    "be it": "Information Technology",
    "b e it": "Information Technology",

    # Electronics & Communication
    "ece": "Electronics and Communication Engineering",
    "e c e": "Electronics and Communication Engineering",
    "ec": "Electronics and Communication Engineering",
    "e c": "Electronics and Communication Engineering",
    "electronics": "Electronics and Communication Engineering",
    "electronics & communication": "Electronics and Communication Engineering",
    "electronics and communication": "Electronics and Communication Engineering",
    "electronics & communication engineering": "Electronics and Communication Engineering",
    "electronics and communication engineering": "Electronics and Communication Engineering",
    "electronics & telecommunication": "Electronics and Communication Engineering",
    "electronics and telecommunication": "Electronics and Communication Engineering",
    "electronics & telecommunication engineering": "Electronics and Communication Engineering",
    "electronics and telecommunication engineering": "Electronics and Communication Engineering",
    "enc": "Electronics and Communication Engineering",
    "e and c": "Electronics and Communication Engineering",
    "e&c": "Electronics and Communication Engineering",
    "entc": "Electronics and Communication Engineering",
    "etc": "Electronics and Communication Engineering",
    "e&tc": "Electronics and Communication Engineering",
    "b tech ece": "Electronics and Communication Engineering",
    "btech ece": "Electronics and Communication Engineering",
    "be ece": "Electronics and Communication Engineering",
    "b e ece": "Electronics and Communication Engineering",

    # Electrical & Electronics
    "eee": "Electrical and Electronics Engineering",
    "e e e": "Electrical and Electronics Engineering",
    "ee": "Electrical and Electronics Engineering",
    "e e": "Electrical and Electronics Engineering",
    "electrical": "Electrical and Electronics Engineering",
    "electrical engineering": "Electrical and Electronics Engineering",
    "electrical & electronics": "Electrical and Electronics Engineering",
    "electrical and electronics": "Electrical and Electronics Engineering",
    "electrical & electronics engineering": "Electrical and Electronics Engineering",
    "electrical and electronics engineering": "Electrical and Electronics Engineering",
    "b tech eee": "Electrical and Electronics Engineering",
    "btech eee": "Electrical and Electronics Engineering",
    "be eee": "Electrical and Electronics Engineering",
    "b e eee": "Electrical and Electronics Engineering",

    # Mechanical
    "me": "Mechanical Engineering",
    "m e": "Mechanical Engineering",
    "mech": "Mechanical Engineering",
    "mechanical": "Mechanical Engineering",
    "mechanical engineering": "Mechanical Engineering",
    "mechanical engg": "Mechanical Engineering",
    "b tech me": "Mechanical Engineering",
    "btech me": "Mechanical Engineering",
    "b tech mech": "Mechanical Engineering",
    "btech mech": "Mechanical Engineering",
    "be me": "Mechanical Engineering",
    "b e me": "Mechanical Engineering",

    # Civil
    "ce": "Civil Engineering",
    "c e": "Civil Engineering",
    "civ": "Civil Engineering",
    "civil": "Civil Engineering",
    "civil engineering": "Civil Engineering",
    "civil engg": "Civil Engineering",
    "b tech ce": "Civil Engineering",
    "btech ce": "Civil Engineering",
    "be ce": "Civil Engineering",
    "b e ce": "Civil Engineering",

    # Chemical
    "che": "Chemical Engineering",
    "c h e": "Chemical Engineering",
    "chem": "Chemical Engineering",
    "chemical": "Chemical Engineering",
    "chemical engineering": "Chemical Engineering",
    "chemical engg": "Chemical Engineering",
    "b tech che": "Chemical Engineering",
    "btech che": "Chemical Engineering",
    "be che": "Chemical Engineering",
    "b e che": "Chemical Engineering",

    # Biotechnology
    "bt": "Biotechnology",
    "b t": "Biotechnology",
    "biotech": "Biotechnology",
    "bio-technology": "Biotechnology",
    "bio technology": "Biotechnology",
    "biotechnology engineering": "Biotechnology",
    "b tech bt": "Biotechnology",
    "btech bt": "Biotechnology",
    "be bt": "Biotechnology",
    "b e bt": "Biotechnology",

    # Data Science & AI
    "ds": "Data Science",
    "d s": "Data Science",
    "data science": "Data Science",
    "cse-ds": "Data Science",
    "cse ds": "Data Science",
    "cse (data science)": "Data Science",
    "ai": "Artificial Intelligence & Machine Learning",
    "a i": "Artificial Intelligence & Machine Learning",
    "aiml": "Artificial Intelligence & Machine Learning",
    "ai & ml": "Artificial Intelligence & Machine Learning",
    "ai and ml": "Artificial Intelligence & Machine Learning",
    "artificial intelligence": "Artificial Intelligence & Machine Learning",
    "artificial intelligence & machine learning": "Artificial Intelligence & Machine Learning",
    "artificial intelligence and machine learning": "Artificial Intelligence & Machine Learning",
    "b tech ds": "Data Science",
    "btech ds": "Data Science",
    "b tech aiml": "Artificial Intelligence & Machine Learning",
    "btech aiml": "Artificial Intelligence & Machine Learning",
}

# Canonical Full Name -> Short Industry Code
BRANCH_CODES: dict[str, str] = {
    "Computer Science and Engineering": "CSE",
    "Information Technology": "IT",
    "Electronics and Communication Engineering": "ECE",
    "Electrical and Electronics Engineering": "EEE",
    "Mechanical Engineering": "ME",
    "Civil Engineering": "CE",
    "Chemical Engineering": "CHE",
    "Biotechnology": "BT",
    "Data Science": "DS",
    "Artificial Intelligence & Machine Learning": "AIML",
}


def normalize_branch_key(text: str | None) -> str:
    """Normalizes branch text for robust alias lookup by removing punctuation and excess whitespace."""
    if not text:
        return ""
    t = text.lower().strip()
    t = t.replace(".", " ").replace("&", " and ").replace("/", " ").replace("-", " ")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def get_canonical_branch(val: str | None) -> str:
    """Resolves any branch alias or abbreviation to its canonical full name."""
    if not val:
        return ""
    k = normalize_branch_key(val)
    if k in CANONICAL_BRANCHES:
        return CANONICAL_BRANCHES[k]

    # Check without common degree prefixes (b.tech, btech, be, etc.)
    k_no_prefix = re.sub(r"^(b\s*tech|btech|b\s*e|be)\s*", "", k).strip()
    if k_no_prefix in CANONICAL_BRANCHES:
        return CANONICAL_BRANCHES[k_no_prefix]

    # Return trimmed original if unmapped
    return val.strip()


def get_branch_code(val: str | None) -> str:
    """Returns the standard short industry code (e.g. CSE, IT, ECE) for a given branch."""
    if not val:
        return ""
    val_clean = str(val).strip()
    upper = val_clean.upper()
    if upper in {"CSE", "IT", "ECE", "EEE", "ME", "CE", "CHE", "BT", "DS"}:
        return upper
    canonical = get_canonical_branch(val_clean)
    if canonical in BRANCH_CODES:
        return BRANCH_CODES[canonical]

    # Fallback to uppercase short key if already an abbreviation
    norm = normalize_branch_key(val).replace(" ", "").upper()
    if len(norm) <= 5:
        return norm
    return val.strip()


def parse_allowed_branches(allowed: Any) -> list[str]:
    """Robustly parses allowed branches from lists, JSON strings, or comma-separated text."""
    if not allowed:
        return []

    items: list[str] = []
    if isinstance(allowed, str):
        s = allowed.strip()
        if s.startswith("[") and s.endswith("]"):
            try:
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    return parse_allowed_branches(parsed)
            except Exception:
                pass
        for part in s.split(","):
            cleaned = part.strip().strip("\"'[]")
            if cleaned:
                items.append(cleaned)
    elif isinstance(allowed, (list, tuple, set)):
        for elem in allowed:
            if isinstance(elem, str):
                if "," in elem:
                    for sub in elem.split(","):
                        cleaned_sub = sub.strip().strip("\"'[]")
                        if cleaned_sub:
                            items.append(cleaned_sub)
                else:
                    cleaned_elem = elem.strip().strip("\"'[]")
                    if cleaned_elem:
                        items.append(cleaned_elem)
            elif elem:
                items.append(str(elem).strip())

    return items


def is_branch_allowed(student_branch: str | None, allowed_branches: Any) -> bool:
    """
    Checks if student's branch is permitted under the allowed branches specification.
    Handles exact names, canonical aliases, acronyms (CSE <-> Computer Science and Engineering),
    wildcards ('All Branches'), and multi-variant inputs symmetrically.
    """
    parsed = parse_allowed_branches(allowed_branches)
    if not parsed:
        return True  # Open to all if not specified

    if not student_branch or not str(student_branch).strip():
        return False

    wildcards = {
        "all",
        "all branches",
        "any",
        "all branch",
        "open to all",
        "all engineering branches",
        "all disciplines",
        "all eligible branches",
    }
    if any(b.lower().strip() in wildcards for b in parsed):
        return True

    std_raw = str(student_branch).strip()
    std_lower = std_raw.lower()
    std_canon = get_canonical_branch(std_raw)
    std_code = get_branch_code(std_raw)

    for item in parsed:
        item_raw = str(item).strip()
        item_lower = item_raw.lower()

        # 1. Exact string match (case-insensitive)
        if std_lower == item_lower:
            return True

        # 2. Canonical full name equality
        item_canon = get_canonical_branch(item_raw)
        if std_canon and item_canon and std_canon.lower() == item_canon.lower():
            return True

        # 3. Short acronym equality (e.g. CSE == CSE)
        item_code = get_branch_code(item_raw)
        if std_code and item_code and std_code.upper() == item_code.upper():
            return True

        # 4. Cross acronym to canonical equality
        if std_code and item_canon and std_canon.lower() == item_canon.lower():
            return True
        if item_code and std_canon and item_canon.lower() == std_canon.lower():
            return True

        # 5. Descriptive substring containment (len >= 4 to avoid 2-letter false positives)
        if len(std_lower) >= 4 and len(item_lower) >= 4:
            if std_lower in item_lower or item_lower in std_lower:
                return True

    return False


# Column Name Auto-Guessing Rules
HEADER_PATTERNS: dict[str, list[str]] = {
    "roll_no": [
        "roll_no", "roll no", "rollno", "roll_number", "registration_no",
        "reg_no", "reg no", "usn", "enrollment_no", "student_id", "urn"
    ],
    "name": [
        "name", "student_name", "full_name", "candidate_name", "student name",
        "candidate name", "fullname"
    ],
    "email": [
        "email", "email_id", "mail", "student_email", "email address",
        "institute_email", "college_email"
    ],
    "branch": [
        "branch", "department", "stream", "dept", "discipline", "branch_name",
        "course_branch"
    ],
    "program": [
        "program", "degree", "course", "programme"
    ],
    "cgpa": [
        "cgpa", "btech_cgpa", "gpa", "b.tech_cgpa", "aggregate_cgpa",
        "degree_cgpa", "current_cgpa", "btech cgpa"
    ],
    "tenth_percentage": [
        "tenth_percentage", "10th", "tenth", "ssc", "matriculation",
        "10th_percentage", "class_10", "10th%", "10th %", "ssc %", "10th percentage"
    ],
    "twelfth_percentage": [
        "twelfth_percentage", "12th", "twelfth", "hsc", "intermediate",
        "12th_percentage", "class_12", "12th%", "12th %", "hsc %", "12th percentage"
    ],
    "diploma_percentage": [
        "diploma_percentage", "diploma", "polytechnic", "diploma%", "diploma %"
    ],
    "date_of_birth": [
        "date_of_birth", "dob", "birth_date", "birthdate", "d.o.b", "d.o.b."
    ],
    "gender": ["gender", "sex"],
    "category": ["category", "caste_category", "social_category"],
    "backlogs_active": ["active_backlogs", "current_backlogs", "standing_arrears", "active backlogs"],
    "backlogs_history": ["total_backlogs", "history_backlogs", "cleared_backlogs", "history of backlogs"],
    "backlog_details": ["backlog_details", "backlog_subjects", "backlog_info"],
    "existing_offers": ["existing_offers", "offers", "offer_details", "placed_company", "previous_offers"],
    "gap_years": ["gap_years", "gaps", "gap", "year_gap"],
}
