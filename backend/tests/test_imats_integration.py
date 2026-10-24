"""
IMATS ERP Integration Contract Tests.
Verifies port interface compliance, exponential backoff, idempotency keys, and offline outbox.
"""

from __future__ import annotations

import pytest

from backend.app.integrations.imats.client import SandboxIMATSClient
from backend.app.integrations.imats.models import OutboxStatus
from backend.app.integrations.imats.outbox import IMATSOutboxManager


@pytest.fixture
def imats_client() -> SandboxIMATSClient:
    return SandboxIMATSClient(is_online=True, initial_backoff_sec=0.01)


@pytest.fixture
def outbox_manager() -> IMATSOutboxManager:
    return IMATSOutboxManager()


def test_imats_client_contract(imats_client: SandboxIMATSClient) -> None:
    # 1. Push Shortlist
    shortlist_res = imats_client.push_shortlist(
        drive_id="drv_001",
        student_ids=["s1", "s2", "s3"],
        idempotency_key="key_sl_1",
    )
    assert shortlist_res["status"] == "acknowledged"
    assert shortlist_res["candidates_count"] == 3
    assert imats_client.stored_shortlists["drv_001"] == ["s1", "s2", "s3"]

    # 2. Push Schedule
    schedule_res = imats_client.push_schedule(
        drive_id="drv_001",
        schedule_items=[{"slot": 1, "room": "Cabin 1"}],
        idempotency_key="key_sc_1",
    )
    assert schedule_res["status"] == "acknowledged"
    assert schedule_res["slots_count"] == 1

    # 3. Fetch Drive Requirements
    reqs = imats_client.fetch_drive_requirements(company_id="comp_1", drive_code="DRV_2026_01")
    assert reqs["min_cgpa"] == 7.0
    assert "CSE" in reqs["allowed_branches"]


def test_imats_idempotency_deduplication(imats_client: SandboxIMATSClient) -> None:
    # First call
    res_1 = imats_client.push_shortlist(
        drive_id="drv_002",
        student_ids=["s10"],
        idempotency_key="idempotent_key_999",
    )

    # Identical replay call
    res_2 = imats_client.push_shortlist(
        drive_id="drv_002",
        student_ids=["s10"],
        idempotency_key="idempotent_key_999",
    )

    assert res_1 == res_2
    # Ensure idempotency cache returned directly without re-incrementing call attempts
    assert imats_client.calls_attempted == 1


def test_imats_retry_with_exponential_backoff(imats_client: SandboxIMATSClient) -> None:
    # Configure 2 transient network failures
    imats_client.simulate_transient_failures(2)

    # Attempt call (should fail twice, backoff, and succeed on 3rd attempt)
    res = imats_client.push_shortlist(
        drive_id="drv_003",
        student_ids=["s20", "s21"],
        idempotency_key="key_retry_test",
    )

    assert res["status"] == "acknowledged"
    assert imats_client.calls_attempted == 3  # 2 failed + 1 success


def test_offline_outbox_queue_and_flush(
    imats_client: SandboxIMATSClient,
    outbox_manager: IMATSOutboxManager,
) -> None:
    # 1. Simulate network disconnect
    imats_client.is_online = False

    # 2. Enqueue items while offline
    e1 = outbox_manager.queue_shortlist(drive_id="drv_off_1", student_ids=["s100"])
    e2 = outbox_manager.queue_schedule(drive_id="drv_off_1", schedule_items=[{"item": "slot"}])

    assert e1.status == OutboxStatus.PENDING
    assert e2.status == OutboxStatus.PENDING
    assert len(outbox_manager.list_entries(status=OutboxStatus.PENDING)) == 2

    # Flush fails while still offline
    stats_fail = outbox_manager.flush(imats_client)
    assert stats_fail["failed"] == 2
    assert stats_fail["sent"] == 0

    # 3. Network connection restored
    imats_client.is_online = True

    stats_success = outbox_manager.flush(imats_client)
    assert stats_success["processed"] == 2
    assert stats_success["sent"] == 2
    assert stats_success["failed"] == 0

    # All entries now SENT
    assert len(outbox_manager.list_entries(status=OutboxStatus.PENDING)) == 0
    assert len(outbox_manager.list_entries(status=OutboxStatus.SENT)) == 2
