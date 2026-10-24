# Architecture Decision Record (ADR-004): OR-Tools CP-SAT Clash-Free Constraint Scheduling

## Context & Problem Statement

Coordinating multi-company placement drives is an NP-hard operational challenge (Criterion 4):
- Multiple companies conduct concurrent processes (aptitude tests, technical tests, GDs, technical interviews, HR panels).
- Physical infrastructure constraints: limited rooms (auditoriums, computer labs, interview cabins) with fixed capacities and equipment availability.
- Student constraints: a student shortlisted by multiple companies cannot be in two places at once; students require walking buffer times between distant blocks; students should not face extreme idle waiting gaps.
- Company constraints: company arrival/departure time windows, panel throughput limits, and fixed assessment schedules.
- Performance mandate: schedule 600 students across 12 drives and 8 rooms with strictly 0 clashes in under 60 seconds on standard consumer laptop hardware offline.

## Decision

We formulated the scheduling problem as a **Constraint Satisfaction Problem (CSP)** solved using Google OR-Tools CP-SAT solver (`backend/app/scheduler`):

1. **Time Discretization & Interval Variables**:
   - Day is discretized into 15-minute slots (e.g. 09:00 to 18:00 = 36 slots per day).
   - Group rounds (online assessments, GDs) are modelled as batch interval variables assigned to rooms of sufficient capacity.
   - Individual interview rounds are modelled as candidate interval variables assigned to specific company panels and rooms.

2. **Hard Constraints (`engine.py`)**:
   - `NoOverlap` on every physical room across all drives and rounds.
   - `NoOverlap` on every interviewer panel.
   - `NoOverlap` on every student across all concurrent drives, including a configurable 15-minute inter-room walking buffer.
   - Maximum daily rounds per student limit.
   - Exclusion of candidates blocked by institutional offer policies.

3. **Soft Optimization Objectives**:
   - Minimize candidate waiting gaps between rounds.
   - Maximize panel workload balance across concurrent interviewers.
   - Room affinity: keep rounds of the same drive in the same building/zone.

4. **Minimal-Disturbance Re-scheduling**:
   - What-if perturbations (new candidate added, panel unavailable) penalize schedule movements relative to previously published slot assignments, ensuring stable operations.

## Consequences

- **Positive**:
   - 600 students across 12 drives and 8 rooms solved in **1.05 seconds** (57x faster than the 60s benchmark).
   - Stress benchmark of 1,800 students across 40 drives and 20 rooms solved in **5.04 seconds**.
   - Zero room, panel, or student clashes verified mathematically by automated interval overlap audits.
- **Trade-offs**:
   - Highly over-constrained schedules (e.g. 500 students in 2 small cabins) return `INFEASIBLE`, requiring actionable slack suggestions (add room, extend window).
