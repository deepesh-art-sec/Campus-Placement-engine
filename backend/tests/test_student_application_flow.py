"""
Tests for Student Drive Application Workflow across all portals:
1. Student portal apply / withdraw actions with eligibility guardrails.
2. Verification that ineligible candidates are blocked with clear explanations.
3. Verification that application status and counts synchronize accurately across:
   - Student Portal (/api/portal/drives, /api/portal/applications)
   - Officer Dashboard Eligibility (/api/eligibility/decisions/{drive_id})
   - Officer Drives Overview (/api/drives, applied_count)
   - Officer Student Registry (/api/students/{id}/drive-statuses)
"""

from __future__ import annotations

import datetime
import json
import uuid
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, delete

from backend.app.api.auth.hasher import hash_password
from backend.app.api.main import app, seed_default_accounts
from backend.app.storage.database import SessionLocal
from backend.app.storage.models.entities import (
    AuditLogModel,
    CompanyModel,
    DriveModel,
    DriveRequirementVersionModel,
    EligibilityDecisionModel,
    EligibilityRunModel,
    NotificationModel,
    StudentApplicationModel,
    StudentModel,
    UserModel,
)


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    seed_default_accounts()
    with TestClient(app) as c:
        yield c


def login_user(client: TestClient, username: str, password: str = "testpass123") -> dict[str, str]:
    res = client.post("/api/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200, f"Login failed for {username}: {res.text}"
    return {"X-CSRF-Token": res.json()["csrf_token"]}


@pytest.fixture
def test_setup():
    db = SessionLocal()

    # 1. Company & Drive
    company_id = f"comp_{uuid.uuid4().hex[:8]}"
    company_name = f"Acme Tech {uuid.uuid4().hex[:6]}"
    company = CompanyModel(
        id=company_id,
        name=company_name,
        tier="tier_1",
    )
    db.add(company)

    drive_id = f"drv_{uuid.uuid4().hex[:8]}"
    drive = DriveModel(
        id=drive_id,
        company_id=company_id,
        company_name=company_name,
        drive_date=datetime.date.today() + datetime.timedelta(days=7),
        mode="on_campus",
        status="published",
        ctc_lpa=14.0,
        is_dream=False,
        version=1,
    )
    db.add(drive)

    req_id = f"req_{uuid.uuid4().hex[:8]}"
    req = DriveRequirementVersionModel(
        id=req_id,
        drive_id=drive_id,
        version_number=1,
        min_cgpa=7.50,
        min_tenth_percentage=65.0,
        min_twelfth_percentage=65.0,
        allowed_branches_json=json.dumps(["CSE", "IT"]),
        max_active_backlogs=0,
        max_gap_years=1,
    )
    db.add(req)

    # 2. Eligible Student & User
    stu1_id = f"stu_el_{uuid.uuid4().hex[:8]}"
    roll1 = f"ROLL_EL_{uuid.uuid4().hex[:6]}"
    stu1 = StudentModel(
        id=stu1_id,
        roll_no=roll1,
        name=f"Eligible Candidate {uuid.uuid4().hex[:6]}",
        email=f"el_{uuid.uuid4().hex[:6]}@college.edu",
        branch="CSE",
        program="B.Tech",
        cgpa=8.50,
        tenth_percentage=85.0,
        twelfth_percentage=82.0,
        diploma_percentage=None,
        date_of_birth=datetime.date(2003, 1, 1),
    )
    db.add(stu1)

    user1_id = f"usr_el_{uuid.uuid4().hex[:8]}"
    user1 = UserModel(
        id=user1_id,
        username=roll1,
        email=stu1.email,
        password_hash=hash_password("testpass123"),
        role="student",
        student_id=stu1_id,
        is_active=True,
    )
    db.add(user1)

    # 3. Ineligible Student & User (low CGPA)
    stu2_id = f"stu_inel_{uuid.uuid4().hex[:8]}"
    roll2 = f"ROLL_INEL_{uuid.uuid4().hex[:6]}"
    stu2 = StudentModel(
        id=stu2_id,
        roll_no=roll2,
        name=f"Ineligible Candidate {uuid.uuid4().hex[:6]}",
        email=f"inel_{uuid.uuid4().hex[:6]}@college.edu",
        branch="CSE",
        program="B.Tech",
        cgpa=6.20,  # Below 7.50
        tenth_percentage=70.0,
        twelfth_percentage=68.0,
        diploma_percentage=None,
        date_of_birth=datetime.date(2003, 2, 2),
    )
    db.add(stu2)

    user2_id = f"usr_inel_{uuid.uuid4().hex[:8]}"
    user2 = UserModel(
        id=user2_id,
        username=roll2,
        email=stu2.email,
        password_hash=hash_password("testpass123"),
        role="student",
        student_id=stu2_id,
        is_active=True,
    )
    db.add(user2)

    # 4. Eligibility Run & Decisions
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    run = EligibilityRunModel(
        id=run_id,
        drive_id=drive_id,
        requirement_version_id=req_id,
        policy_id="default_policy",
        total_evaluated=2,
        total_eligible=1,
        total_ineligible=1,
    )
    db.add(run)

    dec1 = EligibilityDecisionModel(
        id=f"dec_{uuid.uuid4().hex[:8]}",
        run_id=run_id,
        drive_id=drive_id,
        student_id=stu1_id,
        status="eligible",
        reasons_json=json.dumps(["Academic requirements met (Ast Verified). Offer policy clearance verified."]),
        rule_ids_json=json.dumps(["min_cgpa", "allowed_branches"]),
    )
    dec2 = EligibilityDecisionModel(
        id=f"dec_{uuid.uuid4().hex[:8]}",
        run_id=run_id,
        drive_id=drive_id,
        student_id=stu2_id,
        status="ineligible",
        reasons_json=json.dumps(["CGPA 6.20 is below required 7.50"]),
        rule_ids_json=json.dumps(["min_cgpa"]),
    )
    db.add(dec1)
    db.add(dec2)

    db.commit()

    yield {
        "company_id": company_id,
        "drive_id": drive_id,
        "eligible_student": stu1,
        "eligible_roll": roll1,
        "ineligible_student": stu2,
        "ineligible_roll": roll2,
    }

    db.close()

    # Complete teardown: Clean up test records completely to prevent polluting the live database!
    cleanup_db = SessionLocal()
    try:
        cleanup_db.execute(delete(NotificationModel).where(NotificationModel.recipient_username.in_([roll1, roll2])))
        cleanup_db.execute(delete(AuditLogModel).where(AuditLogModel.actor.in_([roll1, roll2])))
        cleanup_db.execute(delete(StudentApplicationModel).where(StudentApplicationModel.drive_id == drive_id))
        cleanup_db.execute(delete(EligibilityDecisionModel).where(EligibilityDecisionModel.drive_id == drive_id))
        cleanup_db.execute(delete(DriveRequirementVersionModel).where(DriveRequirementVersionModel.drive_id == drive_id))
        cleanup_db.execute(delete(DriveModel).where(DriveModel.id == drive_id))
        cleanup_db.execute(delete(CompanyModel).where(CompanyModel.id == company_id))
        cleanup_db.execute(delete(UserModel).where(UserModel.username.in_([roll1, roll2])))
        cleanup_db.execute(delete(StudentModel).where(StudentModel.roll_no.in_([roll1, roll2])))
        cleanup_db.commit()
    finally:
        cleanup_db.close()


def test_eligible_student_can_apply_successfully(client: TestClient, test_setup):
    roll = test_setup["eligible_roll"]
    drive_id = test_setup["drive_id"]

    headers = login_user(client, roll, "testpass123")

    # Student applies for the drive
    res = client.post(
        f"/api/portal/drives/{drive_id}/apply",
        headers=headers,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["has_applied"] is True
    assert data["application_status"] == "applied"
    assert data["drive_id"] == drive_id

    # Verify database persistence
    db = SessionLocal()
    app_record = db.execute(
        select(StudentApplicationModel).where(
            StudentApplicationModel.student_id == test_setup["eligible_student"].id,
            StudentApplicationModel.drive_id == drive_id,
        )
    ).scalar_one_or_none()
    assert app_record is not None
    assert app_record.status == "applied"

    # Verify audit log & notification
    audit = db.execute(
        select(AuditLogModel).where(
            AuditLogModel.action == "APPLY_DRIVE",
            AuditLogModel.actor == roll,
        )
    ).scalar_one_or_none()
    assert audit is not None

    notif = db.execute(
        select(NotificationModel).where(
            NotificationModel.recipient_username == test_setup["eligible_roll"],
            NotificationModel.title.contains("Application Registered"),
        )
    ).scalar_one_or_none()
    assert notif is not None
    db.close()


def test_ineligible_student_is_blocked_from_applying(client: TestClient, test_setup):
    roll = test_setup["ineligible_roll"]
    drive_id = test_setup["drive_id"]

    headers = login_user(client, roll, "testpass123")

    # Ineligible student attempts to apply
    res = client.post(
        f"/api/portal/drives/{drive_id}/apply",
        headers=headers,
    )
    assert res.status_code == 400
    assert "not eligible to apply" in res.json()["detail"].lower()

    # Verify no application record created
    db = SessionLocal()
    app_record = db.execute(
        select(StudentApplicationModel).where(
            StudentApplicationModel.student_id == test_setup["ineligible_student"].id,
            StudentApplicationModel.drive_id == drive_id,
        )
    ).scalar_one_or_none()
    assert app_record is None
    db.close()


def test_student_can_withdraw_and_reapply(client: TestClient, test_setup):
    roll = test_setup["eligible_roll"]
    drive_id = test_setup["drive_id"]

    headers = login_user(client, roll, "testpass123")

    # 1. Apply
    res_apply = client.post(
        f"/api/portal/drives/{drive_id}/apply",
        headers=headers,
    )
    assert res_apply.status_code == 200

    # 2. Withdraw
    res_wd = client.post(
        f"/api/portal/drives/{drive_id}/withdraw",
        headers=headers,
    )
    assert res_wd.status_code == 200
    wd_json = res_wd.json()
    assert wd_json.get("has_applied") is False or wd_json.get("status") == "withdrawn"
    assert wd_json.get("application_status") == "withdrawn" or wd_json.get("status") == "withdrawn"

    db = SessionLocal()
    app_record = db.execute(
        select(StudentApplicationModel).where(
            StudentApplicationModel.student_id == test_setup["eligible_student"].id,
            StudentApplicationModel.drive_id == drive_id,
        )
    ).scalar_one()
    assert app_record.status == "withdrawn"
    db.close()

    # 3. Re-apply
    res_re = client.post(
        f"/api/portal/drives/{drive_id}/apply",
        headers=headers,
    )
    assert res_re.status_code == 200
    assert res_re.json()["has_applied"] is True
    assert res_re.json()["application_status"] == "applied"


def test_applied_status_synchronized_across_dashboards(client: TestClient, test_setup):
    roll = test_setup["eligible_roll"]
    stu_id = test_setup["eligible_student"].id
    drive_id = test_setup["drive_id"]

    student_headers = login_user(client, roll, "testpass123")

    # Student applies
    client.post(
        f"/api/portal/drives/{drive_id}/apply",
        headers=student_headers,
    )

    # 1. Student Portal Drives API
    res_portal = client.get(
        "/api/portal/drives",
        headers=student_headers,
    )
    assert res_portal.status_code == 200
    portal_drives = res_portal.json()
    applied_p = next((d for d in portal_drives if d["drive_id"] == drive_id), None)
    assert applied_p is not None
    assert applied_p["has_applied"] is True
    assert applied_p["application_status"] == "applied"
    assert applied_p["applied_at"] is not None

    # 2. Student Applications endpoint
    res_apps = client.get(
        "/api/portal/applications",
        headers=student_headers,
    )
    assert res_apps.status_code == 200
    apps_list = res_apps.json()
    assert any(a["drive_id"] == drive_id and a["status"] == "applied" for a in apps_list)

    # Now login as officer for administrative endpoints
    officer_headers = login_user(client, "officer", "officer123")

    # 3. Officer Eligibility Decisions API
    res_dec = client.get(
        f"/api/eligibility/decisions/{drive_id}",
        headers=officer_headers,
    )
    assert res_dec.status_code == 200
    decisions = res_dec.json()
    cand_dec = next((d for d in decisions if d["student_id"] == stu_id), None)
    assert cand_dec is not None
    assert cand_dec["has_applied"] is True
    assert cand_dec["applied_at"] is not None

    # 4. Officer Drives Overview API (applied_count >= 1)
    res_drives = client.get(
        "/api/drives",
        headers=officer_headers,
    )
    assert res_drives.status_code == 200
    all_drives = res_drives.json()
    target_drive = next((d for d in all_drives if d["id"] == drive_id), None)
    assert target_drive is not None
    assert target_drive["applied_count"] >= 1

    # 5. Officer Student Registry Drive Statuses API
    res_statuses = client.get(
        f"/api/students/{stu_id}/drive-statuses",
        headers=officer_headers,
    )
    assert res_statuses.status_code == 200
    statuses = res_statuses.json()
    st_item = next((s for s in statuses if s["drive_id"] == drive_id), None)
    assert st_item is not None
    assert st_item["has_applied"] is True
    assert st_item["application_status"] == "applied"
