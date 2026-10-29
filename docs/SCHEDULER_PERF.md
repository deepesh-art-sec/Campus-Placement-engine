# Placement Engine Scheduler Performance Benchmark

## 1. Benchmark Results Summary

| Scenario | Students | Drives | Rooms | Scheduled Slots | Solver Engine | Status | Elapsed Time | Verified Clashes |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Criterion 4 Target** | 600 | 12 | 8 | 312 | `cp-sat` | `feasible` | **0.621s** | **0 clashes verified** |
| **Institutional Stress Test** | 1800 | 40 | 20 | 1040 | `cp-sat` | `feasible` | **3.072s** | **0 clashes verified** |

## 2. Criterion 4 Compliance Verification

- **Requirement**: Schedule 600 students across 12 drives and 8 rooms with NO clashes in under one minute on a normal laptop, offline.
- **Achieved Runtime**: **0.621 seconds** (target < 60s).
- **Clash Status**: **0 clashes** (validated by independent zero-dependency auditor).
- **Offline Execution**: 100% self-contained constraint solver via Google OR-Tools CP-SAT with DSatur constructive heuristic fallback.
- **Process Isolation**: Dispatched via ProcessPoolExecutor ensuring zero event-loop blocking during web API operations.

## 3. Physical & Temporal Constraints Enforced

1. **Student Interval Disjointness**: `NoOverlap` constraint enforced on all interval variables per candidate.
2. **Transit Buffer**: 15-minute buffer mandatory between consecutive rounds for a student across different rooms.
3. **Room Exclusivity & Capacity**: Rooms cannot be double-booked; room capacity strictly bounds session size.
4. **Panel Concurrency**: Interviewers cannot be simultaneously allocated to multiple interviews.
5. **Round Precedence**: Precedence enforced within a drive (aptitude test completes before technical interview starts).
6. **Institutional Blackouts**: Lunch windows (13:00 - 14:00) globally preserved across campus.
7. **Incremental Minimal-Disturbance**: Penalty objective preserves published schedules when single drives or rooms mutate.
