"""
End-to-End Placement Workflow API Integration Tests.
Verifies complete pipeline: extraction -> review -> eligibility -> schedule -> what-if -> publish -> live enforcement -> replay.
"""

from __future__ import annotations

import datetime
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.api.main import app, seed_default_accounts
from backend.app.storage.database import SessionLocal
from backend.app.storage.models.entities import CompanyModel, DriveModel, StudentModel


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    seed_default_accounts()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_officer_headers(client: TestClient) -> dict[str, str]:
    login_res = client.post("/api/auth/login", json={"username": "officer", "password": "officer123"})
    assert login_res.status_code == 200
    csrf = login_res.json()["csrf_token"]
    return {"X-CSRF-Token": csrf}


@pytest.fixture
def setup_pipeline_data() -> tuple[str, str, str]:
    db = SessionLocal()
    # 0. Seed Company
    comp = db.execute(select(CompanyModel).where(CompanyModel.id == "comp_pipe")).scalar_one_or_none()
    if not comp:
        comp = CompanyModel(
            id="comp_pipe",
            name="Pipeline Systems",
            tier="Tier 1",
        )
        db.add(comp)

    # 1. Seed Drive
    d = db.execute(select(DriveModel).where(DriveModel.id == "drv_pipe_01")).scalar_one_or_none()
    if not d:
        d = DriveModel(
            id="drv_pipe_01",
            company_id="comp_pipe",
            company_name="Pipeline Systems",
            drive_date=datetime.date(2026, 11, 20),
            mode="on_campus",
            status="draft",
            ctc_lpa=16.0,
            version=1,
        )
        db.add(d)
    else:
        d.version = 1
        d.status = "draft"

    # 2. Seed Student 1 (eligible: 8.5 CGPA, CSE)
    s1 = db.execute(select(StudentModel).where(StudentModel.roll_no == "PIPE_001")).scalar_one_or_none()
    if not s1:
        s1 = StudentModel(
            id="stu_pipe_01",
            roll_no="PIPE_001",
            name="Rohit Pipeline",
            email="rohit.pipe@college.edu",
            branch="CSE",
            program="B.Tech",
            cgpa=8.5,
            tenth_percentage=85.0,
            date_of_birth=datetime.date(2004, 1, 1),
        )
        db.add(s1)

    # 3. Seed Student 2 (ineligible: 6.5 CGPA, Civil)
    s2 = db.execute(select(StudentModel).where(StudentModel.roll_no == "PIPE_002")).scalar_one_or_none()
    if not s2:
        s2 = StudentModel(
            id="stu_pipe_02",
            roll_no="PIPE_002",
            name="Siddharth Pipe",
            email="sid.pipe@college.edu",
            branch="Civil Engineering",
            program="B.Tech",
            cgpa=6.5,
            tenth_percentage=70.0,
            date_of_birth=datetime.date(2004, 2, 2),
        )
        db.add(s2)

    db.commit()
    res = (str(d.id), str(s1.id), str(s2.id))
    db.close()
    return res


def test_requirement_extraction_api(
    client: TestClient,
    auth_officer_headers: dict[str, str],
) -> None:
    text = (
        "Uber is hiring Software Engineers for campus 2026. "
        "Compensation package: 35 LPA. Minimum CGPA required is 8.0 with no standing backlogs. "
        "Eligible branches: CSE and IT only."
    )
    res = client.post(
        "/api/extract/parse",
        data={"text": text, "company_name": "Uber"},
        headers=auth_officer_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["company_name"] == "Uber"
    assert data["ctc_lpa"] == 35.0
    assert data["fields"]["cgpa_min"]["extracted_value"] == 8.0
    assert "CSE" in data["fields"]["allowed_branches"]["extracted_value"]


def test_eligibility_run_and_scheduling_workflow(
    client: TestClient,
    auth_officer_headers: dict[str, str],
    setup_pipeline_data: tuple[str, str, str],
) -> None:
    drive_id, stu_1_id, stu_2_id = setup_pipeline_data

    # 1. Run eligibility
    elig_res = client.post(
        "/api/eligibility/run",
        json={"drive_id": drive_id},
        headers=auth_officer_headers,
    )
    assert elig_res.status_code == 200
    data = elig_res.json()
    assert data["drive_id"] == drive_id
    assert data["total_evaluated"] >= 2

    # 2. Get decisions
    dec_res = client.get(f"/api/eligibility/decisions/{drive_id}")
    assert dec_res.status_code == 200
    decisions = dec_res.json()
    assert len(decisions) >= 1

    # 3. Generate schedule
    sched_res = client.post(
        "/api/schedules/generate",
        json={"drive_id": drive_id, "num_panels": 2, "round_duration_minutes": 30},
        headers=auth_officer_headers,
    )
    assert sched_res.status_code == 200
    sched_data = sched_res.json()
    assert sched_data["zero_clashes_verified"] is True
    assert sched_data["clash_count"] == 0


def test_what_if_and_publish_lifecycle(
    client: TestClient,
    auth_officer_headers: dict[str, str],
    setup_pipeline_data: tuple[str, str, str],
) -> None:
    drive_id, _, _ = setup_pipeline_data

    # 1. What-If Simulation (in-memory)
    sim_res = client.post(
        "/api/what-if/simulate",
        json={
            "change_type": "cgpa_cutoff",
            "drive_id": drive_id,
            "target_field": "cgpa",
            "old_value": 8.0,
            "new_value": 6.0,
        },
        headers=auth_officer_headers,
    )
    assert sim_res.status_code == 200
    report = sim_res.json()
    assert "Lowering the CGPA cut-off" in report["headline"]

    # 2. Publish Drive
    pub_res = client.post(
        f"/api/drives/{drive_id}/publish",
        json={"expected_base_version": 1, "reason": "Official publish"},
        headers=auth_officer_headers,
    )
    assert pub_res.status_code == 200
    pub_data = pub_res.json()
    assert pub_data["version"] == 2
    assert pub_data["is_published"] is True

    # 3. Rollback Drive
    roll_res = client.post(
        f"/api/drives/{drive_id}/rollback",
        json={"target_version": 2, "reason": "Test rollback"},
        headers=auth_officer_headers,
    )
    assert roll_res.status_code == 200
    assert roll_res.json()["current_version"] == 3


def test_event_result_recording_and_dispute_comparison(
    client: TestClient,
    auth_officer_headers: dict[str, str],
    setup_pipeline_data: tuple[str, str, str],
) -> None:
    drive_id, stu_1_id, stu_2_id = setup_pipeline_data

    # 1. Record recruitment offer event
    event_res = client.post(
        "/api/events/record-result",
        json={
            "student_id": stu_1_id,
            "drive_id": drive_id,
            "event_type": "offered",
            "ctc_lpa": 16.0,
            "reason": "Final technical round clearance",
        },
        headers=auth_officer_headers,
    )
    assert event_res.status_code == 200
    data = event_res.json()
    assert data["event_type"] == "offered"
    assert "policy_changeset" in data

    # 2. Dispute Comparison
    comp_res = client.post(
        "/api/compare/students",
        json={
            "student_a_id": stu_1_id,
            "student_b_id": stu_2_id,
            "drive_id": drive_id,
        },
        headers=auth_officer_headers,
    )
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert "comparative_summary" in comp_data

    # 3. Audit Logs inspection
    audit_res = client.get("/api/audit/logs")
    assert audit_res.status_code == 200
    assert len(audit_res.json()) >= 1
