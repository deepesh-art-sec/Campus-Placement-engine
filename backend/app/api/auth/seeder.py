"""
Institutional User and Demo Student Seeder.
Ensures default administrative and demo student accounts exist in local SQLite.
"""

from __future__ import annotations

import datetime

from sqlalchemy import select

from backend.app.api.auth.hasher import hash_password
from backend.app.storage.database import SessionLocal
from backend.app.storage.models.entities import StudentModel, UserModel


def seed_default_accounts() -> None:
    """Seeds baseline institutional accounts for local college deployment."""
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

        # 1. Placement Officer
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

        # 2. Student Placement Coordinator
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

        # 3. Recruiter Read-Only Account
        stmt_rec = select(UserModel).where(UserModel.username == "recruiter_google")
        recruiter = db.execute(stmt_rec).scalar_one_or_none()
        if not recruiter:
            recruiter = UserModel(
                id="usr_recruiter_google",
                username="recruiter_google",
                email="campus_recruiter@google.com",
                password_hash=hash_password("recruiter123"),
                role="recruiter_readonly",
                company_id="comp_1",
                is_active=True,
            )
            db.add(recruiter)
        else:
            recruiter.password_hash = hash_password("recruiter123")

        # 4. Default Demo Students for LAN Access & Dispute Comparison
        stmt_stu = select(StudentModel).where(StudentModel.roll_no == "PIPE_001")
        stu = db.execute(stmt_stu).scalar_one_or_none()
        if not stu:
            stu = StudentModel(
                id="stu_pipe_001",
                roll_no="PIPE_001",
                name="Rohit Sharma",
                email="rohit.sharma@college.edu",
                branch="CSE",
                program="B.Tech",
                cgpa=8.5,
                tenth_percentage=88.0,
                twelfth_percentage=85.0,
                date_of_birth=datetime.date(2004, 1, 1),
            )
            db.add(stu)
            db.flush()

        stmt_stu_user = select(UserModel).where(UserModel.username == "PIPE_001")
        stu_user = db.execute(stmt_stu_user).scalar_one_or_none()
        if not stu_user:
            stu_user = UserModel(
                id="usr_stu_pipe_001",
                username="PIPE_001",
                email="rohit.sharma@college.edu",
                password_hash=hash_password("123456"),
                role="student",
                student_id=stu.id,
                is_active=True,
            )
            db.add(stu_user)
        else:
            stu_user.password_hash = hash_password("123456")

        # 5. Second Demo Student for Comparative Analysis
        stmt_stu2 = select(StudentModel).where(StudentModel.roll_no == "PIPE_002")
        stu2 = db.execute(stmt_stu2).scalar_one_or_none()
        if not stu2:
            stu2 = StudentModel(
                id="stu_pipe_002",
                roll_no="PIPE_002",
                name="Siddharth Verma",
                email="sid.verma@college.edu",
                branch="Civil Engineering",
                program="B.Tech",
                cgpa=6.5,
                tenth_percentage=72.0,
                twelfth_percentage=68.0,
                date_of_birth=datetime.date(2004, 2, 2),
            )
            db.add(stu2)
            db.flush()

        stmt_stu2_user = select(UserModel).where(UserModel.username == "PIPE_002")
        stu2_user = db.execute(stmt_stu2_user).scalar_one_or_none()
        if not stu2_user:
            stu2_user = UserModel(
                id="usr_stu_pipe_002",
                username="PIPE_002",
                email="sid.verma@college.edu",
                password_hash=hash_password("123456"),
                role="student",
                student_id=stu2.id,
                is_active=True,
            )
            db.add(stu2_user)
        else:
            stu2_user.password_hash = hash_password("123456")

        db.commit()
    finally:
        db.close()
