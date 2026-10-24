"""
Ingests the complete 1,800 Synthetic Students Dataset into SQLite Database.
Creates student entities, backlog records, offers, and student login accounts.
"""

from __future__ import annotations

import os
import sys
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if "pyarrow" not in sys.modules:
    sys.modules["pyarrow"] = None

from sqlalchemy import select
from backend.app.api.auth.hasher import hash_password
from backend.app.importers.student_importer import StudentImporter
from backend.app.storage.database import SessionLocal
from backend.app.storage.models.entities import StudentModel, UserModel
from backend.app.storage.repositories.mappers import student_domain_to_entity


def load_1800_students() -> None:
    start_time = time.perf_counter()
    csv_path = os.path.join(PROJECT_ROOT, "fixtures", "students", "synthetic_students_1800.csv")
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
        return

    print(f"[*] Reading and parsing {csv_path}...")
    with open(csv_path, "rb") as f:
        content = f.read()

    importer = StudentImporter()
    report = importer.parse_file(content, "synthetic_students_1800.csv", dry_run=False)
    print(f"[+] Successfully parsed {len(report.imported_students)} students from 9 branches.")

    db = SessionLocal()
    try:
        # Precompute password hash once for all 1,800 student logins
        default_student_pwd_hash = hash_password("123456")

        # Existing roll numbers in DB
        existing_rolls = set(db.execute(select(StudentModel.roll_no)).scalars().all())
        existing_user_names = set(db.execute(select(UserModel.username)).scalars().all())

        new_students_count = 0
        new_users_count = 0

        batch_size = 200
        for i, s in enumerate(report.imported_students):
            if s.roll_no not in existing_rolls:
                entity = student_domain_to_entity(s)
                db.add(entity)
                existing_rolls.add(s.roll_no)
                new_students_count += 1

                if s.roll_no not in existing_user_names:
                    u = UserModel(
                        id=f"usr_{s.id}",
                        username=s.roll_no,
                        email=s.email,
                        password_hash=default_student_pwd_hash,
                        role="student",
                        student_id=s.id,
                        is_active=True,
                    )
                    db.add(u)
                    existing_user_names.add(s.roll_no)
                    new_users_count += 1

            if (i + 1) % batch_size == 0:
                db.commit()
                print(f"   --> Committed {i + 1}/{len(report.imported_students)} students...")

        db.commit()

        total_in_db = db.execute(select(StudentModel)).scalars().all()
        elapsed = time.perf_counter() - start_time
        print("=" * 65)
        print(f"[OK] Complete Ingestion Finished in {elapsed:.2f} seconds!")
        print(f"    - Added new students: {new_students_count}")
        print(f"    - Added student logins: {new_users_count}")
        print(f"    - Total students in DB: {len(total_in_db)}")
        print("=" * 65)
    except Exception as exc:
        db.rollback()
        print(f"[!] Error during ingestion: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    load_1800_students()
