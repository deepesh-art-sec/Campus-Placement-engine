"""
Domain <-> ORM mappers.
Converts between pure Domain Pydantic models and SQLAlchemy models.
"""

from __future__ import annotations

import json
import re
import uuid

from backend.app.domain.models import (
    BacklogRecord,
    BacklogStatus,
    Company,
    Drive,
    DriveMode,
    DriveStatus,
    EligibilityDecision,
    EligibilityStatus,
    Event,
    GapYearRecord,
    OfferPolicy,
    OfferRecord,
    OfferSource,
    OfferStatus,
    Panel,
    ProtectedDemographics,
    RequirementSet,
    Room,
    Schedule,
    Slot,
    Student,
)
from backend.app.storage.models.entities import (
    AcademicRecordModel,
    BacklogModel,
    CompanyModel,
    DriveModel,
    DriveRequirementVersionModel,
    EligibilityDecisionModel,
    EventModel,
    GapYearModel,
    OfferModel,
    PanelModel,
    PolicyModel,
    RoomModel,
    ScheduleModel,
    StudentModel,
)

# ---------------------------------------------------------
# Student Mappings
# ---------------------------------------------------------

def student_entity_to_domain(model: StudentModel) -> Student:
    sgpa_dict: dict[int, float] = {r.semester: r.sgpa for r in model.academic_records}

    backlogs = [
        BacklogRecord(
            subject=b.subject,
            semester=b.semester,
            status=BacklogStatus(b.status),
            cleared_on=b.cleared_on,
        )
        for b in model.backlogs
    ]

    gap_years = [
        GapYearRecord(
            start_year=g.start_year,
            end_year=g.end_year,
            duration_years=g.duration_years,
            reason=g.reason,
            phase=g.phase,
        )
        for g in model.gap_years
    ]

    offers = [
        OfferRecord(
            id=o.id,
            company=o.company,
            ctc_lpa=o.ctc_lpa,
            fixed_pay_lpa=o.fixed_pay_lpa,
            offer_date=o.offer_date,
            source=OfferSource(o.source),
            is_dream=o.is_dream,
            status=OfferStatus(o.status),
        )
        for o in model.offers
    ]

    protected = ProtectedDemographics(
        gender=model.gender,
        caste=model.caste,
        religion=model.religion,
        category=model.category,
    )

    return Student(
        id=model.id,
        roll_no=model.roll_no,
        name=model.name,
        email=model.email,
        branch=model.branch,
        program=model.program,
        semester_sgpa=sgpa_dict,
        cgpa=model.cgpa,
        tenth_percentage=model.tenth_percentage,
        twelfth_percentage=model.twelfth_percentage,
        diploma_percentage=model.diploma_percentage,
        date_of_birth=model.date_of_birth,
        gap_years=gap_years,
        backlogs=backlogs,
        existing_offers=offers,
        protected_demographics=protected,
        version=model.version,
    )


def student_domain_to_entity(student: Student) -> StudentModel:
    model = StudentModel(
        id=student.id,
        roll_no=student.roll_no,
        name=student.name,
        normalized_name=re.sub(r"\s+", " ", student.name.strip()).lower(),
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
        version=student.version,
    )

    # Academic records
    for sem, sgpa in student.semester_sgpa.items():
        model.academic_records.append(
            AcademicRecordModel(
                id=str(uuid.uuid4()),
                student_id=student.id,
                semester=sem,
                sgpa=sgpa,
            )
        )

    # Backlogs
    for b in student.backlogs:
        model.backlogs.append(
            BacklogModel(
                id=str(uuid.uuid4()),
                student_id=student.id,
                subject=b.subject,
                semester=b.semester,
                status=b.status.value,
                cleared_on=b.cleared_on,
            )
        )

    # Gap years
    for g in student.gap_years:
        model.gap_years.append(
            GapYearModel(
                id=str(uuid.uuid4()),
                student_id=student.id,
                start_year=g.start_year,
                end_year=g.end_year,
                duration_years=g.duration_years,
                reason=g.reason,
                phase=g.phase,
            )
        )

    # Offers
    for o in student.existing_offers:
        model.offers.append(
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

    return model


# ---------------------------------------------------------
# Company & Drive Mappings
# ---------------------------------------------------------

def company_entity_to_domain(model: CompanyModel) -> Company:
    return Company(
        id=model.id,
        name=model.name,
        industry=model.industry,
        tier=model.tier,
        website=model.website,
        created_at=model.created_at,
        version=model.version,
    )


def drive_requirement_entity_to_domain(model: DriveRequirementVersionModel) -> RequirementSet:
    return RequirementSet(
        id=model.id,
        drive_id=model.drive_id,
        version_number=model.version_number,
        raw_source_text=model.raw_source_text,
        parse_confidence=model.parse_confidence,
        min_cgpa=model.min_cgpa,
        min_tenth_percentage=model.min_tenth_percentage,
        min_twelfth_percentage=model.min_twelfth_percentage,
        min_diploma_percentage=model.min_diploma_percentage,
        allowed_branches=json.loads(model.allowed_branches_json or "[]"),
        allowed_programs=json.loads(model.allowed_programs_json or "[]"),
        max_active_backlogs=model.max_active_backlogs,
        allow_history_backlogs=model.allow_history_backlogs,
        max_history_backlogs=model.max_history_backlogs,
        max_gap_years=model.max_gap_years,
        allow_gap_during_degree=model.allow_gap_during_degree,
        custom_rules=json.loads(model.custom_rules_json or "{}"),
        created_at=model.created_at,
    )


def drive_requirement_domain_to_entity(req: RequirementSet) -> DriveRequirementVersionModel:
    return DriveRequirementVersionModel(
        id=req.id,
        drive_id=req.drive_id,
        version_number=req.version_number,
        raw_source_text=req.raw_source_text,
        parse_confidence=req.parse_confidence,
        min_cgpa=req.min_cgpa,
        min_tenth_percentage=req.min_tenth_percentage,
        min_twelfth_percentage=req.min_twelfth_percentage,
        min_diploma_percentage=req.min_diploma_percentage,
        allowed_branches_json=json.dumps(req.allowed_branches),
        allowed_programs_json=json.dumps(req.allowed_programs),
        max_active_backlogs=req.max_active_backlogs,
        allow_history_backlogs=req.allow_history_backlogs,
        max_history_backlogs=req.max_history_backlogs,
        max_gap_years=req.max_gap_years,
        allow_gap_during_degree=req.allow_gap_during_degree,
        custom_rules_json=json.dumps(req.custom_rules),
        created_at=req.created_at,
    )


def drive_entity_to_domain(model: DriveModel) -> Drive:
    req_versions = [drive_requirement_entity_to_domain(r) for r in model.requirement_versions]
    latest_req = max(req_versions, key=lambda r: r.version_number) if req_versions else None

    panels = [
        Panel(
            id=p.id,
            drive_id=p.drive_id,
            name=p.name,
            interviewer_names=json.loads(p.interviewers_json or "[]"),
            room_id=p.room_id,
        )
        for p in model.panels
    ]

    return Drive(
        id=model.id,
        company_id=model.company_id,
        company_name=model.company_name,
        drive_date=model.drive_date,
        mode=DriveMode(model.mode),
        ctc_lpa=model.ctc_lpa,
        is_dream=model.is_dream,
        status=DriveStatus(model.status),
        requirements=latest_req,
        requirement_versions=req_versions,
        panels=panels,
        version=model.version,
    )


def drive_domain_to_entity(drive: Drive) -> DriveModel:
    model = DriveModel(
        id=drive.id,
        company_id=drive.company_id,
        company_name=drive.company_name,
        drive_date=drive.drive_date,
        mode=drive.mode.value,
        ctc_lpa=drive.ctc_lpa,
        is_dream=drive.is_dream,
        status=drive.status.value,
        version=drive.version,
    )

    for req in drive.requirement_versions:
        model.requirement_versions.append(drive_requirement_domain_to_entity(req))

    for p in drive.panels:
        model.panels.append(
            PanelModel(
                id=p.id,
                drive_id=drive.id,
                name=p.name,
                interviewers_json=json.dumps(p.interviewer_names),
                room_id=p.room_id,
            )
        )

    return model


# ---------------------------------------------------------
# Policy Mappings
# ---------------------------------------------------------

def policy_entity_to_domain(model: PolicyModel) -> OfferPolicy:
    return OfferPolicy(
        id=model.id,
        name=model.name,
        version=model.version,
        max_offers_per_student=model.max_offers_per_student,
        dream_tier_ctc_lpa=model.dream_tier_ctc_lpa,
        super_dream_tier_ctc_lpa=model.super_dream_tier_ctc_lpa or 20.0,
        allow_dream_upgrade=model.allow_dream_upgrade,
        upgrade_ctc_multiplier=model.upgrade_ctc_multiplier,
        strict_backlog_cutoff=model.strict_backlog_cutoff,
        allow_multiple_offers_if_different_tiers=model.allow_multiple_offers_if_different_tiers,
        is_active=model.is_active,
        created_at=model.created_at,
    )


def policy_domain_to_entity(policy: OfferPolicy) -> PolicyModel:
    return PolicyModel(
        id=policy.id,
        name=policy.name,
        version=policy.version,
        max_offers_per_student=policy.max_offers_per_student,
        dream_tier_ctc_lpa=policy.dream_tier_ctc_lpa,
        super_dream_tier_ctc_lpa=policy.super_dream_tier_ctc_lpa,
        allow_dream_upgrade=policy.allow_dream_upgrade,
        upgrade_ctc_multiplier=policy.upgrade_ctc_multiplier,
        strict_backlog_cutoff=policy.strict_backlog_cutoff,
        allow_multiple_offers_if_different_tiers=policy.allow_multiple_offers_if_different_tiers,
        is_active=policy.is_active,
        created_at=policy.created_at,
    )


# ---------------------------------------------------------
# Decision Mappings
# ---------------------------------------------------------

def decision_domain_to_entity(d: EligibilityDecision) -> EligibilityDecisionModel:
    return EligibilityDecisionModel(
        id=str(uuid.uuid4()),
        run_id=d.run_id,
        student_id=d.student_id,
        drive_id=d.drive_id,
        status=d.status.value,
        reasons_json=json.dumps(d.reasons),
        rule_ids_json=json.dumps(d.rule_ids_triggered),
        evaluated_at=d.evaluated_at,
    )


def decision_entity_to_domain(model: EligibilityDecisionModel, roll_no: str = "", name: str = "") -> EligibilityDecision:
    return EligibilityDecision(
        student_id=model.student_id,
        student_roll_no=roll_no or (model.student.roll_no if model.student else ""),
        student_name=name or (model.student.name if model.student else ""),
        drive_id=model.drive_id,
        run_id=model.run_id,
        status=EligibilityStatus(model.status),
        reasons=json.loads(model.reasons_json or "[]"),
        rule_ids_triggered=json.loads(model.rule_ids_json or "[]"),
        evaluated_at=model.evaluated_at,
    )


# ---------------------------------------------------------
# Schedule & Room Mappings
# ---------------------------------------------------------

def room_entity_to_domain(model: RoomModel) -> Room:
    return Room(
        id=model.id,
        name=model.name,
        building=model.building,
        capacity=model.capacity,
        has_computers=model.has_computers,
        is_active=model.is_active,
    )


def room_domain_to_entity(room: Room) -> RoomModel:
    return RoomModel(
        id=room.id,
        name=room.name,
        building=room.building,
        capacity=room.capacity,
        has_computers=room.has_computers,
        is_active=room.is_active,
    )


def schedule_entity_to_domain(model: ScheduleModel) -> Schedule:
    slots = [
        Slot(
            id=s.id,
            schedule_id=s.schedule_id,
            drive_id=s.drive_id,
            round_number=s.round_number,
            student_id=s.student_id,
            room_id=s.room_id,
            panel_id=s.panel_id,
            start_time=s.start_time,
            end_time=s.end_time,
        )
        for s in model.slots
    ]
    return Schedule(
        id=model.id,
        name=model.name,
        version=model.version,
        drive_ids=json.loads(model.drive_ids_json or "[]"),
        slots=slots,
        created_at=model.created_at,
    )


# ---------------------------------------------------------
# Event Sourcing Mappings
# ---------------------------------------------------------

def event_entity_to_domain(model: EventModel) -> Event:
    return Event(
        id=model.id,
        aggregate_type=model.aggregate_type,
        aggregate_id=model.aggregate_id,
        event_type=model.event_type,
        actor=model.actor,
        timestamp=model.timestamp,
        payload=json.loads(model.payload_json or "{}"),
    )


def event_domain_to_entity(event: Event) -> EventModel:
    return EventModel(
        id=event.id,
        aggregate_type=event.aggregate_type,
        aggregate_id=event.aggregate_id,
        event_type=event.event_type,
        actor=event.actor,
        timestamp=event.timestamp,
        payload_json=json.dumps(event.payload, default=str),
    )
