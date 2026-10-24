"""
Tests for Event Sourcing and Historical Audit Replay.
"""

from datetime import datetime, timedelta

from backend.app.events.event_service import EventService, EventType, calculate_diff
from backend.app.storage.repositories.sqlalchemy_repo import SqlAlchemyUnitOfWork


def test_calculate_diff_creates_precise_deltas() -> None:
    before = {"cgpa": 7.5, "branch": "CSE", "status": "active"}
    after = {"cgpa": 8.0, "branch": "CSE", "status": "placed"}

    diff = calculate_diff(before, after)
    assert "cgpa" in diff
    assert diff["cgpa"]["before"] == 7.5
    assert diff["cgpa"]["after"] == 8.0
    assert "status" in diff
    assert "branch" not in diff  # Unchanged


def test_event_append_and_aggregate_timeline(test_uow: SqlAlchemyUnitOfWork) -> None:
    with test_uow:
        # Event 1: Creation
        EventService.record_change(
            uow=test_uow,
            aggregate_type="student",
            aggregate_id="std-001",
            event_type=EventType.STUDENT_CREATED,
            actor="officer@college.edu",
            before_state=None,
            after_state={"roll_no": "BT01", "cgpa": 7.5, "branch": "CSE"},
        )

        # Event 2: CGPA revision
        EventService.record_change(
            uow=test_uow,
            aggregate_type="student",
            aggregate_id="std-001",
            event_type=EventType.STUDENT_UPDATED,
            actor="coordinator@college.edu",
            before_state={"roll_no": "BT01", "cgpa": 7.5, "branch": "CSE"},
            after_state={"roll_no": "BT01", "cgpa": 8.2, "branch": "CSE"},
            reason="Semester 6 re-evaluation result",
        )
        test_uow.commit()

    with test_uow:
        timeline = EventService.get_timeline(test_uow, "student", "std-001")
        assert len(timeline) == 2
        assert timeline[0].event_type == EventType.STUDENT_CREATED
        assert timeline[1].event_type == EventType.STUDENT_UPDATED
        assert timeline[1].payload["reason"] == "Semester 6 re-evaluation result"


def test_historical_state_replay_at_timestamp(test_uow: SqlAlchemyUnitOfWork) -> None:
    t0 = datetime(2026, 1, 1, 10, 0, 0)
    t1 = datetime(2026, 1, 2, 10, 0, 0)
    t2 = datetime(2026, 1, 3, 10, 0, 0)

    with test_uow:
        # Event at t0
        EventService.record_change(
            uow=test_uow,
            aggregate_type="policy",
            aggregate_id="pol-01",
            event_type=EventType.POLICY_CREATED,
            actor="officer@college.edu",
            after_state={"dream_ctc": 10.0, "max_offers": 1},
            timestamp=t0,
        )

        # Event at t2
        EventService.record_change(
            uow=test_uow,
            aggregate_type="policy",
            aggregate_id="pol-01",
            event_type=EventType.POLICY_REVISED,
            actor="officer@college.edu",
            before_state={"dream_ctc": 10.0, "max_offers": 1},
            after_state={"dream_ctc": 12.0, "max_offers": 2},
            reason="Increased salary band",
            timestamp=t2,
        )
        test_uow.commit()

    with test_uow:
        # Replay at t1 (between t0 and t2): state should reflect dream_ctc = 10.0
        state_at_t1 = EventService.replay_state_at(test_uow, "policy", "pol-01", t1)
        assert state_at_t1 is not None
        assert state_at_t1["dream_ctc"] == 10.0
        assert state_at_t1["max_offers"] == 1

        # Replay at t2 + 1 hour: state should reflect dream_ctc = 12.0
        state_at_future = EventService.replay_state_at(test_uow, "policy", "pol-01", t2 + timedelta(hours=1))
        assert state_at_future is not None
        assert state_at_future["dream_ctc"] == 12.0
        assert state_at_future["max_offers"] == 2
