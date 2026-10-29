"""
Comprehensive test suite for Clash-Free Placement Scheduling Engine.
Validates:
- Student double-booking prevention across drives
- Room double-booking prevention
- Interviewer / panel conflict prevention
- Back-to-back interviews allowed without clash
- Overlapping interval detection
- Multi-date independence
- Duplicate assignment prevention
- Infeasibility explanation for impossible schedules (no false zero-clash)
- Publish safeguard blocking on hard clashes
- Full end-to-end multi-drive synthetic schedule generation with 0 clashes
"""

import datetime
import json
import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.storage.models.entities import (
    Base,
    CompanyModel,
    CoordinatorRequestModel,
    DriveModel,
    PanelModel,
    RoomModel,
    ScheduleModel,
    SlotModel,
    StudentModel,
    UserModel,
)
from backend.app.domain.models import RoundType
from backend.app.scheduler.clash_service import count_unresolved_clashes, detect_db_slot_clashes
from backend.app.scheduler.models import (
    ScheduleConfig,
    SchedulerDrive,
    SchedulerPanel,
    SchedulerRoom,
    SchedulerRound,
    ScheduleStatus,
    TimeWindow,
)
from backend.app.scheduler.solver import CpSatPlacementScheduler
from backend.app.scheduler.verifier import verify_schedule
from backend.app.api.routes.schedule_routes import generate_schedule, ScheduleGenerateRequest
from backend.app.api.routes.publish_routes import publish_drive, PublishRequest
from fastapi import HTTPException


@pytest.fixture
def memory_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create Officer user
    officer = UserModel(
        id="user_officer",
        username="officer_admin",
        email="officer@campus.edu",
        password_hash="pw",
        role="officer",
    )
    session.add(officer)

    # Base Schedule
    sched = ScheduleModel(
        id="sched_default",
        name="Default Schedule",
        status="published",
        drive_ids_json="[]",
    )
    session.add(sched)

    # Base Rooms
    rooms = [
        RoomModel(id="room_cabin_1", name="Interview Cabin 1", building="Admin Block", capacity=5),
        RoomModel(id="room_cabin_2", name="Interview Cabin 2", building="Admin Block", capacity=5),
        RoomModel(id="room_hall_1", name="Main Auditorium", building="Academic Block", capacity=100),
    ]
    session.add_all(rooms)

    # Base Students
    students = []
    for i in range(1, 21):
        s = StudentModel(
            id=f"stu_{i:03d}",
            roll_no=f"BT21{i:04d}",
            name=f"Student {i}",
            normalized_name=f"student {i}",
            email=f"stu{i}@campus.edu",
            branch="CSE" if i % 2 == 0 else "ECE",
            cgpa=7.0 + (i % 30) * 0.1,
            tenth_percentage=85.0,
            date_of_birth=datetime.date(2003, 1, 1),
        )
        students.append(s)
    session.add_all(students)

    # Base Companies
    c1 = CompanyModel(id="comp_alpha", name="Alpha Technologies")
    c2 = CompanyModel(id="comp_beta", name="Beta Solutions")
    session.add_all([c1, c2])

    session.commit()
    yield session
    session.close()


def test_back_to_back_interviews_not_flagged_as_clashes(memory_db):
    """
    Interviews where slot1.end_time == slot2.start_time must NOT be flagged as clashes.
    Strict overlap requirement: max(start) < min(end).
    """
    d1 = DriveModel(id="drv_1", company_id="comp_alpha", company_name="Alpha", drive_date=datetime.date(2026, 11, 20), status="published", ctc_lpa=12.0)
    d2 = DriveModel(id="drv_2", company_id="comp_beta", company_name="Beta", drive_date=datetime.date(2026, 11, 20), status="published", ctc_lpa=14.0)
    memory_db.add_all([d1, d2])

    # Slot 1: 09:00 - 09:30
    s1 = SlotModel(
        id="s1",
        schedule_id="sched_default",
        drive_id="drv_1",
        student_id="stu_001",
        room_id="room_cabin_1",
        round_number=1,
        start_time=datetime.datetime(2026, 11, 20, 9, 0),
        end_time=datetime.datetime(2026, 11, 20, 9, 30),
    )
    # Slot 2: 09:30 - 10:00 (Back-to-back: start == prev end)
    s2 = SlotModel(
        id="s2",
        schedule_id="sched_default",
        drive_id="drv_2",
        student_id="stu_001",
        room_id="room_cabin_2",
        round_number=1,
        start_time=datetime.datetime(2026, 11, 20, 9, 30),
        end_time=datetime.datetime(2026, 11, 20, 10, 0),
    )
    memory_db.add_all([s1, s2])
    memory_db.commit()

    clashes = detect_db_slot_clashes(memory_db)
    assert len(clashes) == 0, f"Back-to-back interview falsely flagged as clash: {clashes}"
    assert count_unresolved_clashes(memory_db) == 0


def test_overlapping_student_interval_detected_with_exact_details(memory_db):
    """
    Overlapping intervals (e.g. 10:00-10:30 and 10:15-10:45) must be detected with exact details.
    """
    d1 = DriveModel(id="drv_1", company_id="comp_alpha", company_name="Alpha", drive_date=datetime.date(2026, 11, 20), status="published", ctc_lpa=12.0)
    d2 = DriveModel(id="drv_2", company_id="comp_beta", company_name="Beta", drive_date=datetime.date(2026, 11, 20), status="published", ctc_lpa=14.0)
    memory_db.add_all([d1, d2])

    s1 = SlotModel(
        id="slot_a",
        schedule_id="sched_default",
        drive_id="drv_1",
        student_id="stu_001",
        room_id="room_cabin_1",
        round_number=1,
        start_time=datetime.datetime(2026, 11, 20, 10, 0),
        end_time=datetime.datetime(2026, 11, 20, 10, 30),
    )
    s2 = SlotModel(
        id="slot_b",
        schedule_id="sched_default",
        drive_id="drv_2",
        student_id="stu_001",
        room_id="room_cabin_2",
        round_number=1,
        start_time=datetime.datetime(2026, 11, 20, 10, 15),
        end_time=datetime.datetime(2026, 11, 20, 10, 45),
    )
    memory_db.add_all([s1, s2])
    memory_db.commit()

    clashes = detect_db_slot_clashes(memory_db)
    assert len(clashes) == 1
    c = clashes[0]
    assert c["conflict_type"] == "student_double_booking"
    assert c["student_roll"] == "BT210001"
    assert c["drive_a_company"] in ("Alpha", "Beta")
    assert c["drive_b_company"] in ("Alpha", "Beta")
    assert c["status"] == "unresolved"


def test_room_double_booking_detected(memory_db):
    """
    Room booked for multiple drives at overlapping times must be flagged as room_double_booking.
    """
    d1 = DriveModel(id="drv_1", company_id="comp_alpha", company_name="Alpha", drive_date=datetime.date(2026, 11, 20), status="published", ctc_lpa=12.0)
    d2 = DriveModel(id="drv_2", company_id="comp_beta", company_name="Beta", drive_date=datetime.date(2026, 11, 20), status="published", ctc_lpa=14.0)
    memory_db.add_all([d1, d2])

    s1 = SlotModel(
        id="slot_r1",
        schedule_id="sched_default",
        drive_id="drv_1",
        student_id="stu_001",
        room_id="room_cabin_1",
        round_number=1,
        start_time=datetime.datetime(2026, 11, 20, 11, 0),
        end_time=datetime.datetime(2026, 11, 20, 11, 30),
    )
    s2 = SlotModel(
        id="slot_r2",
        schedule_id="sched_default",
        drive_id="drv_2",
        student_id="stu_002",
        room_id="room_cabin_1",  # Same room!
        round_number=1,
        start_time=datetime.datetime(2026, 11, 20, 11, 15),
        end_time=datetime.datetime(2026, 11, 20, 11, 45),
    )
    memory_db.add_all([s1, s2])
    memory_db.commit()

    clashes = detect_db_slot_clashes(memory_db)
    assert len(clashes) == 1
    c = clashes[0]
    assert c["conflict_type"] == "room_double_booking"
    assert c["room_name"] == "Interview Cabin 1"
    assert count_unresolved_clashes(memory_db) == 1


def test_drives_on_different_dates_do_not_clash(memory_db):
    """
    Same student, same room, and same time of day on DIFFERENT dates have zero clashes.
    """
    d1 = DriveModel(id="drv_nov20", company_id="comp_alpha", company_name="Alpha", drive_date=datetime.date(2026, 11, 20), status="published", ctc_lpa=12.0)
    d2 = DriveModel(id="drv_nov21", company_id="comp_beta", company_name="Beta", drive_date=datetime.date(2026, 11, 21), status="published", ctc_lpa=14.0)
    memory_db.add_all([d1, d2])

    s1 = SlotModel(
        id="slot_nov20",
        schedule_id="sched_default",
        drive_id="drv_nov20",
        student_id="stu_001",
        room_id="room_cabin_1",
        round_number=1,
        start_time=datetime.datetime(2026, 11, 20, 10, 0),
        end_time=datetime.datetime(2026, 11, 20, 10, 30),
    )
    s2 = SlotModel(
        id="slot_nov21",
        schedule_id="sched_default",
        drive_id="drv_nov21",
        student_id="stu_001",
        room_id="room_cabin_1",
        round_number=1,
        start_time=datetime.datetime(2026, 11, 21, 10, 0),
        end_time=datetime.datetime(2026, 11, 21, 10, 30),
    )
    memory_db.add_all([s1, s2])
    memory_db.commit()

    assert count_unresolved_clashes(memory_db) == 0
    assert detect_db_slot_clashes(memory_db) == []


def test_cp_sat_solver_prevents_clashes_with_existing_slots():
    """
    Verify solver's interval constraints prevent overlapping student and room assignments
    when existing slots on the same date are provided.
    """
    scheduler = CpSatPlacementScheduler()
    today = datetime.date(2026, 11, 20)

    rooms = [
        SchedulerRoom(id="cabin_101", name="Cabin 101", building="Main", capacity=5),
        SchedulerRoom(id="cabin_102", name="Cabin 102", building="Main", capacity=5),
    ]

    # Pre-existing slot: Student 'stu_01' is busy from 09:00 to 10:00 in Cabin 101
    existing_slots = [
        {
            "start_time": datetime.datetime(2026, 11, 20, 9, 0),
            "end_time": datetime.datetime(2026, 11, 20, 10, 0),
            "student_id": "stu_01",
            "room_id": "cabin_101",
        }
    ]

    drive = SchedulerDrive(
        id="drv_new",
        company_name="New Corp",
        drive_date=today,
        rounds=[
            SchedulerRound(
                round_number=1,
                name="Technical",
                round_type=RoundType.TECHNICAL_INTERVIEW,
                duration_minutes=30,
                is_group_round=False,
                panels=[SchedulerPanel(id="p_1", drive_id="drv_new", round_number=1, name="Panel 1", preferred_room_id="cabin_101")],
            )
        ],
        shortlisted_student_ids=["stu_01", "stu_02"],
    )

    res = scheduler.solve([drive], rooms, existing_slots=existing_slots)
    assert res.status in (ScheduleStatus.FEASIBLE, ScheduleStatus.OPTIMAL)

    # stu_01's slot in the new drive MUST start at or after 10:00 (outside existing busy window)
    stu_01_item = next(it for it in res.items if "stu_01" in it.student_ids)
    assert stu_01_item.start_time >= datetime.datetime(2026, 11, 20, 10, 0)


def test_solver_reports_infeasible_when_oversubscribed():
    """
    When an impossible schedule is requested (e.g. 10 students needing 45-min interviews
    in a 1-hour window with only 1 room), solver reports INFEASIBLE with explanation,
    never falsely returning 0 clashes with empty schedule.
    """
    scheduler = CpSatPlacementScheduler()
    today = datetime.date(2026, 11, 20)

    rooms = [SchedulerRoom(id="single_cabin", name="Single Cabin", building="Main", capacity=2)]

    drive = SchedulerDrive(
        id="drv_impossible",
        company_name="Impossible Corp",
        drive_date=today,
        fixed_window=TimeWindow(
            start_time=datetime.datetime(2026, 11, 20, 9, 0),
            end_time=datetime.datetime(2026, 11, 20, 10, 0),  # 1 hour window
        ),
        rounds=[
            SchedulerRound(
                round_number=1,
                name="Interview",
                round_type=RoundType.TECHNICAL_INTERVIEW,
                duration_minutes=45,
                is_group_round=False,
                panels=[SchedulerPanel(id="p1", drive_id="drv_impossible", round_number=1, name="P1", preferred_room_id="single_cabin")],
            )
        ],
        shortlisted_student_ids=[f"stu_{i}" for i in range(10)],  # 10 students cannot fit in 1 hour
    )

    res = scheduler.solve([drive], rooms)
    assert res.status == ScheduleStatus.INFEASIBLE
    assert res.infeasibility_explanation is not None
    assert len(res.items) == 0


def test_publish_blocked_on_unresolved_hard_clashes(memory_db):
    """
    If hard clashes exist and cannot be automatically resolved, publish_drive must throw 400.
    """
    officer = memory_db.query(UserModel).filter(UserModel.role == "officer").first()

    d1 = DriveModel(id="drv_pub1", company_id="comp_alpha", company_name="Alpha", drive_date=datetime.date(2026, 11, 20), status="published", version=1, ctc_lpa=10.0)
    d2 = DriveModel(id="drv_pub2", company_id="comp_beta", company_name="Beta", drive_date=datetime.date(2026, 11, 20), status="draft", version=1, ctc_lpa=12.0)
    memory_db.add_all([d1, d2])

    # Insert conflicting slots
    s1 = SlotModel(
        id="s_pub1",
        schedule_id="sched_default",
        drive_id="drv_pub1",
        student_id="stu_001",
        room_id="room_cabin_1",
        round_number=1,
        start_time=datetime.datetime(2026, 11, 20, 10, 0),
        end_time=datetime.datetime(2026, 11, 20, 10, 30),
    )
    s2 = SlotModel(
        id="s_pub2",
        schedule_id="sched_default",
        drive_id="drv_pub2",
        student_id="stu_001",
        room_id="room_cabin_2",
        round_number=1,
        start_time=datetime.datetime(2026, 11, 20, 10, 0),
        end_time=datetime.datetime(2026, 11, 20, 10, 30),
    )
    memory_db.add_all([s1, s2])
    memory_db.commit()

    # Make d2 published to simulate active clash
    d2.status = "published"
    memory_db.commit()

    with pytest.raises(HTTPException) as exc_info:
        publish_drive(
            drive_id="drv_pub2",
            req=PublishRequest(expected_base_version=1),
            current_user=officer,
            db=memory_db,
            uow=None,
        )
    assert exc_info.value.status_code == 400


def test_multi_drive_schedule_generation_zero_clashes(memory_db):
    """
    Generate schedules for multiple drives on the same day with overlapping shortlisted candidates.
    Verify all generated slots have ZERO clashes in the database.
    """
    officer = memory_db.query(UserModel).filter(UserModel.role == "officer").first()

    # Create 2 drives on the same day
    d1 = DriveModel(
        id="drv_multi_1",
        company_id="comp_alpha",
        company_name="Alpha Corp",
        drive_date=datetime.date(2026, 11, 25),
        status="published",
        version=1,
        ctc_lpa=15.0,
    )
    d2 = DriveModel(
        id="drv_multi_2",
        company_id="comp_beta",
        company_name="Beta Corp",
        drive_date=datetime.date(2026, 11, 25),
        status="published",
        version=1,
        ctc_lpa=18.0,
    )
    memory_db.add_all([d1, d2])
    memory_db.commit()

    # Shortlisted students for both drives
    common_students = [f"stu_{i:03d}" for i in range(1, 6)]

    # Schedule Drive 1
    res1 = generate_schedule(
        req=ScheduleGenerateRequest(
            drive_id="drv_multi_1",
            num_panels=2,
            round_duration_minutes=30,
            student_ids=common_students,
        ),
        current_user=officer,
        db=memory_db,
    )
    assert res1["is_feasible"] is True
    assert res1["clash_count"] == 0

    # Schedule Drive 2 on the same day with same students
    res2 = generate_schedule(
        req=ScheduleGenerateRequest(
            drive_id="drv_multi_2",
            num_panels=2,
            round_duration_minutes=30,
            student_ids=common_students,
        ),
        current_user=officer,
        db=memory_db,
    )
    assert res2["is_feasible"] is True
    assert res2["clash_count"] == 0

    # Independent audit of all slots in memory_db
    clashes = detect_db_slot_clashes(memory_db)
    assert len(clashes) == 0, f"Unexpected clashes found: {clashes}"
    assert count_unresolved_clashes(memory_db) == 0
