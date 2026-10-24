# Placement Eligibility Rule Semantics Specification

This document provides the definitive, non-ambiguous semantics for all criteria evaluated by the Placement Eligibility Engine. Every rule is evaluated with deterministic mathematical semantics, ensuring absolute transparency and defensibility for college placement officers and students.

---

## 1. Backlogs: Active vs. Historical Semantics

### Definitions
- **Active Backlog**: An un-cleared examination failure where the student has not yet secured a passing grade as of the reference evaluation date.
- **Historical Backlog**: Any backlog that has ever been recorded on the student's academic transcript, regardless of whether it has been subsequently cleared.

### Temporal Comparison Rule
Every active backlog check requires an explicit reference date, denoted $D_{\text{ref}}$ (by default, the company's recruitment drive date or official registration deadline):
1. If a backlog is marked with status `active`, it contributes $+1$ to `active_backlogs`.
2. If a backlog is marked `cleared` with clearance date $D_{\text{cleared}}$:
   - If $D_{\text{cleared}} \le D_{\text{ref}}$: The backlog is considered **cleared** as of the drive date. It contributes $0$ to `active_backlogs` and $+1$ to `historical_backlogs`.
   - If $D_{\text{cleared}} > D_{\text{ref}}$: The backlog was **still pending on the drive date**. It contributes $+1$ to `active_backlogs` and $+1$ to `historical_backlogs`.

### Reference Edge Cases

| Scenario | Clearance Date | Drive Date ($D_{\text{ref}}$) | Active Count | History Count | "No Active Backlogs" Rule | "No History of Backlogs" Rule |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| Cleared last month | 2026-09-22 | 2026-10-22 | 0 | 1 | **ELIGIBLE** | **INELIGIBLE** |
| Cleared yesterday | 2026-10-21 | 2026-10-22 | 0 | 1 | **ELIGIBLE** | **INELIGIBLE** |
| Result declared after drive | 2026-10-25 | 2026-10-22 | 1 | 1 | **INELIGIBLE** | **INELIGIBLE** |
| Never had any arrears | N/A | 2026-10-22 | 0 | 0 | **ELIGIBLE** | **ELIGIBLE** |

---

## 2. CGPA, Percentage, and Rounding Semantics

### The Non-Rounding Principle
- **Strict Cut-Offs**: Cut-offs are treated as non-negotiable step thresholds.
- **Silent Rounding Prohibited**: A student with a CGPA of `6.995` does **not** meet a cut-off of `7.000` unless the company ruleset explicitly enables mathematical rounding.
- When rounding is disabled (default):
  $$\text{Pass} \iff \text{CGPA} \ge \text{Threshold}$$
  - $6.995 \ge 7.000 \implies \mathbf{False}$ (Explanation: *"Not eligible: your CGPA is 6.995 and this company needs 7.00 or above."*)
- When rounding is explicitly enabled by the officer in the rule definition:
  $$\text{Pass} \iff \text{round}(\text{CGPA}, 1) \ge \text{Threshold}$$
  - $\text{round}(6.995, 1) = 7.0 \implies \mathbf{True}$.

### Scale Normalisation (4.0 vs 10.0 Scale)
When university transcripts are issued on a 4.0 GPA scale:
$$\text{CGPA}_{10} = \left(\frac{\text{GPA}_4}{4.0}\right) \times 10.0$$
- Example: $3.8 / 4.0 \implies 9.50 / 10.0$.
- Any scale conversion generates an explicit audit transformation entry in the officer evaluation log.

### Percentage Conversion Formula
When a company requests a percentage equivalence for a CGPA cut-off, the college-approved formula is used and rendered explicitly in the student explanation:
- Standard Formula: $\text{Percentage} = \text{CGPA} \times 10.0$ (or university-specific multiplier such as $\text{CGPA} \times 9.5$).

---

## 3. Education Gap Calculation Semantics

### Scope of Gaps
1. **Pre-University Gap**: Gap between passing 10th and entering 12th/Diploma (standard duration: 2 years).
2. **Pre-Degree Gap**: Gap between passing 12th/Diploma and matriculating into the undergraduate degree (standard duration: 0 years).
3. **During-Degree Gap**: Gap years taken during the undergraduate engineering degree (e.g. semester drop or medical leave).

### Boundary Conditions
- If a company specifies `max_gap_years = 1`:
  - Exactly 1 year gap (e.g. JEE preparation between 12th and college) $\implies \mathbf{ELIGIBLE}$.
  - 2 years gap $\implies \mathbf{INELIGIBLE}$.
- Gap calculations are derived directly from the chronological `EducationTimelineEntry` sequence:
  $$\text{Gap} = \text{Start Year of Degree} - \text{End Year of Qualifying Schooling}$$

---

## 4. Missing Data & Ambiguity Handling

### The Zero Silent Assumptions Policy
The engine **never** makes silent assumptions about missing academic metrics:
1. **Missing 12th Percentage**:
   - If a student entered via lateral entry after a 3-year Polytechnic Diploma, they will not possess a 12th grade mark.
   - If the rule requires `12th Percentage >= 60%`, the evaluator checks whether lateral entry equivalency is enabled:
     - If enabled: The student's `diploma_percentage` is evaluated in lieu of 12th, and an officer notice is attached.
     - If disabled or unspecified: The decision returns `NEEDS_REVIEW` (Flagged) stating:
       *"Needs review: 12th marks missing; student possesses a Diploma (82.5%) which requires equivalency approval."*
2. **Missing Transcripts or Pending Re-evaluations**:
   - Yields `NEEDS_REVIEW` with the exact field specified, never a silent pass or fail.

---

## 5. Branch Equivalence & Degree Programs

### Canonical Resolution
Branches are matched against an institutional dictionary of aliases:
- `"CSE"` $\equiv$ `"Computer Science and Engineering"` $\equiv$ `"B.Tech - CSE"`
- `"IT"` $\equiv$ `"Information Technology"`
- `"ECE"` $\equiv$ `"Electronics and Communication Engineering"`

If a drive specifies `"Computer Science and Engineering"`, any student enrolled in `"CSE"` or `"Computer Science"` is recognized as equivalent, with the alias mapping registered in the evaluation trace.
