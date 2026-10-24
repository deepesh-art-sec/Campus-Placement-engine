"""
Fixture Generator for Placement Engine.
Generates:
  1. 1,800 synthetic student records across 9 branches (CSV and XLSX).
     Includes edge cases: cleared backlogs yesterday/last month, lateral entries, gaps, existing offers.
  2. 25 synthetic drive announcements in mixed formats:
     - Plain text (.txt)
     - Standard email (.eml)
     - PDF documents (.pdf)
     - Microsoft Word documents (.docx)
  3. 3 realistic college placement offer policies with documented ambiguities.
"""

from __future__ import annotations

import csv
import datetime
import json
import os
import random
from email.message import EmailMessage

import docx
import openpyxl
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Deterministic seed for reproducible generation
RANDOM_SEED = 42
random.seed(RANDOM_SEED)

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FIXTURES_DIR = os.path.join(ROOT_DIR, "fixtures")
STUDENTS_DIR = os.path.join(FIXTURES_DIR, "students")
ANNOUNCEMENTS_DIR = os.path.join(FIXTURES_DIR, "announcements")
POLICIES_DIR = os.path.join(FIXTURES_DIR, "policies")

os.makedirs(STUDENTS_DIR, exist_ok=True)
os.makedirs(ANNOUNCEMENTS_DIR, exist_ok=True)
os.makedirs(POLICIES_DIR, exist_ok=True)

BRANCHES = [
    "Computer Science and Engineering",
    "Information Technology",
    "Electronics and Communication Engineering",
    "Electrical and Electronics Engineering",
    "Mechanical Engineering",
    "Civil Engineering",
    "Chemical Engineering",
    "Biotechnology",
    "Data Science",
]

FIRST_NAMES = [
    "Aarav", "Aditi", "Akash", "Ananya", "Aniket", "Ankita", "Arjun", "Bhavna", "Chirag", "Deepak",
    "Divya", "Gaurav", "Harsh", "Isha", "Ishaan", "Kavya", "Manish", "Meera", "Mohit", "Neha",
    "Nikhil", "Pooja", "Pranav", "Priya", "Rahul", "Rhea", "Rohan", "Sakshi", "Sameer", "Sanjay",
    "Shreya", "Siddharth", "Sneha", "Tanvi", "Tarun", "Varun", "Vikram", "Yash", "Zoya", "Kunal"
]

LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Gupta", "Singh", "Kumar", "Mehta", "Shah", "Reddy", "Nair",
    "Iyer", "Rao", "Joshi", "Kulkarni", "Deshmukh", "Chopra", "Malhotra", "Bhatia", "Saxena", "Agarwal"
]


def generate_students(count: int = 1800) -> list[dict]:
    students = []
    base_roll = 20210000

    # Today's reference date: 2026-10-22
    ref_date = datetime.date(2026, 10, 22)

    for i in range(count):
        roll_no = f"BT21{i + 1:04d}"
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        name = f"{first_name} {last_name}"
        email = f"{first_name.lower()}.{last_name.lower()}{i + 1}@college.edu"
        branch = BRANCHES[i % len(BRANCHES)]

        # Realistic CGPA: Gaussian centered at 7.6, clamped between 5.2 and 9.9
        cgpa = min(9.95, max(5.2, round(random.gauss(7.6, 1.1), 2)))

        # 10th and 12th marks
        tenth = min(98.0, max(60.0, round(random.gauss(84.0, 8.0), 2)))

        # 10% lateral entry with diploma instead of 12th
        is_lateral = (i % 10 == 0)
        twelfth = None if is_lateral else min(98.0, max(55.0, round(random.gauss(80.0, 9.0), 2)))
        diploma = min(95.0, max(65.0, round(random.gauss(82.0, 6.0), 2))) if is_lateral else None

        # Age between 21 and 23
        birth_year = 2003 if not is_lateral else 2002
        birth_month = random.randint(1, 12)
        birth_day = random.randint(1, 28)
        dob = datetime.date(birth_year, birth_month, birth_day)

        # Backlog generation
        # ~70% zero backlogs, ~15% active, ~15% cleared
        backlog_status = "none"
        backlogs_active_count = 0
        backlogs_history_count = 0
        backlog_detail = ""

        if 70 <= (i % 100) < 85:
            # Active backlogs
            backlogs_active_count = random.randint(1, 2)
            backlogs_history_count = backlogs_active_count
            backlog_detail = f"Data Structures (active); Engineering Mathematics (active)" if backlogs_active_count > 1 else "Data Structures (active)"
        elif (i % 100) >= 85:
            # Cleared backlogs
            backlogs_active_count = 0
            backlogs_history_count = 1

            # KEY EDGE CASES:
            # i % 20 == 0: Cleared yesterday (1 day before reference date)
            # i % 20 == 1: Cleared last month (30 days before reference date)
            if i % 20 == 0:
                clear_date = ref_date - datetime.timedelta(days=1)
                backlog_detail = f"Engineering Mathematics (cleared {clear_date.isoformat()})"
            elif i % 20 == 1:
                clear_date = ref_date - datetime.timedelta(days=30)
                backlog_detail = f"Operating Systems (cleared {clear_date.isoformat()})"
            else:
                clear_date = ref_date - datetime.timedelta(days=random.randint(60, 300))
                backlog_detail = f"Computer Networks (cleared {clear_date.isoformat()})"

        # Gap year (10% of students have 1 gap year)
        gap_years = 1 if (i % 10 == 3) else 0

        # Existing offers
        # ~20% of students have an existing offer
        existing_offer_str = ""
        if i % 5 == 0:
            if i % 25 == 0:
                # Dream company offer
                existing_offer_str = "Microsoft: 32.0 LPA (accepted)"
            elif i % 15 == 0:
                existing_offer_str = "Infosys: 9.5 LPA (offered)"
            else:
                existing_offer_str = "TCS: 4.0 LPA (accepted)"

        # Protected demographics (stored for institutional analysis, never used in rules)
        gender = "Female" if (i % 3 == 0) else "Male"
        category = "General" if (i % 2 == 0) else ("OBC" if (i % 4 == 1) else "SC")

        students.append({
            "roll_no": roll_no,
            "name": name,
            "email": email,
            "branch": branch,
            "program": "B.Tech",
            "cgpa": cgpa,
            "tenth_percentage": tenth,
            "twelfth_percentage": twelfth if twelfth is not None else "",
            "diploma_percentage": diploma if diploma is not None else "",
            "date_of_birth": dob.isoformat(),
            "active_backlogs": backlogs_active_count,
            "history_backlogs": backlogs_history_count,
            "backlog_details": backlog_detail,
            "gap_years": gap_years,
            "existing_offers": existing_offer_str,
            "gender": gender,
            "category": category,
        })

    return students


def export_students_csv_and_xlsx(students: list[dict]) -> None:
    # CSV
    csv_path = os.path.join(STUDENTS_DIR, "synthetic_students_1800.csv")
    fieldnames = list(students[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(students)
    print(f"Exported {len(students)} synthetic students to {csv_path}")

    # XLSX
    xlsx_path = os.path.join(STUDENTS_DIR, "synthetic_students_1800.xlsx")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Student Directory"
    ws.append(fieldnames)
    for s in students:
        ws.append([s[k] for k in fieldnames])
    wb.save(xlsx_path)
    print(f"Exported {len(students)} synthetic students to {xlsx_path}")


# ---------------------------------------------------------
# Announcements Generator (25 Mixed-Format Announcements)
# ---------------------------------------------------------

COMPANIES_CONFIG = [
    {"name": "Google", "ctc": 36.0, "cgpa": 8.5, "backlogs": "Strictly 0 (No active or historical backlogs)", "branches": ["CSE", "IT", "Data Science"], "mode": "Hybrid"},
    {"name": "Microsoft", "ctc": 44.0, "cgpa": 8.0, "backlogs": "0 active backlogs", "branches": ["CSE", "IT", "ECE"], "mode": "On Campus"},
    {"name": "Amazon", "ctc": 32.0, "cgpa": 7.5, "backlogs": "No active backlogs allowed", "branches": ["CSE", "IT", "ECE", "EEE"], "mode": "On Campus"},
    {"name": "Goldman Sachs", "ctc": 28.0, "cgpa": 8.0, "backlogs": "No history of backlogs", "branches": ["All Branches"], "mode": "Hybrid"},
    {"name": "Oracle", "ctc": 19.5, "cgpa": 7.0, "backlogs": "0 active arrears at time of drive", "branches": ["CSE", "IT", "ECE"], "mode": "On Campus"},
    {"name": "Qualcomm", "ctc": 22.0, "cgpa": 7.8, "backlogs": "No active backlogs", "branches": ["ECE", "EEE", "CSE"], "mode": "On Campus"},
    {"name": "Cisco", "ctc": 17.5, "cgpa": 7.5, "backlogs": "Maximum 1 cleared backlog permitted, 0 active", "branches": ["CSE", "IT", "ECE"], "mode": "On Campus"},
    {"name": "Deloitte USI", "ctc": 9.0, "cgpa": 6.8, "backlogs": "No standing arrears", "branches": ["All Branches"], "mode": "On Campus"},
    {"name": "Tata Consultancy Services", "ctc": 7.0, "cgpa": 6.0, "backlogs": "Max 1 active backlog allowed", "branches": ["All Branches"], "mode": "On Campus"},
    {"name": "Infosys Power Programmer", "ctc": 9.5, "cgpa": 6.5, "backlogs": "0 active backlogs", "branches": ["CSE", "IT", "ECE", "Data Science"], "mode": "Virtual"},
    {"name": "Wipro Turbo", "ctc": 6.5, "cgpa": 6.0, "backlogs": "No active backlogs at time of joining", "branches": ["All Branches"], "mode": "On Campus"},
    {"name": "Accenture Advanced Tech", "ctc": 11.5, "cgpa": 7.0, "backlogs": "0 active backlogs, max 1 year education gap", "branches": ["CSE", "IT", "ECE", "EEE", "Data Science"], "mode": "On Campus"},
    {"name": "Siemens", "ctc": 12.0, "cgpa": 7.0, "backlogs": "No active backlogs", "branches": ["ECE", "EEE", "Mechanical Engineering"], "mode": "On Campus"},
    {"name": "Larsen & Toubro", "ctc": 6.5, "cgpa": 6.5, "backlogs": "Strictly no history of backlogs", "branches": ["Mechanical Engineering", "Civil Engineering", "EEE"], "mode": "On Campus"},
    {"name": "Texas Instruments", "ctc": 25.0, "cgpa": 8.0, "backlogs": "No active backlogs", "branches": ["ECE", "EEE"], "mode": "On Campus"},
    {"name": "Intel", "ctc": 21.0, "cgpa": 7.5, "backlogs": "0 active backlogs", "branches": ["ECE", "CSE", "IT"], "mode": "Hybrid"},
    {"name": "Morgan Stanley", "ctc": 26.0, "cgpa": 8.2, "backlogs": "Zero backlogs throughout", "branches": ["CSE", "IT"], "mode": "Virtual"},
    {"name": "Samsung R&D", "ctc": 16.0, "cgpa": 7.5, "backlogs": "No active backlogs", "branches": ["CSE", "IT", "ECE"], "mode": "On Campus"},
    {"name": "Tata Motors", "ctc": 8.5, "cgpa": 6.5, "backlogs": "No active backlogs, max 1 cleared", "branches": ["Mechanical Engineering", "Electrical and Electronics Engineering"], "mode": "On Campus"},
    {"name": "Reliance Industries", "ctc": 7.5, "cgpa": 6.8, "backlogs": "No active backlogs", "branches": ["Chemical Engineering", "Mechanical Engineering", "Civil Engineering"], "mode": "On Campus"},
    {"name": "ITC Limited", "ctc": 11.0, "cgpa": 7.2, "backlogs": "No history of backlogs", "branches": ["Mechanical Engineering", "Chemical Engineering"], "mode": "On Campus"},
    {"name": "Biocon", "ctc": 7.0, "cgpa": 6.5, "backlogs": "0 active backlogs", "branches": ["Biotechnology", "Chemical Engineering"], "mode": "On Campus"},
    {"name": "ZS Associates", "ctc": 13.5, "cgpa": 7.0, "backlogs": "No standing backlogs", "branches": ["All Branches"], "mode": "Virtual"},
    {"name": "Barclays", "ctc": 14.0, "cgpa": 7.5, "backlogs": "No active arrears", "branches": ["CSE", "IT", "Data Science", "ECE"], "mode": "Hybrid"},
    {"name": "Atlassian", "ctc": 52.0, "cgpa": 8.5, "backlogs": "0 active backlogs, strictly clean academic record", "branches": ["CSE", "IT", "Data Science"], "mode": "Virtual"},
]


def generate_announcements() -> None:
    for idx, c in enumerate(COMPANIES_CONFIG):
        drive_num = idx + 1
        drive_date = (datetime.date(2026, 11, 1) + datetime.timedelta(days=idx * 3)).isoformat()
        branches_str = ", ".join(c["branches"])

        content_text = f"""CAMPUS RECRUITMENT DRIVE ANNOUNCEMENT #{drive_num:02d}
Company: {c['name']}
Drive Date: {drive_date}
Mode of Drive: {c['mode']}
CTC Offered: {c['ctc']} LPA

ELIGIBILITY CRITERIA:
1. Degree: B.Tech / B.E. (Batch of 2026)
2. Minimum CGPA Cut-off: {c['cgpa']} or above in B.Tech
3. 10th & 12th Percentage: Minimum 60.0% aggregate
4. Backlog Policy: {c['backlogs']}
5. Allowed Disciplines / Branches: {branches_str}
6. Education Gap: Maximum 1 year education gap permissible between 12th and degree. No gaps during engineering.

SELECTION PROCESS:
Round 1: Online Technical Assessment (Cognitive & Coding) - 90 mins
Round 2: Technical Interview Panel 1 - 45 mins
Round 3: Technical & System Design Panel 2 - 45 mins
Round 4: HR & Leadership Interview - 30 mins

Students meeting the cut-offs are requested to register on the placement portal by Friday 5:00 PM.
"""

        # Format allocation:
        # 1-7: Plain Text (.txt)
        # 8-13: Email (.eml)
        # 14-19: PDF (.pdf)
        # 20-25: DOCX (.docx)

        clean_comp_name = c["name"].lower().replace(" ", "_").replace("&", "and")

        if drive_num <= 7:
            # Plain Text
            filepath = os.path.join(ANNOUNCEMENTS_DIR, f"{drive_num:02d}_{clean_comp_name}_announcement.txt")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content_text)
        elif drive_num <= 13:
            # Email .eml
            filepath = os.path.join(ANNOUNCEMENTS_DIR, f"{drive_num:02d}_{clean_comp_name}_email.eml")
            msg = EmailMessage()
            msg["Subject"] = f"Campus Recruitment Announcement: {c['name']} (CTC: {c['ctc']} LPA)"
            msg["From"] = f"campus-hiring@{clean_comp_name}.com"
            msg["To"] = "placements@college.edu"
            msg["Date"] = "Mon, 27 Oct 2026 10:00:00 +0530"
            msg.set_content(content_text)
            with open(filepath, "wb") as f:
                f.write(msg.as_bytes())
        elif drive_num <= 19:
            # PDF
            filepath = os.path.join(ANNOUNCEMENTS_DIR, f"{drive_num:02d}_{clean_comp_name}_spec.pdf")
            c_pdf = canvas.Canvas(filepath, pagesize=letter)
            c_pdf.setFont("Helvetica-Bold", 14)
            c_pdf.drawString(50, 750, f"Campus Recruitment: {c['name']}")
            c_pdf.setFont("Helvetica", 10)
            y = 720
            for line in content_text.splitlines():
                if y < 50:
                    c_pdf.showPage()
                    y = 750
                    c_pdf.setFont("Helvetica", 10)
                c_pdf.drawString(50, y, line)
                y -= 15
            c_pdf.save()
        else:
            # DOCX
            filepath = os.path.join(ANNOUNCEMENTS_DIR, f"{drive_num:02d}_{clean_comp_name}_jd.docx")
            doc = docx.Document()
            doc.add_heading(f"Recruitment Drive: {c['name']}", 0)
            for line in content_text.splitlines():
                if line.startswith("CAMPUS") or line.startswith("ELIGIBILITY") or line.startswith("SELECTION"):
                    doc.add_heading(line, level=2)
                else:
                    doc.add_paragraph(line)
            doc.save(filepath)

    print(f"Generated 25 mixed-format synthetic announcements in {ANNOUNCEMENTS_DIR}")


# ---------------------------------------------------------
# Sample Offer Policies (with deliberate real-world ambiguities)
# ---------------------------------------------------------

POLICIES = [
    {
        "id": "policy_1_strict_one_offer",
        "name": "Strict One-Offer with Dream Tier Exception",
        "version": 1,
        "max_offers_per_student": 1,
        "dream_tier_ctc_lpa": 10.0,
        "super_dream_tier_ctc_lpa": 20.0,
        "allow_dream_upgrade": True,
        "upgrade_ctc_multiplier": 1.5,
        "strict_backlog_cutoff": True,
        "allow_multiple_offers_if_different_tiers": True,
        "is_active": True,
        "summary": "Each student is strictly limited to 1 campus offer. If the offer CTC is < 10 LPA, they may participate in 'Dream' drives offering >= 10 LPA.",
        "deliberate_ambiguities": [
            "Off-campus offers: Does not state whether an undeclared off-campus offer disqualifies a student from receiving a second campus offer.",
            "Salary components: Ambiguity over whether the 10.0 LPA cut-off applies to Cost-to-Company (CTC) including retention bonus or fixed base pay only.",
            "Cleared backlogs: Ambiguity over whether a student whose backlog exam results were declared AFTER the drive test but BEFORE the interview is eligible."
        ]
    },
    {
        "id": "policy_2_progressive_multiplier",
        "name": "Progressive Salary Multiplier Policy (1.5x Rule)",
        "version": 1,
        "max_offers_per_student": 2,
        "dream_tier_ctc_lpa": 12.0,
        "super_dream_tier_ctc_lpa": 25.0,
        "allow_dream_upgrade": True,
        "upgrade_ctc_multiplier": 1.5,
        "strict_backlog_cutoff": False,
        "allow_multiple_offers_if_different_tiers": True,
        "is_active": False,
        "summary": "Students may hold up to 2 offers, provided the second offer is at least 1.5x the CTC of the first offer.",
        "deliberate_ambiguities": [
            "Concurrent drives: If a student appears for two drives on the same day and receives offers from both simultaneously, which one takes precedence?",
            "Offer decline: Can a student decline an accepted offer to regain eligibility for a standard drive? Policy mentions no fee or penalty.",
            "Lateral entry eligibility: Does not explicitly state whether diploma aggregate replaces 12th percentage for cut-off calculations."
        ]
    },
    {
        "id": "policy_3_tiered_quota",
        "name": "Tier-Based Quota Policy (Standard, Dream, Super-Dream)",
        "version": 1,
        "max_offers_per_student": 3,
        "dream_tier_ctc_lpa": 8.0,
        "super_dream_tier_ctc_lpa": 18.0,
        "allow_dream_upgrade": True,
        "upgrade_ctc_multiplier": 1.25,
        "strict_backlog_cutoff": True,
        "allow_multiple_offers_if_different_tiers": True,
        "is_active": False,
        "summary": "Students can secure up to 1 offer in Standard (<8 LPA), 1 in Dream (8-18 LPA), and 1 in Super-Dream (>18 LPA).",
        "deliberate_ambiguities": [
            "Timing of re-evaluation: If a student's active backlog is converted to a pass via university re-evaluation two days after the drive registration deadline, does the placement cell permit late entry?",
            "Dream offer lock: Once a Super-Dream offer is obtained, is the student banned from participating even if the job profile differs radically?",
            "Verbal offer vs written letter: Does an official verbal confirmation during campus visit block the student immediately or only upon receiving the physical letter?"
        ]
    }
]


def generate_policies() -> None:
    for p in POLICIES:
        json_path = os.path.join(POLICIES_DIR, f"{p['id']}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(p, f, indent=2)

        md_path = os.path.join(POLICIES_DIR, f"{p['id']}.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# Placement Policy: {p['name']}\n\n")
            f.write(f"**Version**: {p['version']} | **Status**: {'Active' if p['is_active'] else 'Inactive'}\n\n")
            f.write(f"## Summary\n{p['summary']}\n\n")
            f.write("## Rules Specification\n")
            f.write(f"- Max offers permitted: {p['max_offers_per_student']}\n")
            f.write(f"- Dream Tier CTC: {p['dream_tier_ctc_lpa']} LPA\n")
            f.write(f"- Super-Dream Tier CTC: {p['super_dream_tier_ctc_lpa']} LPA\n")
            f.write(f"- Minimum upgrade multiplier: {p['upgrade_ctc_multiplier']}x\n")
            f.write(f"- Backlog cutoff strictness: {p['strict_backlog_cutoff']}\n\n")
            f.write("## Deliberate Policy Ambiguities (Known Edge Cases)\n")
            for amb in p["deliberate_ambiguities"]:
                f.write(f"- {amb}\n")
    print(f"Generated 3 sample offer policies in {POLICIES_DIR}")


def main() -> None:
    print("Generating synthetic dataset fixtures...")
    students = generate_students(1800)
    export_students_csv_and_xlsx(students)
    generate_announcements()
    generate_policies()
    print("All synthetic fixtures generated successfully.")


if __name__ == "__main__":
    main()
