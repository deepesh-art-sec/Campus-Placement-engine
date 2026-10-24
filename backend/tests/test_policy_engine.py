"""
Tests for College Placement Offer Policy Engine, Live Enforcement, and Combined Decisions.
Includes table-driven policy tests, edge-case handling, dispute comparisons, and Hypothesis property tests.
"""

from datetime import date, datetime

from hypothesis import given
from hypothesis import strategies as st

from backend.app.domain.eligibility.ast import CGPAMinRule, RuleSet
from backend.app.domain.models import (
    Drive,
    DriveMode,
    DriveStatus,
    EligibilityStatus,
    OfferRecord,
    OfferSource,
    OfferStatus,
    Slot,
    Student,
)
from backend.app.domain.policy.catalog import (
    PROGRESSIVE_MULTIPLIER_POLICY,
    STRICT_ONE_OFFER_POLICY,
    TIERED_QUOTA_POLICY,
)
from backend.app.domain.policy.checker import compare_students, policy_check
from backend.app.domain.policy.combined import CombinedDecisionEvaluator
from backend.app.domain.policy.enforcement import (
    LiveOfferEnforcementEngine,
    OfferLifecycleEvent,
    OfferLifecycleEventType,
)
from backend.app.domain.policy.models import (
    PolicyCheckStatus,
)


def make_student(
    roll_no: str = "BT301",
    offers: list[OfferRecord] | None = None,
    cgpa: float = 8.5,
) -> Student:
    return Student(
        id=f"std-{roll_no.lower()}",
        roll_no=roll_no,
        name=f"Student {roll_no}",
        email=f"{roll_no.lower()}@college.edu",
        branch="Computer Science and Engineering",
        cgpa=cgpa,
        tenth_percentage=85.0,
        twelfth_percentage=85.0,
        date_of_birth=date(2003, 1, 1),
        existing_offers=offers or [],
    )


def make_drive(
    drive_id: str = "drive-test",
    company_name: str = "TestCorp",
    ctc_lpa: float = 7.0,
    drive_date: date = date(2026, 11, 1),
) -> Drive:
    return Drive(
        id=drive_id,
        company_id=f"comp-{drive_id}",
        company_name=company_name,
        drive_date=drive_date,
        mode=DriveMode.ON_CAMPUS,
        ctc_lpa=ctc_lpa,
        status=DriveStatus.PUBLISHED,
        version=1,
    )


# ---------------------------------------------------------
# Table-Driven Tests per Policy & Toggles
# ---------------------------------------------------------

def test_strict_one_offer_policy_threshold_and_downgrade() -> None:
    policy = STRICT_ONE_OFFER_POLICY  # max_offers=1, dream_threshold=10.0, inclusive=True

    # 1. Student with 0 offers -> ALLOWED
    s0 = make_student("S0")
    d1 = make_drive("d1", ctc_lpa=6.0)
    res0 = policy_check(s0, d1, policy)
    assert res0.status == PolicyCheckStatus.ALLOWED
    assert res0.clause_id == "CLAUSE-1.0-NO-OFFERS"

    # 2. Student with 1 offer (4.5 LPA) applying for non-dream (7.0 LPA) -> BLOCKED
    offer_base = OfferRecord(
        company="Infosys",
        ctc_lpa=4.5,
        offer_date=date(2026, 10, 1),
        source=OfferSource.ON_CAMPUS,
        status=OfferStatus.ACCEPTED,
    )
    s1 = make_student("S1", offers=[offer_base])
    d_nondream = make_drive("d_nondream", ctc_lpa=7.0)
    res1 = policy_check(s1, d_nondream, policy)
    assert res1.status == PolicyCheckStatus.BLOCKED
    assert res1.clause_id == "CLAUSE-2.2-DRIVE-BELOW-DREAM-THRESHOLD"
    assert "below the Dream exception threshold" in res1.plain_english_reason

    # 3. Exactly at the threshold (10.0 LPA) with inclusive=True -> ALLOWED
    d_exact = make_drive("d_exact", ctc_lpa=10.0)
    res_exact = policy_check(s1, d_exact, policy)
    assert res_exact.status == PolicyCheckStatus.ALLOWED
    assert res_exact.clause_id == "CLAUSE-2.1-DREAM-UPGRADE-PERMITTED"

    # 4. Exactly at the threshold with inclusive=False -> BLOCKED
    policy_exclusive = policy.model_copy(update={"is_threshold_inclusive": False})
    res_excl = policy_check(s1, d_exact, policy_exclusive)
    assert res_excl.status == PolicyCheckStatus.BLOCKED
    assert res_excl.clause_id == "CLAUSE-2.2-DRIVE-BELOW-DREAM-THRESHOLD"

    # 5. Student already holds 1 Dream offer (15.0 LPA) -> BLOCKED for another Dream drive
    offer_dream = OfferRecord(
        company="Amazon",
        ctc_lpa=15.0,
        offer_date=date(2026, 10, 5),
        source=OfferSource.ON_CAMPUS,
        is_dream=True,
        status=OfferStatus.ACCEPTED,
    )
    s_dream = make_student("S_DREAM", offers=[offer_dream])
    d_super = make_drive("d_super", ctc_lpa=25.0)
    res_dream = policy_check(s_dream, d_super, policy)
    assert res_dream.status == PolicyCheckStatus.BLOCKED
    assert res_dream.clause_id == "CLAUSE-2.4-DREAM-QUOTA-EXHAUSTED"


def test_progressive_multiplier_policy_1_5x() -> None:
    policy = PROGRESSIVE_MULTIPLIER_POLICY  # max_offers=2, multiplier=1.5x, dream_threshold=12.0

    # Student holds offer of 6.0 LPA
    offer_6 = OfferRecord(
        company="TCS",
        ctc_lpa=6.0,
        offer_date=date(2026, 10, 1),
        source=OfferSource.ON_CAMPUS,
        status=OfferStatus.ACCEPTED,
    )
    s = make_student("S_MULT", offers=[offer_6])

    # Drive A: 8.0 LPA (6.0 * 1.5 = 9.0 required) -> BLOCKED (multiplier not met)
    drive_8 = make_drive("d8", ctc_lpa=8.0)
    res_8 = policy_check(s, drive_8, policy)
    assert res_8.status == PolicyCheckStatus.BLOCKED
    assert res_8.clause_id == "CLAUSE-2.2-DRIVE-BELOW-DREAM-THRESHOLD" or res_8.clause_id == "CLAUSE-2.3-MULTIPLIER-NOT-MET"

    # Drive B: 12.0 LPA (meets dream threshold 12.0 and >= 9.0) -> ALLOWED
    drive_12 = make_drive("d12", ctc_lpa=12.0)
    res_12 = policy_check(s, drive_12, policy)
    assert res_12.status == PolicyCheckStatus.ALLOWED
    assert res_12.clause_id in ("CLAUSE-1.0-WITHIN-OFFER-QUOTA", "CLAUSE-2.1-DREAM-UPGRADE-PERMITTED")

    # Student holds 2 offers -> BLOCKED (max offers reached)
    offer_second = OfferRecord(
        company="Cisco",
        ctc_lpa=14.0,
        offer_date=date(2026, 10, 10),
        status=OfferStatus.ACCEPTED,
    )
    s_2offers = make_student("S_2OFFERS", offers=[offer_6, offer_second])
    drive_30 = make_drive("d30", ctc_lpa=30.0)
    res_2offers = policy_check(s_2offers, drive_30, policy)
    assert res_2offers.status == PolicyCheckStatus.BLOCKED
    assert res_2offers.clause_id == "CLAUSE-1.1-MAX-OFFERS-REACHED" or res_2offers.clause_id == "CLAUSE-2.4-DREAM-QUOTA-EXHAUSTED"


def test_off_campus_and_revoked_offer_toggles() -> None:
    # Test Policy 3 with count_off_campus_offers = False
    policy = TIERED_QUOTA_POLICY
    assert policy.count_off_campus_offers is False

    off_campus_offer = OfferRecord(
        company="Google",
        ctc_lpa=35.0,
        offer_date=date(2026, 10, 1),
        source=OfferSource.OFF_CAMPUS,
        status=OfferStatus.ACCEPTED,
    )
    s_off = make_student("S_OFF", offers=[off_campus_offer])
    drive_campus = make_drive("d_campus", ctc_lpa=7.0)

    # In Policy 3, off-campus is NOT counted -> student is ALLOWED
    res_uncounted = policy_check(s_off, drive_campus, policy)
    assert res_uncounted.status == PolicyCheckStatus.ALLOWED

    # In Policy 1, off-campus IS counted -> student is BLOCKED
    res_counted = policy_check(s_off, drive_campus, STRICT_ONE_OFFER_POLICY)
    assert res_counted.status == PolicyCheckStatus.BLOCKED

    # Test Revoked Offer: Student had campus offer that was REVOKED
    revoked_offer = OfferRecord(
        company="StartupX",
        ctc_lpa=12.0,
        offer_date=date(2026, 10, 1),
        source=OfferSource.ON_CAMPUS,
        status=OfferStatus.REVOKED,
    )
    s_revoked = make_student("S_REV", offers=[revoked_offer])
    res_revoked = policy_check(s_revoked, drive_campus, STRICT_ONE_OFFER_POLICY)
    # Revoked offer does not count -> student is unblocked!
    assert res_revoked.status == PolicyCheckStatus.ALLOWED


def test_offer_dated_after_reference_date() -> None:
    # Offer dated Oct 25, reference evaluation date is Oct 20
    future_offer = OfferRecord(
        company="Wipro",
        ctc_lpa=6.5,
        offer_date=date(2026, 10, 25),
        source=OfferSource.ON_CAMPUS,
        status=OfferStatus.ACCEPTED,
    )
    student = make_student("S_FUTURE", offers=[future_offer])
    drive = make_drive("d_test", ctc_lpa=7.0, drive_date=date(2026, 10, 22))

    # As of Oct 20 (before offer date), student has 0 offers -> ALLOWED
    res_pre = policy_check(student, drive, STRICT_ONE_OFFER_POLICY, as_of=date(2026, 10, 20))
    assert res_pre.status == PolicyCheckStatus.ALLOWED

    # As of Oct 26 (after offer date), student has 1 offer -> BLOCKED
    res_post = policy_check(student, drive, STRICT_ONE_OFFER_POLICY, as_of=date(2026, 10, 26))
    assert res_post.status == PolicyCheckStatus.BLOCKED


# ---------------------------------------------------------
# Live Enforcement & Conflict Detection
# ---------------------------------------------------------

def test_live_enforcement_and_schedule_conflict_detection() -> None:
    policy = STRICT_ONE_OFFER_POLICY
    student = make_student("S_LIVE")

    drive_deloitte = make_drive("drive-deloitte", company_name="Deloitte", ctc_lpa=8.0, drive_date=date(2026, 11, 2))
    upcoming_drives = [drive_deloitte]

    # Student has a published interview slot for Deloitte
    published_slot = Slot(
        id="slot-101",
        schedule_id="sched-1",
        drive_id="drive-deloitte",
        round_number=2,
        student_id=student.id,
        room_id="Room-204",
        start_time=datetime(2026, 11, 2, 10, 30),
        end_time=datetime(2026, 11, 2, 11, 15),
    )

    # Event arrives: Student accepted an offer from TCS (4.5 LPA)
    offer_event = OfferLifecycleEvent(
        event_id="evt-01",
        student_id=student.id,
        company="TCS",
        ctc_lpa=4.5,
        offer_date=date(2026, 10, 22),
        event_type=OfferLifecycleEventType.ACCEPTED,
    )

    updated_student, changeset = LiveOfferEnforcementEngine.apply_event(
        student=student,
        event=offer_event,
        upcoming_drives=upcoming_drives,
        published_slots=[published_slot],
        policy=policy,
        as_of=date(2026, 10, 22),
    )

    # Verify student is newly blocked for Deloitte
    assert "drive-deloitte" in changeset.newly_blocked_drives
    # Verify schedule conflict was detected!
    assert len(changeset.published_schedule_conflicts) == 1
    conflict = changeset.published_schedule_conflicts[0]
    assert conflict.drive_id == "drive-deloitte"
    assert conflict.room_id == "Room-204"
    assert "Deloitte" in conflict.conflict_reason
    assert "Room-204" in conflict.conflict_reason

    # Next event: TCS revokes the offer!
    revoke_event = OfferLifecycleEvent(
        event_id="evt-02",
        student_id=student.id,
        company="TCS",
        ctc_lpa=4.5,
        offer_date=date(2026, 10, 22),
        event_type=OfferLifecycleEventType.REVOKED,
    )

    restored_student, changeset_revoke = LiveOfferEnforcementEngine.apply_event(
        student=updated_student,
        event=revoke_event,
        upcoming_drives=upcoming_drives,
        published_slots=[],
        policy=policy,
        as_of=date(2026, 10, 23),
    )

    # Verify student is now newly UNBLOCKED!
    assert "drive-deloitte" in changeset_revoke.newly_unblocked_drives


# ---------------------------------------------------------
# Dispute Comparison & Combined Decision
# ---------------------------------------------------------

def test_compare_students_explains_dispute() -> None:
    policy = STRICT_ONE_OFFER_POLICY
    drive = make_drive("drive-accenture", company_name="Accenture", ctc_lpa=8.5)

    # Student A holds 1 offer of 6.0 LPA (Blocked)
    offer_a = OfferRecord(company="Wipro", ctc_lpa=6.0, offer_date=date(2026, 10, 1), status=OfferStatus.ACCEPTED)
    student_a = make_student("AARAV", offers=[offer_a])

    # Student B holds 0 offers (Allowed)
    student_b = make_student("BHAVNA", offers=[])

    comparison = compare_students(student_a, student_b, drive, policy)
    assert comparison.student_a_status == PolicyCheckStatus.BLOCKED
    assert comparison.student_b_status == PolicyCheckStatus.ALLOWED
    assert "was BLOCKED while Student Student BHAVNA (BHAVNA) was ALLOWED" in comparison.comparative_summary
    assert "CLAUSE-2.2-DRIVE-BELOW-DREAM-THRESHOLD" in comparison.comparative_summary


def test_combined_decision_shows_both_reasons_separately() -> None:
    evaluator = CombinedDecisionEvaluator()
    policy = STRICT_ONE_OFFER_POLICY
    drive = make_drive("drive-msft", company_name="Microsoft", ctc_lpa=44.0)

    # Rule set requires CGPA >= 8.5
    rule_set = RuleSet(id="rs-msft", name="Microsoft Rules", rules=[CGPAMinRule(id="r-cgpa", min_cgpa=8.5)])

    # Case 1: Academic FAILS (CGPA 7.8), but Policy PASSES (0 offers)
    student_low_cgpa = make_student("S_LOW", cgpa=7.8, offers=[])
    res1 = evaluator.evaluate_combined(student_low_cgpa, drive, rule_set, policy)
    assert res1.final_status == EligibilityStatus.INELIGIBLE
    assert res1.is_academic_eligible is False
    assert res1.is_policy_allowed is True
    # Verify reasons are kept separate
    assert "CGPA is 7.80 and this company needs 8.50" in res1.academic_reason_summary
    assert "0 countable offers" in res1.policy_reason_summary

    # Case 2: Academic PASSES (CGPA 9.2), but Policy BLOCKED (holds 1 offer and drive is below dream)
    drive_low_ctc = make_drive("drive-low", company_name="SmallCorp", ctc_lpa=5.0)
    rule_set_low = RuleSet(id="rs-low", name="SmallCorp Rules", rules=[CGPAMinRule(id="r-cgpa", min_cgpa=6.0)])
    student_placed = make_student(
        "S_PLACED",
        cgpa=9.2,
        offers=[OfferRecord(company="Infosys", ctc_lpa=4.5, offer_date=date(2026, 10, 1), status=OfferStatus.ACCEPTED)],
    )
    res2 = evaluator.evaluate_combined(student_placed, drive_low_ctc, rule_set_low, policy)
    assert res2.final_status == EligibilityStatus.INELIGIBLE
    assert res2.is_academic_eligible is True
    assert res2.is_policy_allowed is False
    assert "Eligible: you meet all academic and backlog requirements" in res2.academic_reason_summary
    assert "below the Dream exception threshold" in res2.policy_reason_summary


# ---------------------------------------------------------
# Property-Based Tests (Hypothesis)
# ---------------------------------------------------------

@given(st.floats(min_value=3.0, max_value=50.0))
def test_property_student_with_no_offers_is_never_blocked(drive_ctc: float) -> None:
    """A student with no existing offers is never blocked by policy, regardless of drive CTC."""
    student = make_student("S_NO_OFFERS", offers=[])
    drive = make_drive("d-prop", ctc_lpa=drive_ctc)

    res1 = policy_check(student, drive, STRICT_ONE_OFFER_POLICY)
    assert res1.status == PolicyCheckStatus.ALLOWED

    res2 = policy_check(student, drive, PROGRESSIVE_MULTIPLIER_POLICY)
    assert res2.status == PolicyCheckStatus.ALLOWED

    res3 = policy_check(student, drive, TIERED_QUOTA_POLICY)
    assert res3.status == PolicyCheckStatus.ALLOWED
