"""
QA Mission 2: Extreme Data Volume Stress Benchmark
Tests 1,800, 5,000, 10,000, and 25,000 students in an isolated SQLite database.
Benchmarks: Bulk Generation/Import, AST Eligibility Evaluation, What-If Simulation, and Spreadsheet Export.
"""

from __future__ import annotations

import datetime
import gc
import json
import os
import random
import sys
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

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
from backend.app.domain.eligibility.evaluator import EligibilityEvaluator, EligibilityStatus
from backend.app.domain.impact.models import ChangeRequest, ChangeType
from backend.app.domain.impact.what_if import WhatIfEngine
from backend.app.domain.models import (
    BacklogRecord,
    BacklogStatus,
    Drive,
    GapYearRecord,
    OfferRecord,
    OfferSource,
    OfferStatus,
    RequirementSet,
    Student,
)
from backend.app.domain.policy.catalog import STRICT_ONE_OFFER_POLICY
from backend.app.scheduler.models import RoomType, SchedulerRoom

BRANCHES = [
    "Computer Science and Engineering",
    "Information Technology",
    "Electronics and Communication Engineering",
    "Mechanical Engineering",
    "Civil Engineering",
    "Electrical Engineering",
    "Chemical Engineering",
    "Biotechnology",
    "Artificial Intelligence and Data Science",
]

RESULTS = {
    "mission": "MISSION 2 — EXTREME DATA VOLUME",
    "timestamp": datetime.datetime.now().isoformat(),
    "benchmarks": [],
}


def generate_synthetic_cohort(count: int, seed: int = 42) -> list[Student]:
    rng = random.Random(seed)
    students = []
    base_dob = datetime.date(2003, 1, 1)

    for i in range(1, count + 1):
        cgpa = round(min(10.0, max(4.0, rng.gauss(7.2, 1.0))), 2)
        tenth = round(min(99.0, max(50.0, rng.gauss(78.0, 8.0))), 1)
        twelfth = round(min(99.0, max(50.0, rng.gauss(75.0, 9.0))), 1)
        branch = BRANCHES[i % len(BRANCHES)]

        # Backlogs distribution
        backlogs = []
        bl_rand = rng.random()
        if bl_rand < 0.20:
            # Cleared backlog
            cleared_dt = datetime.date(2025, rng.randint(1, 12), rng.randint(1, 28))
            backlogs.append(BacklogRecord(subject="Maths I", semester=1, status=BacklogStatus.CLEARED, cleared_on=cleared_dt))
        elif bl_rand < 0.28:
            # Active backlog
            backlogs.append(BacklogRecord(subject="Data Structures", semester=3, status=BacklogStatus.ACTIVE))

        # Gap years distribution
        gap_years = []
        if rng.random() < 0.15:
            gap_years.append(GapYearRecord(start_year=2021, end_year=2022, duration_years=1, reason="Entrance Exam Prep", phase="between_12th_and_degree"))

        # Offers distribution
        offers = []
        if rng.random() < 0.25:
            ctc = round(rng.uniform(4.0, 15.0), 2)
            offers.append(OfferRecord(company="TechCorp", ctc_lpa=ctc, fixed_pay_lpa=ctc * 0.9, offer_date=datetime.date(2026, 9, 15), source=OfferSource.ON_CAMPUS, status=OfferStatus.ACCEPTED))

        students.append(
            Student(
                id=f"stu_vol_{i:06d}",
                roll_no=f"VOL{i:06d}",
                name=f"Student {i}",
                email=f"stu{i}@university.edu",
                branch=branch,
                cgpa=cgpa,
                tenth_percentage=tenth,
                twelfth_percentage=twelfth,
                date_of_birth=base_dob + datetime.timedelta(days=(i % 500)),
                backlogs=backlogs,
                gap_years=gap_years,
                existing_offers=offers,
            )
        )
    return students


def benchmark_volume_level(student_count: int) -> dict:
    print(f"\n=======================================================")
    print(f"[*] BENCHMARKING SCALE: {student_count:,} STUDENTS")
    print(f"=======================================================")

    # 1. Dataset Generation
    t0 = time.perf_counter()
    cohort = generate_synthetic_cohort(student_count)
    gen_time = time.perf_counter() - t0
    print(f"  [+] Generated {student_count:,} student profiles in {gen_time:.3f}s ({student_count / gen_time:,.0f} records/sec)")

    # 2. Rule Set Setup
    rule_set = RuleSet(
        id=f"rs_vol_{student_count}",
        name=f"Enterprise RuleSet {student_count}",
        rules=[
            CGPAMinRule(id="r_cgpa", min_cgpa=7.5),
            PercentageMinRule(id="r_10", qualification="10th", min_percentage=70.0),
            PercentageMinRule(id="r_12", qualification="12th", min_percentage=70.0),
            BranchInRule(id="r_br", allowed_branches=[
                "Computer Science and Engineering",
                "Information Technology",
                "Electronics and Communication Engineering",
                "Artificial Intelligence and Data Science",
            ]),
            ActiveBacklogsMaxRule(id="r_ab", max_backlogs=0),
            HistoricalBacklogsMaxRule(id="r_hb", max_history=1),
            GapYearsMaxRule(id="r_gap", max_gap_years=1),
        ],
    )

    # 3. Batch Eligibility Evaluation
    evaluator = EligibilityEvaluator()
    batch_evaluator = BatchEligibilityEvaluator(evaluator)
    t0 = time.perf_counter()
    decisions = batch_evaluator.evaluate_drive_batch(cohort, rule_set, f"drv_{student_count}")
    eval_time = time.perf_counter() - t0
    eval_throughput = student_count / eval_time

    eligible_count = sum(1 for d in decisions if d.status == EligibilityStatus.ELIGIBLE)
    ineligible_count = sum(1 for d in decisions if d.status == EligibilityStatus.INELIGIBLE)
    flagged_count = sum(1 for d in decisions if d.status == EligibilityStatus.FLAGGED)

    print(f"  [+] Evaluated {student_count:,} students across 7 AST rules in {eval_time:.3f}s")
    print(f"      -> Evaluation Throughput: {eval_throughput:,.0f} evaluations/sec")
    print(f"      -> Eligible: {eligible_count:,} | Ineligible: {ineligible_count:,} | Flagged: {flagged_count:,}")

    # 4. What-If Impact Simulation
    what_if = WhatIfEngine()
    req_set = RequirementSet(
        id=f"req_{student_count}",
        drive_id=f"drv_{student_count}",
        min_cgpa=7.5,
        min_tenth_percentage=70.0,
        min_twelfth_percentage=70.0,
        allowed_branches=[
            "Computer Science and Engineering",
            "Information Technology",
            "Electronics and Communication Engineering",
            "Artificial Intelligence and Data Science",
        ],
        max_active_backlogs=0,
        max_gap_years=1,
    )
    drive_obj = Drive(
        id=f"drv_{student_count}",
        company_id="comp_vol",
        company_name="Titan Systems",
        drive_date=datetime.date(2026, 11, 20),
        mode="on_campus",
        status="published",
        ctc_lpa=14.0,
        requirements=req_set,
        version=1,
    )
    rooms = [
        SchedulerRoom(id="hall_1", name="Auditorium", building="Main", room_type=RoomType.HALL, capacity=200),
        SchedulerRoom(id="cabin_1", name="Cabin 1", building="Block B", room_type=RoomType.CABIN, capacity=5),
    ]
    initial_shortlist = [d.student_id for d in decisions if d.status == EligibilityStatus.ELIGIBLE]

    change_req = ChangeRequest(
        change_type=ChangeType.CGPA_CUTOFF,
        drive_id=drive_obj.id,
        target_field="cgpa",
        old_value=7.5,
        new_value=6.8,
        author_id="qa_officer",
        reason="Load testing what-if impact simulation",
    )
    t0 = time.perf_counter()
    impact_report = what_if.apply_change(
        current_drive=drive_obj,
        all_drives=[drive_obj],
        students=cohort,
        rooms=rooms,
        policy=STRICT_ONE_OFFER_POLICY,
        current_shortlist=initial_shortlist,
        current_schedule_items=[],
        change=change_req,
    )
    what_if_time = time.perf_counter() - t0
    print(f"  [+] What-If Impact Simulation completed in {what_if_time:.3f}s")
    print(f"      -> Headline: '{impact_report.headline}' (+{impact_report.students_added_count:,} candidates)")

    # 5. Export Benchmark (First 2,000 eligible or full cohort if smaller)
    from backend.app.api.export.exporter import export_to_company_xlsx
    from backend.app.api.export.mapping import CompanyExportMapping
    mapping = CompanyExportMapping(
        company_id="comp_vol",
        company_name="Titan Systems",
        sheet_name="Recruiter_Shortlist",
        column_order=["Candidate ID", "Full Legal Name", "Engineering Discipline", "Cumulative GPA"],
        canonical_mapping={
            "Candidate ID": "roll_no",
            "Full Legal Name": "name",
            "Engineering Discipline": "branch",
            "Cumulative GPA": "cgpa",
        }
    )
    export_sample = [s for s in cohort if s.id in initial_shortlist][:2000]
    t0 = time.perf_counter()
    xlsx_bytes = export_to_company_xlsx(students=export_sample, schedule_items=[], mapping=mapping)
    export_time = time.perf_counter() - t0
    print(f"  [+] Shortlist XLSX Export ({len(export_sample):,} rows) generated in {export_time:.3f}s ({len(xlsx_bytes) / 1024:.1f} KB)")

    res = {
        "student_count": student_count,
        "generation_time_s": round(gen_time, 3),
        "evaluation_time_s": round(eval_time, 3),
        "eval_throughput_per_s": round(eval_throughput, 1),
        "eligible_count": eligible_count,
        "ineligible_count": ineligible_count,
        "flagged_count": flagged_count,
        "what_if_simulation_time_s": round(what_if_time, 3),
        "what_if_added_count": impact_report.students_added_count,
        "export_sample_size": len(export_sample),
        "export_time_s": round(export_time, 3),
        "export_size_kb": round(len(xlsx_bytes) / 1024, 1),
    }

    # Garbage collection
    del cohort, decisions, impact_report, xlsx_bytes
    gc.collect()

    return res


def main():
    levels = [1800, 5000, 10000, 25000]
    for count in levels:
        try:
            bench = benchmark_volume_level(count)
            RESULTS["benchmarks"].append(bench)
        except Exception as e:
            print(f"[FAIL] Error at scale {count}: {e}")
            RESULTS["benchmarks"].append({"student_count": count, "error": str(e), "status": "FAILED"})

    out_file = os.path.join(PROJECT_ROOT, "qa_mission2_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, indent=2)

    print("\n" + "=" * 60)
    print("MISSION 2 COMPLETE: Results saved to qa_mission2_results.json")
    print("=" * 60)


if __name__ == "__main__":
    main()
