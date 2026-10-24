"""
Seed database with synthetic dataset fixtures (students, initial drive, active policy).
"""

import json
import os
import sys
from datetime import date, datetime

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

from backend.app.domain.models import Drive, DriveMode, DriveStatus, OfferPolicy, RequirementSet
from backend.app.importers.student_importer import StudentImporter
from backend.app.storage.database import SessionLocal
from backend.app.storage.repositories.sqlalchemy_repo import SqlAlchemyUnitOfWork


def seed() -> None:
    print("Seeding database with synthetic dataset fixtures...")
    uow = SqlAlchemyUnitOfWork(SessionLocal)

    with uow:
        # 1. Seed Active Policy
        policy_path = os.path.join(ROOT_DIR, "fixtures", "policies", "policy_1_strict_one_offer.json")
        with open(policy_path, encoding="utf-8") as f:
            p_data = json.load(f)

        existing_policy = uow.policies.get_active()
        if not existing_policy:
            policy = OfferPolicy(
                id=p_data["id"],
                name=p_data["name"],
                version=p_data["version"],
                max_offers_per_student=p_data["max_offers_per_student"],
                dream_tier_ctc_lpa=p_data["dream_tier_ctc_lpa"],
                super_dream_tier_ctc_lpa=p_data["super_dream_tier_ctc_lpa"],
                allow_dream_upgrade=p_data["allow_dream_upgrade"],
                upgrade_ctc_multiplier=p_data["upgrade_ctc_multiplier"],
                strict_backlog_cutoff=p_data["strict_backlog_cutoff"],
                allow_multiple_offers_if_different_tiers=p_data["allow_multiple_offers_if_different_tiers"],
                is_active=p_data["is_active"],
            )
            uow.policies.add(policy)
            print("Seeded active offer policy.")

        # 2. Seed Sample Drive
        drives = uow.drives.list_all()
        if not drives:
            sample_drive = Drive(
                id="drive-msft-2026",
                company_id="comp-msft",
                company_name="Microsoft",
                drive_date=date(2026, 11, 10),
                mode=DriveMode.ON_CAMPUS,
                ctc_lpa=44.0,
                is_dream=True,
                status=DriveStatus.PUBLISHED,
                version=1,
            )
            req = RequirementSet(
                id="req-msft-v1",
                drive_id="drive-msft-2026",
                version_number=1,
                min_cgpa=8.0,
                min_tenth_percentage=60.0,
                min_twelfth_percentage=60.0,
                allowed_branches=[
                    "Computer Science and Engineering",
                    "Information Technology",
                    "Electronics and Communication Engineering",
                ],
                max_active_backlogs=0,
                allow_history_backlogs=True,
                max_gap_years=1,
            )
            sample_drive.requirements = req
            sample_drive.requirement_versions = [req]
            uow.drives.add(sample_drive)
            print("Seeded sample recruitment drive (Microsoft).")

        # 3. Seed Students via Importer
        student_count = uow.students.count()
        if student_count == 0:
            csv_path = os.path.join(ROOT_DIR, "fixtures", "students", "synthetic_students_1800.csv")
            with open(csv_path, "rb") as f:
                content = f.read()
            importer = StudentImporter()
            report = importer.parse_file(content, "synthetic_students_1800.csv", dry_run=False)
            uow.students.save_batch(report.imported_students)
            print(f"Seeded {len(report.imported_students)} students into SQLite database.")

        uow.commit()
    print("Seeding completed successfully.")


if __name__ == "__main__":
    seed()
