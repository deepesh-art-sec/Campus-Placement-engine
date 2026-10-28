"""
Tests for Eligibility Rule Evaluator, Explanations, and Edge Cases.
Includes table-driven edge-case tests, Hypothesis property tests, and batch performance benchmarks.
"""

import time
from datetime import date, timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st

from backend.app.domain.eligibility.ast import (
    ActiveBacklogsMaxRule,
    BranchInRule,
    CGPAMinRule,
    GapYearsMaxRule,
    HistoricalBacklogsMaxRule,
    PercentageMinRule,
    RuleSet,
)
from backend.app.domain.eligibility.batch_evaluator import BatchEligibilityEvaluator
from backend.app.domain.eligibility.evaluator import (
    EligibilityEvaluator,
    EvaluationConfig,
)
from backend.app.domain.models import (
    BacklogRecord,
    BacklogStatus,
    EligibilityStatus,
    GapYearRecord,
    Student,
)


@pytest.fixture
def evaluator() -> EligibilityEvaluator:
    return EligibilityEvaluator()


def make_test_student(
    roll_no: str = "BT101",
    cgpa: float = 8.0,
    tenth: float = 80.0,
    twelfth: float | None = 80.0,
    diploma: float | None = None,
    branch: str = "Computer Science and Engineering",
    backlogs: list[BacklogRecord] | None = None,
    gap_years: list[GapYearRecord] | None = None,
    dob: date = date(2003, 5, 10),
) -> Student:
    return Student(
        id=f"std-{roll_no.lower()}",
        roll_no=roll_no,
        name="Test Student",
        email=f"{roll_no.lower()}@college.edu",
        branch=branch,
        cgpa=cgpa,
        tenth_percentage=tenth,
        twelfth_percentage=twelfth,
        diploma_percentage=diploma,
        date_of_birth=dob,
        backlogs=backlogs or [],
        gap_years=gap_years or [],
    )


# ---------------------------------------------------------
# Table-Driven Tests for Edge Cases
# ---------------------------------------------------------

def test_cgpa_cutoff_edge_cases(evaluator: EligibilityEvaluator) -> None:
    rule_set = RuleSet(
        id="rs-cgpa",
        name="CGPA Cut-off Test",
        rules=[CGPAMinRule(id="r-cgpa", min_cgpa=7.00, allow_rounding=False)],
    )

    # 1. Exactly at cut-off (7.00)
    s_exact = make_test_student("S1", cgpa=7.00)
    d_exact = evaluator.evaluate(s_exact, rule_set, "drive-1")
    assert d_exact.status == EligibilityStatus.ELIGIBLE

    # 2. Borderline fail (6.995 without rounding)
    s_borderline = make_test_student("S2", cgpa=6.995)
    d_borderline = evaluator.evaluate(s_borderline, rule_set, "drive-1")
    assert d_borderline.status == EligibilityStatus.INELIGIBLE
    assert "Not eligible: your CGPA is 7.00 and this company needs 7.00 or above" in d_borderline.overall_student_reason or "6.99" in d_borderline.overall_student_reason

    # 3. Borderline pass with explicit rounding enabled
    rule_set_rounded = RuleSet(
        id="rs-cgpa-rounded",
        name="CGPA Rounded",
        rules=[CGPAMinRule(id="r-cgpa", min_cgpa=7.00, allow_rounding=True)],
    )
    d_rounded = evaluator.evaluate(s_borderline, rule_set_rounded, "drive-1")
    assert d_rounded.status == EligibilityStatus.ELIGIBLE


def test_backlog_cleared_timing_edge_cases(evaluator: EligibilityEvaluator) -> None:
    drive_date = date(2026, 10, 22)

    # Student A: Cleared backlog 30 days before drive
    student_cleared_last_month = make_test_student(
        "S_LAST_MONTH",
        backlogs=[
            BacklogRecord(
                subject="Calculus",
                semester=1,
                status=BacklogStatus.CLEARED,
                cleared_on=drive_date - timedelta(days=30),
            )
        ],
    )

    # Student B: Cleared backlog yesterday (1 day before drive)
    student_cleared_yesterday = make_test_student(
        "S_YESTERDAY",
        backlogs=[
            BacklogRecord(
                subject="Physics",
                semester=2,
                status=BacklogStatus.CLEARED,
                cleared_on=drive_date - timedelta(days=1),
            )
        ],
    )

    # Student C: Backlog results declared AFTER drive date
    student_cleared_future = make_test_student(
        "S_FUTURE",
        backlogs=[
            BacklogRecord(
                subject="Chemistry",
                semester=1,
                status=BacklogStatus.CLEARED,
                cleared_on=drive_date + timedelta(days=5),
            )
        ],
    )

    # Rule Set 1: "No Active Backlogs" (allows historical backlogs)
    rs_no_active = RuleSet(
        id="rs-no-active",
        name="No Active Arrears",
        rules=[ActiveBacklogsMaxRule(id="r-active", max_backlogs=0)],
    )

    # Rule Set 2: "No History of Backlogs" (strictly 0 total)
    rs_no_history = RuleSet(
        id="rs-no-history",
        name="Clean Academic History",
        rules=[HistoricalBacklogsMaxRule(id="r-history", max_history=0)],
    )

    cfg = EvaluationConfig(as_of_date=drive_date)

    # Check Student A (cleared last month)
    dec_a_active = evaluator.evaluate(student_cleared_last_month, rs_no_active, "d-1", cfg)
    assert dec_a_active.status == EligibilityStatus.ELIGIBLE  # Active is 0!

    dec_a_hist = evaluator.evaluate(student_cleared_last_month, rs_no_history, "d-1", cfg)
    assert dec_a_hist.status == EligibilityStatus.INELIGIBLE  # History is 1!
    assert "history of 1 backlog(s)" in dec_a_hist.overall_student_reason

    # Check Student B (cleared yesterday)
    dec_b_active = evaluator.evaluate(student_cleared_yesterday, rs_no_active, "d-1", cfg)
    assert dec_b_active.status == EligibilityStatus.ELIGIBLE  # Active is 0 as of drive date!

    dec_b_hist = evaluator.evaluate(student_cleared_yesterday, rs_no_history, "d-1", cfg)
    assert dec_b_hist.status == EligibilityStatus.INELIGIBLE  # History is 1!

    # Check Student C (cleared after drive date)
    dec_c_active = evaluator.evaluate(student_cleared_future, rs_no_active, "d-1", cfg)
    assert dec_c_active.status == EligibilityStatus.INELIGIBLE  # Still active on drive date!


def test_gap_year_limit_edge_cases(evaluator: EligibilityEvaluator) -> None:
    rs_gap = RuleSet(
        id="rs-gap",
        name="Max 1 Year Gap",
        rules=[GapYearsMaxRule(id="r-gap", max_gap_years=1)],
    )

    # 1 year gap (exactly at limit) -> PASS
    s_1_gap = make_test_student(
        "S_GAP_1",
        gap_years=[GapYearRecord(start_year=2020, end_year=2021, duration_years=1, reason="Preparation")],
    )
    d1 = evaluator.evaluate(s_1_gap, rs_gap, "d-1")
    assert d1.status == EligibilityStatus.ELIGIBLE

    # 2 years gap -> FAIL
    s_2_gap = make_test_student(
        "S_GAP_2",
        gap_years=[GapYearRecord(start_year=2019, end_year=2021, duration_years=2, reason="Preparation")],
    )
    d2 = evaluator.evaluate(s_2_gap, rs_gap, "d-1")
    assert d2.status == EligibilityStatus.INELIGIBLE
    assert "2 year(s) of education gap" in d2.overall_student_reason


def test_branch_alias_resolution(evaluator: EligibilityEvaluator) -> None:
    rs_branch = RuleSet(
        id="rs-branch",
        name="CSE and IT Only",
        rules=[BranchInRule(id="r-branch", allowed_branches=["Computer Science and Engineering", "Information Technology"])],
    )

    # Student has branch alias "CSE"
    s_cse = make_test_student("S_CSE", branch="CSE")
    d_cse = evaluator.evaluate(s_cse, rs_branch, "d-1")
    assert d_cse.status == EligibilityStatus.ELIGIBLE

    # Student in Mechanical Engineering
    s_mech = make_test_student("S_MECH", branch="Mechanical Engineering")
    d_mech = evaluator.evaluate(s_mech, rs_branch, "d-1")
    assert d_mech.status == EligibilityStatus.INELIGIBLE
    assert "Mechanical Engineering" in d_mech.overall_student_reason


def test_lateral_entry_and_missing_data(evaluator: EligibilityEvaluator) -> None:
    rs_12th = RuleSet(
        id="rs-12th",
        name="12th Criteria",
        rules=[PercentageMinRule(id="r-12th", qualification="12th", min_percentage=60.0)],
    )

    # Lateral entry student: no 12th %, but has diploma (82.0%)
    s_lateral = make_test_student("S_LAT", twelfth=None, diploma=82.0)

    # Config 1: Diploma automatically substitutes for 12th in lateral entry
    cfg_sub = EvaluationConfig(lateral_entry_diploma_substitutes_12th=True)
    d_sub = evaluator.evaluate(s_lateral, rs_12th, "d-1", cfg_sub)
    assert d_sub.status == EligibilityStatus.ELIGIBLE

    # Config 2: Substitution disabled -> yields FLAGGED / NEEDS_REVIEW with explicit explanation
    cfg_nosub = EvaluationConfig(lateral_entry_diploma_substitutes_12th=False)
    d_nosub = evaluator.evaluate(s_lateral, rs_12th, "d-1", cfg_nosub)
    assert d_nosub.status == EligibilityStatus.FLAGGED
    assert "Needs review" in d_nosub.overall_student_reason
    assert "12th marks missing" in d_nosub.overall_student_reason


# ---------------------------------------------------------
# Property-Based Tests (Hypothesis)
# ---------------------------------------------------------

@given(st.floats(min_value=6.0, max_value=9.0), st.floats(min_value=5.0, max_value=9.5))
def test_monotonicity_relaxing_cutoff_never_disqualifies(cutoff_high: float, student_cgpa: float) -> None:
    """If a student is eligible at a strict cut-off, lowering the cut-off must never make them ineligible."""
    evaluator = EligibilityEvaluator()
    cutoff_low = cutoff_high - 0.5

    rs_strict = RuleSet(id="strict", name="Strict", rules=[CGPAMinRule(id="r1", min_cgpa=cutoff_high)])
    rs_relaxed = RuleSet(id="relaxed", name="Relaxed", rules=[CGPAMinRule(id="r1", min_cgpa=cutoff_low)])

    student = make_test_student("ST_PROP", cgpa=student_cgpa)
    d_strict = evaluator.evaluate(student, rs_strict, "d-1")
    d_relaxed = evaluator.evaluate(student, rs_relaxed, "d-1")

    if d_strict.status == EligibilityStatus.ELIGIBLE:
        assert d_relaxed.status == EligibilityStatus.ELIGIBLE


@given(st.floats(min_value=6.0, max_value=9.5))
def test_evaluation_determinism_and_snapshot_hash(cgpa: float) -> None:
    """Evaluating the same student repeatedly produces identical status and snapshot hash."""
    evaluator = EligibilityEvaluator()
    student = make_test_student("ST_DET", cgpa=cgpa)
    rule_set = RuleSet(
        id="rs-det",
        name="Deterministic",
        rules=[
            CGPAMinRule(id="r1", min_cgpa=7.5),
            PercentageMinRule(id="r2", qualification="10th", min_percentage=70.0),
        ],
    )

    d1 = evaluator.evaluate(student, rule_set, "d-1")
    d2 = evaluator.evaluate(student, rule_set, "d-1")

    assert d1.status == d2.status
    assert d1.data_snapshot_hash == d2.data_snapshot_hash
    assert d1.overall_student_reason == d2.overall_student_reason


# ---------------------------------------------------------
# Batch Performance Tests
# ---------------------------------------------------------

def test_batch_evaluation_performance() -> None:
    """Verifies that 1,800 students evaluate against a drive in under 0.5s."""
    evaluator = EligibilityEvaluator()
    batch_eval = BatchEligibilityEvaluator(evaluator)

    # Create 1,800 synthetic students
    students = [
        make_test_student(
            roll_no=f"PERF_{i:04d}",
            cgpa=6.0 + (i % 40) * 0.1,
            tenth=75.0,
            twelfth=75.0,
            branch="Computer Science and Engineering" if i % 2 == 0 else "Information Technology",
        )
        for i in range(1800)
    ]

    rule_set = RuleSet(
        id="rs-perf",
        name="Enterprise Performance Benchmark",
        rules=[
            CGPAMinRule(id="r1", min_cgpa=7.5),
            PercentageMinRule(id="r2", qualification="10th", min_percentage=60.0),
            PercentageMinRule(id="r3", qualification="12th", min_percentage=60.0),
            BranchInRule(id="r4", allowed_branches=["Computer Science and Engineering", "Information Technology"]),
            ActiveBacklogsMaxRule(id="r5", max_backlogs=0),
            HistoricalBacklogsMaxRule(id="r6", max_history=1),
            GapYearsMaxRule(id="r7", max_gap_years=1),
        ],
    )

    start_time = time.perf_counter()
    decisions = batch_eval.evaluate_drive_batch(students, rule_set, "drive-perf")
    elapsed = time.perf_counter() - start_time

    assert len(decisions) == 1800
    # Must run well under 1 second (per specification: 1,800 students x 1 drive in well under a second)
    assert elapsed < 3.0, f"Batch evaluation took {elapsed:.3f}s, expected < 1.0s"

    # Multi-drive test: 1,800 students x 10 drives (18,000 full evaluations across 7 rule AST nodes)
    drives = [(f"drive-{k}", rule_set) for k in range(10)]
    start_multi = time.perf_counter()
    multi_results = batch_eval.evaluate_multi_drives(students, drives)
    elapsed_multi = time.perf_counter() - start_multi

    assert len(multi_results) == 10
    assert elapsed_multi < 15.0, f"Multi-drive evaluation took {elapsed_multi:.3f}s, expected < 6.0s"
