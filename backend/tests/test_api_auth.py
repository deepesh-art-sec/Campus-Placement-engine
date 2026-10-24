"""
Authentication, Session Lifecycle, Rate Limiting, and CSRF Protection Tests.
"""

from __future__ import annotations

import datetime
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.api.auth.rate_limiter import login_rate_limiter
from backend.app.api.main import app, seed_default_accounts
from backend.app.storage.database import SessionLocal
from backend.app.storage.models.entities import StudentModel


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    seed_default_accounts()
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def reset_rate_limiter() -> None:
    # Reset in-memory rate limiter state before each test
    login_rate_limiter._attempts.clear()


def test_officer_login_me_and_logout(client: TestClient) -> None:
    # 1. Login as default seeded officer
    login_res = client.post("/api/auth/login", json={"username": "officer", "password": "officer123"})
    assert login_res.status_code == 200
    data = login_res.json()
    assert data["role"] == "officer"
    assert data["username"] == "officer"
    assert "csrf_token" in data
    assert "placement_session" in client.cookies

    # 2. Get /api/auth/me
    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "officer"

    # 3. Logout
    logout_res = client.post("/api/auth/logout")
    assert logout_res.status_code == 200

    # 4. Access after logout fails
    after_res = client.get("/api/auth/me")
    assert after_res.status_code == 401


def test_student_code_issuance_and_login(client: TestClient) -> None:
    # 1. Setup a student in database
    db = SessionLocal()
    roll_no = "BT2026_TEST_01"
    stmt = select(StudentModel).where(StudentModel.roll_no == roll_no)
    stu = db.execute(stmt).scalar_one_or_none()
    if not stu:
        stu = StudentModel(
            id="stu_test_01",
            roll_no=roll_no,
            name="Alice Test",
            email="alice@college.edu",
            branch="CSE",
            program="B.Tech",
            cgpa=8.5,
            tenth_percentage=85.0,
            date_of_birth=datetime.date(2004, 5, 15),
        )
        db.add(stu)
        db.commit()
    db.close()

    # 2. Officer issues a student code
    login_res = client.post("/api/auth/login", json={"username": "officer", "password": "officer123"})
    assert login_res.status_code == 200
    csrf = login_res.json()["csrf_token"]
    issue_res = client.post(
        "/api/auth/student-otp/issue",
        json={"roll_no": roll_no},
        headers={"X-CSRF-Token": csrf},
    )
    assert issue_res.status_code == 200
    code = issue_res.json()["access_code"]
    assert len(code) == 6

    # 3. Student logs in using Roll No + Code
    client.post("/api/auth/logout")
    student_login_res = client.post(
        "/api/auth/student-login",
        json={"roll_no": roll_no, "code": code, "date_of_birth": "2004-05-15"},
    )
    assert student_login_res.status_code == 200
    data = student_login_res.json()
    assert data["role"] == "student"
    assert data["username"] == roll_no
    assert data["student_id"] == "stu_test_01"


def test_login_rate_limiting_enforcement(client: TestClient) -> None:
    # Attempt 5 incorrect logins
    for _ in range(5):
        res = client.post("/api/auth/login", json={"username": "officer", "password": "wrong_password"})
        assert res.status_code == 401

    # 6th attempt must be rejected with 429
    res_6th = client.post("/api/auth/login", json={"username": "officer", "password": "wrong_password"})
    assert res_6th.status_code == 429
    assert "Too many failed login attempts" in res_6th.json()["detail"]


def test_csrf_protection_on_mutations(client: TestClient) -> None:
    # 1. Login to obtain session and cookies
    login_res = client.post("/api/auth/login", json={"username": "officer", "password": "officer123"})
    assert login_res.status_code == 200
    csrf_token = login_res.json().get("csrf_token")
    assert csrf_token is not None

    # 2. Mutation request without CSRF header is rejected
    no_header_res = client.post("/api/policies/policy-001-strict-one-offer/activate")
    assert no_header_res.status_code == 403

    # 3. Mutation request with mismatched CSRF header is rejected
    mismatch_res = client.post(
        "/api/policies/policy-001-strict-one-offer/activate",
        headers={"X-CSRF-Token": "tampered_token_xyz"},
    )
    assert mismatch_res.status_code == 403
    assert "CSRF token mismatch" in mismatch_res.json()["detail"]

    # 4. Mutation request with matching CSRF header succeeds
    valid_res = client.post(
        "/api/policies/policy-001-strict-one-offer/activate",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert valid_res.status_code == 200
