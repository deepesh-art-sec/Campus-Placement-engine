"""
Instant Demo State Reset Script (< 2 seconds).
Restores the database to a clean, deterministic institutional state for live presentations.
"""

from __future__ import annotations

import datetime
import os
import sys
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from alembic import command
from alembic.config import Config
from sqlalchemy import delete, select

from backend.app.api.auth.hasher import hash_password
from backend.app.api.auth.seeder import seed_default_accounts
from backend.app.domain.models import (
    BacklogRecord,
    BacklogStatus,
    Drive,
    OfferRecord,
    OfferSource,
    OfferStatus,
    Student,
)
from backend.app.storage.database import SessionLocal
from backend.app.storage.models.entities import (
    AcademicRecordModel,
    AuditLogModel,
    BacklogModel,
    CompanyModel,
    DriveModel,
    DriveRequirementVersionModel,
    EligibilityDecisionModel,
    OfferModel,
    PanelModel,
    RoomModel,
    ScheduleModel,
    SlotModel,
    StudentModel,
    UserModel,
)
from backend.app.storage.repositories.mappers import student_domain_to_entity


def reset_demo() -> None:
    start_time = time.perf_counter()
    print("========================================================")
    print("INSTITUTIONAL PLACEMENT ENGINE: DEMO STATE RESET")
    print("========================================================")

    # 1. Run migrations to ensure clean schema
    print("[1/4] Checking and syncing SQLite schema via Alembic...")
    alembic_ini_path = os.path.join(PROJECT_ROOT, "backend", "alembic.ini")
    alembic_cfg = Config(alembic_ini_path)
    alembic_cfg.set_main_option("script_location", os.path.join(PROJECT_ROOT, "backend", "alembic"))
    command.upgrade(alembic_cfg, "head")

    # 2. Clear transactional and staging tables cleanly
    print("[2/4] Clearing transactional and staging tables...")
    with SessionLocal() as db:
        db.execute(delete(SlotModel))
        db.execute(delete(ScheduleModel))
        db.execute(delete(EligibilityDecisionModel))
        db.execute(delete(PanelModel))
        db.execute(delete(DriveRequirementVersionModel))
        db.execute(delete(DriveModel))
        db.execute(delete(CompanyModel))
        db.execute(delete(BacklogModel))
        db.execute(delete(OfferModel))
        db.execute(delete(AcademicRecordModel))
        db.execute(delete(UserModel))
        db.execute(delete(StudentModel))
        db.execute(delete(RoomModel))
        db.execute(delete(AuditLogModel))
        db.commit()

        # 3. Seed Default Accounts
        print("[3/4] Seeding default authentication accounts...")
        seed_default_accounts()

        # 4. Seed Standard Demo Rooms
        rooms = [
            RoomModel(id="hall_1", name="Auditorium Hall A", building="Main Block", capacity=150, has_computers=False),
            RoomModel(id="hall_2", name="Seminar Hall B", building="Main Block", capacity=100, has_computers=False),
            RoomModel(id="lab_1", name="Computing Lab 1", building="IT Block", capacity=80, has_computers=True),
            RoomModel(id="lab_2", name="Computing Lab 2", building="IT Block", capacity=60, has_computers=True),
            RoomModel(id="cabin_1", name="Interview Cabin 1", building="Placement Cell", capacity=6, has_computers=False),
            RoomModel(id="cabin_2", name="Interview Cabin 2", building="Placement Cell", capacity=6, has_computers=False),
            RoomModel(id="cabin_3", name="Interview Cabin 3", building="Placement Cell", capacity=6, has_computers=False),
            RoomModel(id="cabin_4", name="Interview Cabin 4", building="Placement Cell", capacity=6, has_computers=False),
        ]
        db.add_all(rooms)

        # 5. Enrich Demo Students (Personas A, B, C)
        # Persona B: Priya Nair (Lateral Entry)
        stu2 = db.execute(select(StudentModel).where(StudentModel.roll_no == "PIPE_002")).scalar_one()
        stu2.name = "Priya Nair"
        stu2.branch = "Information Technology"
        stu2.cgpa = 7.8
        stu2.twelfth_percentage = None
        stu2.diploma_percentage = 82.5  # Lateral Entry
        # Cleared backlog
        db.add(
            BacklogModel(
                id="bl_pipe_002",
                student_id=stu2.id,
                subject="Engineering Mathematics",
                semester=3,
                status="cleared",
                cleared_on=datetime.date(2026, 10, 15),
            )
        )
        # Existing regular offer
        db.add(
            OfferModel(
                id="off_pipe_002",
                student_id=stu2.id,
                company="Wipro",
                ctc_lpa=6.0,
                offer_date=datetime.date(2026, 10, 1),
                source="on_campus",
                is_dream=False,
                status="accepted",
            )
        )

        # Persona C: Student 3 (Rohan Gupta - 9.8 CGPA but Policy Blocked)
        stu3 = StudentModel(
            id="stu_pipe_003",
            roll_no="PIPE_003",
            name="Rohan Gupta",
            email="rohan.gupta@college.edu",
            branch="Computer Science and Engineering",
            program="B.Tech",
            cgpa=9.8,
            tenth_percentage=95.0,
            twelfth_percentage=96.0,
            date_of_birth=datetime.date(2004, 2, 14),
        )
        db.add(stu3)
        db.flush()

        db.add(
            OfferModel(
                id="off_pipe_003",
                student_id=stu3.id,
                company="Infosys",
                ctc_lpa=8.0,
                offer_date=datetime.date(2026, 9, 25),
                source="on_campus",
                is_dream=False,
                status="accepted",
            )
        )
        db.add(
            UserModel(
                id="usr_stu_pipe_003",
                username="PIPE_003",
                email="rohan.gupta@college.edu",
                password_hash=hash_password("123456"),
                role="student",
                student_id=stu3.id,
                is_active=True,
            )
        )

        # 6. Seed Demo Companies & Drives
        today = datetime.date(2026, 11, 20)

        c1 = CompanyModel(id="comp_techcorp", name="TechCorp Solutions", industry="IT Services", tier="Standard")
        c2 = CompanyModel(id="comp_innotech", name="InnoTech Labs", industry="Product", tier="Dream")
        c3 = CompanyModel(id="comp_northwind", name="Northwind Dynamics", industry="Deep Tech", tier="Super Dream")
        db.add_all([c1, c2, c3])
        db.flush()

        # Drive 1: TechCorp (Regular, 7.5 LPA)
        d1 = DriveModel(
            id="drive_techcorp",
            company_id="comp_techcorp",
            company_name="TechCorp Solutions",
            drive_date=today,
            mode="on_campus",
            ctc_lpa=7.5,
            is_dream=False,
            status="published",
            version=1,
        )
        req1 = DriveRequirementVersionModel(
            id="req_techcorp_v1",
            drive_id="drive_techcorp",
            version_number=1,
            min_cgpa=7.0,
            min_tenth_percentage=60.0,
            min_twelfth_percentage=60.0,
            allowed_branches_json='["Computer Science and Engineering", "Information Technology", "Electronics and Communication Engineering"]',
            max_active_backlogs=0,
            max_gap_years=1,
        )
        d1.requirement_versions.append(req1)

        # Drive 2: InnoTech (Dream Drive, 14.0 LPA)
        d2 = DriveModel(
            id="drive_innotech",
            company_id="comp_innotech",
            company_name="InnoTech Labs",
            drive_date=today,
            mode="on_campus",
            ctc_lpa=14.0,
            is_dream=True,
            status="published",
            version=1,
        )
        req2 = DriveRequirementVersionModel(
            id="req_innotech_v1",
            drive_id="drive_innotech",
            version_number=1,
            min_cgpa=7.5,
            min_tenth_percentage=65.0,
            min_twelfth_percentage=65.0,
            allowed_branches_json='["Computer Science and Engineering", "Information Technology"]',
            max_active_backlogs=0,
            max_gap_years=1,
        )
        d2.requirement_versions.append(req2)

        # Drive 3: Northwind (Super-Dream Drive, 22.0 LPA)
        d3 = DriveModel(
            id="drive_northwind",
            company_id="comp_northwind",
            company_name="Northwind Dynamics",
            drive_date=today + datetime.timedelta(days=1),
            mode="on_campus",
            ctc_lpa=22.0,
            is_dream=True,
            status="published",
            version=1,
        )
        req3 = DriveRequirementVersionModel(
            id="req_northwind_v1",
            drive_id="drive_northwind",
            version_number=1,
            min_cgpa=8.5,
            min_tenth_percentage=75.0,
            min_twelfth_percentage=75.0,
            allowed_branches_json='["Computer Science and Engineering"]',
            max_active_backlogs=0,
            max_gap_years=0,
        )
        d3.requirement_versions.append(req3)

        db.add_all([d1, d2, d3])
        db.commit()

    elapsed = time.perf_counter() - start_time
    print(f"[4/4] Demo state restored successfully in {elapsed:.3f} seconds (< 2.0s target).")
    print("Accounts: officer/officer123 | coordinator/coord123 | PIPE_001/123456 | PIPE_002/123456 | PIPE_003/123456")
    print("========================================================")


if __name__ == "__main__":
    reset_demo()
