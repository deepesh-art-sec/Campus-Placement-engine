from sqlalchemy import delete
import json
import uuid
import datetime
from collections.abc import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.api.main import app, seed_default_accounts
from backend.app.storage.database import SessionLocal
from backend.app.storage.models.entities import (
    CoordinatorRequestModel,
    NotificationModel,
    StudentModel,
    UserModel,
)


@pytest.fixture
def officer_client() -> Generator[tuple[TestClient, dict[str, str]], None, None]:
    seed_default_accounts()
    with TestClient(app) as c:
        # Log in as officer
        login_res = c.post("/api/auth/login", json={"username": "officer", "password": "officer123"})
        assert login_res.status_code == 200
        csrf_token = login_res.json().get("csrf_token", "")
        headers = {"X-CSRF-Token": csrf_token}
        yield c, headers


@pytest.fixture
def db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_officer_inbox_summary_and_items(officer_client: tuple[TestClient, dict[str, str]], db: Session) -> None:
    client, headers = officer_client

    # Create a dummy coordinator request
    req_id = f"req_{uuid.uuid4().hex[:8]}"
    req = CoordinatorRequestModel(
        id=req_id,
        request_type="rule_doubt",
        title="Cutoff Clarification",
        description="Clarification needed for 60% vs 65% in 12th standard",
        submitted_by="coordinator_jane",
        status="open",
        submitted_at=datetime.datetime.utcnow(),
    )
    db.add(req)
    db.commit()

    # Test summary endpoint
    sum_res = client.get("/api/officer/inbox/summary", headers=headers)
    assert sum_res.status_code == 200
    sum_data = sum_res.json()
    assert "total_pending" in sum_data
    assert sum_data["total_pending"] >= 1

    # Test items endpoint
    items_res = client.get("/api/officer/inbox/items?status_filter=pending", headers=headers)
    assert items_res.status_code == 200
    items = items_res.json()
    assert isinstance(items, list)
    matching = [it for it in items if it["id"] == req_id]
    assert len(matching) == 1
    assert matching[0]["title"] == "Cutoff Clarification"
    assert matching[0]["source_dashboard"] == "Coordinator Dashboard"
    assert matching[0]["is_pending"] is True

    # Teardown
    db.delete(req)
    db.commit()


def test_officer_inbox_approve_student_correction(officer_client: tuple[TestClient, dict[str, str]], db: Session) -> None:
    client, headers = officer_client

    # Use an existing student from the seeded database
    student = db.query(StudentModel).first()
    assert student is not None
    orig_cgpa = student.cgpa
    new_cgpa = 9.85 if orig_cgpa != 9.85 else 9.45

    corr_id = f"corr_{uuid.uuid4().hex[:8]}"
    corr_req = CoordinatorRequestModel(
        id=corr_id,
        request_type="student_data_correction",
        title=f"Data Correction: {student.roll_no} (cgpa)",
        description="Discrepancy in semester 6 marksheet vs registry",
        submitted_by=student.roll_no,
        target_id=student.id,
        status="pending",
        payload_json=json.dumps({"field": "cgpa", "requested_value": new_cgpa}),
        submitted_at=datetime.datetime.utcnow(),
    )
    db.add(corr_req)
    db.commit()

    # Officer approves the correction
    appr_res = client.post(
        "/api/officer/inbox/approve",
        json={
            "item_id": corr_id,
            "source_type": "coordinator_request",
            "response_note": "Verified with academic cell; grade sheet updated.",
        },
        headers=headers,
    )
    assert appr_res.status_code == 200
    assert appr_res.json()["status"] == "success"

    # Verify student CGPA in SQLite was automatically updated!
    db.refresh(student)
    assert student.cgpa == new_cgpa

    # Verify request status in SQLite is now 'approved'
    db.refresh(corr_req)
    assert corr_req.status == "approved"
    assert "Verified with academic cell" in corr_req.officer_response

    # Teardown: restore student CGPA and delete request
    student.cgpa = orig_cgpa
    db.delete(corr_req)
    db.commit()


def test_officer_inbox_reject_and_comment(officer_client: tuple[TestClient, dict[str, str]], db: Session) -> None:
    client, headers = officer_client

    req_id = f"req_{uuid.uuid4().hex[:8]}"
    req = CoordinatorRequestModel(
        id=req_id,
        request_type="logistics",
        title="Extra interview room needed",
        description="Need placement room B-102 for evening round",
        submitted_by="coordinator_mike",
        status="open",
        submitted_at=datetime.datetime.utcnow(),
    )
    db.add(req)
    db.commit()

    # Add threaded comment
    comm_res = client.post(
        "/api/officer/inbox/comment",
        json={"item_id": req_id, "text": "Checking availability with estates team."},
        headers=headers,
    )
    assert comm_res.status_code == 200
    assert len(comm_res.json()["comments"]) >= 1

    # Reject request
    rej_res = client.post(
        "/api/officer/inbox/reject",
        json={"item_id": req_id, "reason": "All B-block rooms reserved for university exams."},
        headers=headers,
    )
    assert rej_res.status_code == 200
    assert rej_res.json()["status"] == "success"

    db.refresh(req)
    assert req.status == "rejected"
    assert "reserved for university exams" in req.officer_response

    # Teardown
    db.delete(req)
    db.commit()


def test_officer_inbox_send_message(officer_client: tuple[TestClient, dict[str, str]], db: Session) -> None:
    client, headers = officer_client

    send_res = client.post(
        "/api/officer/inbox/send-message",
        json={
            "recipient_role": "coordinators",
            "title": "Daily Briefing at 08:30 AM",
            "message": "All coordinators must report to the placement war room for Day 1 briefing.",
            "category": "urgent_alert",
        },
        headers=headers,
    )
    assert send_res.status_code == 201
    assert send_res.json()["status"] == "success"
    assert "broadcast_id" in send_res.json()

    # Teardown
    db.execute(delete(NotificationModel).where(NotificationModel.title == "Daily Briefing at 08:30 AM"))
    db.commit()
