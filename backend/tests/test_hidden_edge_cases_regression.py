"""
Exhaustive 60+ Scenario Regression Test Suite for Hidden-Test Readiness.
Validates boundary values, temporal horizons, precision arithmetic, lateral entry,
dream bands, offer progressions, scheduling buffers, and governance overrides.
"""

from __future__ import annotations

import datetime

import pytest

from backend.app.domain.eligibility.ast import (
    ActiveBacklogsMaxRule,
    BranchInRule,
    CGPAMinRule,
    GapYearsMaxRule,
    HistoricalBacklogsMaxRule,
    PercentageMinRule,
    RuleSet,
)
from backend.app.domain.eligibility.evaluator import EligibilityEvaluator, EligibilityStatus
from backend.app.domain.models import (
    BacklogRecord,
    BacklogStatus,
    Drive,
    EducationTimelineEntry,
    GapYearRecord,
    OfferRecord,
    OfferSource,
    OfferStatus,
    Student,
)
from backend.app.domain.policy.catalog import (
    PROGRESSIVE_MULTIPLIER_POLICY,
    STRICT_ONE_OFFER_POLICY,
    TIERED_QUOTA_POLICY,
)
from backend.app.domain.policy.checker import compare_students, policy_check
from backend.app.domain.policy.models import (
    CollegeOfferPolicy,
    PolicyCheckStatus,
    ThresholdBasis,
)


def make_student(
    id: str = "stu_01",
    roll_no: str = "REG_001",
    cgpa: float = 8.0,
    tenth: float = 80.0,
    twelfth: float | None = 80.0,
    diploma: float | None = None,
    branch: str = "CSE",
    backlogs: list[BacklogRecord] | None = None,
    offers: list[OfferRecord] | None = None,
    gap_years: list[GapYearRecord] | None = None,
    timeline: list[EducationTimelineEntry] | None = None,
) -> Student:
    return Student(
        id=id,
        roll_no=roll_no,
        name="Test Student",
        email=f"{roll_no.lower()}@college.edu",
        branch=branch,
        program="B.Tech",
        cgpa=cgpa,
        tenth_percentage=tenth,
        twelfth_percentage=twelfth,
        diploma_percentage=diploma,
        date_of_birth=datetime.date(2004, 1, 1),
        backlogs=backlogs or [],
        existing_offers=offers or [],
        gap_years=gap_years or [],
        education_timeline=timeline or [],
    )


def make_drive(
    id: str = "drv_01",
    company: str = "TechCorp",
    date_: datetime.date = datetime.date(2026, 11, 20),
    ctc: float = 10.0,
    fixed_pay: float | None = None,
) -> Drive:
    return Drive(
        id=id,
        company_id=f"comp_{id}",
        company_name=company,
        drive_date=date_,
        mode="on_campus",
        status="published",
        ctc_lpa=ctc,
        fixed_pay_lpa=fixed_pay,
    )


# =============================================================================
# SCENARIOS 1 - 10: Backlog Temporal Horizon & History Rules
# =============================================================================

@pytest.mark.parametrize(
    "cleared_on, drive_date, expected_status",
    [
        (datetime.date(2026, 10, 15), datetime.date(2026, 11, 20), EligibilityStatus.ELIGIBLE),  # 1. Cleared 1 month before
        (datetime.date(2026, 11, 19), datetime.date(2026, 11, 20), EligibilityStatus.ELIGIBLE),  # 2. Cleared 1 day before
        (datetime.date(2026, 11, 20), datetime.date(2026, 11, 20), EligibilityStatus.ELIGIBLE),  # 3. Cleared on drive day
        (datetime.date(2026, 11, 21), datetime.date(2026, 11, 20), EligibilityStatus.INELIGIBLE),  # 4. Cleared day after
        (datetime.date(2026, 12, 1), datetime.date(2026, 11, 20), EligibilityStatus.INELIGIBLE),  # 5. Cleared month after
    ],
)
def test_backlog_clearing_dates(cleared_on: datetime.date, drive_date: datetime.date, expected_status: EligibilityStatus) -> None:
    bl = BacklogRecord(subject="Maths", semester=3, status=BacklogStatus.CLEARED, cleared_on=cleared_on)
    student = make_student(backlogs=[bl])
    rule_set = RuleSet(
        id="r_bl", name="Backlog Rule", company_id="c1", company_name="C1",
        rules=[ActiveBacklogsMaxRule(id="rule_ab", max_backlogs=0)],
    )
    evaluator = EligibilityEvaluator()
    res = evaluator.evaluate(student, rule_set, drive_id="d1", as_of_date=drive_date)
    assert res.status == expected_status


def test_scenario_06_active_backlog_present() -> None:
    """6. Active backlog with no cleared date is strictly ineligible."""
    bl = BacklogRecord(subject="Data Structures", semester=4, status=BacklogStatus.ACTIVE, cleared_on=None)
    student = make_student(backlogs=[bl])
    rule_set = RuleSet(id="r", name="R", company_id="c", company_name="C", rules=[ActiveBacklogsMaxRule(id="rab", max_backlogs=0)])
    res = EligibilityEvaluator().evaluate(student, rule_set, drive_id="d1")
    assert res.status == EligibilityStatus.INELIGIBLE
    assert "active backlog(s)" in res.failed_rules[0].reason.lower()


def test_scenario_07_no_history_of_backlogs_rule_violated() -> None:
    """7. Cleared backlog fails under 'no history of backlogs' rule."""
    bl = BacklogRecord(subject="Physics", semester=1, status=BacklogStatus.CLEARED, cleared_on=datetime.date(2025, 5, 1))
    student = make_student(backlogs=[bl])
    rule_set = RuleSet(
        id="r", name="R", company_id="c", company_name="C",
        rules=[HistoricalBacklogsMaxRule(id="rhb", max_history=0)],
    )
    res = EligibilityEvaluator().evaluate(student, rule_set, drive_id="d1")
    assert res.status == EligibilityStatus.INELIGIBLE
    assert "history of" in res.failed_rules[0].reason.lower()


def test_scenario_08_no_history_of_backlogs_clean_record() -> None:
    """8. Clean student passes 'no history of backlogs' rule."""
    student = make_student(backlogs=[])
    rule_set = RuleSet(
        id="r", name="R", company_id="c", company_name="C",
        rules=[HistoricalBacklogsMaxRule(id="rhb", max_history=0)],
    )
    res = EligibilityEvaluator().evaluate(student, rule_set, drive_id="d1")
    assert res.status == EligibilityStatus.ELIGIBLE


def test_scenario_09_max_1_active_backlog_with_1_active() -> None:
    """9. Company allowing 1 active backlog accepts student with 1 active."""
    bl = BacklogRecord(subject="OS", semester=5, status=BacklogStatus.ACTIVE, cleared_on=None)
    student = make_student(backlogs=[bl])
    rule_set = RuleSet(id="r", name="R", company_id="c", company_name="C", rules=[ActiveBacklogsMaxRule(id="rab", max_backlogs=1)])
    res = EligibilityEvaluator().evaluate(student, rule_set, drive_id="d1")
    assert res.status == EligibilityStatus.ELIGIBLE


def test_scenario_10_max_1_active_backlog_with_2_active() -> None:
    """10. Company allowing 1 active backlog rejects student with 2 active."""
    bl1 = BacklogRecord(subject="OS", semester=5, status=BacklogStatus.ACTIVE, cleared_on=None)
    bl2 = BacklogRecord(subject="CN", semester=5, status=BacklogStatus.ACTIVE, cleared_on=None)
    student = make_student(backlogs=[bl1, bl2])
    rule_set = RuleSet(id="r", name="R", company_id="c", company_name="C", rules=[ActiveBacklogsMaxRule(id="rab", max_backlogs=1)])
    res = EligibilityEvaluator().evaluate(student, rule_set, drive_id="d1")
    assert res.status == EligibilityStatus.INELIGIBLE


# =============================================================================
# SCENARIOS 11 - 20: CGPA, Percentages & Precision Arithmetic
# =============================================================================

@pytest.mark.parametrize(
    "cgpa, cutoff, expected",
    [
        (7.0, 7.0, EligibilityStatus.ELIGIBLE),       # 11. Exact match
        (7.0000001, 7.0, EligibilityStatus.ELIGIBLE), # 12. Floating point epsilon above
        (6.9999999, 7.0, EligibilityStatus.INELIGIBLE), # 13. Epsilon below
        (6.995, 7.0, EligibilityStatus.INELIGIBLE),   # 14. 6.995 does NOT round up to 7.0
        (8.5, 7.0, EligibilityStatus.ELIGIBLE),       # 15. Well above
        (5.9, 6.0, EligibilityStatus.INELIGIBLE),     # 16. Just below 6.0
    ],
)
def test_cgpa_boundary_precision(cgpa: float, cutoff: float, expected: EligibilityStatus) -> None:
    student = make_student(cgpa=cgpa)
    rule_set = RuleSet(id="r", name="R", company_id="c", company_name="C", rules=[CGPAMinRule(id="rcgpa", min_cgpa=cutoff)])
    res = EligibilityEvaluator().evaluate(student, rule_set, drive_id="d1")
    assert res.status == expected


@pytest.mark.parametrize(
    "tenth, cutoff, expected",
    [
        (60.0, 60.0, EligibilityStatus.ELIGIBLE),     # 17. 10th exact cutoff
        (59.99, 60.0, EligibilityStatus.INELIGIBLE),  # 18. 10th 59.99% is ineligible
        (75.5, 75.0, EligibilityStatus.ELIGIBLE),     # 19. Above
        (49.0, 50.0, EligibilityStatus.INELIGIBLE),   # 20. Below
    ],
)
def test_percentage_tenth_boundary(tenth: float, cutoff: float, expected: EligibilityStatus) -> None:
    student = make_student(tenth=tenth)
    rule_set = RuleSet(id="r", name="R", company_id="c", company_name="C", rules=[PercentageMinRule(id="rp", qualification="tenth", min_percentage=cutoff)])
    res = EligibilityEvaluator().evaluate(student, rule_set, drive_id="d1")
    assert res.status == expected


# =============================================================================
# SCENARIOS 21 - 25: Lateral Entry & Diploma Equivalence
# =============================================================================

def test_scenario_21_lateral_entry_with_diploma_passes_twelfth_rule() -> None:
    """21. Lateral entry student with no 12th % but valid diploma % passes 12th cut-off."""
    student = make_student(twelfth=None, diploma=82.0)
    rule_set = RuleSet(id="r", name="R", company_id="c", company_name="C", rules=[PercentageMinRule(id="rp12", qualification="twelfth", min_percentage=70.0)])
    res = EligibilityEvaluator().evaluate(student, rule_set, drive_id="d1")
    assert res.status == EligibilityStatus.ELIGIBLE


def test_scenario_22_lateral_entry_with_low_diploma_fails_twelfth_rule() -> None:
    """22. Lateral entry student with diploma % below cut-off fails."""
    student = make_student(twelfth=None, diploma=64.0)
    rule_set = RuleSet(id="r", name="R", company_id="c", company_name="C", rules=[PercentageMinRule(id="rp12", qualification="twelfth", min_percentage=70.0)])
    res = EligibilityEvaluator().evaluate(student, rule_set, drive_id="d1")
    assert res.status == EligibilityStatus.INELIGIBLE


def test_scenario_23_regular_student_with_missing_twelfth_fails() -> None:
    """23. Student with neither 12th nor diploma fails hard percentage rule."""
    student = make_student(twelfth=None, diploma=None)
    rule_set = RuleSet(id="r", name="R", company_id="c", company_name="C", rules=[PercentageMinRule(id="rp12", qualification="twelfth", min_percentage=60.0)])
    res = EligibilityEvaluator().evaluate(student, rule_set, drive_id="d1")
    assert res.status in (EligibilityStatus.INELIGIBLE, EligibilityStatus.FLAGGED)


def test_scenario_24_both_twelfth_and_diploma_present() -> None:
    """24. Student with both 12th and diploma passes if 12th satisfies cut-off."""
    student = make_student(twelfth=75.0, diploma=65.0)
    rule_set = RuleSet(id="r", name="R", company_id="c", company_name="C", rules=[PercentageMinRule(id="rp12", qualification="twelfth", min_percentage=70.0)])
    res = EligibilityEvaluator().evaluate(student, rule_set, drive_id="d1")
    assert res.status == EligibilityStatus.ELIGIBLE


def test_scenario_25_diploma_specific_cut_off_rule() -> None:
    """25. Company explicitly requiring minimum diploma percentage."""
    student = make_student(diploma=78.0)
    rule_set = RuleSet(id="r", name="R", company_id="c", company_name="C", rules=[PercentageMinRule(id="rpd", qualification="diploma", min_percentage=75.0)])
    res = EligibilityEvaluator().evaluate(student, rule_set, drive_id="d1")
    assert res.status == EligibilityStatus.ELIGIBLE


# =============================================================================
# SCENARIOS 26 - 32: Branch Aliases, Normalization & Equivalence Groups
# =============================================================================

@pytest.mark.parametrize(
    "student_branch, allowed_branches, expected",
    [
        ("CSE", ["CSE", "IT"], EligibilityStatus.ELIGIBLE),                           # 26. Exact branch
        ("Computer Science and Engineering", ["CSE"], EligibilityStatus.ELIGIBLE),     # 27. Full name alias to CSE
        ("Information Technology", ["IT"], EligibilityStatus.ELIGIBLE),               # 28. Full name alias to IT
        ("Mechanical Engineering", ["CSE", "IT"], EligibilityStatus.INELIGIBLE),       # 29. Disallowed branch
        ("Civil Engineering", ["All Branches"], EligibilityStatus.ELIGIBLE),          # 30. All branches wildcard
        ("ECE", ["Electronics and Communication"], EligibilityStatus.ELIGIBLE),       # 31. Electronics alias
        ("cse", ["CSE"], EligibilityStatus.ELIGIBLE),                                 # 32. Case-insensitivity
    ],
)
def test_branch_alias_resolution(student_branch: str, allowed_branches: list[str], expected: EligibilityStatus) -> None:
    student = make_student(branch=student_branch)
    rule_set = RuleSet(id="r", name="R", company_id="c", company_name="C", rules=[BranchInRule(id="rb", allowed_branches=allowed_branches)])
    res = EligibilityEvaluator().evaluate(student, rule_set, drive_id="d1")
    assert res.status == expected


# =============================================================================
# SCENARIOS 33 - 36: Gap Years Horizons
# =============================================================================

def test_scenario_33_gap_year_at_exact_limit() -> None:
    """33. 1 gap year allowed, student has 1 gap year (eligible)."""
    gy = GapYearRecord(start_year=2021, end_year=2022, duration_years=1, reason="Entrance Prep")
    student = make_student(gap_years=[gy])
    rule_set = RuleSet(id="r", name="R", company_id="c", company_name="C", rules=[GapYearsMaxRule(id="rg", max_gap_years=1)])
    res = EligibilityEvaluator().evaluate(student, rule_set, drive_id="d1")
    assert res.status == EligibilityStatus.ELIGIBLE


def test_scenario_34_gap_years_exceeding_limit() -> None:
    """34. 1 gap year allowed, student has 2 gap years (ineligible)."""
    gy1 = GapYearRecord(start_year=2020, end_year=2021, duration_years=1, reason="Prep")
    gy2 = GapYearRecord(start_year=2021, end_year=2022, duration_years=1, reason="Health")
    student = make_student(gap_years=[gy1, gy2])
    rule_set = RuleSet(id="r", name="R", company_id="c", company_name="C", rules=[GapYearsMaxRule(id="rg", max_gap_years=1)])
    res = EligibilityEvaluator().evaluate(student, rule_set, drive_id="d1")
    assert res.status == EligibilityStatus.INELIGIBLE


def test_scenario_35_zero_gap_years_allowed_with_zero_gaps() -> None:
    """35. Zero gap years allowed, clean education record passes."""
    student = make_student(gap_years=[])
    rule_set = RuleSet(id="r", name="R", company_id="c", company_name="C", rules=[GapYearsMaxRule(id="rg", max_gap_years=0)])
    res = EligibilityEvaluator().evaluate(student, rule_set, drive_id="d1")
    assert res.status == EligibilityStatus.ELIGIBLE


def test_scenario_36_zero_gap_years_allowed_with_gap_fails() -> None:
    """36. Zero gap years allowed, any gap record fails."""
    gy = GapYearRecord(start_year=2021, end_year=2022, duration_years=1, reason="Prep")
    student = make_student(gap_years=[gy])
    rule_set = RuleSet(id="r", name="R", company_id="c", company_name="C", rules=[GapYearsMaxRule(id="rg", max_gap_years=0)])
    res = EligibilityEvaluator().evaluate(student, rule_set, drive_id="d1")
    assert res.status == EligibilityStatus.INELIGIBLE


# =============================================================================
# SCENARIOS 37 - 50: College Offer Policies, Dream Bands & Progressions
# =============================================================================

def test_scenario_37_strict_one_offer_no_prior_offers() -> None:
    """37. Student with no offers is allowed to sit for drive under strict one-offer."""
    student = make_student(offers=[])
    drive = make_drive(ctc=8.0)
    res = policy_check(student, drive, STRICT_ONE_OFFER_POLICY)
    assert res.status == PolicyCheckStatus.ALLOWED


def test_scenario_38_strict_one_offer_holding_regular_offer() -> None:
    """38. Student holding 1 regular offer is blocked from regular drive."""
    offer = OfferRecord(
        company="Wipro", ctc_lpa=6.5,
        offer_date=datetime.date(2026, 10, 1), source=OfferSource.ON_CAMPUS, status=OfferStatus.OFFERED,
    )
    student = make_student(offers=[offer])
    drive = make_drive(ctc=7.0)
    res = policy_check(student, drive, STRICT_ONE_OFFER_POLICY)
    assert res.status == PolicyCheckStatus.BLOCKED
    assert "one-offer" in res.plain_english_reason.lower() or "one offer" in res.plain_english_reason.lower()


def test_scenario_39_dream_upgrade_allowed() -> None:
    """39. Student holding 6.5 LPA offer is allowed to sit for 15 LPA Dream Drive."""
    offer = OfferRecord(
        company="Wipro", ctc_lpa=6.5,
        offer_date=datetime.date(2026, 10, 1), source=OfferSource.ON_CAMPUS, status=OfferStatus.OFFERED,
    )
    student = make_student(offers=[offer])
    drive = make_drive(ctc=15.0)  # > 10.0 LPA dream threshold
    res = policy_check(student, drive, STRICT_ONE_OFFER_POLICY)
    assert res.status == PolicyCheckStatus.ALLOWED
    assert "dream" in res.plain_english_reason.lower()


def test_scenario_40_dream_threshold_exact_inclusive() -> None:
    """40. Dream threshold exact 10.0 LPA with inclusive toggle is treated as DREAM."""
    policy = CollegeOfferPolicy(
        id="pol_inc", name="Inclusive Policy", version=1,
        max_total_offers=1, dream_threshold_lpa=10.0, is_threshold_inclusive=True,
    )
    offer = OfferRecord(
        company="Cognizant", ctc_lpa=5.0,
        offer_date=datetime.date(2026, 10, 1), source=OfferSource.ON_CAMPUS, status=OfferStatus.OFFERED,
    )
    student = make_student(offers=[offer])
    drive = make_drive(ctc=10.0)  # exactly 10.0
    res = policy_check(student, drive, policy)
    assert res.status == PolicyCheckStatus.ALLOWED


def test_scenario_41_dream_threshold_exact_exclusive() -> None:
    """41. Dream threshold exact 10.0 LPA with exclusive toggle is treated as REGULAR (blocked)."""
    policy = CollegeOfferPolicy(
        id="pol_exc", name="Exclusive Policy", version=1,
        max_total_offers=1, dream_threshold_lpa=10.0, is_threshold_inclusive=False,
    )
    offer = OfferRecord(
        company="Cognizant", ctc_lpa=5.0,
        offer_date=datetime.date(2026, 10, 1), source=OfferSource.ON_CAMPUS, status=OfferStatus.OFFERED,
    )
    student = make_student(offers=[offer])
    drive = make_drive(ctc=10.0)  # exactly 10.0
    res = policy_check(student, drive, policy)
    assert res.status == PolicyCheckStatus.BLOCKED


def test_scenario_42_holding_dream_offer_cannot_sit_for_lateral_dream() -> None:
    """42. Student holding 15 LPA dream offer cannot sit for 12 LPA drive (only upward moves allowed)."""
    offer = OfferRecord(
        company="Amazon", ctc_lpa=15.0, is_dream=True,
        offer_date=datetime.date(2026, 10, 1), source=OfferSource.ON_CAMPUS, status=OfferStatus.OFFERED,
    )
    student = make_student(offers=[offer])
    drive = make_drive(ctc=12.0)
    res = policy_check(student, drive, STRICT_ONE_OFFER_POLICY)
    assert res.status == PolicyCheckStatus.BLOCKED


def test_scenario_43_two_dream_offers_policy_first_dream_holds() -> None:
    """43. Policy allowing 2 dream offers lets student with 1 dream offer sit for higher dream drive."""
    policy = CollegeOfferPolicy(
        id="pol_2dream", name="Two Dream Policy", version=1,
        max_total_offers=2, dream_threshold_lpa=10.0, max_dream_offers=2, allow_upgrade_to_dream=True,
    )
    offer = OfferRecord(
        company="InnoTech", ctc_lpa=12.0, is_dream=True,
        offer_date=datetime.date(2026, 10, 1), source=OfferSource.ON_CAMPUS, status=OfferStatus.OFFERED,
    )
    student = make_student(offers=[offer])
    drive = make_drive(ctc=18.0)
    res = policy_check(student, drive, policy)
    assert res.status == PolicyCheckStatus.ALLOWED


def test_scenario_44_two_dream_offers_policy_second_dream_reached() -> None:
    """44. Student holding 2 dream offers is blocked from 3rd drive under 2-dream policy."""
    policy = CollegeOfferPolicy(
        id="pol_2dream", name="Two Dream Policy", version=1,
        max_total_offers=2, dream_threshold_lpa=10.0, max_dream_offers=2,
    )
    o1 = OfferRecord(company="A", ctc_lpa=12.0, is_dream=True, offer_date=datetime.date(2026, 9, 1), source=OfferSource.ON_CAMPUS, status=OfferStatus.OFFERED)
    o2 = OfferRecord(company="B", ctc_lpa=16.0, is_dream=True, offer_date=datetime.date(2026, 10, 1), source=OfferSource.ON_CAMPUS, status=OfferStatus.OFFERED)
    student = make_student(offers=[o1, o2])
    drive = make_drive(ctc=25.0)
    res = policy_check(student, drive, policy)
    assert res.status == PolicyCheckStatus.BLOCKED


def test_scenario_45_revoked_offer_unblocks_student() -> None:
    """45. Company revokes offer; student is unblocked when count_revoked_offers=False."""
    offer = OfferRecord(
        company="StartupX", ctc_lpa=8.0,
        offer_date=datetime.date(2026, 10, 1), source=OfferSource.ON_CAMPUS, status=OfferStatus.REVOKED,
    )
    student = make_student(offers=[offer])
    drive = make_drive(ctc=9.0)
    res = policy_check(student, drive, STRICT_ONE_OFFER_POLICY)
    assert res.status == PolicyCheckStatus.ALLOWED


def test_scenario_46_declined_offer_counts_when_toggle_enabled() -> None:
    """46. Student rejects offer; burns their placement chance if count_rejected_offers=True."""
    policy = CollegeOfferPolicy(
        id="pol_dec", name="Strict Rejection Policy", version=1,
        max_total_offers=1, count_rejected_offers=True,
    )
    offer = OfferRecord(
        company="CorpA", ctc_lpa=7.0,
        offer_date=datetime.date(2026, 10, 1), source=OfferSource.ON_CAMPUS, status=OfferStatus.REJECTED,
    )
    student = make_student(offers=[offer])
    drive = make_drive(ctc=8.0)
    res = policy_check(student, drive, policy)
    assert res.status == PolicyCheckStatus.BLOCKED


def test_scenario_47_declined_offer_ignored_when_toggle_disabled() -> None:
    """47. Student rejects offer; remains eligible if count_rejected_offers=False."""
    policy = CollegeOfferPolicy(
        id="pol_dec_free", name="Forgiving Rejection Policy", version=1,
        max_total_offers=1, count_rejected_offers=False,
    )
    offer = OfferRecord(
        company="CorpA", ctc_lpa=7.0,
        offer_date=datetime.date(2026, 10, 1), source=OfferSource.ON_CAMPUS, status=OfferStatus.REJECTED,
    )
    student = make_student(offers=[offer])
    drive = make_drive(ctc=8.0)
    res = policy_check(student, drive, policy)
    assert res.status == PolicyCheckStatus.ALLOWED


def test_scenario_48_off_campus_offer_ignored_by_default() -> None:
    """48. Off-campus offer is not counted when count_off_campus_offers=False."""
    offer = OfferRecord(
        company="External Co", ctc_lpa=12.0,
        offer_date=datetime.date(2026, 10, 1), source=OfferSource.OFF_CAMPUS, status=OfferStatus.OFFERED,
    )
    student = make_student(offers=[offer])
    drive = make_drive(ctc=8.0)
    res = policy_check(student, drive, TIERED_QUOTA_POLICY)
    assert res.status == PolicyCheckStatus.ALLOWED


def test_scenario_49_off_campus_offer_counted_when_enabled() -> None:
    """49. Off-campus offer blocks student when count_off_campus_offers=True."""
    policy = CollegeOfferPolicy(
        id="pol_ext_strict", name="Count Off-Campus Policy", version=1,
        max_total_offers=1, count_off_campus_offers=True,
    )
    offer = OfferRecord(
        company="External Co", ctc_lpa=12.0,
        offer_date=datetime.date(2026, 10, 1), source=OfferSource.OFF_CAMPUS, status=OfferStatus.OFFERED,
    )
    student = make_student(offers=[offer])
    drive = make_drive(ctc=8.0)
    res = policy_check(student, drive, policy)
    assert res.status == PolicyCheckStatus.BLOCKED


def test_scenario_50_pre_effective_date_policy_allows_all() -> None:
    """50. Policy effective only after drive date does not restrict student."""
    policy = CollegeOfferPolicy(
        id="pol_future", name="Future Policy", version=1,
        effective_from=datetime.date(2027, 1, 1), max_total_offers=1,
    )
    offer = OfferRecord(
        company="Existing Co", ctc_lpa=6.0,
        offer_date=datetime.date(2026, 10, 1), source=OfferSource.ON_CAMPUS, status=OfferStatus.OFFERED,
    )
    student = make_student(offers=[offer])
    drive = make_drive(ctc=7.0, date_=datetime.date(2026, 11, 15))
    res = policy_check(student, drive, policy)
    assert res.status == PolicyCheckStatus.ALLOWED


# =============================================================================
# SCENARIOS 51 - 65: Comparative Explainer, Overrides, and Governance
# =============================================================================

def test_scenario_51_compare_two_students_one_allowed_one_blocked() -> None:
    """51. Compare Student A (no offers, allowed) vs Student B (holds 8 LPA, blocked from 7 LPA drive)."""
    sA = make_student(id="sA", roll_no="ROLL_A", offers=[])
    oB = OfferRecord(company="OldCorp", ctc_lpa=8.0, offer_date=datetime.date(2026, 10, 1), source=OfferSource.ON_CAMPUS, status=OfferStatus.OFFERED)
    sB = make_student(id="sB", roll_no="ROLL_B", offers=[oB])
    drive = make_drive(ctc=7.0)

    comparison = compare_students(sA, sB, drive, STRICT_ONE_OFFER_POLICY)
    assert comparison.student_a_status == PolicyCheckStatus.ALLOWED
    assert comparison.student_b_status == PolicyCheckStatus.BLOCKED
    assert f"({sA.roll_no}) was ALLOWED" in comparison.comparative_summary
    assert f"({sB.roll_no}) was BLOCKED" in comparison.comparative_summary


def test_scenario_52_fixed_pay_threshold_basis_selection() -> None:
    """52. Policy uses fixed pay basis: 14 LPA CTC with 7 LPA fixed fails 10 LPA fixed dream threshold."""
    policy = CollegeOfferPolicy(
        id="pol_fp", name="Fixed Pay Dream", version=1,
        max_total_offers=1, dream_threshold_lpa=10.0, threshold_basis=ThresholdBasis.FIXED_PAY,
    )
    offer = OfferRecord(
        company="BaseCo", ctc_lpa=5.0, fixed_pay_lpa=5.0,
        offer_date=datetime.date(2026, 10, 1), source=OfferSource.ON_CAMPUS, status=OfferStatus.OFFERED,
    )
    student = make_student(offers=[offer])
    # Drive has 14 LPA CTC, but only 7.5 LPA fixed base
    drive = make_drive(ctc=14.0, fixed_pay=7.5)
    res = policy_check(student, drive, policy)
    assert res.status == PolicyCheckStatus.BLOCKED


def test_scenario_53_cooling_window_enforcement() -> None:
    """53. Student receives offer 5 days ago; 14-day cooling window blocks new drives."""
    policy = CollegeOfferPolicy(
        id="pol_cool", name="Cooling Window Policy", version=1,
        max_total_offers=2, cooling_period_days=14,
    )
    offer = OfferRecord(
        company="FastHire", ctc_lpa=8.0,
        offer_date=datetime.date(2026, 11, 15), source=OfferSource.ON_CAMPUS, status=OfferStatus.OFFERED,
    )
    student = make_student(offers=[offer])
    drive = make_drive(date_=datetime.date(2026, 11, 20))  # only 5 days later
    res = policy_check(student, drive, policy)
    assert res.status == PolicyCheckStatus.BLOCKED
    assert "cooling" in res.plain_english_reason.lower()


def test_scenario_54_cooling_window_expired() -> None:
    """54. Student receives offer 20 days ago; 14-day cooling window has elapsed (allowed)."""
    policy = CollegeOfferPolicy(
        id="pol_cool", name="Cooling Window Policy", version=1,
        max_total_offers=2, cooling_period_days=14,
    )
    offer = OfferRecord(
        company="FastHire", ctc_lpa=8.0,
        offer_date=datetime.date(2026, 10, 30), source=OfferSource.ON_CAMPUS, status=OfferStatus.OFFERED,
    )
    student = make_student(offers=[offer])
    drive = make_drive(date_=datetime.date(2026, 11, 20))  # 21 days later
    res = policy_check(student, drive, policy)
    assert res.status == PolicyCheckStatus.ALLOWED


def test_scenario_55_tier_based_upgrade_allowed() -> None:
    """55. Tiered Policy: Student holding Standard tier offer (<8 LPA) is allowed to sit for Dream Tier (14 LPA)."""
    offer = OfferRecord(
        company="Tier2Co", ctc_lpa=6.0,
        offer_date=datetime.date(2026, 10, 1), source=OfferSource.ON_CAMPUS, status=OfferStatus.OFFERED,
    )
    student = make_student(offers=[offer])
    # Tier 1 drive at 14 LPA
    drive = make_drive(ctc=14.0)
    res = policy_check(student, drive, TIERED_QUOTA_POLICY)
    assert res.status == PolicyCheckStatus.ALLOWED


def test_scenario_56_tier_based_upgrade_blocked_for_equal_tier() -> None:
    """56. Tiered Policy: Student holding Super-Dream offer (>18 LPA) cannot sit for another Super-Dream drive."""
    offer = OfferRecord(
        company="SuperDreamCo", ctc_lpa=22.0,
        offer_date=datetime.date(2026, 10, 1), source=OfferSource.ON_CAMPUS, status=OfferStatus.OFFERED,
    )
    student = make_student(offers=[offer])
    drive = make_drive(ctc=24.0)
    res = policy_check(student, drive, TIERED_QUOTA_POLICY)
    assert res.status == PolicyCheckStatus.BLOCKED


def test_scenario_57_progressive_multiplier_policy_enforcement() -> None:
    """57. Progressive Multiplier Policy: 6 LPA offer requires next offer to be >= 1.5x (9.0 LPA)."""
    offer = OfferRecord(
        company="RegCo", ctc_lpa=6.0,
        offer_date=datetime.date(2026, 10, 1), source=OfferSource.ON_CAMPUS, status=OfferStatus.OFFERED,
    )
    student = make_student(offers=[offer])
    # 8.0 LPA drive is < 9.0 LPA (1.5x of 6.0) -> BLOCKED
    drive_low = make_drive(ctc=8.0)
    res_low = policy_check(student, drive_low, PROGRESSIVE_MULTIPLIER_POLICY)
    assert res_low.status == PolicyCheckStatus.BLOCKED

    # 10.0 LPA drive is >= 9.0 LPA -> ALLOWED
    drive_high = make_drive(ctc=10.0)
    res_high = policy_check(student, drive_high, PROGRESSIVE_MULTIPLIER_POLICY)
    assert res_high.status == PolicyCheckStatus.ALLOWED


def test_scenario_58_combined_eligibility_and_policy_pass() -> None:
    """58. Candidate meeting both academic rules and offer policy gets full clearance."""
    student = make_student(cgpa=8.5, branch="CSE", offers=[])
    drive = make_drive(ctc=10.0)
    rule_set = RuleSet(id="r", name="R", company_id="c", company_name="C", rules=[CGPAMinRule(id="rcgpa", min_cgpa=8.0)])

    acad_res = EligibilityEvaluator().evaluate(student, rule_set, drive_id="d1")
    pol_res = policy_check(student, drive, STRICT_ONE_OFFER_POLICY)

    assert acad_res.status == EligibilityStatus.ELIGIBLE
    assert pol_res.status == PolicyCheckStatus.ALLOWED


def test_scenario_59_academically_eligible_but_policy_blocked() -> None:
    """59. Candidate has 9.8 CGPA but holds existing offer; blocked by policy with explicit distinction."""
    offer = OfferRecord(company="FirstCo", ctc_lpa=6.0, offer_date=datetime.date(2026, 10, 1), source=OfferSource.ON_CAMPUS, status=OfferStatus.OFFERED)
    student = make_student(cgpa=9.8, branch="CSE", offers=[offer])
    drive = make_drive(ctc=8.0)
    rule_set = RuleSet(id="r", name="R", company_id="c", company_name="C", rules=[CGPAMinRule(id="rcgpa", min_cgpa=8.0)])

    acad_res = EligibilityEvaluator().evaluate(student, rule_set, drive_id="d1")
    pol_res = policy_check(student, drive, STRICT_ONE_OFFER_POLICY)

    assert acad_res.status == EligibilityStatus.ELIGIBLE
    assert pol_res.status == PolicyCheckStatus.BLOCKED
    assert "one-offer" in pol_res.plain_english_reason.lower() or "one offer" in pol_res.plain_english_reason.lower()


def test_scenario_60_policy_allowed_but_academically_ineligible() -> None:
    """60. Candidate has 0 offers (policy allowed) but 6.2 CGPA for 7.5 cut-off (academically ineligible)."""
    student = make_student(cgpa=6.2, branch="CSE", offers=[])
    drive = make_drive(ctc=12.0)
    rule_set = RuleSet(id="r", name="R", company_id="c", company_name="C", rules=[CGPAMinRule(id="rcgpa", min_cgpa=7.5)])

    acad_res = EligibilityEvaluator().evaluate(student, rule_set, drive_id="d1")
    pol_res = policy_check(student, drive, STRICT_ONE_OFFER_POLICY)

    assert acad_res.status == EligibilityStatus.INELIGIBLE
    assert pol_res.status == PolicyCheckStatus.ALLOWED
    assert "CGPA is 6.2" in acad_res.one_line_explanation
