"""
High-Performance Embedder for 25,000 Students and Multi-Company Recruiter Desks.
Generates 25,000 realistic student records and embeds them directly into SQLite WAL database
along with 13 comprehensive campus recruiters and drives.
"""

from __future__ import annotations

import csv
import datetime
import json
import os
import random
import sqlite3
import sys
import uuid

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

from backend.app.api.auth.hasher import hash_password

DB_PATH = os.path.join(ROOT_DIR, "placement_engine.db")
STUDENTS_CSV = os.path.join(ROOT_DIR, "fixtures", "students", "synthetic_students_25000.csv")
os.makedirs(os.path.dirname(STUDENTS_CSV), exist_ok=True)

FIRST_NAMES = [
    "Aarav", "Aditi", "Akash", "Ananya", "Aniket", "Ankita", "Arjun", "Bhavna", "Chirag", "Deepak",
    "Divya", "Gaurav", "Harsh", "Isha", "Ishaan", "Kavya", "Manish", "Meera", "Mohit", "Neha",
    "Nikhil", "Pooja", "Pranav", "Priya", "Rahul", "Rhea", "Rohan", "Sakshi", "Sameer", "Sanjay",
    "Shreya", "Siddharth", "Sneha", "Tanvi", "Tarun", "Varun", "Vikram", "Yash", "Zoya", "Kunal",
    "Aditya", "Alok", "Avani", "Ayush", "Dev", "Esha", "Ishita", "Karan", "Kritika", "Madhav",
    "Nandini", "Omkar", "Pallavi", "Rachit", "Riddhi", "Rishabh", "Ritika", "Samarth", "Sanya", "Tanmay",
    "Kartik", "Kiran", "Madhu", "Manoj", "Mukesh", "Naveen", "Pankaj", "Preeti", "Rajesh", "Ritu",
    "Rohit", "Santosh", "Sarita", "Satish", "Seema", "Shalini", "Sunita", "Suresh", "Umesh", "Vinay"
]

LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Gupta", "Singh", "Kumar", "Mehta", "Shah", "Reddy", "Nair",
    "Iyer", "Rao", "Joshi", "Kulkarni", "Deshmukh", "Chopra", "Malhotra", "Bhatia", "Saxena", "Agarwal",
    "Bansal", "Chouhan", "Das", "Dutta", "Ghosh", "Kapoor", "Mishra", "Pandey", "Pillai", "Sen",
    "Bose", "Chatterjee", "Dubey", "Garg", "Jain", "Kaur", "Mittal", "Prasad", "Shukla", "Trivedi"
]

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

COMPANIES_DATA = [
    {
        "id": "comp_microsoft",
        "name": "Microsoft",
        "industry": "Software & Cloud",
        "tier": "Super Dream",
        "role": "SDE - Cloud & AI",
        "ctc": 44.0,
        "date": "2026-11-04",
        "mode": "on_campus",
        "cgpa_min": 8.0,
        "tenth_min": 60.0,
        "twelfth_min": 60.0,
        "branches": ["Computer Science and Engineering", "Information Technology", "Electronics and Communication Engineering", "Data Science"],
        "max_backlogs": 0,
        "username": "recruiter_microsoft",
    },
    {
        "id": "comp_google",
        "name": "Google",
        "industry": "Software & Internet",
        "tier": "Super Dream",
        "role": "Software Development Engineer",
        "ctc": 36.0,
        "date": "2026-11-01",
        "mode": "hybrid",
        "cgpa_min": 8.5,
        "tenth_min": 60.0,
        "twelfth_min": 60.0,
        "branches": ["Computer Science and Engineering", "Information Technology", "Data Science"],
        "max_backlogs": 0,
        "username": "recruiter_google",
    },
    {
        "id": "comp_amazon",
        "name": "Amazon",
        "industry": "E-Commerce & AWS",
        "tier": "Super Dream",
        "role": "Software Development Engineer I",
        "ctc": 32.0,
        "date": "2026-11-07",
        "mode": "on_campus",
        "cgpa_min": 7.5,
        "tenth_min": 60.0,
        "twelfth_min": 60.0,
        "branches": ["Computer Science and Engineering", "Information Technology", "Electronics and Communication Engineering", "Electrical and Electronics Engineering"],
        "max_backlogs": 0,
        "username": "recruiter_amazon",
    },
    {
        "id": "comp_goldman",
        "name": "Goldman Sachs",
        "industry": "FinTech & Banking",
        "tier": "Super Dream",
        "role": "Engineering Analyst",
        "ctc": 30.0,
        "date": "2026-11-12",
        "mode": "on_campus",
        "cgpa_min": 8.0,
        "tenth_min": 70.0,
        "twelfth_min": 70.0,
        "branches": ["Computer Science and Engineering", "Information Technology", "Electronics and Communication Engineering", "Data Science"],
        "max_backlogs": 0,
        "username": "recruiter_goldman",
    },
    {
        "id": "comp_qualcomm",
        "name": "Qualcomm",
        "industry": "Semiconductors & Wireless",
        "tier": "Dream",
        "role": "Associate Hardware/Firmware Engineer",
        "ctc": 28.0,
        "date": "2026-11-15",
        "mode": "on_campus",
        "cgpa_min": 7.8,
        "tenth_min": 65.0,
        "twelfth_min": 65.0,
        "branches": ["Electronics and Communication Engineering", "Electrical and Electronics Engineering", "Computer Science and Engineering"],
        "max_backlogs": 0,
        "username": "recruiter_qualcomm",
    },
    {
        "id": "comp_oracle",
        "name": "Oracle",
        "industry": "Enterprise Software & OCI",
        "tier": "Dream",
        "role": "Member of Technical Staff (MTS)",
        "ctc": 24.0,
        "date": "2026-11-18",
        "mode": "on_campus",
        "cgpa_min": 7.5,
        "tenth_min": 60.0,
        "twelfth_min": 60.0,
        "branches": ["Computer Science and Engineering", "Information Technology", "Data Science"],
        "max_backlogs": 0,
        "username": "recruiter_oracle",
    },
    {
        "id": "comp_cisco",
        "name": "Cisco",
        "industry": "Networking & Security",
        "tier": "Dream",
        "role": "Technical Consulting Engineer",
        "ctc": 22.0,
        "date": "2026-11-20",
        "mode": "on_campus",
        "cgpa_min": 7.0,
        "tenth_min": 60.0,
        "twelfth_min": 60.0,
        "branches": ["Computer Science and Engineering", "Information Technology", "Electronics and Communication Engineering", "Electrical and Electronics Engineering"],
        "max_backlogs": 1,
        "username": "recruiter_cisco",
    },
    {
        "id": "comp_campus_partner",
        "name": "Campus Hiring Partner",
        "industry": "Technology",
        "tier": "Dream",
        "role": "Software Development Engineer",
        "ctc": 18.5,
        "date": "2026-11-22",
        "mode": "on_campus",
        "cgpa_min": 6.0,
        "tenth_min": 60.0,
        "twelfth_min": 60.0,
        "branches": ["Computer Science and Engineering", "Information Technology", "Electronics and Communication Engineering", "Data Science"],
        "max_backlogs": 0,
        "username": "recruiter",
    },
    {
        "id": "comp_deloitte",
        "name": "Deloitte",
        "industry": "Consulting & Audit",
        "tier": "Tier 1",
        "role": "Technology Analyst",
        "ctc": 12.0,
        "date": "2026-11-25",
        "mode": "on_campus",
        "cgpa_min": 6.5,
        "tenth_min": 60.0,
        "twelfth_min": 60.0,
        "branches": BRANCHES,
        "max_backlogs": 1,
        "username": "recruiter_deloitte",
    },
    {
        "id": "comp_infosys",
        "name": "Infosys",
        "industry": "IT Services & Consulting",
        "tier": "Tier 1",
        "role": "Specialist Programmer",
        "ctc": 9.5,
        "date": "2026-11-28",
        "mode": "on_campus",
        "cgpa_min": 6.5,
        "tenth_min": 60.0,
        "twelfth_min": 60.0,
        "branches": BRANCHES,
        "max_backlogs": 0,
        "username": "recruiter_infosys",
    },
    {
        "id": "comp_accenture",
        "name": "Accenture",
        "industry": "Consulting & Technology",
        "tier": "Tier 1",
        "role": "Advanced Application Engineering Analyst",
        "ctc": 8.5,
        "date": "2026-12-01",
        "mode": "on_campus",
        "cgpa_min": 6.5,
        "tenth_min": 60.0,
        "twelfth_min": 60.0,
        "branches": BRANCHES,
        "max_backlogs": 0,
        "username": "recruiter_accenture",
    },
    {
        "id": "comp_tcs",
        "name": "Tata Consultancy Services",
        "industry": "IT Services & Consulting",
        "tier": "Tier 2",
        "role": "Systems Engineer (Digital)",
        "ctc": 7.5,
        "date": "2026-12-03",
        "mode": "on_campus",
        "cgpa_min": 6.0,
        "tenth_min": 60.0,
        "twelfth_min": 60.0,
        "branches": BRANCHES,
        "max_backlogs": 1,
        "username": "recruiter_tcs",
    },
    {
        "id": "comp_wipro",
        "name": "Wipro",
        "industry": "IT Services",
        "tier": "Tier 2",
        "role": "Project Engineer (Turbo)",
        "ctc": 6.5,
        "date": "2026-12-05",
        "mode": "on_campus",
        "cgpa_min": 6.0,
        "tenth_min": 60.0,
        "twelfth_min": 60.0,
        "branches": BRANCHES,
        "max_backlogs": 1,
        "username": "recruiter_wipro",
    },
]


def run():
    print(f"[*] Starting 25,000 student fixture generation & database embedding...")
    random.seed(42)
    ref_date = datetime.date(2026, 10, 22)
    now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    students_rows = []
    backlogs_rows = []
    gap_years_rows = []
    offers_rows = []
    csv_rows = []

    TOTAL_STUDENTS = 25000

    for i in range(TOTAL_STUDENTS):
        roll_no = f"BT21{i + 1:04d}"
        fn = random.choice(FIRST_NAMES)
        ln = random.choice(LAST_NAMES)
        name = f"{fn} {ln}"
        email = f"{fn.lower()}.{ln.lower()}{i + 1}@college.edu"
        branch = BRANCHES[i % len(BRANCHES)]

        cgpa = min(9.95, max(5.2, round(random.gauss(7.6, 1.1), 2)))
        tenth = min(98.0, max(60.0, round(random.gauss(84.0, 8.0), 2)))
        is_lateral = (i % 10 == 0)
        twelfth = None if is_lateral else min(98.0, max(55.0, round(random.gauss(80.0, 9.0), 2)))
        diploma = min(95.0, max(65.0, round(random.gauss(82.0, 6.0), 2))) if is_lateral else None
        birth_year = 2003 if not is_lateral else 2002
        dob = datetime.date(birth_year, (i % 12) + 1, (i % 28) + 1)

        stu_id = f"stu_bt21_{i + 1:05d}"
        if i == 0:
            stu_id = "stu_bt210001"  # Preserve existing demo student ID

        # Backlogs
        backlogs_active_count = 0
        backlogs_history_count = 0
        backlog_detail = ""
        if 70 <= (i % 100) < 85:
            backlogs_active_count = 1 if (i % 2 == 0) else 2
            backlogs_history_count = backlogs_active_count
            backlogs_rows.append((
                str(uuid.uuid4()), stu_id, "Data Structures", 3, "active", None, now_str
            ))
            if backlogs_active_count > 1:
                backlogs_rows.append((
                    str(uuid.uuid4()), stu_id, "Engineering Mathematics", 2, "active", None, now_str
                ))
                backlog_detail = "Data Structures (active); Engineering Mathematics (active)"
            else:
                backlog_detail = "Data Structures (active)"
        elif (i % 100) >= 85:
            backlogs_active_count = 0
            backlogs_history_count = 1
            clear_days = (i % 180) + 1
            clear_date = ref_date - datetime.timedelta(days=clear_days)
            backlogs_rows.append((
                str(uuid.uuid4()), stu_id, "Engineering Mathematics", 2, "cleared", clear_date.isoformat(), now_str
            ))
            backlog_detail = f"Engineering Mathematics (cleared {clear_date.isoformat()})"

        # Gap year
        gap_years = 1 if (i % 10 == 3) else 0
        if gap_years > 0:
            gap_years_rows.append((
                str(uuid.uuid4()), stu_id, 2020, 2021, 1, "Competitive Exam Preparation", "post_12th", now_str
            ))

        # Existing offers
        existing_offer_str = ""
        if i % 5 == 0:
            if i % 25 == 0:
                existing_offer_str = "Microsoft: 32.0 LPA (accepted)"
                offers_rows.append((
                    str(uuid.uuid4()), stu_id, "Microsoft", 32.0, 28.0, "2026-09-15", "on_campus", 1, "accepted", now_str
                ))
            elif i % 15 == 0:
                existing_offer_str = "Infosys: 9.5 LPA (offered)"
                offers_rows.append((
                    str(uuid.uuid4()), stu_id, "Infosys", 9.5, 8.5, "2026-09-20", "on_campus", 0, "offered", now_str
                ))
            else:
                existing_offer_str = "TCS: 4.0 LPA (accepted)"
                offers_rows.append((
                    str(uuid.uuid4()), stu_id, "TCS", 4.0, 3.8, "2026-09-10", "on_campus", 0, "accepted", now_str
                ))

        gender = "Female" if (i % 3 == 0) else "Male"
        category = "General" if (i % 2 == 0) else ("OBC" if (i % 4 == 1) else "SC")

        students_rows.append((
            stu_id,
            roll_no,
            name,
            email,
            branch,
            "B.Tech",
            cgpa,
            tenth,
            twelfth,
            diploma,
            dob.isoformat(),
            gender,
            None,  # caste
            None,  # religion
            category,
            1,     # version
            now_str,
            now_str,
        ))

        csv_rows.append({
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

    # 1. Export CSV
    print(f"[*] Exporting CSV to {STUDENTS_CSV}...")
    with open(STUDENTS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"[+] Successfully exported {len(csv_rows)} records to CSV.")

    # 2. Connect to SQLite database
    print(f"[*] Connecting to {DB_PATH} and embedding records...")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = OFF;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    cur = conn.cursor()

    # Clear previous student entities to avoid conflicts
    cur.execute("DELETE FROM backlogs;")
    cur.execute("DELETE FROM gap_years;")
    cur.execute("DELETE FROM offers;")
    cur.execute("DELETE FROM students;")

    # Insert 25,000 students
    cur.executemany("""
        INSERT INTO students (
            id, roll_no, name, email, branch, program, cgpa, tenth_percentage,
            twelfth_percentage, diploma_percentage, date_of_birth, gender,
            caste, religion, category, version, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, students_rows)
    print(f"[+] Inserted {len(students_rows)} students into database.")

    if backlogs_rows:
        cur.executemany("""
            INSERT INTO backlogs (id, student_id, subject, semester, status, cleared_on, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, backlogs_rows)
        print(f"[+] Inserted {len(backlogs_rows)} backlog records.")

    if gap_years_rows:
        cur.executemany("""
            INSERT INTO gap_years (id, student_id, start_year, end_year, duration_years, reason, phase, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, gap_years_rows)
        print(f"[+] Inserted {len(gap_years_rows)} gap year records.")

    if offers_rows:
        cur.executemany("""
            INSERT INTO offers (id, student_id, company, ctc_lpa, fixed_pay_lpa, offer_date, source, is_dream, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, offers_rows)
        print(f"[+] Inserted {len(offers_rows)} prior student offer records.")

    # 3. Seed Companies, Drives, Requirement Versions & Recruiter Users
    print("[*] Filing 13 company recruiter desks, recruitment drives, and interview setups...")
    hashed_pwd = hash_password("admin123")
    hashed_stu_pwd = hash_password("123456")

    # Clear previous drives/companies
    cur.execute("DELETE FROM eligibility_decisions;")
    cur.execute("DELETE FROM slots;")
    cur.execute("DELETE FROM panels;")
    cur.execute("DELETE FROM drive_requirement_versions;")
    cur.execute("DELETE FROM drives;")
    cur.execute("DELETE FROM companies;")
    cur.execute("DELETE FROM schedules;")
    cur.execute("DELETE FROM rooms;")

    # Common rooms
    rooms_data = [
        ("room_101", "Interview Suite 101", "Placement Block A", 4, 1, 1, now_str),
        ("room_102", "Interview Suite 102", "Placement Block A", 4, 1, 1, now_str),
        ("room_103", "Interview Suite 103", "Placement Block A", 4, 1, 1, now_str),
        ("room_201", "Boardroom Cabin 201", "Placement Block B", 6, 1, 1, now_str),
        ("room_202", "Boardroom Cabin 202", "Placement Block B", 6, 1, 1, now_str),
    ]
    cur.executemany("""
        INSERT INTO rooms (id, name, building, capacity, has_computers, is_active, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, rooms_data)

    # Master Schedule
    schedule_id = "sched_fall_2026"
    all_drive_ids = [f"drv_{c['id'].replace('comp_', '')}" for c in COMPANIES_DATA]
    cur.execute("""
        INSERT INTO schedules (id, name, version, status, drive_ids_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (schedule_id, "Campus Placement Master Schedule 2026-27", 1, "published", json.dumps(all_drive_ids), now_str))

    for idx, comp in enumerate(COMPANIES_DATA):
        comp_id = comp["id"]
        drive_id = f"drv_{comp_id.replace('comp_', '')}"
        req_id = f"req_{comp_id.replace('comp_', '')}_v1"
        panel_id = f"panel_{comp_id.replace('comp_', '')}"
        room_id = rooms_data[idx % len(rooms_data)][0]

        # 1. Company
        cur.execute("""
            INSERT INTO companies (id, name, industry, tier, website, version, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (comp_id, comp["name"], comp["industry"], comp["tier"], f"https://{comp_id.replace('comp_', '')}.com", 1, now_str))

        # 2. Drive
        cur.execute("""
            INSERT INTO drives (id, company_id, company_name, drive_date, mode, ctc_lpa, is_dream, status, version, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (drive_id, comp_id, comp["name"], comp["date"], comp["mode"], comp["ctc"], 1 if comp["ctc"] >= 15.0 else 0, "PUBLISHED", 1, now_str))

        # 3. Requirement Version
        cur.execute("""
            INSERT INTO drive_requirement_versions (
                id, drive_id, version_number, raw_source_text, parse_confidence,
                min_cgpa, min_tenth_percentage, min_twelfth_percentage, min_diploma_percentage,
                allowed_branches_json, allowed_programs_json, max_active_backlogs,
                allow_history_backlogs, max_history_backlogs, max_gap_years,
                allow_gap_during_degree, custom_rules_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            req_id, drive_id, 1, f"Official criteria for {comp['name']}", 0.98,
            comp["cgpa_min"], comp["tenth_min"], comp["twelfth_min"], 65.0,
            json.dumps(comp["branches"]), json.dumps(["B.Tech"]), comp["max_backlogs"],
            1, None, 1, 0, "[]", now_str
        ))

        # 4. Panel
        cur.execute("""
            INSERT INTO panels (id, drive_id, name, interviewers_json, room_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (panel_id, drive_id, f"{comp['name']} Tech Panel 1", json.dumps(["HR Manager", "Senior Architect"]), room_id, now_str))

        # 5. Recruiter User Account
        u_id = f"usr_{comp['username']}"
        cur.execute("DELETE FROM users WHERE username = ?", (comp["username"],))
        cur.execute("""
            INSERT INTO users (id, username, email, password_hash, role, is_active, student_id, created_at, company_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (u_id, comp["username"], f"recruiter@{comp_id.replace('comp_', '')}.com", hashed_pwd, "recruiter_readonly", 1, None, now_str, comp_id))

        # 6. Eligible Candidate Shortlist & Slots for this drive
        # Pick top matching candidates from students_rows
        eligible_candidates = [
            s for s in students_rows
            if s[6] >= comp["cgpa_min"] and s[4] in comp["branches"]
        ][:40]

        for rank, c_stu in enumerate(eligible_candidates):
            c_id = c_stu[0]
            # Decision
            cur.execute("""
                INSERT INTO eligibility_decisions (id, run_id, student_id, drive_id, status, reasons_json, rule_ids_json, evaluated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()), f"run_{drive_id}", c_id, drive_id, "eligible",
                json.dumps([f"CGPA {c_stu[6]} >= {comp['cgpa_min']}", f"Branch {c_stu[4]} is eligible"]),
                json.dumps(["RULE_CGPA", "RULE_BRANCH"]), now_str
            ))

            # Slots for first 6 candidates
            if rank < 6:
                start_dt = datetime.datetime(2026, 11, 20, 9, 0, 0) + datetime.timedelta(minutes=rank * 30)
                end_dt = start_dt + datetime.timedelta(minutes=25)
                slot_time = start_dt.strftime("%Y-%m-%d %H:%M:%S")
                slot_end = end_dt.strftime("%Y-%m-%d %H:%M:%S")
                cur.execute("""
                    INSERT INTO slots (id, schedule_id, drive_id, student_id, round_number, room_id, panel_id, start_time, end_time, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(uuid.uuid4()), schedule_id, drive_id, c_id, 1, room_id, panel_id, slot_time, slot_end, now_str
                ))

    # Also seed administrative accounts
    admin_accounts = [
        ("usr_admin_root", "admin", "admin@college.edu", hashed_pwd, "officer", 1, None, now_str, None),
        ("usr_officer_root", "officer", "tpo@college.edu", hashed_pwd, "officer", 1, None, now_str, None),
        ("usr_coord_root", "coordinator", "coordinator@college.edu", hashed_pwd, "coordinator", 1, None, now_str, None),
        ("usr_stu_bt210001", "BT210001", "aarav.patel1@college.edu", hashed_stu_pwd, "student", 1, "stu_bt210001", now_str, None),
        ("usr_stu_pipe_001", "PIPE_001", "rohit.sharma@college.edu", hashed_stu_pwd, "student", 1, "stu_bt210001", now_str, None),
    ]

    for acc in admin_accounts:
        cur.execute("DELETE FROM users WHERE username = ?", (acc[1],))
        cur.execute("""
            INSERT INTO users (id, username, email, password_hash, role, is_active, student_id, created_at, company_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, acc)

    conn.commit()
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.close()

    print("[+] Database population complete: 25,000 students, 13 recruiter company desks, schedules & slots filed!")


if __name__ == "__main__":
    run()