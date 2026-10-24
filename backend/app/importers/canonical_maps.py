"""
Canonical maps and alias definitions for Placement Engine Importers.
"""

# Canonical Branch Mapping (Lowercase normalized alias -> Canonical Name)
CANONICAL_BRANCHES: dict[str, str] = {
    # Computer Science
    "cse": "Computer Science and Engineering",
    "cs": "Computer Science and Engineering",
    "computer science": "Computer Science and Engineering",
    "computer science and engineering": "Computer Science and Engineering",
    "computer science & engineering": "Computer Science and Engineering",
    "comp sci": "Computer Science and Engineering",
    "b.tech cse": "Computer Science and Engineering",
    "b.tech - cse": "Computer Science and Engineering",

    # Information Technology
    "it": "Information Technology",
    "infotech": "Information Technology",
    "information technology": "Information Technology",
    "info tech": "Information Technology",
    "b.tech it": "Information Technology",

    # Electronics & Communication
    "ece": "Electronics and Communication Engineering",
    "electronics": "Electronics and Communication Engineering",
    "electronics & communication": "Electronics and Communication Engineering",
    "electronics and communication": "Electronics and Communication Engineering",
    "electronics & communication engineering": "Electronics and Communication Engineering",
    "electronics and communication engineering": "Electronics and Communication Engineering",
    "enc": "Electronics and Communication Engineering",

    # Electrical & Electronics
    "eee": "Electrical and Electronics Engineering",
    "electrical": "Electrical and Electronics Engineering",
    "electrical & electronics": "Electrical and Electronics Engineering",
    "electrical and electronics": "Electrical and Electronics Engineering",
    "electrical and electronics engineering": "Electrical and Electronics Engineering",

    # Mechanical
    "me": "Mechanical Engineering",
    "mech": "Mechanical Engineering",
    "mechanical": "Mechanical Engineering",
    "mechanical engineering": "Mechanical Engineering",
    "mechanical engg": "Mechanical Engineering",

    # Civil
    "ce": "Civil Engineering",
    "civil": "Civil Engineering",
    "civil engineering": "Civil Engineering",

    # Chemical
    "che": "Chemical Engineering",
    "chem": "Chemical Engineering",
    "chemical": "Chemical Engineering",
    "chemical engineering": "Chemical Engineering",

    # Biotechnology
    "bt": "Biotechnology",
    "biotech": "Biotechnology",
    "bio-technology": "Biotechnology",
    "biotechnology": "Biotechnology",

    # Data Science & AI
    "ds": "Data Science",
    "data science": "Data Science",
    "cse-ds": "Data Science",
    "cse (data science)": "Data Science",
    "ai": "Artificial Intelligence & Machine Learning",
    "aiml": "Artificial Intelligence & Machine Learning",
    "ai & ml": "Artificial Intelligence & Machine Learning",
}

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
