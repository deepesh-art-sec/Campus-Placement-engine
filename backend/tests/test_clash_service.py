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
    RoomModel,
    ScheduleModel,
    SlotModel,
    StudentModel,
)
from backend.app.scheduler.clash_service import count_unresolved_clashes, detect_db_slot_clashes


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed base test data
    c1 = CompanyModel(id="comp_1", name="Alpha Corp")
    c2 = CompanyModel(id="comp_2", name="Beta Tech")
    session.add_all([c1, c2])

    st = StudentModel(
        id="stu_test_1",
        roll_no="TEST001",
        name="Test Candidate",
        normalized_name="test candidate",
        email="test@candidate.com",
        branch="CSE",
        cgpa=9.0,
        tenth_percentage=90.0,
        date_of_birth=datetime.date(2003, 1, 1),
    )
    session.add(st)

    r1 = RoomModel(id="room_1", name="Cabin 1", building="Main", capacity=5)
    r2 = RoomModel(id="room_2", name="Cabin 2", building="Main", capacity=5)
    session.add_all([r1, r2])

    d1 = DriveModel(
        id="drv_alpha",
        company_id="comp_1",
        company_name="Alpha Corp",
        drive_date=datetime.date(2026, 11, 20),
        status="published",
        ctc_lpa=12.0,
    )
    d2 = DriveModel(
        id="drv_beta",
        company_id="comp_2",
        company_name="Beta Tech",
        drive_date=datetime.date(2026, 11, 20),
        status="published",
        ctc_lpa=15.0,
    )
    session.add_all([d1, d2])

    s_sched1 = ScheduleModel(id="sched_1", name="Sched 1", status="published", drive_ids_json='["drv_alpha"]')
    s_sched2 = ScheduleModel(id="sched_2", name="Sched 2", status="published", drive_ids_json='["drv_beta"]')
    session.add_all([s_sched1, s_sched2])

    session.commit()
    yield session
    session.close()


def test_no_clashes_when_no_slots(test_db):
    assert count_unresolved_clashes(test_db) == 0
    assert detect_db_slot_clashes(test_db) == []


def test_clash_detected_when_overlapping(test_db):
    slot1 = SlotModel(
        id="slot_1",
        schedule_id="sched_1",
        drive_id="drv_alpha",
        student_id="stu_test_1",
        room_id="room_1",
        round_number=1,
        start_time=datetime.datetime(2026, 11, 20, 10, 0),
        end_time=datetime.datetime(2026, 11, 20, 10, 30),
    )
    slot2 = SlotModel(
        id="slot_2",
        schedule_id="sched_2",
        drive_id="drv_beta",
        student_id="stu_test_1",
        room_id="room_2",
        round_number=1,
        start_time=datetime.datetime(2026, 11, 20, 10, 0),
        end_time=datetime.datetime(2026, 11, 20, 10, 30),
    )
    test_db.add_all([slot1, slot2])
    test_db.commit()

    clashes = detect_db_slot_clashes(test_db)
    assert len(clashes) == 1
    assert clashes[0]["status"] == "unresolved"
    assert clashes[0]["student_roll"] == "TEST001"
    assert count_unresolved_clashes(test_db) == 1


def test_draft_drives_are_ignored_by_clash_service(test_db):
    # Set d2 to draft
    d2 = test_db.query(DriveModel).filter(DriveModel.id == "drv_beta").first()
    d2.status = "draft"
    test_db.commit()

    slot1 = SlotModel(
        id="slot_1",
        schedule_id="sched_1",
        drive_id="drv_alpha",
        student_id="stu_test_1",
        room_id="room_1",
        round_number=1,
        start_time=datetime.datetime(2026, 11, 20, 10, 0),
        end_time=datetime.datetime(2026, 11, 20, 10, 30),
    )
    slot2 = SlotModel(
        id="slot_2",
        schedule_id="sched_2",
        drive_id="drv_beta",
        student_id="stu_test_1",
        room_id="room_2",
        round_number=1,
        start_time=datetime.datetime(2026, 11, 20, 10, 0),
        end_time=datetime.datetime(2026, 11, 20, 10, 30),
    )
    test_db.add_all([slot1, slot2])
    test_db.commit()

    # Even though slots overlap, beta is draft, so 0 operational clashes
    assert count_unresolved_clashes(test_db) == 0


def test_approved_preference_resolves_clash(test_db):
    slot1 = SlotModel(
        id="slot_1",
        schedule_id="sched_1",
        drive_id="drv_alpha",
        student_id="stu_test_1",
        room_id="room_1",
        round_number=1,
        start_time=datetime.datetime(2026, 11, 20, 10, 0),
        end_time=datetime.datetime(2026, 11, 20, 10, 30),
    )
    slot2 = SlotModel(
        id="slot_2",
        schedule_id="sched_2",
        drive_id="drv_beta",
        student_id="stu_test_1",
        room_id="room_2",
        round_number=1,
        start_time=datetime.datetime(2026, 11, 20, 10, 0),
        end_time=datetime.datetime(2026, 11, 20, 10, 30),
    )
    req = CoordinatorRequestModel(
        id="req_1",
        request_type="clash_preference",
        title="Clash Pref",
        description="Prefers Alpha",
        submitted_by="coord1",
        status="approved",
        target_id="TEST001",
        payload_json=json.dumps({"preferred_drive_id": "drv_alpha", "conflicting_drive_id": "drv_beta"}),
    )
    test_db.add_all([slot1, slot2, req])
    test_db.commit()

    clashes = detect_db_slot_clashes(test_db)
    assert len(clashes) == 1
    assert clashes[0]["status"] == "resolved"
    assert clashes[0]["recorded_preference"] == "Alpha Corp"
    assert count_unresolved_clashes(test_db) == 0
