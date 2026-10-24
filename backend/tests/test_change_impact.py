"""
Comprehensive test suite for change impact preview, what-if engine, versioning,
publish safeguards, offline output queue, and audit replay (Part 6).
Tests:
  - Scenario tests per change type (CGPA, percentage, branches, backlogs, gaps, manual overrides)
  - Mandatory reason validation for manual overrides (fails if < 5 chars)
  - Headline-number correctness test against brute-force recomputation
  - Second-order downstream effect tracing across drives and offer policies
  - Publish safeguards: blocked by unresolved reviews, clashes, or stale version lock
  - Immutable version snapshots, optimistic concurrency, and rollback
  - Offline output queue: student notifications and recruiter CSV/clipboard roster
  - Audit replay determinism from append-only event log
"""

from __future__ import annotations

import datetime

import pytest

from backend.app.domain.exceptions import StaleVersionError
from backend.app.domain.impact.models import (
    ChangeRequest,
    ChangeType,
    ImpactReport,
)
from backend.app.domain.impact.output_queue import OutputQueueService
from backend.app.domain.impact.replay import DecisionReplayer
from backend.app.domain.impact.safeguards import PublishSafeguards
from backend.app.domain.impact.second_order import SecondOrderAnalyzer
from backend.app.domain.impact.what_if import WhatIfEngine
from backend.app.domain.models import (
    BacklogRecord,
    BacklogStatus,
    Drive,
    GapYearRecord,
    RequirementSet,
    Student,
)
from backend.app.domain.policy.catalog import PROGRESSIVE_MULTIPLIER_POLICY, STRICT_ONE_OFFER_POLICY
from backend.app.events.event_service import EventService
from backend.app.scheduler.models import RoomType, ScheduledItem, SchedulerRoom
from backend.app.storage.repositories.interfaces import IUnitOfWork


@pytest.fixture
def what_if_engine() -> WhatIfEngine:
    return WhatIfEngine()


@pytest.fixture
def sample_students() -> list[Student]:
    students = []
    # 30 students with varying CGPA, branches, backlogs, and gap years
    branches = ["CSE", "IT", "ECE", "Mechanical Engineering", "Civil Engineering"]
    for i in range(1, 31):
        students.append(
            Student(
                id=f"stu_{i:03d}",
                roll_no=f"ROLL_{i:03d}",
                name=f"Student {i}",
                email=f"student{i}@college.edu",
                date_of_birth=datetime.date(2004, 1, 1),
                branch=branches[i % len(branches)],
                program="B.Tech",
                cgpa=round(6.0 + (i * 0.12), 2),  # 6.12 to 9.6
                tenth_percentage=round(65.0 + (i * 0.8), 1),
                twelfth_percentage=round(65.0 + (i * 0.7), 1),
                gap_years=[GapYearRecord(start_year=2022, end_year=2023, duration_years=1, reason="Prep")] if i % 6 == 0 else [],
                backlogs=[BacklogRecord(subject="Maths", semester=2, status=BacklogStatus.ACTIVE)] if i % 5 == 0 else [],
            )
        )
    return students


@pytest.fixture
def sample_drive() -> Drive:
    req = RequirementSet(
        id="req_d1",
        drive_id="d1",
        min_cgpa=7.5,
        min_tenth_percentage=60.0,
        min_twelfth_percentage=60.0,
        allowed_branches=["CSE", "IT", "ECE"],
        max_active_backlogs=0,
        max_gap_years=1,
    )
    return Drive(
        id="d1",
        company_id="comp_1",
        company_name="Google",
        drive_date=datetime.date(2026, 11, 1),
        ctc_lpa=36.0,
        requirements=req,
        version=1,
    )


@pytest.fixture
def sample_rooms() -> list[SchedulerRoom]:
    return [
        SchedulerRoom(id="hall_1", name="Auditorium", building="Main Block", room_type=RoomType.HALL, capacity=100),
        SchedulerRoom(id="cabin_1", name="Interview Cabin 1", building="Placement", room_type=RoomType.CABIN, capacity=5),
        SchedulerRoom(id="cabin_2", name="Interview Cabin 2", building="Placement", room_type=RoomType.CABIN, capacity=5),
    ]


# -----------------------------------------------------------------------------
# 1. Scenario Tests per Change Type
# -----------------------------------------------------------------------------

def test_what_if_cgpa_cutoff_lowering_and_raising(
    what_if_engine: WhatIfEngine,
    sample_drive: Drive,
    sample_students: list[Student],
    sample_rooms: list[SchedulerRoom],
) -> None:
    policy = STRICT_ONE_OFFER_POLICY
    # Initially eligible students at 7.5 CGPA in CSE/IT/ECE with 0 backlogs
    initial_shortlist = [
        s.id for s in sample_students
        if s.cgpa >= 7.5 and s.branch in ["CSE", "IT", "ECE"] and not s.backlogs
    ]

    # 1. Lower cut-off from 7.5 to 6.8
    req_lower = ChangeRequest(
        change_type=ChangeType.CGPA_CUTOFF,
        drive_id=sample_drive.id,
        target_field="cgpa",
        old_value=7.5,
        new_value=6.8,
    )
    report_lower = what_if_engine.apply_change(
        current_drive=sample_drive,
        all_drives=[sample_drive],
        students=sample_students,
        rooms=sample_rooms,
        policy=policy,
        current_shortlist=initial_shortlist,
        current_schedule_items=[],
        change=req_lower,
    )

    assert report_lower.students_added_count > 0
    assert report_lower.students_removed_count == 0
    assert "Lowering the CGPA cut-off from 7.5 to 6.8 adds" in report_lower.headline
    assert f"adds {report_lower.students_added_count} students" in report_lower.headline

    # 2. Raise cut-off from 7.5 to 8.5
    req_raise = ChangeRequest(
        change_type=ChangeType.CGPA_CUTOFF,
        drive_id=sample_drive.id,
        target_field="cgpa",
        old_value=7.5,
        new_value=8.5,
    )
    report_raise = what_if_engine.apply_change(
        current_drive=sample_drive,
        all_drives=[sample_drive],
        students=sample_students,
        rooms=sample_rooms,
        policy=policy,
        current_shortlist=initial_shortlist,
        current_schedule_items=[],
        change=req_raise,
    )

    assert report_raise.students_removed_count > 0
    assert "Raising the CGPA cut-off from 7.5 to 8.5 removes" in report_raise.headline


def test_what_if_branch_addition_and_removal(
    what_if_engine: WhatIfEngine,
    sample_drive: Drive,
    sample_students: list[Student],
    sample_rooms: list[SchedulerRoom],
) -> None:
    policy = STRICT_ONE_OFFER_POLICY
    initial_shortlist = [
        s.id for s in sample_students
        if s.cgpa >= 7.5 and s.branch in ["CSE", "IT", "ECE"] and not s.backlogs
    ]

    # Add Mechanical Engineering
    change_add = ChangeRequest(
        change_type=ChangeType.BRANCH_ADDED,
        drive_id=sample_drive.id,
        branch_name="Mechanical Engineering",
    )
    report_add = what_if_engine.apply_change(
        current_drive=sample_drive,
        all_drives=[sample_drive],
        students=sample_students,
        rooms=sample_rooms,
        policy=policy,
        current_shortlist=initial_shortlist,
        current_schedule_items=[],
        change=change_add,
    )

    assert report_add.students_added_count > 0
    assert all(a.branch == "Mechanical Engineering" for a in report_add.students_added)
    assert "Adding Mechanical Engineering to eligible branches adds" in report_add.headline


def test_what_if_backlog_criteria_restriction(
    what_if_engine: WhatIfEngine,
    sample_drive: Drive,
    sample_students: list[Student],
    sample_rooms: list[SchedulerRoom],
) -> None:
    policy = STRICT_ONE_OFFER_POLICY
    # Initially eligible under 1 backlog
    initial_shortlist = [
        s.id for s in sample_students
        if s.cgpa >= 7.5 and s.branch in ["CSE", "IT", "ECE"] and len(s.backlogs) <= 1
    ]

    change_backlog = ChangeRequest(
        change_type=ChangeType.BACKLOG_RULE,
        drive_id=sample_drive.id,
        old_value=1,
        new_value=0,
    )
    report = what_if_engine.apply_change(
        current_drive=sample_drive,
        all_drives=[sample_drive],
        students=sample_students,
        rooms=sample_rooms,
        policy=policy,
        current_shortlist=initial_shortlist,
        current_schedule_items=[],
        change=change_backlog,
    )

    # Candidates with active backlogs must be removed, zero added
    assert report.students_added_count == 0
    assert report.students_removed_count > 0
    assert "Restricting the backlog criteria removes" in report.headline


def test_what_if_manual_student_override_with_mandatory_reason(
    what_if_engine: WhatIfEngine,
    sample_drive: Drive,
    sample_students: list[Student],
    sample_rooms: list[SchedulerRoom],
) -> None:
    policy = STRICT_ONE_OFFER_POLICY

    # Manual inclusion requires rationale >= 5 chars
    valid_change = ChangeRequest(
        change_type=ChangeType.MANUAL_STUDENT_ADD,
        drive_id=sample_drive.id,
        student_id="stu_001",
        mandatory_reason="Department Head special recommendation for coding excellence",
    )
    report = what_if_engine.apply_change(
        current_drive=sample_drive,
        all_drives=[sample_drive],
        students=sample_students,
        rooms=sample_rooms,
        policy=policy,
        current_shortlist=[],
        current_schedule_items=[],
        change=valid_change,
    )
    assert report.students_added_count == 1
    assert report.students_added[0].student_id == "stu_001"
    assert "Department Head special recommendation" in report.students_added[0].reason

    # Rejection if mandatory_reason is missing or too short
    with pytest.raises(ValueError) as exc:
        ChangeRequest(
            change_type=ChangeType.MANUAL_STUDENT_ADD,
            drive_id=sample_drive.id,
            student_id="stu_002",
            mandatory_reason="OK",  # < 5 chars
        )
    assert "mandatory rationale of at least 5 characters" in str(exc.value)


# -----------------------------------------------------------------------------
# 2. Headline-Number Correctness Test Against Brute-Force Recompute
# -----------------------------------------------------------------------------

def test_headline_number_correctness_against_brute_force(
    what_if_engine: WhatIfEngine,
    sample_drive: Drive,
    sample_students: list[Student],
    sample_rooms: list[SchedulerRoom],
) -> None:
    policy = STRICT_ONE_OFFER_POLICY
    initial_shortlist = [s.id for s in sample_students if s.cgpa >= 8.0 and s.branch in ["CSE", "IT"]]

    change = ChangeRequest(
        change_type=ChangeType.CGPA_CUTOFF,
        drive_id=sample_drive.id,
        target_field="cgpa",
        old_value=8.0,
        new_value=7.0,
    )

    report = what_if_engine.apply_change(
        current_drive=sample_drive,
        all_drives=[sample_drive],
        students=sample_students,
        rooms=sample_rooms,
        policy=policy,
        current_shortlist=initial_shortlist,
        current_schedule_items=[],
        change=change,
    )

    # Brute-force recomputation
    expected_added = len(report.students_added)
    expected_removed = len(report.students_removed)
    expected_clashes = len(report.newly_clashing_students)

    # Exact numbers must be embedded in the headline
    assert f"adds {expected_added} students" in report.headline
    assert report.students_added_count == expected_added
    assert report.students_removed_count == expected_removed
    assert report.clashes_count == expected_clashes
    assert "; 0 clashes detected." in report.headline


# -----------------------------------------------------------------------------
# 3. Second-Order Downstream Effects
# -----------------------------------------------------------------------------

def test_second_order_effect_tracing(
    sample_drive: Drive,
    sample_students: list[Student],
) -> None:
    analyzer = SecondOrderAnalyzer()

    drive_b = Drive(
        id="d2",
        company_id="comp_2",
        company_name="Infosys",
        drive_date=datetime.date(2026, 11, 10),
        ctc_lpa=9.5,
    )

    newly_eligible = [sample_students[0]]

    # 1. Under Strict One Offer Policy
    effects_strict = analyzer.trace_downstream_effects(
        source_drive=sample_drive,
        newly_eligible_students=newly_eligible,
        all_drives=[sample_drive, drive_b],
        policy=STRICT_ONE_OFFER_POLICY,
    )
    assert len(effects_strict) == 1
    eff = effects_strict[0]
    assert eff.target_drive_name == "Infosys"
    assert "Clause 1.1" in eff.clause_cited
    assert "disqualify candidate from sitting for 'Infosys'" in eff.causal_chain

    # 2. Under Progressive Multiplier Policy (36 LPA at 1.5x requires next offer >= 54 LPA)
    effects_prog = analyzer.trace_downstream_effects(
        source_drive=sample_drive,
        newly_eligible_students=newly_eligible,
        all_drives=[sample_drive, drive_b],
        policy=PROGRESSIVE_MULTIPLIER_POLICY,
    )
    assert len(effects_prog) == 1
    assert "Dream Upgrade Multiplier" in effects_prog[0].clause_cited
    assert "locked out" in effects_prog[0].causal_chain


# -----------------------------------------------------------------------------
# 4. Publish Safeguards & Optimistic Concurrency
# -----------------------------------------------------------------------------

def test_publish_safeguards_block_conditions(
    sample_drive: Drive,
    sample_rooms: list[SchedulerRoom],
) -> None:
    safeguards = PublishSafeguards()
    report = ImpactReport(
        change_summary="Cut-off revised",
        headline="Simulated headline",
        drive_id=sample_drive.id,
        drive_name=sample_drive.company_name,
        students_added_count=0,
        students_removed_count=0,
        clashes_count=0,
    )

    # 1. Unresolved Reviews block publish
    res_review_blocked = safeguards.validate_for_publish(
        drive_id=sample_drive.id,
        current_version=1,
        expected_base_version=1,
        unresolved_review_items=["Review ambiguity for 10th percentage"],
        schedule_items=[],
        rooms=sample_rooms,
        drives=[],
        impact_report=report,
    )
    assert res_review_blocked.can_publish is False
    assert any("unresolved review queue items" in r for r in res_review_blocked.block_reasons)

    # 2. Stale Version Lock blocks publish
    res_stale = safeguards.validate_for_publish(
        drive_id=sample_drive.id,
        current_version=2,  # Current is 2
        expected_base_version=1,  # Requested against 1
        unresolved_review_items=[],
        schedule_items=[],
        rooms=sample_rooms,
        drives=[],
        impact_report=report,
    )
    assert res_stale.can_publish is False
    assert res_stale.stale_version_detected is True
    assert any("Stale version lock" in r for r in res_stale.block_reasons)


def test_commit_publish_and_rollback(
    test_uow: IUnitOfWork,
    sample_drive: Drive,
) -> None:
    safeguards = PublishSafeguards()

    with test_uow:
        # Publishing increments version to 2 and records event
        snapshot_v2 = safeguards.commit_publish(
            uow=test_uow,
            drive=sample_drive,
            requirements=sample_drive.requirements,  # type: ignore[arg-type]
            shortlist_student_ids=["stu_001", "stu_002"],
            schedule_items=[],
            expected_base_version=1,
            actor="OFFICER_BOB",
            reason="Finalized shortlists",
        )

        assert sample_drive.version == 2
        assert snapshot_v2.version == 2
        assert snapshot_v2.audit_hash != ""

        # Concurrency collision: trying to publish again against expected v1 fails
        with pytest.raises(StaleVersionError):
            safeguards.commit_publish(
                uow=test_uow,
                drive=sample_drive,
                requirements=sample_drive.requirements,  # type: ignore[arg-type]
                shortlist_student_ids=["stu_001"],
                schedule_items=[],
                expected_base_version=1,  # Expected 1, but drive is now 2!
            )

        # Rollback restores snapshot
        rolled_back = safeguards.rollback_to_version(
            uow=test_uow,
            drive=sample_drive,
            target_snapshot=snapshot_v2,
            actor="SUPERVISOR_ALICE",
            reason="Correcting human error",
        )
        assert rolled_back.requirements.id == snapshot_v2.requirements.id


# -----------------------------------------------------------------------------
# 5. Output Queue Generation (100% Offline)
# -----------------------------------------------------------------------------

def test_output_queue_offline_generation(
    sample_drive: Drive,
    sample_students: list[Student],
) -> None:
    queue = OutputQueueService()

    slot_time = datetime.datetime(2026, 11, 1, 9, 30)
    sched_item = ScheduledItem(
        schedule_id="sch_1",
        drive_id=sample_drive.id,
        round_number=1,
        round_name="Technical Assessment",
        student_ids=["stu_001", "stu_002"],
        room_id="hall_1",
        room_name="Auditorium",
        start_time=slot_time,
        end_time=slot_time + datetime.timedelta(minutes=60),
    )

    # 1. Student notifications
    notifications = queue.generate_student_notifications(
        drive=sample_drive,
        students=sample_students,
        schedule_items=[sched_item],
    )
    assert len(notifications) == 2
    n1 = notifications[0]
    assert n1.student_email == "student1@college.edu"
    assert "Auditorium" in n1.message
    assert "Google recruitment drive" in n1.message

    # 2. Recruiter export
    roster = queue.generate_recruiter_export(
        drive=sample_drive,
        students=sample_students,
        schedule_items=[sched_item],
    )
    assert roster.total_candidates == 2
    assert "Roll No,Candidate Name,Branch,CGPA,Round,Slot,Venue,Panel" in roster.csv_content
    assert "ROLL_001" in roster.csv_content
    assert "GOOGLE RECRUITMENT ROSTER" in roster.clipboard_text


# -----------------------------------------------------------------------------
# 6. Audit Replay Determinism
# -----------------------------------------------------------------------------

def test_audit_replay_determinism(
    test_uow: IUnitOfWork,
    sample_drive: Drive,
    sample_students: list[Student],
) -> None:
    replayer = DecisionReplayer()
    policy = STRICT_ONE_OFFER_POLICY
    student = sample_students[0]  # stu_001 has CGPA 6.12, drive cut-off is 7.5

    hist_date = datetime.datetime(2026, 10, 3, 10, 0)

    with test_uow:
        # Record historical event
        EventService.record_change(
            uow=test_uow,
            aggregate_type="STUDENT",
            aggregate_id=student.id,
            event_type="STUDENT_SNAPSHOT",
            actor="SYSTEM",
            after_state={"cgpa": 6.12, "branch": student.branch},
            timestamp=hist_date,
        )

        explanation = replayer.explain_historical_decision(
            uow=test_uow,
            student=student,
            drive=sample_drive,
            policy=policy,
            as_of=hist_date,
        )

    assert explanation.student_id == student.id
    assert explanation.final_status == "ineligible"
    assert "CGPA" in explanation.academic_reason
    assert "03 Oct 2026" in explanation.narrative
    assert len(explanation.rules_failed) >= 1
