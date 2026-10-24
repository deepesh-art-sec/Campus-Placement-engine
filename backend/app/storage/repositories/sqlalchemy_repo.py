"""
SQLAlchemy Repository implementations with Unit-of-Work and Optimistic Concurrency Control.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, selectinload

from backend.app.domain.exceptions import ConcurrencyConflictError
from backend.app.domain.models import (
    Drive,
    EligibilityDecision,
    Event,
    OfferPolicy,
    RequirementSet,
    Room,
    Schedule,
    Student,
)
from backend.app.storage.models.entities import (
    BacklogModel,
    CompanyModel,
    DriveModel,
    EligibilityDecisionModel,
    EligibilityRunModel,
    EventModel,
    OfferModel,
    PolicyModel,
    RoomModel,
    ScheduleModel,
    SlotModel,
    StudentModel,
)
from backend.app.storage.repositories.mappers import (
    decision_domain_to_entity,
    decision_entity_to_domain,
    drive_domain_to_entity,
    drive_entity_to_domain,
    drive_requirement_domain_to_entity,
    event_domain_to_entity,
    event_entity_to_domain,
    policy_domain_to_entity,
    policy_entity_to_domain,
    room_domain_to_entity,
    room_entity_to_domain,
    schedule_entity_to_domain,
    student_domain_to_entity,
    student_entity_to_domain,
)


class SqlAlchemyStudentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _query(self) -> Any:
        return select(StudentModel).options(
            selectinload(StudentModel.academic_records),
            selectinload(StudentModel.backlogs),
            selectinload(StudentModel.gap_years),
            selectinload(StudentModel.offers),
        )

    def get_by_id(self, student_id: str) -> Student | None:
        stmt = self._query().where(StudentModel.id == student_id)
        result = self.session.execute(stmt).scalar_one_or_none()
        return student_entity_to_domain(result) if result else None

    def get_by_roll_no(self, roll_no: str) -> Student | None:
        stmt = self._query().where(StudentModel.roll_no == roll_no)
        result = self.session.execute(stmt).scalar_one_or_none()
        return student_entity_to_domain(result) if result else None

    def list_all(self, branch: str | None = None, limit: int = 1000, offset: int = 0) -> list[Student]:
        stmt = self._query()
        if branch:
            stmt = stmt.where(StudentModel.branch == branch)
        stmt = stmt.offset(offset).limit(limit)
        results = self.session.execute(stmt).scalars().all()
        return [student_entity_to_domain(r) for r in results]

    def count(self, branch: str | None = None) -> int:
        stmt = select(func.count(StudentModel.id))
        if branch:
            stmt = stmt.where(StudentModel.branch == branch)
        return self.session.execute(stmt).scalar_one()

    def add(self, student: Student) -> Student:
        entity = student_domain_to_entity(student)
        self.session.add(entity)
        self.session.flush()
        return student

    def update(self, student: Student) -> Student:
        # Optimistic concurrency check
        current_version = student.version
        next_version = current_version + 1

        stmt = (
            update(StudentModel)
            .where(StudentModel.id == student.id, StudentModel.version == current_version)
            .values(
                name=student.name,
                email=student.email,
                branch=student.branch,
                program=student.program,
                cgpa=student.cgpa,
                tenth_percentage=student.tenth_percentage,
                twelfth_percentage=student.twelfth_percentage,
                diploma_percentage=student.diploma_percentage,
                date_of_birth=student.date_of_birth,
                gender=student.protected_demographics.gender if student.protected_demographics else None,
                caste=student.protected_demographics.caste if student.protected_demographics else None,
                religion=student.protected_demographics.religion if student.protected_demographics else None,
                category=student.protected_demographics.category if student.protected_demographics else None,
                version=next_version,
            )
        )
        res = self.session.execute(stmt)
        rowcount = getattr(res, "rowcount", 0)
        if rowcount == 0:
            existing = self.session.get(StudentModel, student.id)
            if existing is None:
                raise ValueError(f"Student with id {student.id} not found.")
            raise ConcurrencyConflictError(
                f"Concurrent modification on student {student.id}. Version expected: {current_version}, actual: {existing.version}."
            )

        # Sync child collections: backlogs, offers, gap_years
        # Clear existing backlogs and re-add
        self.session.query(BacklogModel).filter(BacklogModel.student_id == student.id).delete()
        for b in student.backlogs:
            self.session.add(
                BacklogModel(
                    id=str(uuid.uuid4()),
                    student_id=student.id,
                    subject=b.subject,
                    semester=b.semester,
                    status=b.status.value,
                    cleared_on=b.cleared_on,
                )
            )

        # Clear existing offers and re-add
        self.session.query(OfferModel).filter(OfferModel.student_id == student.id).delete()
        for o in student.existing_offers:
            self.session.add(
                OfferModel(
                    id=o.id or str(uuid.uuid4()),
                    student_id=student.id,
                    company=o.company,
                    ctc_lpa=o.ctc_lpa,
                    fixed_pay_lpa=o.fixed_pay_lpa,
                    offer_date=o.offer_date,
                    source=o.source.value,
                    is_dream=o.is_dream,
                    status=o.status.value,
                )
            )

        student.version = next_version
        self.session.flush()
        return student

    def save_batch(self, students: list[Student]) -> int:
        for student in students:
            entity = student_domain_to_entity(student)
            self.session.add(entity)
        self.session.flush()
        return len(students)


class SqlAlchemyDriveRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _query(self) -> Any:
        return select(DriveModel).options(
            selectinload(DriveModel.requirement_versions),
            selectinload(DriveModel.panels),
        )

    def get_by_id(self, drive_id: str) -> Drive | None:
        stmt = self._query().where(DriveModel.id == drive_id)
        result = self.session.execute(stmt).scalar_one_or_none()
        return drive_entity_to_domain(result) if result else None

    def list_all(self) -> list[Drive]:
        stmt = self._query().order_by(DriveModel.drive_date.desc())
        results = self.session.execute(stmt).scalars().all()
        return [drive_entity_to_domain(r) for r in results]

    def add(self, drive: Drive) -> Drive:
        # Check if company exists, if not create company
        company = self.session.get(CompanyModel, drive.company_id)
        if not company:
            company = CompanyModel(
                id=drive.company_id,
                name=drive.company_name,
            )
            self.session.add(company)
            self.session.flush()

        entity = drive_domain_to_entity(drive)
        self.session.add(entity)
        self.session.flush()
        return drive

    def update(self, drive: Drive) -> Drive:
        current_version = drive.version
        next_version = current_version + 1

        stmt = (
            update(DriveModel)
            .where(DriveModel.id == drive.id, DriveModel.version == current_version)
            .values(
                company_name=drive.company_name,
                drive_date=drive.drive_date,
                mode=drive.mode.value,
                ctc_lpa=drive.ctc_lpa,
                is_dream=drive.is_dream,
                status=drive.status.value,
                version=next_version,
            )
        )
        res = self.session.execute(stmt)
        rowcount = getattr(res, "rowcount", 0)
        if rowcount == 0:
            existing = self.session.get(DriveModel, drive.id)
            if existing is None:
                raise ValueError(f"Drive {drive.id} not found.")
            raise ConcurrencyConflictError(
                f"Concurrent modification on drive {drive.id}. Expected version {current_version}, found {existing.version}."
            )
        drive.version = next_version
        self.session.flush()
        return drive

    def add_requirement_version(self, req: RequirementSet) -> RequirementSet:
        entity = drive_requirement_domain_to_entity(req)
        self.session.add(entity)
        self.session.flush()
        return req


class SqlAlchemyPolicyRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_active(self) -> OfferPolicy | None:
        stmt = (
            select(PolicyModel)
            .where(PolicyModel.is_active.is_(True))
            .order_by(PolicyModel.version.desc())
            .limit(1)
        )
        result = self.session.execute(stmt).scalar_one_or_none()
        return policy_entity_to_domain(result) if result else None

    def get_by_id(self, policy_id: str) -> OfferPolicy | None:
        result = self.session.get(PolicyModel, policy_id)
        return policy_entity_to_domain(result) if result else None

    def add(self, policy: OfferPolicy) -> OfferPolicy:
        entity = policy_domain_to_entity(policy)
        self.session.add(entity)
        self.session.flush()
        return policy


class SqlAlchemyEligibilityRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_run(
        self,
        run_id: str,
        drive_id: str,
        requirement_version_id: str,
        policy_id: str,
        total_evaluated: int,
        total_eligible: int,
        total_ineligible: int,
        executed_by: str,
    ) -> str:
        run = EligibilityRunModel(
            id=run_id,
            drive_id=drive_id,
            requirement_version_id=requirement_version_id,
            policy_id=policy_id,
            total_evaluated=total_evaluated,
            total_eligible=total_eligible,
            total_ineligible=total_ineligible,
            executed_by=executed_by,
        )
        self.session.add(run)
        self.session.flush()
        return run_id

    def save_decisions(self, decisions: list[EligibilityDecision]) -> int:
        for d in decisions:
            entity = decision_domain_to_entity(d)
            self.session.add(entity)
        self.session.flush()
        return len(decisions)

    def get_decisions_for_drive(self, drive_id: str) -> list[EligibilityDecision]:
        stmt = (
            select(EligibilityDecisionModel)
            .options(selectinload(EligibilityDecisionModel.student))
            .where(EligibilityDecisionModel.drive_id == drive_id)
            .order_by(EligibilityDecisionModel.evaluated_at.desc())
        )
        results = self.session.execute(stmt).scalars().all()
        return [decision_entity_to_domain(r) for r in results]

    def get_decision_for_student(self, drive_id: str, student_id: str) -> EligibilityDecision | None:
        stmt = (
            select(EligibilityDecisionModel)
            .options(selectinload(EligibilityDecisionModel.student))
            .where(
                EligibilityDecisionModel.drive_id == drive_id,
                EligibilityDecisionModel.student_id == student_id,
            )
            .order_by(EligibilityDecisionModel.evaluated_at.desc())
            .limit(1)
        )
        result = self.session.execute(stmt).scalar_one_or_none()
        return decision_entity_to_domain(result) if result else None


class SqlAlchemyScheduleRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, schedule_id: str) -> Schedule | None:
        stmt = (
            select(ScheduleModel)
            .options(selectinload(ScheduleModel.slots))
            .where(ScheduleModel.id == schedule_id)
        )
        result = self.session.execute(stmt).scalar_one_or_none()
        return schedule_entity_to_domain(result) if result else None

    def save(self, schedule: Schedule) -> Schedule:
        model = ScheduleModel(
            id=schedule.id,
            name=schedule.name,
            version=schedule.version,
            drive_ids_json=json.dumps(schedule.drive_ids),
            created_at=schedule.created_at,
        )
        self.session.add(model)
        for s in schedule.slots:
            slot_model = SlotModel(
                id=s.id,
                schedule_id=schedule.id,
                drive_id=s.drive_id,
                student_id=s.student_id,
                round_number=s.round_number,
                room_id=s.room_id,
                panel_id=s.panel_id,
                start_time=s.start_time,
                end_time=s.end_time,
            )
            self.session.add(slot_model)
        self.session.flush()
        return schedule

    def list_rooms(self) -> list[Room]:
        stmt = select(RoomModel).where(RoomModel.is_active.is_(True))
        results = self.session.execute(stmt).scalars().all()
        return [room_entity_to_domain(r) for r in results]

    def add_room(self, room: Room) -> Room:
        entity = room_domain_to_entity(room)
        self.session.add(entity)
        self.session.flush()
        return room


class SqlAlchemyEventRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def append(self, event: Event) -> None:
        entity = event_domain_to_entity(event)
        self.session.add(entity)
        self.session.flush()

    def get_events_for_aggregate(self, aggregate_type: str, aggregate_id: str) -> list[Event]:
        stmt = (
            select(EventModel)
            .where(
                EventModel.aggregate_type == aggregate_type,
                EventModel.aggregate_id == aggregate_id,
            )
            .order_by(EventModel.timestamp.asc())
        )
        results = self.session.execute(stmt).scalars().all()
        return [event_entity_to_domain(r) for r in results]

    def list_events(self, limit: int = 100) -> list[Event]:
        stmt = select(EventModel).order_by(EventModel.timestamp.desc()).limit(limit)
        results = self.session.execute(stmt).scalars().all()
        return [event_entity_to_domain(r) for r in results]


class SqlAlchemyUnitOfWork:
    """Unit of Work implementation managing database transactions and repository lifecycles."""

    def __init__(self, session_factory: Any) -> None:
        self.session_factory = session_factory
        self.session: Session | None = None

    def __enter__(self) -> SqlAlchemyUnitOfWork:
        self.session = self.session_factory()
        self.students = SqlAlchemyStudentRepository(self.session)
        self.drives = SqlAlchemyDriveRepository(self.session)
        self.policies = SqlAlchemyPolicyRepository(self.session)
        self.eligibility = SqlAlchemyEligibilityRepository(self.session)
        self.schedules = SqlAlchemyScheduleRepository(self.session)
        self.events = SqlAlchemyEventRepository(self.session)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.session:
            if exc_type is not None:
                self.rollback()
            self.session.close()

    def commit(self) -> None:
        if self.session:
            self.session.commit()

    def rollback(self) -> None:
        if self.session:
            self.session.rollback()
