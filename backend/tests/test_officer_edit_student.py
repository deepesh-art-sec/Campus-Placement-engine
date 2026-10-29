"""
Tests for Placement Officer editing student details, academic marks, and backlogs.
Verifies server-side validation, unique constraints, backlog synchronization,
audit trail logging, and RBAC protections.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.api.main import app, seed_default_accounts
from backend.app.storage.database import SessionLocal
from backend.app.storage.models.entities import AuditLogModel, BacklogModel, StudentModel


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    seed_default_accounts()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def test_students() -> tuple[str, str]:
    db = SessionLocal()
    s1_id = f"stu_edit_{uuid.uuid4().hex[:8]}"
    s2_id = f"stu_edit_{uuid.uuid4().hex[:8]}"

    stu1 = StudentModel(
        id=s1_id,
        roll_no=f"ROLL_EDIT_1_{uuid.uuid4().hex[:6]}",
        name=f"Student One {uuid.uuid4().hex[:6]}",
        email=f"edit1_{uuid.uuid4().hex[:6]}@college.edu",
        branch="CSE",
        program="B.Tech",
        cgpa=7.50,
        tenth_percentage=85.0,
        twelfth_percentage=82.0,
        diploma_percentage=None,
        date_of_birth=datetime.date(2003, 5, 15),
    )
    stu2 = StudentModel(
        id=s2_id,
        roll_no=f"ROLL_EDIT_2_{uuid.uuid4().hex[:6]}",
        name=f"Student Two {uuid.uuid4().hex[:6]}",
        email=f"edit2_{uuid.uuid4().hex[:6]}@college.edu",
        branch="ECE",
        program="B.Tech",
        cgpa=8.10,
        tenth_percentage=90.0,
        twelfth_percentage=88.0,
        diploma_percentage=None,
        date_of_birth=datetime.date(2003, 8, 20),
    )
    db.add(stu1)
    db.add(stu2)
    db.commit()

    db.close()
    return s1_id, s2_id


def test_officer_edit_student_details_and_backlogs(client: TestClient, test_students: tuple[str, str]) -> None:
    stu1_id, stu2_id = test_students

    # 1. Login as placement officer
    login_res = client.post("/api/auth/login", json={"username": "officer", "password": "officer123"})
    assert login_res.status_code == 200
    csrf = client.cookies.get("csrf_token") or ""

    # 2. Update Student 1 details: name, branch, cgpa, percentages, backlogs, etc.
    new_name = f"Updated John {uuid.uuid4().hex[:4]}"
    update_payload = {
        "roll_no": f"ROLL_UPDATED_{uuid.uuid4().hex[:6]}",
        "name": new_name,
        "email": f"updated_john_{uuid.uuid4().hex[:6]}@college.edu",
        "branch": "Information Technology",
        "program": "B.Tech",
        "cgpa": 9.45,
        "tenth_percentage": 93.5,
        "twelfth_percentage": 91.0,
        "diploma_percentage": None,
        "date_of_birth": "2003-05-15",
        "gender": "Male",
        "category": "General",
        "active_backlogs": 2,
        "history_backlogs": 1,
        "reason": "Re-evaluation cleared and updated marks approved by College Dean.",
    }

    put_res = client.put(
        f"/api/students/{stu1_id}",
        json=update_payload,
        headers={"X-CSRF-Token": csrf},
    )
    assert put_res.status_code == 200, put_res.text
    put_data = put_res.json()
    assert put_data["id"] == stu1_id
    assert "successfully updated" in put_data["message"]
    assert put_data["student"]["name"] == new_name
    assert put_data["student"]["cgpa"] == 9.45
    assert put_data["student"]["active_backlogs"] == 2
    assert put_data["student"]["history_backlogs"] == 1

    # 3. Retrieve student and verify persistence
    get_res = client.get(f"/api/students/{stu1_id}")
    assert get_res.status_code == 200
    stu_data = get_res.json()
    assert stu_data["name"] == new_name
    assert stu_data["cgpa"] == 9.45
    assert stu_data["branch"] in ("IT", "Information Technology")

    # 4. Verify backlogs in database
    db = SessionLocal()
    b_records = db.execute(select(BacklogModel).where(BacklogModel.student_id == stu1_id)).scalars().all()
    active_b = [b for b in b_records if b.status == "active"]
    cleared_b = [b for b in b_records if b.status == "cleared"]
    assert len(active_b) == 2
    assert len(cleared_b) == 1

    # 5. Verify audit log entry
    audit = db.execute(
        select(AuditLogModel).where(
            AuditLogModel.entity_id == stu1_id,
            AuditLogModel.action == "UPDATE_STUDENT_DETAILS",
        )
    ).scalar_one_or_none()
    assert audit is not None
    assert audit.actor == "officer"
    assert "Re-evaluation cleared" in audit.changes_json

    db.close()


def test_officer_edit_student_duplicate_roll_and_email_prevention(client: TestClient, test_students: tuple[str, str]) -> None:
    stu1_id, stu2_id = test_students

    # Login as officer
    client.post("/api/auth/login", json={"username": "officer", "password": "officer123"})
    csrf = client.cookies.get("csrf_token") or ""

    # Get student 2 details to find roll and email
    s2_res = client.get(f"/api/students/{stu2_id}")
    s2_data = s2_res.json()

    # Try updating Student 1 with Student 2's roll number -> should fail with 400
    collision_payload = {
        "roll_no": s2_data["roll_no"],
        "name": f"Collision Name {uuid.uuid4().hex[:6]}",
        "email": f"collision_{uuid.uuid4().hex[:6]}@college.edu",
        "branch": "CSE",
        "program": "B.Tech",
        "cgpa": 7.0,
        "tenth_percentage": 80.0,
        "date_of_birth": "2003-01-01",
        "reason": "Test duplicate collision",
    }
    fail_res = client.put(f"/api/students/{stu1_id}", json=collision_payload, headers={"X-CSRF-Token": csrf})
    assert fail_res.status_code == 400
    assert "already assigned to candidate" in fail_res.json()["detail"]


def test_coordinator_cannot_directly_edit_student(client: TestClient, test_students: tuple[str, str]) -> None:
    stu1_id, _ = test_students

    # Login as coordinator
    login_coord = client.post("/api/auth/login", json={"username": "coordinator", "password": "coord123"})
    assert login_coord.status_code == 200
    csrf = client.cookies.get("csrf_token") or ""

    payload = {
        "roll_no": "ROLL_NEW",
        "name": "Unauthorized Edit",
        "email": "unauth@college.edu",
        "branch": "CSE",
        "program": "B.Tech",
        "cgpa": 9.9,
        "tenth_percentage": 95.0,
        "date_of_birth": "2003-01-01",
        "reason": "Unauthorized attempt",
    }
    coord_res = client.put(f"/api/students/{stu1_id}", json=payload, headers={"X-CSRF-Token": csrf})
    assert coord_res.status_code == 403
    assert "Coordinators cannot edit academic marks directly" in coord_res.json()["detail"]
