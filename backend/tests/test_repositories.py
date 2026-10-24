"""
Contract tests for Repositories, Unit of Work, and Optimistic Concurrency Control.
"""

from datetime import date

import pytest

from backend.app.domain.exceptions import ConcurrencyConflictError
from backend.app.domain.models import (
    BacklogRecord,
    BacklogStatus,
    Drive,
    DriveMode,
    DriveStatus,
    RequirementSet,
    Student,
)
from backend.app.storage.repositories.sqlalchemy_repo import SqlAlchemyUnitOfWork


def make_sample_student(roll_no: str = "BT210001", version: int = 1) -> Student:
    return Student(
        id=f"std-{roll_no.lower()}",
        roll_no=roll_no,
        name="Aarav Sharma",
        email=f"{roll_no.lower()}@college.edu",
        branch="Computer Science and Engineering",
        program="B.Tech",
        cgpa=8.5,
        tenth_percentage=88.0,
        twelfth_percentage=85.0,
        date_of_birth=date(2003, 5, 12),
        backlogs=[
            BacklogRecord(
                subject="Mathematics",
                semester=2,
                status=BacklogStatus.CLEARED,
                cleared_on=date(2024, 6, 1),
            )
        ],
        version=version,
    )


def test_student_crud_and_backlogs(test_uow: SqlAlchemyUnitOfWork) -> None:
    student = make_sample_student("BT210010")

    with test_uow:
        test_uow.students.add(student)
        test_uow.commit()

    with test_uow:
        retrieved = test_uow.students.get_by_roll_no("BT210010")
        assert retrieved is not None
        assert retrieved.name == "Aarav Sharma"
        assert retrieved.cgpa == 8.5
        assert len(retrieved.backlogs) == 1
        assert retrieved.backlogs[0].status == BacklogStatus.CLEARED
        assert retrieved.backlogs[0].cleared_on == date(2024, 6, 1)


def test_optimistic_concurrency_conflict(test_uow: SqlAlchemyUnitOfWork) -> None:
    student = make_sample_student("BT210020")

    # Insert student (version 1)
    with test_uow:
        test_uow.students.add(student)
        test_uow.commit()

    # Load instance A and instance B concurrently
    with test_uow:
        inst_a = test_uow.students.get_by_roll_no("BT210020")
        inst_b = test_uow.students.get_by_roll_no("BT210020")
        assert inst_a is not None and inst_b is not None

        # Update instance A (advances version to 2)
        inst_a.cgpa = 9.1
        test_uow.students.update(inst_a)
        test_uow.commit()

    # Now instance B attempts to update using stale version 1
    with test_uow:
        inst_b.cgpa = 9.3
        with pytest.raises(ConcurrencyConflictError, match="Concurrent modification"):
            test_uow.students.update(inst_b)


def test_unit_of_work_transaction_rollback(test_uow: SqlAlchemyUnitOfWork) -> None:
    student = make_sample_student("BT210030")

    try:
        with test_uow:
            test_uow.students.add(student)
            # Intentionally simulate an error before commit
            raise RuntimeError("Simulated transaction failure")
    except RuntimeError:
        pass

    # Verify student was rolled back and NOT persisted
    with test_uow:
        retrieved = test_uow.students.get_by_roll_no("BT210030")
        assert retrieved is None


def test_drive_and_requirement_version_persistence(test_uow: SqlAlchemyUnitOfWork) -> None:
    drive = Drive(
        id="drive-google-2026",
        company_id="comp-google",
        company_name="Google",
        drive_date=date(2026, 11, 15),
        mode=DriveMode.HYBRID,
        ctc_lpa=36.0,
        is_dream=True,
        status=DriveStatus.PUBLISHED,
        version=1,
    )
    req1 = RequirementSet(
        id="req-google-v1",
        drive_id="drive-google-2026",
        version_number=1,
        min_cgpa=8.5,
        min_tenth_percentage=75.0,
        allowed_branches=["Computer Science and Engineering", "Information Technology"],
        max_active_backlogs=0,
    )
    drive.requirement_versions = [req1]
    drive.requirements = req1

    with test_uow:
        test_uow.drives.add(drive)
        test_uow.commit()

    with test_uow:
        loaded = test_uow.drives.get_by_id("drive-google-2026")
        assert loaded is not None
        assert loaded.company_name == "Google"
        assert loaded.requirements is not None
        assert loaded.requirements.min_cgpa == 8.5
        assert "Information Technology" in loaded.requirements.allowed_branches
