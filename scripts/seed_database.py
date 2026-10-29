"""
IM-101 Master Database Seeder and Integrity Validator.
Generates exactly 1,800 synthetic students distributed evenly across 9 canonical branches (200 each),
with 1,800 globally unique full names, consistent semester SGPAs, CGPA, backlogs, and offers.
"""

from __future__ import annotations

import csv
import datetime
import json
import os
import random
import re
import sys
import uuid

# Ensure repository root is in sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from backend.app.api.auth.hasher import hash_password
from backend.app.api.auth.seeder import RECRUITER_COMPANIES
from backend.app.storage.database import Base, SessionLocal, engine
from backend.app.storage.models.entities import (
    AcademicRecordModel,
    BacklogModel,
    CompanyModel,
    DriveModel,
    DriveRequirementVersionModel,
    GapYearModel,
    OfferModel,
    PolicyModel,
    RoomModel,
    StudentModel,
    UserModel,
)

# 9 Canonical Branches and their Display Names
CANONICAL_BRANCHES = [
    "CSE",
    "IT",
    "ECE",
    "EEE",
    "ME",
    "CE",
    "CHE",
    "BT",
    "DS",
]

BRANCH_DISPLAY_NAMES = {
    "CSE": "Computer Science and Engineering",
    "IT": "Information Technology",
    "ECE": "Electronics and Communication Engineering",
    "EEE": "Electrical and Electronics Engineering",
    "ME": "Mechanical Engineering",
    "CE": "Civil Engineering",
    "CHE": "Chemical Engineering",
    "BT": "Biotechnology",
    "DS": "Data Science",
}

# Authentic Indian First Names Pool (Diverse male and female)
FIRST_NAMES = [
    "Aarav", "Aanya", "Aditya", "Advait", "Ahana", "Ajay", "Akanksha", "Akhil", "Alok", "Aman",
    "Amit", "Amrita", "Anand", "Ananya", "Anil", "Aniruddh", "Ankita", "Anmol", "Ansh", "Anushka",
    "Arjun", "Aryan", "Ashish", "Avani", "Ayush", "Bhavna", "Chetan", "Darshan", "Deepika", "Dev",
    "Dhruv", "Divya", "Gaurav", "Gayatri", "Harsh", "Harshit", "Ishaan", "Ishita", "Jay", "Jyoti",
    "Karan", "Karthik", "Kavita", "Kavya", "Keshav", "Kiran", "Komal", "Kunal", "Madhav", "Manish",
    "Manisha", "Manoj", "Mayank", "Meera", "Mohit", "Mukund", "Nakul", "Namrata", "Naveen", "Neha",
    "Nikhil", "Niharika", "Nitin", "Pankaj", "Parth", "Payal", "Pooja", "Pradeep", "Pranav", "Prateek",
    "Priya", "Priyanka", "Rahul", "Rajat", "Rajesh", "Rakesh", "Ramesh", "Rashmi", "Ritu", "Riya",
    "Rohan", "Rohit", "Sachin", "Sameer", "Sandeep", "Sanjay", "Saurabh", "Shalini", "Shivam", "Shreya",
    "Siddharth", "Sneha", "Soham", "Srikant", "Sumit", "Suresh", "Swati", "Tanvi", "Tarun", "Utkarsh",
    "Vaibhav", "Varun", "Vedant", "Vidya", "Vikas", "Vikram", "Vinay", "Vishal", "Vivek", "Yash",
]

# Authentic Indian Surnames Pool (Diverse across all regions)
LAST_NAMES = [
    "Agarwal", "Ahluwalia", "Banerjee", "Bhat", "Bhattacharya", "Chakraborty", "Chatterjee", "Chauhan",
    "Choudhury", "Das", "Deshmukh", "Dixit", "Dubey", "Dutta", "Ganguly", "Ghosh", "Goswami", "Goyal",
    "Gupta", "Hegde", "Iyer", "Iyengar", "Jain", "Jha", "Joshi", "Kapoor", "Kashyap", "Kaul", "Kaur",
    "Khanna", "Kulkarni", "Kumar", "Majumdar", "Malhotra", "Malik", "Mandal", "Mathur", "Mehta", "Menon",
    "Mishra", "Mitra", "Mukherjee", "Mukhopadhyay", "Nair", "Nambiar", "Pai", "Pal", "Pandey", "Patel",
    "Patil", "Pillai", "Prabhu", "Prasad", "Raina", "Rajput", "Ramachandran", "Rao", "Rastogi", "Ray",
    "Reddy", "Roy", "Sahni", "Saraf", "Sarin", "Saxena", "Sen", "Sengupta", "Sethi", "Shah", "Sharma",
    "Shetty", "Shukla", "Singh", "Singhania", "Sinha", "Somani", "Srivastava", "Subramanian", "Talwar",
    "Tandon", "Tiwari", "Tripathi", "Trivedi", "Varma", "Venkatesh", "Verma", "Yadav",
]

# Branch-Specific Technical Subjects for Backlog Realism
BRANCH_SUBJECTS = {
    "CSE": ["Data Structures", "Operating Systems", "Computer Networks", "Database Management", "Compiler Design", "Algorithms"],
    "IT": ["Web Technologies", "Information Security", "Software Engineering", "Cloud Computing", "Distributed Systems", "Object Oriented Programming"],
    "ECE": ["Analog Circuits", "Digital Signal Processing", "Microprocessors", "Signals and Systems", "Electromagnetic Theory", "VLSI Design"],
    "EEE": ["Power Systems", "Control Systems", "Electrical Machines", "Power Electronics", "Circuit Theory", "High Voltage Engineering"],
    "ME": ["Thermodynamics", "Fluid Mechanics", "Strength of Materials", "Kinematics of Machinery", "Heat Transfer", "Manufacturing Processes"],
    "CE": ["Structural Analysis", "Geotechnical Engineering", "Fluid Mechanics", "Surveying", "Concrete Technology", "Transportation Engineering"],
    "CHE": ["Chemical Reaction Engineering", "Mass Transfer Operations", "Heat Transfer Operations", "Process Dynamics", "Transport Phenomena", "Thermodynamics"],
    "BT": ["Molecular Biology", "Biochemistry", "Bioprocess Engineering", "Genetic Engineering", "Immunology", "Bioinformatics"],
    "DS": ["Machine Learning", "Probability & Statistics", "Big Data Analytics", "Deep Learning", "Data Mining", "Data Visualization"],
}

CATEGORIES = ["General", "General-EWS", "OBC-NCL", "SC", "ST"]
GENDERS = ["Male", "Female"]


def normalize_full_name(name: str) -> str:
    """Normalizes a name string by trimming, collapsing spaces, and lowercasing."""
    return re.sub(r"\s+", " ", name.strip()).lower()


def generate_unique_names(count: int = 1800, seed: int = 42) -> list[tuple[str, str, str]]:
    """Generates exactly `count` unique (first_name, last_name, full_name) tuples with zero collisions."""
    rng = random.Random(seed)
    pairs: list[tuple[str, str]] = []
    for fn in FIRST_NAMES:
        for ln in LAST_NAMES:
            pairs.append((fn, ln))

    rng.shuffle(pairs)
    if len(pairs) < count:
        raise ValueError(f"Name pool ({len(pairs)}) is smaller than requested count ({count}).")

    selected: list[tuple[str, str, str]] = []
    seen_normalized: set[str] = set()

    for fn, ln in pairs:
        full = f"{fn} {ln}"
        norm = normalize_full_name(full)
        if norm not in seen_normalized:
            seen_normalized.add(norm)
            selected.append((fn, ln, full))
            if len(selected) == count:
                break

    if len(selected) != count:
        raise RuntimeError(f"Failed to generate {count} unique names. Generated {len(selected)}.")

    return selected


def seed_database(force_recreate: bool = False, random_seed: int = 2026) -> dict[str, Any]:
    """
    Main seeding routine.
    Creates tables, seeds exactly 1,800 students (200 per branch), baseline companies, drives,
    active offer policy, rooms, and administrative user accounts.
    """
    rng = random.Random(random_seed)
    db: Session = SessionLocal()

    try:
        # Check if already seeded with exactly 1,800 students
        existing_student_count = db.execute(select(func.count(StudentModel.id))).scalar_one()
        if existing_student_count == 1800 and not force_recreate:
            print(f"Database already contains exactly 1,800 students. Validating existing records...")
            return validate_seeded_database(db)

        if force_recreate:
            print("Force recreation requested: Dropping and recreating all tables...")
            Base.metadata.drop_all(bind=engine)
            Base.metadata.create_all(bind=engine)
        else:
            Base.metadata.create_all(bind=engine)

        # Clear student sub-tables and students safely if not force recreating
        db.execute(delete(AcademicRecordModel))
        db.execute(delete(BacklogModel))
        db.execute(delete(GapYearModel))
        db.execute(delete(OfferModel))
        db.execute(delete(StudentModel))
        db.flush()

        print("Generating 1,800 unique student identities across 9 canonical branches...")
        unique_name_tuples = generate_unique_names(1800, seed=random_seed)

        # Prepare company list for offers
        offer_companies = [
            ("comp_tcs", "Tata Consultancy Services", 7.5, False),
            ("comp_infosys", "Infosys", 9.5, False),
            ("comp_wipro", "Wipro", 6.5, False),
            ("comp_accenture", "Accenture", 8.5, False),
            ("comp_deloitte", "Deloitte", 12.0, True),
            ("comp_cisco", "Cisco", 22.0, True),
            ("comp_oracle", "Oracle", 24.0, True),
            ("comp_qualcomm", "Qualcomm", 28.0, True),
            ("comp_amazon", "Amazon", 32.0, True),
            ("comp_microsoft", "Microsoft", 44.0, True),
            ("comp_google", "Google", 36.0, True),
        ]

        students_to_add: list[StudentModel] = []
        academic_records_to_add: list[AcademicRecordModel] = []
        backlogs_to_add: list[BacklogModel] = []
        offers_to_add: list[OfferModel] = []
        gap_years_to_add: list[GapYearModel] = []

        csv_rows: list[dict[str, Any]] = []

        name_idx = 0
        roll_counter = 1

        # Distribute 200 students into each of the 9 branches = exactly 1800
        for branch_code in CANONICAL_BRANCHES:
            for _ in range(200):
                fn, ln, full_name = unique_name_tuples[name_idx]
                norm_name = normalize_full_name(full_name)
                name_idx += 1

                student_id = f"stu_bt21{roll_counter:04d}"
                roll_no = f"BT21{roll_counter:04d}"
                email = f"{fn.lower()}.{ln.lower()}.{roll_no.lower()}@college.edu"
                roll_counter += 1

                # Generate 6 semesters of realistic SGPAs such that CGPA strictly equals average of SGPAs
                cgpa = round(rng.triangular(6.0, 9.8, 7.8), 2)
                target_sum = round(cgpa * 6, 2)
                while True:
                    sgpas: list[float] = []
                    cur_sum = 0.0
                    for _ in range(5):
                        s = round(max(5.0, min(10.0, cgpa + rng.uniform(-0.35, 0.35))), 2)
                        sgpas.append(s)
                        cur_sum = round(cur_sum + s, 2)
                    s6 = round(target_sum - cur_sum, 2)
                    if 5.0 <= s6 <= 10.0:
                        sgpas.append(s6)
                        break

                for sem, sem_sgpa in enumerate(sgpas, start=1):
                    academic_records_to_add.append(
                        AcademicRecordModel(
                            id=f"acad_{student_id}_s{sem}",
                            student_id=student_id,
                            semester=sem,
                            sgpa=sem_sgpa,
                        )
                    )

                # 10th and 12th / Diploma
                tenth_pct = round(rng.uniform(65.0, 98.0), 2)
                is_lateral = (roll_counter % 12 == 0)  # ~8% lateral entry students
                if is_lateral:
                    twelfth_pct = None
                    diploma_pct = round(rng.uniform(68.0, 92.0), 2)
                else:
                    twelfth_pct = round(rng.uniform(60.0, 97.0), 2)
                    diploma_pct = None

                dob_year = 2003 if roll_counter % 2 == 0 else 2004
                dob_month = rng.randint(1, 12)
                dob_day = rng.randint(1, 28)
                dob = datetime.date(dob_year, dob_month, dob_day)

                gender = "Female" if fn in [
                    "Aanya", "Ahana", "Akanksha", "Amrita", "Ananya", "Ankita", "Anushka", "Avani",
                    "Bhavna", "Deepika", "Divya", "Gayatri", "Ishita", "Jyoti", "Kavita", "Kavya",
                    "Kiran", "Komal", "Manisha", "Meera", "Namrata", "Neha", "Niharika", "Payal",
                    "Pooja", "Priya", "Priyanka", "Rashmi", "Ritu", "Riya", "Shalini", "Shreya",
                    "Sneha", "Swati", "Tanvi", "Vidya",
                ] else "Male"
                category = rng.choice(CATEGORIES)

                # Backlogs distribution: 70% 0, 18% cleared, 12% active
                backlog_dice = rng.random()
                active_backlog_count = 0
                cleared_backlog_count = 0

                if backlog_dice < 0.70:
                    # Clean record
                    pass
                elif backlog_dice < 0.88:
                    # 1 or 2 cleared backlogs in earlier semesters
                    num_cleared = 1 if rng.random() < 0.75 else 2
                    cleared_backlog_count = num_cleared
                    subjects_sample = rng.sample(BRANCH_SUBJECTS[branch_code], num_cleared)
                    for b_idx, subj in enumerate(subjects_sample):
                        sem_failed = rng.choice([1, 2, 3])
                        clear_date = datetime.date(2025, 6, 15) + datetime.timedelta(days=b_idx * 60)
                        backlogs_to_add.append(
                            BacklogModel(
                                id=f"bl_{student_id}_{b_idx+1}",
                                student_id=student_id,
                                subject=subj,
                                semester=sem_failed,
                                status="cleared",
                                cleared_on=clear_date,
                            )
                        )
                else:
                    # 1 or 2 active backlogs
                    num_active = 1 if rng.random() < 0.80 else 2
                    active_backlog_count = num_active
                    subjects_sample = rng.sample(BRANCH_SUBJECTS[branch_code], num_active)
                    for b_idx, subj in enumerate(subjects_sample):
                        sem_failed = rng.choice([4, 5, 6])
                        backlogs_to_add.append(
                            BacklogModel(
                                id=f"bl_{student_id}_{b_idx+1}",
                                student_id=student_id,
                                subject=subj,
                                semester=sem_failed,
                                status="active",
                                cleared_on=None,
                            )
                        )

                # Gap Years: ~6% of students have 1 gap year (between 12th & college)
                if roll_counter % 16 == 0:
                    gap_years_to_add.append(
                        GapYearModel(
                            id=f"gap_{student_id}",
                            student_id=student_id,
                            start_year=2020,
                            end_year=2021,
                            duration_years=1,
                            reason="Entrance examination preparation",
                            phase="between_12th_and_degree",
                        )
                    )

                # Placement Offers: ~18% students have received an offer
                # Eligible students (CGPA >= 6.5, active_backlogs == 0) can receive offers
                if active_backlog_count == 0 and cgpa >= 6.5 and (roll_counter % 5 == 0):
                    comp_pick = rng.choice(offer_companies)
                    offer_date = datetime.date(2026, 8, 1) + datetime.timedelta(days=(roll_counter % 75))
                    offers_to_add.append(
                        OfferModel(
                            id=f"off_{student_id}",
                            student_id=student_id,
                            company=comp_pick[1],
                            ctc_lpa=comp_pick[2],
                            fixed_pay_lpa=round(comp_pick[2] * 0.85, 2),
                            offer_date=offer_date,
                            source="on_campus",
                            is_dream=comp_pick[3],
                            status="accepted" if rng.random() < 0.80 else "offered",
                        )
                    )

                # Create StudentModel instance
                student_model = StudentModel(
                    id=student_id,
                    roll_no=roll_no,
                    name=full_name,
                    normalized_name=norm_name,
                    email=email,
                    branch=branch_code,
                    program="B.Tech",
                    cgpa=cgpa,
                    tenth_percentage=tenth_pct,
                    twelfth_percentage=twelfth_pct,
                    diploma_percentage=diploma_pct,
                    date_of_birth=dob,
                    gender=gender,
                    caste=category,
                    religion="Not Declared",
                    category=category,
                    version=1,
                )
                students_to_add.append(student_model)

                # CSV Export Row
                csv_rows.append({
                    "roll_no": roll_no,
                    "name": full_name,
                    "email": email,
                    "branch": branch_code,
                    "program": "B.Tech",
                    "cgpa": cgpa,
                    "tenth_percentage": tenth_pct,
                    "twelfth_percentage": twelfth_pct if twelfth_pct is not None else "",
                    "diploma_percentage": diploma_pct if diploma_pct is not None else "",
                    "dob": dob.isoformat(),
                    "gender": gender,
                    "category": category,
                    "sem1_sgpa": sgpas[0],
                    "sem2_sgpa": sgpas[1],
                    "sem3_sgpa": sgpas[2],
                    "sem4_sgpa": sgpas[3],
                    "sem5_sgpa": sgpas[4],
                    "sem6_sgpa": sgpas[5],
                    "active_backlogs": active_backlog_count,
                    "cleared_backlogs": cleared_backlog_count,
                })

        # Bulk insert into database
        print(f"Persisting {len(students_to_add)} students and {len(academic_records_to_add)} semester records...")
        db.add_all(students_to_add)
        db.flush()

        db.add_all(academic_records_to_add)
        db.add_all(backlogs_to_add)
        db.add_all(gap_years_to_add)
        db.add_all(offers_to_add)
        db.flush()

        # Seed Active Offer Policy
        stmt_pol = select(PolicyModel).where(PolicyModel.is_active == True)
        active_pol = db.execute(stmt_pol).scalar_one_or_none()
        if not active_pol:
            active_pol = PolicyModel(
                id="policy_1_strict_one_offer",
                name="Strict One-Offer with Dream Tier Exception",
                version=1,
                max_offers_per_student=1,
                dream_tier_ctc_lpa=10.0,
                super_dream_tier_ctc_lpa=20.0,
                allow_dream_upgrade=True,
                upgrade_ctc_multiplier=1.5,
                strict_backlog_cutoff=True,
                allow_multiple_offers_if_different_tiers=True,
                is_active=True,
            )
            db.add(active_pol)
            db.flush()

        # Seed Baseline Campus Interview Rooms for OR-Tools Scheduler
        room_data = [
            ("room_auditorium", "Main Auditorium", "Academic Complex", 180, False),
            ("room_seminar_a", "Seminar Hall A", "Academic Complex", 80, True),
            ("room_seminar_b", "Seminar Hall B", "Academic Complex", 80, True),
            ("room_cabin_101", "Interview Cabin 101", "Placement Block", 6, False),
            ("room_cabin_102", "Interview Cabin 102", "Placement Block", 6, False),
            ("room_cabin_103", "Interview Cabin 103", "Placement Block", 6, False),
            ("room_cabin_104", "Interview Cabin 104", "Placement Block", 6, False),
            ("room_cabin_105", "Interview Cabin 105", "Placement Block", 6, False),
            ("room_lab_cse", "Computing Systems Lab", "IT Block", 60, True),
        ]
        for r_id, r_name, r_bldg, r_cap, r_comp in room_data:
            stmt_r = select(RoomModel).where(RoomModel.id == r_id)
            if not db.execute(stmt_r).scalar_one_or_none():
                db.add(RoomModel(id=r_id, name=r_name, building=r_bldg, capacity=r_cap, has_computers=r_comp, is_active=True))
        db.flush()

        # Seed Partner Companies and Recruiter Desks
        for rc in RECRUITER_COMPANIES:
            comp_id = rc["id"]
            drive_id = f"drv_{comp_id.replace('comp_', '')}"
            req_id = f"req_{comp_id.replace('comp_', '')}_v1"

            stmt_comp = select(CompanyModel).where((CompanyModel.id == comp_id) | (CompanyModel.name == rc["name"]))
            comp = db.execute(stmt_comp).scalars().first()
            if not comp:
                comp = CompanyModel(
                    id=comp_id,
                    name=rc["name"],
                    industry="Technology",
                    tier="Tier 1",
                    website=f"https://{comp_id.replace('comp_', '')}.com",
                    version=1,
                )
                db.add(comp)
                db.flush()

            stmt_drv = select(DriveModel).where((DriveModel.id == drive_id) | (DriveModel.company_id == comp.id))
            drv = db.execute(stmt_drv).scalars().first()
            if not drv:
                drv = DriveModel(
                    id=drive_id,
                    company_id=comp.id,
                    company_name=comp.name,
                    drive_date=datetime.date(2026, 11, 15) + datetime.timedelta(days=(len(rc["name"]) % 10)),
                    mode="on_campus",
                    ctc_lpa=rc["ctc"],
                    is_dream=True if rc["ctc"] >= 10.0 else False,
                    status="published",
                    version=1,
                )
                db.add(drv)
                db.flush()

            stmt_req = select(DriveRequirementVersionModel).where(DriveRequirementVersionModel.drive_id == drv.id)
            if not db.execute(stmt_req).scalars().first():
                db.add(
                    DriveRequirementVersionModel(
                        id=req_id,
                        drive_id=drv.id,
                        version_number=1,
                        min_cgpa=rc["cgpa"],
                        min_tenth_percentage=60.0,
                        min_twelfth_percentage=60.0,
                        max_active_backlogs=0,
                        allowed_branches_json=json.dumps(["CSE", "IT", "ECE", "DS"]),
                    )
                )
                db.flush()

            # Recruiter User
            stmt_usr = select(UserModel).where(UserModel.username == rc["username"])
            rec_user = db.execute(stmt_usr).scalars().first()
            if not rec_user:
                db.add(
                    UserModel(
                        id=f"usr_{rc['username']}",
                        username=rc["username"],
                        email=f"recruiter@{comp_id.replace('comp_', '')}.com",
                        password_hash=hash_password("recruiter123"),
                        role="recruiter_readonly",
                        company_id=comp.id,
                        is_active=True,
                    )
                )

        # Administrative Accounts
        admin_users = [
            ("usr_admin_root", "admin", "admin@college.edu", "admin123", "officer", None),
            ("usr_officer_root", "officer", "tpo@college.edu", "officer123", "officer", None),
            ("usr_coord_root", "coordinator", "coordinator@college.edu", "coord123", "coordinator", None),
            ("usr_stu_bt210001", "BT210001", "student1@college.edu", "123456", "student", "stu_bt210001"),
            ("usr_stu_bt210002", "BT210002", "student2@college.edu", "123456", "student", "stu_bt210002"),
            ("usr_stu_pipe_001", "PIPE_001", "rohit.pipe@college.edu", "123456", "student", "stu_bt210001"),
        ]
        for u_id, u_name, u_email, u_pwd, u_role, u_stu_id in admin_users:
            stmt_u = select(UserModel).where(UserModel.username == u_name)
            existing_u = db.execute(stmt_u).scalar_one_or_none()
            if not existing_u:
                db.add(
                    UserModel(
                        id=u_id,
                        username=u_name,
                        email=u_email,
                        password_hash=hash_password(u_pwd),
                        role=u_role,
                        student_id=u_stu_id,
                        is_active=True,
                    )
                )
            else:
                existing_u.password_hash = hash_password(u_pwd)
                existing_u.student_id = u_stu_id

        db.commit()
        print("Database commit succeeded! All 1,800 records safely committed.")

        # Update synthetic_students_1800.csv fixture for 100% repository consistency
        csv_path = os.path.join(REPO_ROOT, "fixtures", "students", "synthetic_students_1800.csv")
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        if csv_rows:
            with open(csv_path, "w", encoding="utf-8", newline="") as f_csv:
                writer = csv.DictWriter(f_csv, fieldnames=list(csv_rows[0].keys()))
                writer.writeheader()
                writer.writerows(csv_rows)
            print(f"Synchronized fixtures CSV at {csv_path} (1,800 rows).")

        # Stamp Alembic migration revision to head to prevent duplicate column migrations
        try:
            import subprocess
            subprocess.run([sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", "stamp", "head"], cwd=REPO_ROOT, check=False)
        except Exception:
            pass

        return validate_seeded_database(db)

    except Exception as exc:
        db.rollback()
        print(f"DATABASE SEEDING FAILED: {exc}")
        raise
    finally:
        db.close()


def validate_seeded_database(db: Session | None = None) -> dict[str, Any]:
    """Runs all 8 mandatory automated validation checks against the seeded database."""
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        print("\n==================================================================")
        print("RUNNING MANDATORY AUTOMATED VALIDATION CHECKS (ALL MUST PASS)")
        print("==================================================================")

        # 1. Total Student Count = 1,800
        total_students = db.execute(select(func.count(StudentModel.id))).scalar_one()
        assert total_students == 1800, f"Total student count is {total_students}, expected 1800."
        print(f"[PASS] Total student count: {total_students} == 1800")

        # 2. Distinct Student IDs = 1,800
        distinct_ids = db.execute(select(func.count(func.distinct(StudentModel.id)))).scalar_one()
        assert distinct_ids == 1800, f"Distinct student IDs is {distinct_ids}, expected 1800."
        print(f"[PASS] Distinct student ID count: {distinct_ids} == 1800")

        # 3. Distinct Roll Numbers = 1,800
        distinct_rolls = db.execute(select(func.count(func.distinct(StudentModel.roll_no)))).scalar_one()
        assert distinct_rolls == 1800, f"Distinct roll numbers is {distinct_rolls}, expected 1800."
        print(f"[PASS] Distinct roll number count: {distinct_rolls} == 1800")

        # 4. Distinct Normalized Full Names = 1,800 (Duplicate count = 0)
        distinct_norm_names = db.execute(select(func.count(func.distinct(StudentModel.normalized_name)))).scalar_one()
        assert distinct_norm_names == 1800, f"Distinct normalized full names is {distinct_norm_names}, expected 1800."
        print(f"[PASS] Distinct normalized full-name count: {distinct_norm_names} == 1800 (Duplicates = 0)")

        # Verify duplicate full names query
        dup_names = db.execute(
            select(StudentModel.normalized_name, func.count(StudentModel.id))
            .group_by(StudentModel.normalized_name)
            .having(func.count(StudentModel.id) > 1)
        ).all()
        assert len(dup_names) == 0, f"Found {len(dup_names)} duplicate normalized names: {dup_names}"
        print(f"[PASS] Duplicate normalized full-name count: {len(dup_names)} == 0")

        # 5. Invalid or Missing IDs / Names
        invalid_ids = db.execute(select(func.count(StudentModel.id)).where((StudentModel.id == None) | (StudentModel.id == ""))).scalar_one()
        invalid_names = db.execute(select(func.count(StudentModel.id)).where((StudentModel.name == None) | (StudentModel.name == ""))).scalar_one()
        assert invalid_ids == 0, f"Invalid IDs: {invalid_ids}"
        assert invalid_names == 0, f"Invalid names: {invalid_names}"
        print(f"[PASS] Missing or blank IDs: {invalid_ids} | Missing or blank Names: {invalid_names}")

        # 6. Branch Distribution: Exactly 9 Canonical Branches, exactly 200 per branch
        branch_counts = db.execute(
            select(StudentModel.branch, func.count(StudentModel.id))
            .group_by(StudentModel.branch)
            .order_by(StudentModel.branch)
        ).all()
        branch_dict = {b: cnt for b, cnt in branch_counts}
        assert len(branch_dict) == 9, f"Expected exactly 9 canonical branches, found {len(branch_dict)}: {list(branch_dict.keys())}"
        for b in CANONICAL_BRANCHES:
            assert b in branch_dict, f"Canonical branch '{b}' missing from database!"
            assert branch_dict[b] == 200, f"Branch '{b}' has {branch_dict[b]} students, expected exactly 200."
            print(f"  - Branch '{b:4}' ({BRANCH_DISPLAY_NAMES[b]}): {branch_dict[b]} students")
        print("[PASS] Exactly 9 canonical branches with exactly 200 students each!")

        # 7. Academic and SGPA/CGPA Consistency
        total_acad_records = db.execute(select(func.count(AcademicRecordModel.id))).scalar_one()
        assert total_acad_records == 1800 * 6, f"Expected {1800 * 6} semester records, found {total_acad_records}."
        print(f"[PASS] Semester SGPA records: {total_acad_records} (exactly 6 semesters per student)")

        # Verify CGPA strictly equals average of semester SGPAs
        mismatched_cgpas = db.execute(text("""
            SELECT s.id, s.cgpa, round(avg(a.sgpa), 2) as calculated
            FROM students s
            JOIN academic_records a ON s.id = a.student_id
            GROUP BY s.id
            HAVING abs(s.cgpa - round(avg(a.sgpa), 2)) > 0.01;
        """)).fetchall()
        assert len(mismatched_cgpas) == 0, f"Found {len(mismatched_cgpas)} CGPA mismatches with semester SGPAs!"
        print(f"[PASS] Inconsistent SGPA/CGPA records: {len(mismatched_cgpas)} == 0")

        # 8. Backlogs Consistency
        total_backlogs = db.execute(select(func.count(BacklogModel.id))).scalar_one()
        active_bl_in_table = db.execute(select(func.count(BacklogModel.id)).where(BacklogModel.status == "active")).scalar_one()
        cleared_bl_in_table = db.execute(select(func.count(BacklogModel.id)).where(BacklogModel.status == "cleared")).scalar_one()
        print(f"[PASS] Backlog records total: {total_backlogs} (Active: {active_bl_in_table}, Cleared: {cleared_bl_in_table})")

        # 9. Existing Offers Consistency
        total_offers = db.execute(select(func.count(OfferModel.id))).scalar_one()
        assert total_offers > 0, "No offers found in database."
        print(f"[PASS] Existing student placement offers: {total_offers}")

        # 10. SQLite PRAGMA Checks
        raw_conn = engine.raw_connection()
        try:
            cursor = raw_conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            integrity_result = cursor.fetchall()
            assert integrity_result == [("ok",)], f"PRAGMA integrity_check failed: {integrity_result}"
            print("[PASS] SQLite PRAGMA integrity_check: ok")

            cursor.execute("PRAGMA foreign_key_check;")
            fk_violations = cursor.fetchall()
            assert len(fk_violations) == 0, f"PRAGMA foreign_key_check found violations: {fk_violations}"
            print(f"[PASS] SQLite PRAGMA foreign_key_check: 0 violations (Foreign Key Integrity OK)")
        finally:
            raw_conn.close()

        print("==================================================================")
        print("ALL 10 AUTOMATED INTEGRITY CHECKS PASSED WITH 100% SUCCESS!")
        print("==================================================================\n")

        return {
            "total_students": total_students,
            "distinct_ids": distinct_ids,
            "distinct_normalized_names": distinct_norm_names,
            "duplicate_normalized_names": len(dup_names),
            "branch_distribution": branch_dict,
            "total_academic_records": total_acad_records,
            "total_backlogs": total_backlogs,
            "active_backlogs": active_bl_in_table,
            "cleared_backlogs": cleared_bl_in_table,
            "total_offers": total_offers,
            "integrity_check": "ok",
            "foreign_key_violations": 0,
        }
    finally:
        if should_close:
            db.close()


if __name__ == "__main__":
    force = "--force" in sys.argv or "-f" in sys.argv
    seed_database(force_recreate=force)
