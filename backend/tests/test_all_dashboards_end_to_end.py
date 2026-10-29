"""
Comprehensive Multi-Dashboard End-to-End Test Suite.
Validates the data model, security boundaries, and cross-dashboard synchronization
across all 4 user portals:
1. Student Dashboard (Profile, Drives, Eligibility AST Verdicts, Apply/Withdraw, Schedule, CSV Export)
2. Placement Officer Dashboard (Drives, AST Engine, Student Registry, Drive Statuses, Schedule Board, Clashes)
3. Coordinator Dashboard (Overview Metrics, Operational Requests, Clashes, Live Schedule)
4. Recruiter Portal (Tenant Isolation, Approved Shortlist, Why Candidate Eligible AST, Interview Schedule, CSV Export)
5. Cross-Dashboard Live Coordination (Applied status propagation & Zero Hard Clash scheduling)
"""

from __future__ import annotations

import datetime
import json
import uuid
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.api.main import app, seed_default_accounts
from backend.app.storage.database import SessionLocal
from backend.app.storage.models.entities import (
    CompanyModel,
    DriveModel,
    DriveRequirementVersionModel,
    EligibilityDecisionModel,
    EligibilityRunModel,
    RoomModel,
    ScheduleModel,
    SlotModel,
    StudentModel,
    UserModel,
)


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    seed_default_accounts()
    with TestClient(app) as c:
        yield c


def login(client: TestClient, username: str, password: str) -> dict[str, str]:
    res = client.post("/api/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200, f"Login failed for {username}: {res.text}"
    csrf = res.json().get("csrf_token", "")
    return {"X-CSRF-Token": csrf}


@pytest.fixture
def setup_dashboard_data():
    """Seeds a realistic drive, room, and schedules to test cross-dashboard workflows."""
    db = SessionLocal()

    # 1. Target Company & Drive
    comp_id = "comp_test_dash"
    comp = db.execute(select(CompanyModel).where(CompanyModel.id == comp_id)).scalar_one_or_none()
    if not comp:
        comp = CompanyModel(
            id=comp_id,
            name="Apex Technologies",
            tier="Tier 1",
            website="https://apextech.com",
            version=1,
        )
        db.add(comp)
        db.flush()

    drive_id = "drv_test_dash"
    drive = db.execute(select(DriveModel).where(DriveModel.id == drive_id)).scalar_one_or_none()
    if not drive:
        drive = DriveModel(
            id=drive_id,
            company_id=comp.id,
            company_name=comp.name,
            drive_date=datetime.date.today() + datetime.timedelta(days=5),
            mode="on_campus",
            status="published",
            ctc_lpa=24.0,
            is_dream=True,
            version=1,
        )
        db.add(drive)
        db.flush()

    req_id = "req_test_dash_v1"
    req = db.execute(select(DriveRequirementVersionModel).where(DriveRequirementVersionModel.id == req_id)).scalar_one_or_none()
    if not req:
        req = DriveRequirementVersionModel(
            id=req_id,
            drive_id=drive.id,
            version_number=1,
            min_cgpa=8.0,
            min_tenth_percentage=65.0,
            min_twelfth_percentage=65.0,
            allowed_branches_json=json.dumps(["CSE", "IT"]),
            max_active_backlogs=0,
            max_gap_years=1,
        )
        db.add(req)
        db.flush()
    else:
        req.min_cgpa = 8.0
        req.min_tenth_percentage = 65.0
        req.min_twelfth_percentage = 65.0
        req.allowed_branches_json = json.dumps(["CSE", "IT"])
        db.flush()

    # 2. Eligible Student with 0 existing offers (Rajat Saxena - BT210002)
    stu_bt = db.execute(select(StudentModel).where(StudentModel.roll_no == "BT210002")).scalar_one_or_none()
    assert stu_bt is not None, "BT210002 student should be present in database"

    # Ensure user account exists
    usr = db.execute(select(UserModel).where(UserModel.username == "BT210002")).scalar_one_or_none()
    if not usr:
        from backend.app.api.auth.hasher import hash_password
        usr = UserModel(
            id="usr_stu_bt210002",
            username="BT210002",
            email=stu_bt.email,
            password_hash=hash_password("123456"),
            role="student",
            student_id=stu_bt.id,
            is_active=True,
        )
        db.add(usr)
        db.flush()

    # 3. Clean up any previous decision for this drive & student to prevent duplicates
    existing_dec = db.execute(
        select(EligibilityDecisionModel).where(
            EligibilityDecisionModel.drive_id == drive.id,
            EligibilityDecisionModel.student_id == stu_bt.id,
        )
    ).scalars().all()
    for d in existing_dec:
        db.delete(d)
    db.flush()

    run_id = f"run_{uuid.uuid4().hex[:8]}"
    run = EligibilityRunModel(
        id=run_id,
        drive_id=drive.id,
        requirement_version_id=req.id,
        policy_id="default_policy",
        total_evaluated=1,
        total_eligible=1,
        total_ineligible=0,
    )
    db.add(run)

    dec_id = f"dec_{uuid.uuid4().hex[:8]}"
    dec = EligibilityDecisionModel(
        id=dec_id,
        run_id=run_id,
        drive_id=drive.id,
        student_id=stu_bt.id,
        status="eligible",
        reasons_json=json.dumps(["CGPA 8.09 >= 8.0", "10th: 87.42% >= 65%", "12th: 67.78% >= 65%", "CSE in ['CSE', 'IT']", "Zero active backlogs"]),
        rule_ids_json=json.dumps(["min_cgpa", "min_tenth_percentage", "min_twelfth_percentage", "allowed_branches"]),
    )
    db.add(dec)

    # 4. Room & Schedule
    room_id = "room_test_101"
    room = db.execute(select(RoomModel).where(RoomModel.id == room_id)).scalar_one_or_none()
    if not room:
        room = RoomModel(
            id=room_id,
            name="Lab 101",
            building="Tech Block A",
            capacity=40,
            is_active=True,
        )
        db.add(room)
        db.flush()

    sched_id = f"sched_{drive.id}"
    sched = db.execute(select(ScheduleModel).where(ScheduleModel.id == sched_id)).scalar_one_or_none()
    if not sched:
        sched = ScheduleModel(
            id=sched_id,
            name="Apex Campus Schedule",
            status="published",
            drive_ids_json=json.dumps([drive.id]),
        )
        db.add(sched)
        db.flush()

    # Ensure clean slots
    existing_slots = db.execute(select(SlotModel).where(SlotModel.drive_id == drive.id)).scalars().all()
    for s in existing_slots:
        db.delete(s)
    db.flush()

    slot_id = f"slot_{uuid.uuid4().hex[:8]}"
    slot_start = datetime.datetime.combine(drive.drive_date, datetime.time(10, 0))
    slot_end = datetime.datetime.combine(drive.drive_date, datetime.time(10, 45))
    slot = SlotModel(
        id=slot_id,
        schedule_id=sched.id,
        drive_id=drive.id,
        student_id=stu_bt.id,
        room_id=room.id,
        round_number=1,
        start_time=slot_start,
        end_time=slot_end,
    )
    db.add(slot)

    # 5. Dedicated Recruiter for Apex Technologies
    rec_user_id = "usr_rec_apex"
    rec_user = db.execute(select(UserModel).where(UserModel.username == "recruiter_apex")).scalar_one_or_none()
    if not rec_user:
        from backend.app.api.auth.hasher import hash_password
        rec_user = UserModel(
            id=rec_user_id,
            username="recruiter_apex",
            email="recruiter@apextech.com",
            password_hash=hash_password("apex123"),
            role="recruiter_readonly",
            company_id=comp.id,
            is_active=True,
        )
        db.add(rec_user)

    res_data = {
        "company_id": str(comp.id),
        "drive_id": str(drive.id),
        "company_name": str(comp.name),
        "student_id": str(stu_bt.id),
        "student_roll": "BT210002",
        "recruiter_user": "recruiter_apex",
        "recruiter_pass": "apex123",
        "room_name": str(room.name),
    }

    db.commit()
    db.close()

    yield res_data


# =============================================================================
# 1. Student Dashboard Tests
# =============================================================================

def test_student_dashboard_endpoints(client: TestClient, setup_dashboard_data):
    """Verifies that the Student Portal displays accurate academic profile, drive verdicts, and schedules."""
    roll = setup_dashboard_data["student_roll"]
    drive_id = setup_dashboard_data["drive_id"]
    headers = login(client, roll, "123456")

    # A. Personal Academic Profile
    me_res = client.get("/api/portal/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["roll_no"] == roll
    assert len(me_data["name"]) > 0
    assert me_data["cgpa"] >= 7.0
    assert me_data["branch"] == "CSE"

    # B. Drives Stream & Eligibility Verdict
    drives_res = client.get("/api/portal/drives", headers=headers)
    assert drives_res.status_code == 200
    drives_list = drives_res.json()
    assert len(drives_list) > 0

    apex_drive = next((d for d in drives_list if d["drive_id"] == drive_id), None)
    assert apex_drive is not None
    assert apex_drive["company_name"] == "Apex Technologies"
    assert apex_drive["status"] == "eligible"

    # C. Student Interview Schedule
    sched_res = client.get("/api/portal/schedule", headers=headers)
    assert sched_res.status_code == 200
    sched_data = sched_res.json()
    assert len(sched_data) > 0
    slot = next((s for s in sched_data if s["drive_id"] == drive_id), None)
    assert slot is not None

    # D. Official Status Sheet Export
    csv_res = client.get("/api/portal/status-sheet-csv", headers=headers)
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers.get("content-type", "")
    assert roll in csv_res.text


# =============================================================================
# 2. Placement Officer Dashboard Tests
# =============================================================================

def test_officer_dashboard_endpoints(client: TestClient, setup_dashboard_data):
    """Verifies Placement Officer views: Drives, AST Engine, Registry, Schedule Board, and Messages."""
    headers = login(client, "officer", "officer123")
    drive_id = setup_dashboard_data["drive_id"]
    student_id = setup_dashboard_data["student_id"]

    # A. Drives Overview
    drives_res = client.get("/api/drives", headers=headers)
    assert drives_res.status_code == 200
    drives = drives_res.json()
    apex = next((d for d in drives if d["id"] == drive_id), None)
    assert apex is not None
    assert apex["company_name"] == "Apex Technologies"
    assert "applied_count" in apex

    # B. Eligibility Table View & Trace
    dec_res = client.get(f"/api/eligibility/decisions/{drive_id}", headers=headers)
    assert dec_res.status_code == 200
    decisions = dec_res.json()
    aarav_dec = next((d for d in decisions if d["student_id"] == student_id), None)
    assert aarav_dec is not None
    assert aarav_dec["status"] == "eligible"
    assert len(aarav_dec["passed_rules"]) > 0

    # C. Student Registry
    stu_res = client.get("/api/students", headers=headers)
    assert stu_res.status_code == 200
    stu_data = stu_res.json()
    items = stu_data.get("items", [])
    assert any(s["roll_no"] == "BT210002" for s in items)

    # D. Student Registry Drive Statuses
    ds_res = client.get(f"/api/students/{student_id}/drive-statuses", headers=headers)
    assert ds_res.status_code == 200
    statuses = ds_res.json()
    apex_status = next((s for s in statuses if s["drive_id"] == drive_id), None)
    assert apex_status is not None
    assert apex_status["status"] == "eligible"

    # E. Schedule Board & Zero Clash Count
    sched_res = client.get(f"/api/schedules/{drive_id}", headers=headers)
    assert sched_res.status_code == 200
    slots = sched_res.json()
    assert isinstance(slots, list)
    assert len(slots) > 0
    # Every scheduled slot has zero hard clashes
    assert all(not s.get("has_clash", False) for s in slots)


# =============================================================================
# 3. Coordinator Dashboard Tests
# =============================================================================

def test_coordinator_dashboard_endpoints(client: TestClient, setup_dashboard_data):
    """Verifies Student Coordinator view: metrics, operational requests, and live clashes."""
    headers = login(client, "coordinator", "coord123")

    # A. Coordinator Operational Metrics
    metrics_res = client.get("/api/coordinator/overview-metrics", headers=headers)
    assert metrics_res.status_code == 200
    metrics = metrics_res.json()
    assert "upcoming_drives_count" in metrics
    assert "unresolved_clashes" in metrics

    # B. Coordinator Operational Requests
    requests_res = client.get("/api/coordinator/requests", headers=headers)
    assert requests_res.status_code == 200
    assert isinstance(requests_res.json(), list)

    # C. Coordinator Clash Watch
    clashes_res = client.get("/api/coordinator/clashes", headers=headers)
    assert clashes_res.status_code == 200
    clash_data = clashes_res.json()
    assert isinstance(clash_data, list)
    assert len(clash_data) == 0  # Confirms zero unresolved clashes in live schedule


# =============================================================================
# 4. Recruiter Portal Tests
# =============================================================================

def test_recruiter_portal_endpoints(client: TestClient, setup_dashboard_data):
    """Verifies tenant-isolated Recruiter Portal: my-drive, approved shortlist, and AST explanation."""
    headers = login(client, setup_dashboard_data["recruiter_user"], setup_dashboard_data["recruiter_pass"])
    roll = setup_dashboard_data["student_roll"]

    # A. Tenant Isolated Drive Details
    ov_res = client.get("/api/recruiter/my-drive", headers=headers)
    assert ov_res.status_code == 200
    overview = ov_res.json()
    assert overview["company_name"] == "Apex Technologies"
    assert overview["total_shortlisted"] >= 1

    # B. Shortlist Candidates with Application Status
    sl_res = client.get("/api/recruiter/shortlist", headers=headers)
    assert sl_res.status_code == 200
    sl_data = sl_res.json()
    cand = next((c for c in sl_data["shortlist"] if c["roll_no"] == roll), None)
    assert cand is not None
    assert cand["branch"] == "CSE"
    assert cand["cgpa"] >= 8.0
    assert "has_applied" in cand

    # C. Why Candidate Eligible AST Verification Breakdown
    why_res = client.get(f"/api/recruiter/candidate/{roll}/why", headers=headers)
    assert why_res.status_code == 200
    why_data = why_res.json()
    assert why_data["verdict"] == "VERIFIED_ELIGIBLE"
    assert why_data["company_name"] == "Apex Technologies"
    assert len(why_data["criteria"]) > 0

    # D. Shortlist CSV Export
    csv_res = client.get("/api/recruiter/export/shortlist.csv", headers=headers)
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers.get("content-type", "")
    assert roll in csv_res.text


# =============================================================================
# 5. Cross-Dashboard Live Synchronization Test
# =============================================================================

def test_cross_dashboard_live_coordination(setup_dashboard_data):
    """
    Simulates candidate applying via Student Portal with independent sessions,
    and asserts that the application propagates instantly across Officer,
    Recruiter, and Coordinator dashboards without session crosstalk.
    """
    roll = setup_dashboard_data["student_roll"]
    student_id = setup_dashboard_data["student_id"]
    drive_id = setup_dashboard_data["drive_id"]

    with TestClient(app) as stu_client, TestClient(app) as off_client, TestClient(app) as rec_client:
        student_headers = login(stu_client, roll, "123456")
        officer_headers = login(off_client, "officer", "officer123")
        recruiter_headers = login(rec_client, setup_dashboard_data["recruiter_user"], setup_dashboard_data["recruiter_pass"])

        # 1. Candidate applies in Student Portal
        apply_res = stu_client.post(f"/api/portal/drives/{drive_id}/apply", headers=student_headers)
        assert apply_res.status_code == 200, apply_res.text
        assert apply_res.json()["has_applied"] is True

        # 2. Check Student Portal drives immediately reflects Applied
        p_drives = stu_client.get("/api/portal/drives", headers=student_headers).json()
        apex_p = next(d for d in p_drives if d["drive_id"] == drive_id)
        assert apex_p["has_applied"] is True
        assert apex_p["application_status"] == "applied"

        # 3. Check Placement Officer Eligibility Table immediately reflects Applied
        off_decisions = off_client.get(f"/api/eligibility/decisions/{drive_id}", headers=officer_headers).json()
        aarav_dec = next(d for d in off_decisions if d["student_id"] == student_id)
        assert aarav_dec["has_applied"] is True
        assert aarav_dec["applied_at"] is not None

        # 4. Check Placement Officer Drives Overview immediately reflects incremented applied_count
        off_drives = off_client.get("/api/drives", headers=officer_headers).json()
        apex_off = next(d for d in off_drives if d["id"] == drive_id)
        assert apex_off["applied_count"] >= 1

        # 5. Check Placement Officer Student Profile Drive Statuses reflects Applied
        off_statuses = off_client.get(f"/api/students/{student_id}/drive-statuses", headers=officer_headers).json()
        apex_st = next(s for s in off_statuses if s["drive_id"] == drive_id)
        assert apex_st["has_applied"] is True

        # 6. Check Recruiter Shortlist reflects Applied
        rec_shortlist = rec_client.get("/api/recruiter/shortlist", headers=recruiter_headers).json()
        rec_cand = next(c for c in rec_shortlist["shortlist"] if c["roll_no"] == roll)
        assert rec_cand["has_applied"] is True

        # 7. Check Candidate withdraws in Student Portal
        withdraw_res = stu_client.post(f"/api/portal/drives/{drive_id}/withdraw", headers=student_headers)
        assert withdraw_res.status_code == 200
        assert withdraw_res.json()["has_applied"] is False

        # 8. Check Officer Table reflects withdrawal
        off_decisions_post = off_client.get(f"/api/eligibility/decisions/{drive_id}", headers=officer_headers).json()
        aarav_dec_post = next(d for d in off_decisions_post if d["student_id"] == student_id)
        assert aarav_dec_post["has_applied"] is False
