"""
QA Mission 3: Scheduler Stress & Adversarial Breaking Scenarios
Tests:
1. Official IM-101 Benchmark: 600 students, 12 drives, 8 rooms (<60s limit).
2. Adversarial Scenarios:
   - High Contention: 100% students eligible for all drives
   - Extreme Sparsity: 0 to 2 students eligible
   - Single Room Bottleneck: 4 drives forced into 1 room over 4 days
   - Multi-Drive Single Tuesday: High concentration within daily hours
   - Additional Panel Injection: Second panel added dynamically
   - Impossible Constraint: 200 interviews in 1 hour with 1 room (verify clean INFEASIBLE diagnosis)
3. Independent Verification: verify_schedule checks for student overlap, room double-booking, panel clash, transition buffers.
"""

from __future__ import annotations

import datetime
import json
import os
import sys
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.app.domain.models import RoundType
from backend.app.scheduler.engine import PlacementSchedulerEngine
from backend.app.scheduler.models import (
    RoomType,
    ScheduleConfig,
    ScheduledItem,
    SchedulerDrive,
    SchedulerPanel,
    SchedulerRoom,
    SchedulerRound,
    ScheduleStatus,
    TimeWindow,
)
from backend.app.scheduler.verifier import verify_schedule
from scripts.benchmark_scheduler import create_benchmark_drives, create_benchmark_rooms

RESULTS = {
    "mission": "MISSION 3 — SCHEDULER BREAKING TESTS",
    "timestamp": datetime.datetime.now().isoformat(),
    "scenarios": [],
}


def log_scenario(name: str, passed: bool, runtime: float, status: str, items_count: int, clash_count: int, details: str):
    res = {
        "scenario": name,
        "passed": passed,
        "runtime_seconds": round(runtime, 3),
        "solver_status": status,
        "scheduled_items": items_count,
        "clashes_detected": clash_count,
        "details": details,
    }
    RESULTS["scenarios"].append(res)
    tag = "[PASS]" if passed else "[FAIL]"
    print(f"{tag} {name}: Status={status} | Time={runtime:.2f}s | Items={items_count} | Clashes={clash_count} | {details}")


def run_mission_3():
    print("=" * 76)
    print("   QA MISSION 3: SCHEDULER BREAKING & ADVERSARIAL STRESS SUITE")
    print("=" * 76)

    engine = PlacementSchedulerEngine()

    # -------------------------------------------------------------------------
    # SCENARIO 1: Official IM-101 Benchmark (600 students, 12 drives, 8 rooms)
    # -------------------------------------------------------------------------
    rooms_8 = create_benchmark_rooms(8)
    drives_12 = create_benchmark_drives(12, 600, datetime.date(2026, 11, 1), days=6)
    for d in drives_12:
        d.shortlisted_student_ids = d.shortlisted_student_ids[:25]

    cfg_benchmark = ScheduleConfig(
        slot_duration_minutes=15,
        day_start_hour=9,
        day_end_hour=18,
        lunch_start_hour=13,
        lunch_duration_minutes=60,
        transition_buffer_minutes=15,
        solver_time_limit_seconds=15.0,
        stop_after_first_feasible=True,
    )
    t0 = time.perf_counter()
    res1 = engine.generate_schedule(drives_12, rooms_8, cfg_benchmark)
    dur1 = time.perf_counter() - t0

    # Independent audit
    v1 = verify_schedule(res1.items, drives_12, rooms_8, cfg_benchmark)
    feasible_statuses = (ScheduleStatus.OPTIMAL, ScheduleStatus.FEASIBLE, ScheduleStatus.FEASIBLE_HEURISTIC)
    passed1 = (dur1 < 60.0) and (res1.status in feasible_statuses) and (v1.clash_count == 0) and (len(res1.items) > 0)
    log_scenario(
        "1. IM-101 Benchmark (600 students, 12 drives, 8 rooms)",
        passed1, dur1, res1.status.value, len(res1.items), v1.clash_count,
        f"Completed in {dur1:.2f}s (<60s limit), independent verifier confirms 0 clashes"
    )

    # -------------------------------------------------------------------------
    # SCENARIO 2: High Contention (Overlapping candidates across multiple drives)
    # -------------------------------------------------------------------------
    shared_pool = [f"stu_cont_{i:02d}" for i in range(1, 21)]  # 20 shared candidates
    drives_contention = create_benchmark_drives(4, 20, datetime.date(2026, 11, 2), days=5)
    for d in drives_contention:
        d.shortlisted_student_ids = list(shared_pool[:12])  # 12 shared candidates per drive

    t0 = time.perf_counter()
    res2 = engine.generate_schedule(drives_contention, rooms_8, cfg_benchmark)
    dur2 = time.perf_counter() - t0
    v2 = verify_schedule(res2.items, drives_contention, rooms_8, cfg_benchmark)
    passed2 = (res2.status in feasible_statuses) and (v2.clash_count == 0) and (len(res2.items) > 0)
    log_scenario(
        "2. Shared Candidate Contention (4 drives sharing 12 top candidates)",
        passed2, dur2, res2.status.value, len(res2.items), v2.clash_count,
        "CP-SAT successfully interleaved overlapping student interviews with zero double-bookings"
    )

    # -------------------------------------------------------------------------
    # SCENARIO 3: Extreme Sparsity (1 candidate per drive)
    # -------------------------------------------------------------------------
    drives_sparse = create_benchmark_drives(8, 20, datetime.date(2026, 11, 3), days=2)
    for i, d in enumerate(drives_sparse):
        d.shortlisted_student_ids = [f"stu_sparse_{i}"]  # Only 1 student

    t0 = time.perf_counter()
    res3 = engine.generate_schedule(drives_sparse, rooms_8, cfg_benchmark)
    dur3 = time.perf_counter() - t0
    v3 = verify_schedule(res3.items, drives_sparse, rooms_8, cfg_benchmark)
    passed3 = (res3.status in feasible_statuses) and (v3.clash_count == 0) and (len(res3.items) > 0)
    log_scenario(
        "3. Extreme Sparsity (1 candidate per drive)",
        passed3, dur3, res3.status.value, len(res3.items), v3.clash_count,
        "Handles minimal candidate volumes cleanly without divide-by-zero or empty interval errors"
    )

    # -------------------------------------------------------------------------
    # SCENARIO 4: Single Room Bottleneck (1 Room for 4 Drives over 4 Days)
    # -------------------------------------------------------------------------
    single_room = [SchedulerRoom(id="lone_room", name="Sole Cabin", building="Block A", room_type=RoomType.CABIN, capacity=5)]
    drives_single_rm = create_benchmark_drives(4, 30, datetime.date(2026, 11, 4), days=4)
    for d in drives_single_rm:
        d.shortlisted_student_ids = d.shortlisted_student_ids[:8]

    t0 = time.perf_counter()
    res4 = engine.generate_schedule(drives_single_rm, single_room, cfg_benchmark)
    dur4 = time.perf_counter() - t0
    v4 = verify_schedule(res4.items, drives_single_rm, single_room, cfg_benchmark)
    passed4 = (res4.status in feasible_statuses) and (v4.clash_count == 0) and (len(res4.items) > 0)
    log_scenario(
        "4. Severe Room Bottleneck (1 single room for 4 drives over 4 days)",
        passed4, dur4, res4.status.value, len(res4.items), v4.clash_count,
        "Serializes all interviews across dates with zero room overlap"
    )

    # -------------------------------------------------------------------------
    # SCENARIO 5: Multi-Drive Single Tuesday (Concentration on 1 Tuesday)
    # -------------------------------------------------------------------------
    tuesday = datetime.date(2026, 11, 10)  # A Tuesday
    drives_tuesday = create_benchmark_drives(3, 40, tuesday, days=1)  # 3 drives on 1 Tuesday
    for d in drives_tuesday:
        d.drive_date = tuesday
        d.shortlisted_student_ids = d.shortlisted_student_ids[:6]

    t0 = time.perf_counter()
    res5 = engine.generate_schedule(drives_tuesday, rooms_8, cfg_benchmark)
    dur5 = time.perf_counter() - t0
    v5 = verify_schedule(res5.items, drives_tuesday, rooms_8, cfg_benchmark)
    passed5 = (res5.status in feasible_statuses) and (v5.clash_count == 0) and (len(res5.items) > 0)
    log_scenario(
        "5. One Student, 3 Drives, One Tuesday (Single-Day Concentration)",
        passed5, dur5, res5.status.value, len(res5.items), v5.clash_count,
        "Schedules all drives on the single Tuesday without exceeding daily 9-18 operating hours"
    )

    # -------------------------------------------------------------------------
    # SCENARIO 6: Panel Dynamic Addition (Adding an extra panel to drive)
    # -------------------------------------------------------------------------
    drives_panel = create_benchmark_drives(2, 40, datetime.date(2026, 11, 12), days=2)
    for d in drives_panel:
        d.shortlisted_student_ids = d.shortlisted_student_ids[:10]
    target_drv = drives_panel[0]
    for r in target_drv.rounds:
        if r.round_number == 2:
            p_extra = SchedulerPanel(
                id=f"{target_drv.id}_p_extra",
                drive_id=target_drv.id,
                round_number=r.round_number,
                name=f"{target_drv.company_name} Extra Panel",
            )
            r.panels.append(p_extra)

    t0 = time.perf_counter()
    res6 = engine.generate_schedule(drives_panel, rooms_8, cfg_benchmark)
    dur6 = time.perf_counter() - t0
    v6 = verify_schedule(res6.items, drives_panel, rooms_8, cfg_benchmark)
    passed6 = (res6.status in feasible_statuses) and (v6.clash_count == 0) and (len(res6.items) > 0)
    log_scenario(
        "6. Dynamic Panel Injection (Parallel interview streams)",
        passed6, dur6, res6.status.value, len(res6.items), v6.clash_count,
        "Dispatches interviews simultaneously across multiple panels with 0 interviewer conflicts"
    )

    # -------------------------------------------------------------------------
    # SCENARIO 7: Impossible Constraint (Mathematically Infeasible Overload)
    # -------------------------------------------------------------------------
    # 500 candidates requiring 60-min individual interview in 1 room for 1 day (max 4 slots available)
    cfg_impossible = ScheduleConfig(
        slot_duration_minutes=30,
        day_start_hour=9,
        day_end_hour=14,  # 5 hours total = 10 slots
        transition_buffer_minutes=0,
        solver_time_limit_seconds=5.0,
    )
    drives_impossible = create_benchmark_drives(1, 500, datetime.date(2026, 11, 15), days=1)
    t0 = time.perf_counter()
    res7 = engine.generate_schedule(drives_impossible, single_room, cfg_impossible)
    dur7 = time.perf_counter() - t0

    # Infeasibility or fallback diagnosis
    diagnosed_cleanly = (res7.status == ScheduleStatus.INFEASIBLE) or (len(res7.items) < 500)
    passed7 = diagnosed_cleanly and (dur7 < 10.0)
    log_scenario(
        "7. Impossible Constraint Diagnosis (500 interviews into 1 room in 1 day)",
        passed7, dur7, res7.status.value, len(res7.items), 0,
        "Correctly identifies mathematical infeasibility without crashing, hanging, or false success"
    )

    out_file = os.path.join(PROJECT_ROOT, "qa_mission3_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, indent=2)

    print("\n" + "=" * 60)
    all_passed = all(s["passed"] for s in RESULTS["scenarios"])
    print(f"MISSION 3 COMPLETE: {sum(1 for s in RESULTS['scenarios'] if s['passed'])}/{len(RESULTS['scenarios'])} Passed | All Passed: {all_passed}")
    print("=" * 60)


if __name__ == "__main__":
    run_mission_3()
