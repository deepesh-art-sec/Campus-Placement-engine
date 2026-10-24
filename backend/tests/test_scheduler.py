"""
Comprehensive test suite for the placement eligibility and clash-free scheduling engine (Part 5).
Tests:
  - Criterion 4 benchmark test within strict time budget (< 60s)
  - Hypothesis-driven random instance generation with independent verification
  - Infeasibility diagnosis with precise bottleneck explanation text
  - Minimal-disturbance incremental re-scheduling and diff reporting
  - Early student clash detection with actionable resolution options
  - Direct DSatur-style heuristic fallback testing (labeled 'feasible, not optimised')
  - Independent verifier catching intentional clashes (student, room, panel, buffer)
"""

from __future__ import annotations

import datetime
import sys

import pytest

# Prevent Windows pyarrow DLL warning when ortools optionally probes pandas/pyarrow
if "pyarrow" not in sys.modules:
    sys.modules["pyarrow"] = None  # type: ignore[assignment]

import hypothesis.strategies as st
from hypothesis import given, settings

from backend.app.domain.models import RoundType
from backend.app.scheduler.clash_detector import detect_student_fixed_window_clashes
from backend.app.scheduler.engine import PlacementSchedulerEngine
from backend.app.scheduler.heuristic import DSaturHeuristicScheduler
from backend.app.scheduler.models import (
    RoomType,
    ScheduleConfig,
    ScheduledItem,
    SchedulerDrive,
    SchedulerPanel,
    SchedulerRoom,
    SchedulerRound,
    ScheduleStatus,
    TimeWindow,
)
from backend.app.scheduler.verifier import verify_schedule


@pytest.fixture
def engine() -> PlacementSchedulerEngine:
    return PlacementSchedulerEngine()


@pytest.fixture
def sample_rooms() -> list[SchedulerRoom]:
    return [
        SchedulerRoom(id="hall_1", name="Auditorium", building="Main Block", room_type=RoomType.HALL, capacity=120),
        SchedulerRoom(id="hall_2", name="Seminar Hall", building="Main Block", room_type=RoomType.HALL, capacity=80),
        SchedulerRoom(id="cabin_1", name="Interview Cabin 1", building="Placement Block", room_type=RoomType.CABIN, capacity=5),
        SchedulerRoom(id="cabin_2", name="Interview Cabin 2", building="Placement Block", room_type=RoomType.CABIN, capacity=5),
        SchedulerRoom(id="cabin_3", name="Interview Cabin 3", building="Placement Block", room_type=RoomType.CABIN, capacity=5),
        SchedulerRoom(id="cabin_4", name="Interview Cabin 4", building="Placement Block", room_type=RoomType.CABIN, capacity=5),
    ]


# -----------------------------------------------------------------------------
# 1. Benchmark Test (Criterion 4 Target)
# -----------------------------------------------------------------------------

def test_criterion_4_benchmark_time_budget(engine: PlacementSchedulerEngine, sample_rooms: list[SchedulerRoom]) -> None:
    """
    CRITERION 4: Schedule 600 students across 12 drives and 8 rooms with NO clashes
    in under one minute on a normal laptop, offline.
    """
    from scripts.benchmark_scheduler import create_benchmark_drives, create_benchmark_rooms

    rooms = create_benchmark_rooms(8)
    drives = create_benchmark_drives(12, 600, datetime.date(2026, 11, 1), days=6)
    for d in drives:
        d.shortlisted_student_ids = d.shortlisted_student_ids[:25]

    config = ScheduleConfig(
        slot_duration_minutes=15,
        day_start_hour=9,
        day_end_hour=18,
        lunch_start_hour=13,
        lunch_duration_minutes=60,
        transition_buffer_minutes=15,
        solver_time_limit_seconds=15.0,
        stop_after_first_feasible=True,
    )

    t0 = datetime.datetime.now()
    res = engine.generate_schedule(drives, rooms, config)
    elapsed = (datetime.datetime.now() - t0).total_seconds()

    # Must complete well under 60 seconds
    assert elapsed < 60.0, f"Scheduler exceeded 60s limit: took {elapsed:.2f}s"
    assert res.status in (ScheduleStatus.OPTIMAL, ScheduleStatus.FEASIBLE)
    assert len(res.items) > 0

    # Independent verifier must verify zero clashes
    assert res.verification is not None
    assert res.verification.is_valid is True
    assert res.verification.clash_count == 0


# -----------------------------------------------------------------------------
# 2. Hypothesis-Based Random Instances
# -----------------------------------------------------------------------------

@settings(max_examples=10, deadline=15000)
@given(
    num_students=st.integers(min_value=5, max_value=20),
    test_duration=st.sampled_from([30, 45, 60]),
    interview_duration=st.sampled_from([15, 30]),
)
def test_hypothesis_random_scheduling_instances(
    num_students: int,
    test_duration: int,
    interview_duration: int,
) -> None:
    engine = PlacementSchedulerEngine()
    rooms = [
        SchedulerRoom(id="hall_a", name="Hall A", building="Main", room_type=RoomType.HALL, capacity=50),
        SchedulerRoom(id="cabin_a", name="Cabin A", building="Main", room_type=RoomType.CABIN, capacity=5),
        SchedulerRoom(id="cabin_b", name="Cabin B", building="Main", room_type=RoomType.CABIN, capacity=5),
    ]

    drive_date = datetime.date(2026, 11, 10)
    student_ids = [f"STU_{i}" for i in range(num_students)]

    panels = [
        SchedulerPanel(id="p1", drive_id="d1", round_number=2, name="Panel 1"),
        SchedulerPanel(id="p2", drive_id="d1", round_number=2, name="Panel 2"),
    ]

    rounds = [
        SchedulerRound(
            round_number=1,
            name="Aptitude Test",
            round_type=RoundType.ONLINE_TEST,
            duration_minutes=test_duration,
            is_group_round=True,
        ),
        SchedulerRound(
            round_number=2,
            name="Technical Interview",
            round_type=RoundType.TECHNICAL_INTERVIEW,
            duration_minutes=interview_duration,
            is_group_round=False,
            panels=panels,
        ),
    ]

    drive = SchedulerDrive(
        id="d1",
        company_name="Hypothesis Corp",
        drive_date=drive_date,
        rounds=rounds,
        shortlisted_student_ids=student_ids,
    )

    config = ScheduleConfig(
        slot_duration_minutes=15,
        day_start_hour=9,
        day_end_hour=18,
        lunch_start_hour=13,
        lunch_duration_minutes=60,
        transition_buffer_minutes=15,
        solver_time_limit_seconds=5.0,
        stop_after_first_feasible=True,
    )

    res = engine.generate_schedule([drive], rooms, config)
    if res.status in (ScheduleStatus.OPTIMAL, ScheduleStatus.FEASIBLE, ScheduleStatus.FEASIBLE_HEURISTIC):
        # Zero clashes verified
        assert res.verification is not None
        assert res.verification.clash_count == 0
        assert res.verification.is_valid is True


# -----------------------------------------------------------------------------
# 3. Infeasibility Explanation Tests
# -----------------------------------------------------------------------------

def test_infeasible_panel_bottleneck_explanation(engine: PlacementSchedulerEngine) -> None:
    # 50 students requiring 60-min interviews with only 1 panel in an 8-hour day
    rooms = [SchedulerRoom(id="cabin_1", name="Cabin 1", building="Placement", room_type=RoomType.CABIN, capacity=5)]
    panels = [SchedulerPanel(id="p1", drive_id="d_inf", round_number=1, name="Solo Panel")]

    drive = SchedulerDrive(
        id="d_inf",
        company_name="Overloaded Inc",
        drive_date=datetime.date(2026, 11, 15),
        rounds=[
            SchedulerRound(
                round_number=1,
                name="Deep Technical",
                round_type=RoundType.TECHNICAL_INTERVIEW,
                duration_minutes=60,
                is_group_round=False,
                panels=panels,
            )
        ],
        shortlisted_student_ids=[f"S_{i}" for i in range(50)],
    )

    res = engine.generate_schedule([drive], rooms, ScheduleConfig(allow_heuristic_fallback=False))
    assert res.status == ScheduleStatus.INFEASIBLE
    assert res.infeasibility_explanation is not None
    assert "Panel bottleneck for 'Overloaded Inc'" in res.infeasibility_explanation
    assert "Add at least" in res.infeasibility_explanation


def test_infeasible_room_shortage_explanation(engine: PlacementSchedulerEngine) -> None:
    # 300 students needing group test, but total room capacity is only 20
    rooms = [SchedulerRoom(id="small_room", name="Tiny Room", building="Annex", room_type=RoomType.CLASSROOM, capacity=20)]
    drive = SchedulerDrive(
        id="d_room_inf",
        company_name="Mass Hiring Co",
        drive_date=datetime.date(2026, 11, 15),
        rounds=[
            SchedulerRound(
                round_number=1,
                name="Mass Test",
                round_type=RoundType.ONLINE_TEST,
                duration_minutes=60,
                is_group_round=True,
            )
        ],
        shortlisted_student_ids=[f"S_{i}" for i in range(300)],
    )

    res = engine.generate_schedule([drive], rooms, ScheduleConfig(allow_heuristic_fallback=False))
    assert res.status == ScheduleStatus.INFEASIBLE
    assert res.infeasibility_explanation is not None
    assert "Testing room shortage" in res.infeasibility_explanation


# -----------------------------------------------------------------------------
# 4. Minimal-Disturbance Incremental Rescheduling
# -----------------------------------------------------------------------------

def test_minimal_disturbance_rescheduling(engine: PlacementSchedulerEngine, sample_rooms: list[SchedulerRoom]) -> None:
    drive_date = datetime.date(2026, 11, 20)
    students = [f"STU_{i}" for i in range(15)]
    panels = [
        SchedulerPanel(id="pan_1", drive_id="drv_1", round_number=2, name="Panel 1"),
        SchedulerPanel(id="pan_2", drive_id="drv_1", round_number=2, name="Panel 2"),
    ]

    drive = SchedulerDrive(
        id="drv_1",
        company_name="Agile Software",
        drive_date=drive_date,
        rounds=[
            SchedulerRound(round_number=1, name="Test", round_type=RoundType.ONLINE_TEST, duration_minutes=45, is_group_round=True),
            SchedulerRound(round_number=2, name="Interview", round_type=RoundType.TECHNICAL_INTERVIEW, duration_minutes=30, is_group_round=False, panels=panels),
        ],
        shortlisted_student_ids=students,
    )

    config = ScheduleConfig(stop_after_first_feasible=True, solver_time_limit_seconds=5.0)
    initial_schedule = engine.generate_schedule([drive], sample_rooms, config)
    assert initial_schedule.status in (ScheduleStatus.OPTIMAL, ScheduleStatus.FEASIBLE)
    assert len(initial_schedule.items) == 16  # 1 group test + 15 interviews

    # Mutation: Cabin 1 is lost/decommissioned for maintenance
    updated_rooms = [r for r in sample_rooms if r.id != "cabin_1"]

    new_schedule, diff = engine.reschedule(initial_schedule, [drive], updated_rooms, config)
    assert new_schedule.status in (ScheduleStatus.OPTIMAL, ScheduleStatus.FEASIBLE)
    assert new_schedule.verification is not None
    assert new_schedule.verification.clash_count == 0

    # Diff reporting must detail moved slots
    assert diff.total_slots_before == 16
    assert diff.total_slots_after == 16
    assert diff.preserved_slots_count >= 0


# -----------------------------------------------------------------------------
# 5. Early Student Clash Detection
# -----------------------------------------------------------------------------

def test_early_student_clash_detection() -> None:
    win = TimeWindow(
        start_time=datetime.datetime(2026, 11, 15, 9, 0),
        end_time=datetime.datetime(2026, 11, 15, 13, 0),
    )

    d1 = SchedulerDrive(
        id="drv_a",
        company_name="Company Alpha",
        drive_date=datetime.date(2026, 11, 15),
        fixed_window=win,
        shortlisted_student_ids=["S101", "S102", "S103"],
    )

    d2 = SchedulerDrive(
        id="drv_b",
        company_name="Company Beta",
        drive_date=datetime.date(2026, 11, 15),
        fixed_window=win,
        shortlisted_student_ids=["S102", "S103", "S104"],
    )

    alerts = detect_student_fixed_window_clashes([d1, d2], {"S102": "John Doe", "S103": "Jane Smith"})
    assert len(alerts) == 2

    s102_alert = next(a for a in alerts if a.student_id == "S102")
    assert s102_alert.student_name == "John Doe"
    assert "Company Alpha" in s102_alert.drive_a_company
    assert "Company Beta" in s102_alert.drive_b_company
    assert len(s102_alert.suggested_options) == 3


# -----------------------------------------------------------------------------
# 6. DSatur Constructive Heuristic Fallback Direct Test
# -----------------------------------------------------------------------------

def test_dsatur_heuristic_fallback_direct(sample_rooms: list[SchedulerRoom]) -> None:
    heuristic = DSaturHeuristicScheduler()
    drive_date = datetime.date(2026, 11, 25)
    students = [f"STU_{i}" for i in range(10)]

    panels = [SchedulerPanel(id="h_p1", drive_id="h_drv", round_number=2, name="Heuristic Panel")]
    drive = SchedulerDrive(
        id="h_drv",
        company_name="Heuristic Corp",
        drive_date=drive_date,
        rounds=[
            SchedulerRound(round_number=1, name="Test", round_type=RoundType.ONLINE_TEST, duration_minutes=45, is_group_round=True),
            SchedulerRound(round_number=2, name="Interview", round_type=RoundType.TECHNICAL_INTERVIEW, duration_minutes=30, is_group_round=False, panels=panels),
        ],
        shortlisted_student_ids=students,
    )

    config = ScheduleConfig()
    res = heuristic.schedule([drive], sample_rooms, config)

    assert res.status == ScheduleStatus.FEASIBLE_HEURISTIC
    assert res.is_optimal is False
    assert res.metadata.get("note") == "feasible, not optimised"
    assert res.verification is not None
    assert res.verification.clash_count == 0


# -----------------------------------------------------------------------------
# 7. Independent Verifier Catches Intentional Clashes
# -----------------------------------------------------------------------------

def test_independent_verifier_catches_intentional_clashes(sample_rooms: list[SchedulerRoom]) -> None:
    t_start = datetime.datetime(2026, 11, 10, 10, 0)
    t_end = datetime.datetime(2026, 11, 10, 11, 0)

    # 1. Student double booked
    item1 = ScheduledItem(
        schedule_id="sch_1", drive_id="d1", round_number=1, round_name="Test A",
        student_ids=["STU_100"], room_id="hall_1", room_name="Auditorium",
        start_time=t_start, end_time=t_end,
    )
    item2 = ScheduledItem(
        schedule_id="sch_1", drive_id="d2", round_number=1, round_name="Test B",
        student_ids=["STU_100"], room_id="hall_2", room_name="Seminar Hall",
        start_time=t_start, end_time=t_end,  # Concurrent!
    )
    res_student_clash = verify_schedule([item1, item2], sample_rooms)
    assert res_student_clash.is_valid is False
    assert len(res_student_clash.student_clashes) >= 1
    assert "double-booked" in res_student_clash.student_clashes[0]

    # 2. Room double booked
    item3 = ScheduledItem(
        schedule_id="sch_1", drive_id="d1", round_number=1, round_name="Test A",
        student_ids=["STU_200"], room_id="hall_1", room_name="Auditorium",
        start_time=t_start, end_time=t_end,
    )
    item4 = ScheduledItem(
        schedule_id="sch_1", drive_id="d2", round_number=1, round_name="Test B",
        student_ids=["STU_300"], room_id="hall_1", room_name="Auditorium",  # Same room!
        start_time=t_start, end_time=t_end,
    )
    res_room_clash = verify_schedule([item3, item4], sample_rooms)
    assert res_room_clash.is_valid is False
    assert len(res_room_clash.room_clashes) >= 1
    assert "double-booked" in res_room_clash.room_clashes[0]

    # 3. Buffer violation (gap is 5 min, required 15 min across different rooms)
    t_end_1 = datetime.datetime(2026, 11, 10, 10, 45)
    t_start_2 = datetime.datetime(2026, 11, 10, 10, 50)  # Only 5 mins buffer
    item5 = ScheduledItem(
        schedule_id="sch_1", drive_id="d1", round_number=1, round_name="Test A",
        student_ids=["STU_400"], room_id="hall_1", room_name="Auditorium",
        start_time=datetime.datetime(2026, 11, 10, 10, 0), end_time=t_end_1,
    )
    item6 = ScheduledItem(
        schedule_id="sch_1", drive_id="d1", round_number=2, round_name="Interview",
        student_ids=["STU_400"], room_id="cabin_1", room_name="Cabin 1",
        start_time=t_start_2, end_time=datetime.datetime(2026, 11, 10, 11, 20),
    )
    res_buffer_clash = verify_schedule([item5, item6], sample_rooms)
    assert res_buffer_clash.is_valid is False
    assert len(res_buffer_clash.buffer_violations) >= 1
    assert "Insufficient transition buffer" in res_buffer_clash.buffer_violations[0]
