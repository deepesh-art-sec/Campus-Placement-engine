# Institutional Placement Engine Edge Case Semantics & Specification (Core Engine)

This document formalizes the exact algorithmic decision boundaries, rounding rules, temporal interpretations, and dispute resolutions across all edge cases evaluated by the engine.

---

## 1. Academic & Backlog Rule Semantics

### 1.1 Backlog Clearing Temporal Horizon
- **Rule**: When a drive requires "No active backlogs", the student's backlog status is evaluated **as-of the drive date**, NOT the current wall-clock date.
- **Cleared Month Prior**: If a backlog was cleared on `2026-10-15` and the drive date is `2026-11-20`, the backlog is status `cleared` $\rightarrow$ **ELIGIBLE**.
- **Cleared Day Before**: If cleared on `2026-11-19` for a drive on `2026-11-20` $\rightarrow$ **ELIGIBLE**.
- **Cleared On Drive Day**: If marked cleared on `2026-11-20` $\rightarrow$ **ELIGIBLE** (inclusive bounds).
- **Cleared Day After Drive**: If cleared on `2026-11-21` $\rightarrow$ **INELIGIBLE** (was active on drive day).
- **History of Backlogs**: If the company explicitly specifies "No history of backlogs" (`historical_backlogs_max = 0`), any cleared backlog in previous semesters renders the student **INELIGIBLE**, citing the historical clause.

### 1.2 Cut-Off Boundaries & Precision Arithmetic
- **Exact Cut-Off**: A student with CGPA `7.000` against a minimum cut-off of `7.000` is **ELIGIBLE** ($\ge$).
- **Precision & Rounding**: CGPA cut-offs are compared at standard floating-point precision ($10^{-6}$ epsilon). A CGPA of `6.995` is **INELIGIBLE** when cut-off is `7.0`. Truncation vs half-up rounding is configurable via the rule parameter `allow_rounding=false` (default: strict non-rounding).
- **10th & 12th Percentages**: A percentage cut-off of `60.0%` with candidate having `59.99%` is **INELIGIBLE**.

### 1.3 Lateral Entry & Missing Records
- **Lateral Entry**: Students entering directly into Year 2 (Semester 3) via Polytechnic Diploma do not possess a 12th mark sheet. If a company rule specifies `min_twelfth_percentage = 60.0%`, the engine checks if `diploma_percentage` is present. If present and $\ge 60.0\%$, the candidate passes with the reason noting diploma equivalence.
- **Missing Record**: If neither 12th nor diploma is on file and the rule is hard, status is **INELIGIBLE** / **NEEDS_REVIEW**.

### 1.4 Gap Years Calculation
- **Calendar Days**: A 1-year gap limit allows up to 365 days (or 366 in leap years) between educational stages.
- **Limit Horizon**: A candidate with exactly 365 days gap is **ELIGIBLE**. A candidate with 366 days is **INELIGIBLE** unless an officer exemption is documented.

### 1.5 Branch Aliases & Degree Equivalence
- **Alias Equivalence**: Canonical mapping normalizes variations:
  - `["CSE", "Computer Science", "B.Tech - Computer Science & Engineering", "CS"]` $\rightarrow$ Canonical `CSE`.
  - `["IT", "Information Technology"]` $\rightarrow$ Canonical `IT`.
  - `Allied CS` $\rightarrow$ `{CSE, IT, AI&DS, CCE, Software Engineering}`.

---

## 2. Institutional Offer Policy Semantics

### 2.1 Dream Company Band Interpretation
- **Threshold Inclusivity**:
  - `band_inclusive = true`: An offer of exactly `10.0 LPA` meets a dream threshold of `10.0 LPA` $\rightarrow$ classified as **DREAM**.
  - `band_inclusive = false`: An offer of `10.0 LPA` is regular; only $> 10.0\text{ LPA}$ qualifies as dream.
- **Basis**: Configurable between Total CTC (`ctc`) or Fixed Base Pay (`fixed_pay`). Default: `ctc`.

### 2.2 Offer Progression & Rejection
- **Strict One-Offer**: Once a student holds an active countable offer, they are blocked from subsequent regular drives.
- **Dream Upgrade**: A student holding a regular offer ($< 10\text{ LPA}$) is allowed to sit for a dream company drive ($\ge 10\text{ LPA}$).
- **Lateral Dream Moves**: A student holding a dream offer of $15\text{ LPA}$ cannot sit for a $12\text{ LPA}$ drive (upward progression only).
- **Revoked Offers**: A company revoking an offer frees the student, provided `count_revoked_offers = false`.
- **Declined Offers**: Configurable toggle `count_declined_offers`: if true, turning down an on-campus offer counts against placement quota; if false, student remains unblocked.
- **Off-Campus Offers**: Evaluated against toggle `count_off_campus_offers` (default: false, unverified external offers do not block students).

---

## 3. Conflict-Free Scheduling & Solver Bounds

### 3.1 Interval Invariants
- **No Overlapping Student Slots**: A student cannot be scheduled in two interview panels or tests simultaneously:
  $$\forall s, \quad [start_{i}, end_{i}) \cap [start_{j}, end_{j}) = \emptyset$$
- **Transition Buffers**: A mandatory 15-minute buffer is inserted when a student moves between physical buildings.
- **Lunch & Blackouts**: All solver intervals respect college lunch hours (12:30 - 13:30) and pre-configured room blackout windows.
