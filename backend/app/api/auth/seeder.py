"""
Institutional User and Demo Student Seeder.
Ensures default administrative, demo student accounts, and multi-company recruiter partner desks exist.
"""

from __future__ import annotations

import datetime
import json

from sqlalchemy import select

from backend.app.api.auth.hasher import hash_password
from backend.app.storage.database import SessionLocal
from backend.app.storage.models.entities import (
    CompanyModel,
    DriveModel,
    DriveRequirementVersionModel,
    StudentModel,
    UserModel,
)

RECRUITER_COMPANIES = [
    {
        "id": "comp_campus_partner",
        "name": "Campus Hiring Partner",
        "username": "recruiter",
        "ctc": 18.5,
        "cgpa": 6.0,
        "role": "Software Development Engineer",
    },
    {
        "id": "comp_microsoft",
        "name": "Microsoft",
        "username": "recruiter_microsoft",
        "ctc": 44.0,
        "cgpa": 8.0,
        "role": "SDE - Cloud & AI",
    },
    {
        "id": "comp_google",
        "name": "Google",
        "username": "recruiter_google",
        "ctc": 36.0,
        "cgpa": 8.5,
        "role": "Software Development Engineer",
    },
    {
        "id": "comp_amazon",
        "name": "Amazon",
        "username": "recruiter_amazon",
        "ctc": 32.0,
        "cgpa": 7.5,
        "role": "Software Development Engineer I",
    },
    {
        "id": "comp_goldman",
        "name": "Goldman Sachs",
        "username": "recruiter_goldman",
        "ctc": 30.0,
        "cgpa": 8.0,
        "role": "Engineering Analyst",
    },
    {
        "id": "comp_qualcomm",
        "name": "Qualcomm",
        "username": "recruiter_qualcomm",
        "ctc": 28.0,
        "cgpa": 7.8,
        "role": "Associate Hardware/Firmware Engineer",
    },
    {
        "id": "comp_oracle",
        "name": "Oracle",
        "username": "recruiter_oracle",
        "ctc": 24.0,
        "cgpa": 7.5,
        "role": "Member of Technical Staff (MTS)",
    },
    {
        "id": "comp_cisco",
        "name": "Cisco",
        "username": "recruiter_cisco",
        "ctc": 22.0,
        "cgpa": 7.0,
        "role": "Technical Consulting Engineer",
    },
    {
        "id": "comp_deloitte",
        "name": "Deloitte",
        "username": "recruiter_deloitte",
        "ctc": 12.0,
        "cgpa": 6.5,
        "role": "Technology Analyst",
    },
    {
        "id": "comp_infosys",
        "name": "Infosys",
        "username": "recruiter_infosys",
        "ctc": 9.5,
        "cgpa": 6.5,
        "role": "Specialist Programmer",
    },
    {
        "id": "comp_accenture",
        "name": "Accenture",
        "username": "recruiter_accenture",
        "ctc": 8.5,
        "cgpa": 6.5,
        "role": "Advanced Application Engineering Analyst",
    },
    {
        "id": "comp_tcs",
        "name": "Tata Consultancy Services",
        "username": "recruiter_tcs",
        "ctc": 7.5,
        "cgpa": 6.0,
        "role": "Systems Engineer (Digital)",
    },
    {
        "id": "comp_wipro",
        "name": "Wipro",
        "username": "recruiter_wipro",
        "ctc": 6.5,
        "cgpa": 6.0,
        "role": "Project Engineer (Turbo)",
    },
]


def seed_default_accounts() -> None:
    """Seeds baseline institutional accounts and partner drives for local college deployment."""
    db = SessionLocal()
    try:
        # 0. Primary Administrator (admin / admin123)
        stmt_admin = select(UserModel).where(UserModel.username == "admin")
        admin_u = db.execute(stmt_admin).scalar_one_or_none()
        if not admin_u:
            admin_u = UserModel(
                id="usr_admin_root",
                username="admin",
                email="admin@college.edu",
                password_hash=hash_password("admin123"),
                role="officer",
                is_active=True,
            )
            db.add(admin_u)
        else:
            admin_u.password_hash = hash_password("admin123")

        # 1. Placement Officer (officer / officer123 or admin123)
        stmt = select(UserModel).where(UserModel.username == "officer")
        officer = db.execute(stmt).scalar_one_or_none()
        if not officer:
            officer = UserModel(
                id="usr_officer_root",
                username="officer",
                email="tpo@college.edu",
                password_hash=hash_password("officer123"),
                role="officer",
                is_active=True,
            )
            db.add(officer)
        else:
            officer.password_hash = hash_password("officer123")

        # 2. Student Placement Coordinator (coordinator / coord123 or admin123)
        stmt_coord = select(UserModel).where(UserModel.username == "coordinator")
        coord = db.execute(stmt_coord).scalar_one_or_none()
        if not coord:
            coord = UserModel(
                id="usr_coord_root",
                username="coordinator",
                email="coordinator@college.edu",
                password_hash=hash_password("coord123"),
                role="coordinator",
                is_active=True,
            )
            db.add(coord)
        else:
            coord.password_hash = hash_password("coord123")

        # 3. Seed All Partner Companies, Drives, and Recruiter Desks
        for rc in RECRUITER_COMPANIES:
            comp_id = rc["id"]
            drive_id = f"drv_{comp_id.replace('comp_', '')}"
            req_id = f"req_{comp_id.replace('comp_', '')}_v1"

            # Company
            stmt_comp = select(CompanyModel).where((CompanyModel.id == comp_id) | (CompanyModel.name == rc['name']))
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

            # Drive
            stmt_drv = select(DriveModel).where((DriveModel.id == drive_id) | (DriveModel.company_id == comp.id))
            drv = db.execute(stmt_drv).scalars().first()
            if not drv:
                drv = DriveModel(
                    id=drive_id,
                    company_id=comp.id,
                    company_name=comp.name,
                    drive_date=datetime.date.today() + datetime.timedelta(days=len(rc["name"])),
                    mode="on_campus",
                    ctc_lpa=rc["ctc"],
                    is_dream=True if rc["ctc"] >= 15.0 else False,
                    status="PUBLISHED",
                    version=1,
                )
                db.add(drv)
                db.flush()

            # Requirement Version
            stmt_req = select(DriveRequirementVersionModel).where(
                DriveRequirementVersionModel.drive_id == drv.id
            )
            req_v = db.execute(stmt_req).scalars().first()
            if not req_v:
                req_v = DriveRequirementVersionModel(
                    id=req_id,
                    drive_id=drv.id,
                    version_number=1,
                    min_cgpa=rc["cgpa"],
                    min_tenth_percentage=60.0,
                    min_twelfth_percentage=60.0,
                    max_active_backlogs=0,
                    allowed_branches_json=json.dumps([
                        "Computer Science and Engineering",
                        "Information Technology",
                        "Electronics and Communication Engineering",
                        "Data Science",
                    ]),
                )
                db.add(req_v)
                db.flush()

            # Recruiter User Account
            stmt_usr = select(UserModel).where(UserModel.username == rc["username"])
            rec_user = db.execute(stmt_usr).scalars().first()
            if not rec_user:
                rec_user = UserModel(
                    id=f"usr_{rc['username']}",
                    username=rc["username"],
                    email=f"recruiter@{comp_id.replace('comp_', '')}.com",
                    password_hash=hash_password("recruiter123"),
                    role="recruiter_readonly",
                    company_id=comp.id,
                    is_active=True,
                )
                db.add(rec_user)
            else:
                rec_user.company_id = comp.id
                rec_user.password_hash = hash_password("recruiter123")

        # 4. Default Demo Students for LAN Access & Dispute Comparison
        stmt_bt = select(StudentModel).where(StudentModel.roll_no == "BT210001")
        stu_bt = db.execute(stmt_bt).scalar_one_or_none()
        if not stu_bt:
            stu_bt = StudentModel(
                id="stu_bt210001",
                roll_no="BT210001",
                name="Aarav Patel",
                email="aarav.patel@college.edu",
                branch="CSE",
                program="B.Tech",
                cgpa=8.8,
                tenth_percentage=90.0,
                twelfth_percentage=89.0,
                date_of_birth=datetime.date(2004, 3, 15),
            )
            db.add(stu_bt)
            db.flush()

        stmt_bt_user = select(UserModel).where(UserModel.username == "BT210001")
        bt_user = db.execute(stmt_bt_user).scalar_one_or_none()
        if not bt_user:
            bt_user = UserModel(
                id="usr_stu_bt210001",
                username="BT210001",
                email="aarav.patel@college.edu",
                password_hash=hash_password("123456"),
                role="student",
                student_id=stu_bt.id,
                is_active=True,
            )
            db.add(bt_user)
        else:
            bt_user.password_hash = hash_password("123456")

        stmt_stu_user = select(UserModel).where(UserModel.username == "PIPE_001")
        stu_user = db.execute(stmt_stu_user).scalar_one_or_none()
        if not stu_user:
            stu_user = UserModel(
                id="usr_stu_pipe_001",
                username="PIPE_001",
                email="rohit.sharma@college.edu",
                password_hash=hash_password("123456"),
                role="student",
                student_id=stu_bt.id,
                is_active=True,
            )
            db.add(stu_user)
        else:
            stu_user.password_hash = hash_password("123456")

        db.commit()
    finally:
        db.close()
