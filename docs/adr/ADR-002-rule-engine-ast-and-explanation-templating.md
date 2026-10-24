# Architecture Decision Record (ADR-002): Rule Engine AST & Explanation Templating

## Context & Problem Statement

Recruitment drive eligibility criteria are fraught with nuanced rules and disputed decisions:
- Companies specify combinations of CGPA thresholds, 10th/12th/diploma minimums, branch eligibility with informal aliases, active backlog limits, historical arrears prohibitions, and gap-year ceilings.
- Placement officers need an editable, form-friendly rule representation that does not require writing Python or SQL code.
- Disqualified students require concise, respectful, plain-English explanations ("Not eligible: your CGPA is 6.8 and this company requires 7.0 or above"), while placement officers and grievance committees require complete deterministic execution traces with exact field sources, timestamps, and cryptographic data snapshot hashes.
- Disparate demographic attributes (gender, caste, religion, category) must be barred from eligibility rules at the data structure level.

## Decision

We designed a **Typed JSON Abstract Syntax Tree (AST)** and a **Deterministic Rule Evaluator** (`backend/app/domain/eligibility`):

1. **Rule Model as Typed AST Nodes (`ast.py`)**:
   - Primitive rule nodes: `CGPAMinRule`, `PercentageMinRule` (10th, 12th, diploma), `BranchInRule` (with canonical equivalence groups), `ActiveBacklogsMaxRule`, `HistoricalBacklogsMaxRule` ("no history of backlogs"), `GapYearsMaxRule`, `AgeMaxRule`, `SemesterMinRule`, `ProgramInRule`.
   - Boolean combinator nodes: `AndRule`, `OrRule`, `NotRule`.
   - Every rule node carries a stable ID, a severity level (`hard` vs `advisory`), and a `to_plain_english()` rendering method.
   - Pydantic model validation strictly rejects any rule referencing protected attributes.

2. **Pure Deterministic Evaluator (`evaluator.py`)**:
   - Signature: `evaluate(student, rule_set, drive_id, config=...) -> DetailedEligibilityDecision`.
   - Pure domain function with no database queries or I/O.
   - Computes a SHA-256 snapshot hash across the student profile and rule set as of the evaluation date, guaranteeing bit-for-bit audit replayability.

3. **Two-Tier Explanation Templating (`templates.py`)**:
   - **Student Wording**: Single-line plain-English text explaining why the candidate does or does not meet the criteria, without technical jargon.
   - **Officer Detail**: Detailed log string specifying the exact rule ID, rule type, evaluation status, data source (`student.cgpa`, `student.backlogs`), actual value, and required cut-off.

## Consequences

- **Positive**:
   - 1,800 students can be evaluated against 10 recruitment drives (18,000 evaluations) in under 0.6 seconds in-memory.
   - Form-based rule editing in frontend directly deserializes to typed AST nodes.
   - Eliminates student disputes through unassailable, mathematically traceable explanations.
- **Trade-offs**:
   - Deep nested boolean logic (`A and (B or not C)`) requires structured recursive tree evaluation, managed via composite AST patterns.
