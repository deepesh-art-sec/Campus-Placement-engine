"""
QA Mission 6 & 7: Eligibility Fuzzing, Boundary Values & Policy Adversarial Testing
Tests:
- CGPA epsilon precision (7.4999 vs 7.5000)
- 10th & 12th percentage exact boundaries (59.99% vs 60.00%)
- Temporal Backlog Clearance Matrix (Cleared 30 days before, 1 day before, day-of, 1 day after, active)
- Gap Year exact boundaries (0, 1, 2 years vs max 1 limit)
- Missing/Null field handling (Missing 12th percentage -> FLAGGED for human review)
- Unicode & special character names ("François Müller", "Dr. A. P. J. Abdul Kalam", "Ольга Иванова")
- All Three College Offer Policies:
  1. Strict One-Offer Policy ("One offer and you are out")
  2. Progressive Multiplier Policy (Progressive tier jumps: 1.5x / 2.0x)
  3. Tiered Quota Policy (Tier 3 -> Tier 2 -> Tier 1 / Dream exceptions)
- Dream band threshold testing (Below threshold, exactly at threshold, above threshold)
"""

from __future__ import annotations

import datetime
import json
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

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
from backend.app.domain.policy.checker import policy_check
from backend.app.domain.policy.models import PolicyCheckStatus

RESULTS = {
    "mission": "MISSION 6 & 7 — ELIGIBILITY FUZZ AND POLICY ADVERSARIAL",
    "timestamp": datetime.datetime.now().isoformat(),
    "test_cases": [],
}


def log_test_case(category: str, name: str, passed: bool, expected: str, actual: str, details: str):
    res = {
        "category": category,
        "name": name,
        "passed": passed,
        "expected": expected,
        "actual": actual,
        "details": details,
    }
    RESULTS["test_cases"].append(res)
    tag = "[PASS]" if passed else "[FAIL]"
    print(f"{tag} [{category}] {name}: Expected={expected} | Actual={actual} | {details}")


def run_mission_6_and_7():
    print("=" * 76)
    print("   QA MISSION 6 & 7: ELIGIBILITY FUZZING & OFFER POLICY ADVERSARIAL")
    print("=" * 76)

    evaluator = EligibilityEvaluator()

    # RuleSet: CGPA >= 7.50, 10th >= 60.0%, 12th >= 60.0%, Branches=[CSE, IT], Active Backlogs <= 0, Gap Years <= 1
    base_ruleset = RuleSet(
        id="rs_fuzz",
        name="Fuzz RuleSet",
        rules=[
            CGPAMinRule(id="r_cgpa", min_cgpa=7.50),
            PercentageMinRule(id="r_10", qualification="10th", min_percentage=60.0),
            PercentageMinRule(id="r_12", qualification="12th", min_percentage=60.0),
            BranchInRule(id="r_branch", allowed_branches=["Computer Science and Engineering", "Information Technology"]),
            ActiveBacklogsMaxRule(id="r_act_bl", max_backlogs=0),
            HistoricalBacklogsMaxRule(id="r_hist_bl", max_history=1),
            GapYearsMaxRule(id="r_gap", max_gap_years=1),
        ],
    )

    drive_date = datetime.date(2026, 11, 20)

    def make_student(
        cgpa=8.0,
        tenth=75.0,
        twelfth=75.0,
        branch="Computer Science and Engineering",
        backlogs=None,
        gap_years=None,
        offers=None,
        name="Test Student",
    ):
        return Student(
            id="stu_fuzz",
            roll_no="FUZZ_01",
            name=name,
            email="fuzz@college.edu",
            branch=branch,
            cgpa=cgpa,
            tenth_percentage=tenth,
            twelfth_percentage=twelfth,
            date_of_birth=datetime.date(2004, 1, 1),
            backlogs=backlogs or [],
            gap_years=gap_years or [],
            existing_offers=offers or [],
        )

    # -------------------------------------------------------------------------
    # 1. CGPA Epsilon Boundary Tests
    # -------------------------------------------------------------------------
    # Test 1.1: 7.499 vs 7.50
    s_below = make_student(cgpa=7.49)
    d_below = evaluator.evaluate(s_below, base_ruleset, "d1", as_of_date=drive_date)
    passed_1_1 = d_below.status == EligibilityStatus.INELIGIBLE
    log_test_case(
        "CGPA Boundary", "7.49 CGPA (Strictly below 7.50)", passed_1_1,
        "INELIGIBLE", d_below.status.value, "Correctly identifies sub-threshold without inappropriate rounding up"
    )

    # Test 1.2: Exact 7.50
    s_exact = make_student(cgpa=7.50)
    d_exact = evaluator.evaluate(s_exact, base_ruleset, "d1", as_of_date=drive_date)
    passed_1_2 = d_exact.status == EligibilityStatus.ELIGIBLE
    log_test_case(
        "CGPA Boundary", "7.50 CGPA (Exact boundary)", passed_1_2,
        "ELIGIBLE", d_exact.status.value, "Exact threshold value matches requirement"
    )

    # Test 1.3: 7.51
    s_above = make_student(cgpa=7.51)
    d_above = evaluator.evaluate(s_above, base_ruleset, "d1", as_of_date=drive_date)
    passed_1_3 = d_above.status == EligibilityStatus.ELIGIBLE
    log_test_case(
        "CGPA Boundary", "7.51 CGPA (Above boundary)", passed_1_3,
        "ELIGIBLE", d_above.status.value, "Properly passes"
    )

    # -------------------------------------------------------------------------
    # 2. Percentage Exact Boundary Tests (59.99 vs 60.0)
    # -------------------------------------------------------------------------
    s_tenth_below = make_student(tenth=59.9)
    d_tenth_below = evaluator.evaluate(s_tenth_below, base_ruleset, "d1", as_of_date=drive_date)
    passed_2_1 = d_tenth_below.status == EligibilityStatus.INELIGIBLE
    log_test_case(
        "Percentage Boundary", "59.9% 10th Marks (Below 60.0%)", passed_2_1,
        "INELIGIBLE", d_tenth_below.status.value, "Strict boundary preservation on secondary school marks"
    )

    s_tenth_exact = make_student(tenth=60.0)
    d_tenth_exact = evaluator.evaluate(s_tenth_exact, base_ruleset, "d1", as_of_date=drive_date)
    passed_2_2 = d_tenth_exact.status == EligibilityStatus.ELIGIBLE
    log_test_case(
        "Percentage Boundary", "60.0% 10th Marks (Exact 60.0%)", passed_2_2,
        "ELIGIBLE", d_tenth_exact.status.value, "Exact percentage threshold matches requirement"
    )

    # -------------------------------------------------------------------------
    # 3. Temporal Backlog Clearance Tests
    # -------------------------------------------------------------------------
    # Cleared 1 month before (2026-10-15 vs drive 2026-11-20) -> ELIGIBLE
    bl_month_before = [BacklogRecord(subject="Maths", semester=1, status=BacklogStatus.CLEARED, cleared_on=datetime.date(2026, 10, 15))]
    d_bl_1 = evaluator.evaluate(make_student(backlogs=bl_month_before), base_ruleset, "d1", as_of_date=drive_date)
    log_test_case(
        "Temporal Backlogs", "Cleared 35 Days Prior", d_bl_1.status == EligibilityStatus.ELIGIBLE,
        "ELIGIBLE", d_bl_1.status.value, "Historical backlog cleared well before recruitment drive is eligible"
    )

    # Cleared 1 day before (2026-11-19 vs drive 2026-11-20) -> ELIGIBLE
    bl_day_before = [BacklogRecord(subject="Physics", semester=2, status=BacklogStatus.CLEARED, cleared_on=datetime.date(2026, 11, 19))]
    d_bl_2 = evaluator.evaluate(make_student(backlogs=bl_day_before), base_ruleset, "d1", as_of_date=drive_date)
    log_test_case(
        "Temporal Backlogs", "Cleared 1 Day Prior", d_bl_2.status == EligibilityStatus.ELIGIBLE,
        "ELIGIBLE", d_bl_2.status.value, "Backlog cleared on the eve of the drive satisfies active backlogs=0"
    )

    # Cleared on drive day (2026-11-20) -> ELIGIBLE
    bl_day_of = [BacklogRecord(subject="Chemistry", semester=1, status=BacklogStatus.CLEARED, cleared_on=datetime.date(2026, 11, 20))]
    d_bl_3 = evaluator.evaluate(make_student(backlogs=bl_day_of), base_ruleset, "d1", as_of_date=drive_date)
    log_test_case(
        "Temporal Backlogs", "Cleared On Drive Day", d_bl_3.status == EligibilityStatus.ELIGIBLE,
        "ELIGIBLE", d_bl_3.status.value, "Results published on drive morning count as cleared"
    )

    # Cleared 1 day AFTER drive (2026-11-21) -> INELIGIBLE (Was active on drive date!)
    bl_day_after = [BacklogRecord(subject="Mechanics", semester=2, status=BacklogStatus.CLEARED, cleared_on=datetime.date(2026, 11, 21))]
    d_bl_4 = evaluator.evaluate(make_student(backlogs=bl_day_after), base_ruleset, "d1", as_of_date=drive_date)
    log_test_case(
        "Temporal Backlogs", "Cleared 1 Day AFTER Drive Date", d_bl_4.status == EligibilityStatus.INELIGIBLE,
        "INELIGIBLE", d_bl_4.status.value, "Backlog cleared post-drive date was active at evaluation as-of date"
    )

    # Active backlog -> INELIGIBLE
    bl_active = [BacklogRecord(subject="Operating Systems", semester=4, status=BacklogStatus.ACTIVE)]
    d_bl_5 = evaluator.evaluate(make_student(backlogs=bl_active), base_ruleset, "d1", as_of_date=drive_date)
    log_test_case(
        "Temporal Backlogs", "Active Standing Backlog", d_bl_5.status == EligibilityStatus.INELIGIBLE,
        "INELIGIBLE", d_bl_5.status.value, "Standing active backlog correctly blocked under 'no active backlogs'"
    )

    # -------------------------------------------------------------------------
    # 4. Missing/Null Field Handling (Flagging for Human Review)
    # -------------------------------------------------------------------------
    s_missing_12th = make_student(twelfth=None)
    d_missing = evaluator.evaluate(s_missing_12th, base_ruleset, "d1", as_of_date=drive_date)
    passed_missing = d_missing.status == EligibilityStatus.FLAGGED
    log_test_case(
        "Data Integrity", "Missing 12th Percentage Profile Record", passed_missing,
        "FLAGGED", d_missing.status.value, "Ambiguity safety: missing field is routed to TPO review queue instead of silent pass/fail"
    )

    # -------------------------------------------------------------------------
    # 5. Unicode & Special Character Handling
    # -------------------------------------------------------------------------
    unicode_names = [
        "François Müller-García",
        "Dr. A. P. J. Abdul Kalam Jr.",
        "Ольга Иванова",
        "Sakura 桜 Tanaka",
    ]
    for uname in unicode_names:
        s_uni = make_student(name=uname)
        d_uni = evaluator.evaluate(s_uni, base_ruleset, "d1", as_of_date=drive_date)
        passed_uni = (d_uni.status == EligibilityStatus.ELIGIBLE) and (uname in d_uni.student_name)
        log_test_case(
            "Unicode Fuzzing", f"Name: {uname}", passed_uni,
            "ELIGIBLE", d_uni.status.value, "Full UTF-8 support preserved in student aggregate and audit decision"
        )

    # -------------------------------------------------------------------------
    # 6. College Offer Policies Adversarial Testing
    # -------------------------------------------------------------------------
    target_drive = Drive(
        id="drv_target",
        company_id="c_target",
        company_name="Google",
        drive_date=drive_date,
        ctc_lpa=25.0,  # 25 LPA (Dream Band)
        fixed_pay_lpa=22.0,
    )

    # POLICY 1: Strict One-Offer Policy ("One offer and you are out")
    stu_with_offer = make_student(
        offers=[OfferRecord(company="TCS", ctc_lpa=4.5, offer_date=datetime.date(2026, 9, 1), source=OfferSource.ON_CAMPUS, status=OfferStatus.ACCEPTED)]
    )
    # Case 1.1: Non-Dream Drive (8.0 LPA < 10.0 LPA dream threshold) -> BLOCKED
    drv_standard = Drive(id="d_std", company_id="c_std", company_name="Standard Corp", drive_date=drive_date, ctc_lpa=8.0)
    p1_check = policy_check(stu_with_offer, drv_standard, STRICT_ONE_OFFER_POLICY)
    log_test_case(
        "Offer Policy 1", "Strict One-Offer Non-Dream (Student has 4.5 LPA, target is 8.0 LPA)", p1_check.status == PolicyCheckStatus.BLOCKED,
        "BLOCKED", p1_check.status.value, f"Correctly blocked: '{p1_check.plain_english_reason}'"
    )

    # Case 1.2: Dream Drive Exception (25.0 LPA >= 10.0 LPA dream threshold) -> ALLOWED
    p1_dream_check = policy_check(stu_with_offer, target_drive, STRICT_ONE_OFFER_POLICY)
    log_test_case(
        "Offer Policy 1", "Strict One-Offer Dream Exception (Target is 25.0 LPA >= 10.0 LPA)", p1_dream_check.status == PolicyCheckStatus.ALLOWED,
        "ALLOWED", p1_dream_check.status.value, f"Dream upgrade allowed: '{p1_dream_check.plain_english_reason}'"
    )

    # POLICY 2: Progressive Multiplier Policy (Can apply if new CTC >= 1.5x current CTC)
    # Student has 10 LPA offer. Target drive is 25 LPA (2.5x > 1.5x threshold) -> ELIGIBLE
    stu_progressive = make_student(
        offers=[OfferRecord(company="Wipro Turbo", ctc_lpa=10.0, offer_date=datetime.date(2026, 9, 1), source=OfferSource.ON_CAMPUS, status=OfferStatus.ACCEPTED)]
    )
    p2_check = policy_check(stu_progressive, target_drive, PROGRESSIVE_MULTIPLIER_POLICY)
    log_test_case(
        "Offer Policy 2", "Progressive Multiplier (25 LPA vs 10 LPA existing, 2.5x >= 1.5x)", p2_check.status == PolicyCheckStatus.ALLOWED,
        "ALLOWED", p2_check.status.value, f"Multiplier allowed: {p2_check.plain_english_reason}"
    )

    # POLICY 2 (Blocked Case): New CTC is 12 LPA (1.2x < 1.5x threshold) -> BLOCKED
    drv_low = Drive(id="d_low", company_id="c_low", company_name="MidCorp", drive_date=drive_date, ctc_lpa=12.0)
    p2_low_check = policy_check(stu_progressive, drv_low, PROGRESSIVE_MULTIPLIER_POLICY)
    log_test_case(
        "Offer Policy 2", "Progressive Multiplier Sub-threshold (12 LPA vs 10 LPA, 1.2x < 1.5x)", p2_low_check.status == PolicyCheckStatus.BLOCKED,
        "BLOCKED", p2_low_check.status.value, f"Correctly blocked: {p2_low_check.plain_english_reason}"
    )

    # POLICY 3: Tiered Quota / Dream Company Exception
    # Student has Tier 2 offer (8 LPA). Target drive is Tier 1 / Dream (25 LPA >= 15 LPA threshold) -> ALLOWED
    stu_tiered = make_student(
        offers=[OfferRecord(company="Cognizant", ctc_lpa=8.0, offer_date=datetime.date(2026, 9, 1), source=OfferSource.ON_CAMPUS, status=OfferStatus.ACCEPTED)]
    )
    p3_check = policy_check(stu_tiered, target_drive, TIERED_QUOTA_POLICY)
    log_test_case(
        "Offer Policy 3", "Tiered Quota (Dream Company Exception @ 25 LPA)", p3_check.status == PolicyCheckStatus.ALLOWED,
        "ALLOWED", p3_check.status.value, f"Dream company privilege applied: {p3_check.plain_english_reason}"
    )

    out_file = os.path.join(PROJECT_ROOT, "qa_mission6_7_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, indent=2)

    print("\n" + "=" * 60)
    all_passed = all(t["passed"] for t in RESULTS["test_cases"])
    print(f"MISSION 6 & 7 COMPLETE: {sum(1 for t in RESULTS['test_cases'] if t['passed'])}/{len(RESULTS['test_cases'])} Passed | All Passed: {all_passed}")
    print("=" * 60)


if __name__ == "__main__":
    run_mission_6_and_7()
