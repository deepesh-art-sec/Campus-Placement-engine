import datetime
import uuid
from collections.abc import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.main import app, seed_default_accounts
from backend.app.storage.database import SessionLocal
from backend.app.storage.models.entities import (
    CompanyExportMappingModel,
    CompanyModel,
    CoordinatorRequestModel,
    DriveModel,
    DriveRequirementVersionModel,
    EligibilityDecisionModel,
    EligibilityRunModel,
    NotificationModel,
    OfferModel,
    PanelModel,
    PendingResultModel,
    PlacementRequestModel,
    RoomModel,
    ScheduleModel,
    SlotModel,
    StudentApplicationModel,
    StudentModel,
    UserModel,
)


@pytest.fixture
def officer_client() -> Generator[tuple[TestClient, dict[str, str]], None, None]:
    seed_default_accounts()
    with TestClient(app) as c:
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


def test_complete_company_and_drive_purge(officer_client: tuple[TestClient, dict[str, str]], db: Session) -> None:
    client, headers = officer_client

    # 1. Grab an existing student
    student = db.execute(select(StudentModel)).scalars().first()
    assert student is not None
    initial_version = student.version

    # Grab room and schedule
    room = db.execute(select(RoomModel)).scalars().first()
    if not room:
        room = RoomModel(id=f"room_{uuid.uuid4().hex[:8]}", name="Classroom 101", capacity=30, room_type="classroom")
        db.add(room)
        db.flush()

    schedule = db.execute(select(ScheduleModel)).scalars().first()
    if not schedule:
        schedule = ScheduleModel(
            id=f"sch_{uuid.uuid4().hex[:8]}",
            name="Main Schedule",
            start_date=datetime.date(2026, 11, 20),
            end_date=datetime.date(2026, 11, 30),
            day_start_time="09:00",
            day_end_time="18:00",
            slot_duration_minutes=30,
            status="draft",
        )
        db.add(schedule)
        db.flush()

    comp_id = f"comp_{uuid.uuid4().hex[:8]}"
    drv_id = f"drv_{uuid.uuid4().hex[:8]}"
    comp_name = f"TestPurgeCorp_{uuid.uuid4().hex[:4]}"

    # 2. Insert company and drive
    company = CompanyModel(id=comp_id, name=comp_name, tier="Tier 1")
    db.add(company)
    db.flush()

    drive = DriveModel(
        id=drv_id,
        company_id=comp_id,
        company_name=comp_name,
        drive_date=datetime.date(2026, 11, 25),
        mode="on_campus",
        status="published",
        ctc_lpa=16.5,
        version=1,
    )
    db.add(drive)
    db.flush()

    # 3. Add requirement, slot, decisions, application, offer, requests, mappings, recruiter
    req_ver = DriveRequirementVersionModel(
        id=f"req_{uuid.uuid4().hex[:8]}",
        drive_id=drv_id,
        version_number=1,
        min_cgpa=7.0,
        min_tenth_percentage=60.0,
        min_twelfth_percentage=60.0,
        allowed_branches_json='["CSE", "ECE"]',
        allowed_programs_json='["B.Tech"]',
        max_active_backlogs=0,
        max_history_backlogs=0,
    )
    db.add(req_ver)

    slot = SlotModel(
        id=f"slot_{uuid.uuid4().hex[:8]}",
        schedule_id=schedule.id,
        drive_id=drv_id,
        student_id=student.id,
        round_number=1,
        room_id=room.id,
        start_time=datetime.datetime(2026, 11, 25, 10, 0),
        end_time=datetime.datetime(2026, 11, 25, 10, 45),
    )
    db.add(slot)

    app_rec = StudentApplicationModel(
        id=f"app_{uuid.uuid4().hex[:8]}",
        student_id=student.id,
        drive_id=drv_id,
        status="applied",
    )
    db.add(app_rec)

    offer = OfferModel(
        id=f"off_{uuid.uuid4().hex[:8]}",
        student_id=student.id,
        company=comp_name,
        ctc_lpa=16.5,
        offer_date=datetime.date(2026, 11, 26),
        status="offered",
    )
    db.add(offer)

    coord_req = CoordinatorRequestModel(
        id=f"cr_{uuid.uuid4().hex[:8]}",
        request_type="logistics",
        title=f"Logistics request for {comp_name}",
        description="Need 2 projectors",
        submitted_by="coordinator",
        target_id=drv_id,
        status="open",
    )
    db.add(coord_req)

    mapping = CompanyExportMappingModel(
        id=f"map_{uuid.uuid4().hex[:8]}",
        company_id=comp_id,
        company_name=comp_name,
        sheet_name="Candidates",
        column_mappings_json="{}",
        column_widths_json="{}",
    )
    db.add(mapping)

    rec_user = UserModel(
        id=f"usr_{uuid.uuid4().hex[:8]}",
        username=f"recruiter_{comp_name.lower().replace(' ', '_')}",
        email=f"recruiter_{uuid.uuid4().hex[:4]}@company.com",
        password_hash="test_hash",
        role="recruiter",
        company_id=comp_id,
        is_active=True,
    )
    db.add(rec_user)
    db.commit()

    # Verify everything exists before delete
    assert db.execute(select(CompanyModel).where(CompanyModel.id == comp_id)).scalar_one_or_none() is not None
    assert db.execute(select(DriveModel).where(DriveModel.id == drv_id)).scalar_one_or_none() is not None
    assert db.execute(select(OfferModel).where(OfferModel.company == comp_name)).scalar_one_or_none() is not None

    # Call DELETE /api/drives/{drv_id}
    res = client.delete(f"/api/drives/{drv_id}?reason=FullPurgeTest", headers=headers)
    assert res.status_code == 200
    assert "removed completely" in res.json().get("message", "").lower()

    # Expire and verify total cleanup in database
    db.expire_all()
    assert db.execute(select(CompanyModel).where(CompanyModel.id == comp_id)).scalar_one_or_none() is None
    assert db.execute(select(CompanyModel).where(CompanyModel.name == comp_name)).scalar_one_or_none() is None
    assert db.execute(select(DriveModel).where(DriveModel.id == drv_id)).scalar_one_or_none() is None
    assert db.execute(select(SlotModel).where(SlotModel.drive_id == drv_id)).scalars().all() == []
    assert db.execute(select(StudentApplicationModel).where(StudentApplicationModel.drive_id == drv_id)).scalars().all() == []
    assert db.execute(select(OfferModel).where(OfferModel.company == comp_name)).scalars().all() == []
    assert db.execute(select(CoordinatorRequestModel).where(CoordinatorRequestModel.target_id == drv_id)).scalars().all() == []
    assert db.execute(select(CompanyExportMappingModel).where(CompanyExportMappingModel.company_id == comp_id)).scalar_one_or_none() is None

    # Verify recruiter was detached & deactivated
    ru_check = db.execute(select(UserModel).where(UserModel.id == rec_user.id)).scalar_one_or_none()
    assert ru_check is not None
    assert ru_check.company_id is None
    assert ru_check.is_active is False

    # Verify student version was incremented
    stu_check = db.execute(select(StudentModel).where(StudentModel.id == student.id)).scalar_one()
    assert stu_check.version == initial_version + 1


def test_delete_company_by_id_endpoint(officer_client: tuple[TestClient, dict[str, str]], db: Session) -> None:
    client, headers = officer_client

    comp_id = f"comp_{uuid.uuid4().hex[:8]}"
    comp_name = f"DirectCompanyPurge_{uuid.uuid4().hex[:4]}"

    company = CompanyModel(id=comp_id, name=comp_name, tier="Tier 2")
    db.add(company)
    db.commit()

    assert db.execute(select(CompanyModel).where(CompanyModel.id == comp_id)).scalar_one_or_none() is not None

    res = client.delete(f"/api/drives/company/{comp_id}?reason=PurgeDirectCompany", headers=headers)
    assert res.status_code == 200

    db.expire_all()
    assert db.execute(select(CompanyModel).where(CompanyModel.id == comp_id)).scalar_one_or_none() is None
