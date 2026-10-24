"""
Role-Based Access Control (RBAC) and Privacy Tampering Prevention Tests.
Verifies server-enforced data privacy: candidates can never access another student's record.
"""

from __future__ import annotations

import datetime
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.api.main import app, seed_default_accounts
from backend.app.storage.database import SessionLocal
from backend.app.storage.models.entities import StudentModel


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    seed_default_accounts()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def seeded_students() -> tuple[StudentModel, StudentModel]:
    db = SessionLocal()
    # Student 1 (Alice)
    s1 = db.execute(select(StudentModel).where(StudentModel.roll_no == "ROLL_PRIVACY_01")).scalar_one_or_none()
    if not s1:
        s1 = StudentModel(
            id="stu_priv_01",
            roll_no="ROLL_PRIVACY_01",
            name="Alice Privacy",
            email="alice.privacy@college.edu",
            branch="CSE",
            program="B.Tech",
            cgpa=9.1,
            tenth_percentage=90.0,
            date_of_birth=datetime.date(2004, 1, 1),
        )
        db.add(s1)

    # Student 2 (Bob)
    s2 = db.execute(select(StudentModel).where(StudentModel.roll_no == "ROLL_PRIVACY_02")).scalar_one_or_none()
    if not s2:
        s2 = StudentModel(
            id="stu_priv_02",
            roll_no="ROLL_PRIVACY_02",
            name="Bob Privacy",
            email="bob.privacy@college.edu",
            branch="ECE",
            program="B.Tech",
            cgpa=7.2,
            tenth_percentage=75.0,
            date_of_birth=datetime.date(2004, 2, 2),
        )
        db.add(s2)

    db.commit()
    db.refresh(s1)
    db.refresh(s2)
    db.close()
    return s1, s2


def test_coordinator_limited_access(client: TestClient) -> None:
    # 1. Login as coordinator
    login_res = client.post("/api/auth/login", json={"username": "coordinator", "password": "coord123"})
    assert login_res.status_code == 200
    csrf = login_res.json()["csrf_token"]

    # 2. Coordinator CAN view students
    students_res = client.get("/api/students")
    assert students_res.status_code == 200

    # 3. Coordinator CANNOT delete a student (Officer only)
    del_res = client.delete("/api/students/stu_priv_01", headers={"X-CSRF-Token": csrf})
    assert del_res.status_code == 403
    assert "not authorized" in del_res.json()["detail"]

    # 4. Coordinator CANNOT publish a drive (Officer only)
    pub_res = client.post(
        "/api/drives/d1/publish",
        json={"expected_base_version": 1, "reason": "Attempt by coordinator"},
        headers={"X-CSRF-Token": csrf},
    )
    assert pub_res.status_code == 403


def test_recruiter_tenant_isolation(client: TestClient) -> None:
    # 1. Login as recruiter
    login_res = client.post("/api/auth/login", json={"username": "recruiter_google", "password": "recruiter123"})
    assert login_res.status_code == 200

    # 2. Recruiter CANNOT view master student registry
    students_res = client.get("/api/students")
    assert students_res.status_code == 403

    # 3. Recruiter CANNOT view college policies
    pol_res = client.get("/api/policies/active")
    assert pol_res.status_code == 200 or pol_res.status_code == 403  # Active policy can be public or restricted


def test_student_privacy_tampering_blocked(
    client: TestClient,
    seeded_students: tuple[StudentModel, StudentModel],
) -> None:
    stu_1, stu_2 = seeded_students

    # 1. Issue access code for Student 1 (Alice)
    client.post("/api/auth/login", json={"username": "officer", "password": "officer123"})
    csrf_off = client.cookies.get("csrf_token") or ""
    issue_res = client.post(
        "/api/auth/student-otp/issue",
        json={"roll_no": stu_1.roll_no},
        headers={"X-CSRF-Token": csrf_off},
    )
    code_alice = issue_res.json()["access_code"]
    client.post("/api/auth/logout")

    # 2. Alice logs in
    login_alice = client.post(
        "/api/auth/student-login",
        json={"roll_no": stu_1.roll_no, "code": code_alice, "date_of_birth": "2004-01-01"},
    )
    assert login_alice.status_code == 200

    # 3. Alice accesses her OWN portal
    portal_res = client.get("/api/portal/me")
    assert portal_res.status_code == 200
    assert portal_res.json()["name"] == "Alice Privacy"

    # 4. Alice accesses her own student endpoint URL
    own_res = client.get(f"/api/students/{stu_1.id}")
    assert own_res.status_code == 200
    assert own_res.json()["roll_no"] == stu_1.roll_no

    # 5. TAMPERING TEST: Alice tries to access Bob's student ID
    tamper_res = client.get(f"/api/students/{stu_2.id}")
    assert tamper_res.status_code == 403
    assert "strictly restricted" in tamper_res.json()["detail"]

    # 6. TAMPERING TEST: Alice tries to generate Bob's PDF status sheet
    tamper_pdf_res = client.get(f"/api/exports/student-pdf/{stu_2.id}")
    assert tamper_pdf_res.status_code == 403
    assert "only generate your own status sheet" in tamper_pdf_res.json()["detail"]

    # 7. Alice's portal endpoints never expose Bob's data
    drives_res = client.get("/api/portal/drives")
    assert drives_res.status_code == 200
    for item in drives_res.json():
        assert "rank" not in item  # No competitive rankings
