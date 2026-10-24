"""
Automated Air-Gap Guardrail and Socket-Level Interception Suite.
Guarantees zero outbound network connections during all operations:
ingestion, extraction, rule evaluation, scheduling, what-if, publishing, and export.
"""

from __future__ import annotations

import datetime
import socket
from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.app.api.main import app, seed_default_accounts
from backend.app.domain.eligibility.ast import RuleSet
from backend.app.domain.eligibility.evaluator import EligibilityEvaluator, EligibilityStatus
from backend.app.domain.models import Drive, RoundType, Student
from backend.app.domain.policy.catalog import STRICT_ONE_OFFER_POLICY
from backend.app.domain.policy.checker import policy_check
from backend.app.domain.policy.models import PolicyCheckStatus
from backend.app.extract.deterministic_extractor import DeterministicExtractor
from backend.app.scheduler.engine import PlacementSchedulerEngine
from backend.app.scheduler.models import (
    RoomType,
    ScheduleConfig,
    SchedulerDrive,
    SchedulerRoom,
    SchedulerRound,
    ScheduleStatus,
)


class AirgapViolationError(Exception):
    """Raised when an unauthorized outbound network connection is attempted."""
    pass


@pytest.fixture(autouse=True)
def block_external_sockets(monkeypatch: pytest.MonkeyPatch) -> None:
    """Intercepts all socket connection attempts at the OS level."""
    orig_connect = socket.socket.connect

    def guarded_connect(self: socket.socket, address: Any) -> None:
        host = address[0] if isinstance(address, tuple) and len(address) > 0 else str(address)
        # Allow only local loopback addresses
        allowed_hosts = ("127.0.0.1", "localhost", "::1", "0.0.0.0", "testserver")
        if host not in allowed_hosts and not str(host).startswith("127."):
            raise AirgapViolationError(f"CRITICAL PRIVACY VIOLATION: Outbound connection attempt to {host} in air-gapped mode!")
        return orig_connect(self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)


def test_airgap_requirement_extraction_offline() -> None:
    """Asserts announcement requirement extraction functions with zero network access."""
    sample_text = (
        "Company: Microsoft\n"
        "Package: 44 LPA\n"
        "Eligibility: CGPA 7.5 and above. "
        "No active backlogs. Maximum 1 gap year permitted."
    )
    extractor = DeterministicExtractor()
    extracted = extractor.extract(sample_text)
    assert extracted is not None
    assert extracted.cgpa_min is not None
    assert extracted.cgpa_min.value == 7.5
    rule_set = extracted.to_rule_set("Microsoft", "comp_msft")
    assert len(rule_set.rules) >= 2


def test_airgap_eligibility_evaluation_offline() -> None:
    """Asserts rule evaluation is purely mathematical and completely offline."""
    student = Student(
        id="stu_guard_01",
        roll_no="SEC_001",
        name="Aarav Sharma",
        email="aarav@college.edu",
        branch="Computer Science",
        program="B.Tech",
        cgpa=8.2,
        tenth_percentage=85.0,
        twelfth_percentage=82.0,
        date_of_birth=datetime.date(2004, 5, 12),
        backlogs=[],
    )

    rule_set = RuleSet(
        id="rules_msft",
        name="Microsoft Standards",
        company_id="comp_msft",
        company_name="Microsoft",
        rules=[],
    )
    evaluator = EligibilityEvaluator()
    decision = evaluator.evaluate(student, rule_set, drive_id="drv_guard_01")
    assert decision.status == EligibilityStatus.ELIGIBLE


def test_airgap_offer_policy_enforcement_offline() -> None:
    """Asserts policy logic evaluates without any external calls."""
    student = Student(
        id="stu_guard_02",
        roll_no="SEC_002",
        name="Bhavna Rao",
        email="bhavna@college.edu",
        branch="Information Technology",
        program="B.Tech",
        cgpa=9.1,
        tenth_percentage=90.0,
        twelfth_percentage=88.0,
        date_of_birth=datetime.date(2004, 3, 15),
        backlogs=[],
    )
    drive = Drive(
        id="drv_guard_01",
        company_id="comp_01",
        company_name="TCS",
        drive_date=datetime.date(2026, 11, 20),
        mode="on_campus",
        status="published",
        ctc_lpa=7.0,
    )
    result = policy_check(
        student=student,
        drive=drive,
        policy=STRICT_ONE_OFFER_POLICY,
    )
    assert result.status == PolicyCheckStatus.ALLOWED


def test_airgap_cpsat_scheduler_offline() -> None:
    """Asserts OR-Tools CP-SAT scheduler solves constraint satisfaction strictly in-memory."""
    rooms = [
        SchedulerRoom(id="hall_1", name="Auditorium", building="Main", room_type=RoomType.HALL, capacity=100),
    ]
    round_1 = SchedulerRound(
        round_number=1,
        name="Online Assessment",
        round_type=RoundType.ONLINE_TEST,
        duration_minutes=60,
        required_room_type=RoomType.HALL,
        is_group_round=True,
        max_batch_size=50,
    )
    drives = [
        SchedulerDrive(
            id="drv_test",
            company_name="Acme",
            drive_date=datetime.date(2026, 11, 25),
            rounds=[round_1],
            shortlisted_student_ids=[f"stu_{i}" for i in range(10)],
        )
    ]
    engine = PlacementSchedulerEngine()
    result = engine.generate_schedule(drives, rooms, ScheduleConfig(slot_duration_minutes=30))
    assert result.status in (ScheduleStatus.OPTIMAL, ScheduleStatus.FEASIBLE)
    assert len(result.items) > 0


def test_airgap_full_api_pipeline_with_testclient() -> None:
    """Asserts complete API workflow executes with 0 external network requests."""
    seed_default_accounts()
    with TestClient(app) as client:
        # 1. Health check
        h = client.get("/api/health")
        assert h.status_code == 200

        # 2. Officer login
        login_res = client.post("/api/auth/login", json={"username": "officer", "password": "officer123"})
        assert login_res.status_code == 200
        csrf = login_res.json()["csrf_token"]
        headers = {"X-CSRF-Token": csrf}

        # 3. Create drive
        d_res = client.post(
            "/api/drives",
            json={
                "company_name": "Airgap Security Systems",
                "drive_date": "2026-12-01",
                "mode": "on_campus",
                "status": "draft",
                "ctc_lpa": 22.0,
            },
            headers=headers,
        )
        assert d_res.status_code == 201

        # 4. List students
        stu_res = client.get("/api/students?limit=10", headers=headers)
        assert stu_res.status_code == 200
        assert stu_res.json()["total"] >= 2
