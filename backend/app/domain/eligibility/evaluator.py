"""
Deterministic Eligibility Rule Evaluator.
Pure domain logic: No database or network I/O.
Computes explainable eligibility decisions, full officer traces, and cryptographic reproducibility hashes.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.app.domain.eligibility.ast import (
    ActiveBacklogsMaxRule,
    AgeMaxRule,
    AndRule,
    BranchInRule,
    CGPAMinRule,
    CustomFieldRule,
    GapYearsMaxRule,
    HistoricalBacklogsMaxRule,
    NotRule,
    OrRule,
    PercentageMinRule,
    ProgramInRule,
    RuleNode,
    RuleSet,
    RuleSeverity,
    SemesterMinRule,
)
from backend.app.domain.eligibility.templates import TemplateEngine
from backend.app.domain.models import EligibilityStatus, Student
from backend.app.importers.canonical_maps import CANONICAL_BRANCHES, is_branch_allowed


class RuleEvaluationStatus(StrEnum):
    PASSED = "pass"
    FAILED = "fail"
    REVIEW = "review"


class RuleEvaluationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    rule_id: str
    rule_type: str
    severity: RuleSeverity
    status: RuleEvaluationStatus
    actual_value: Any
    required_value: Any
    data_source: str
    student_explanation: str
    officer_detail: str
    is_ambiguous: bool = False
    ambiguity_reason: str | None = None

    @property
    def reason(self) -> str:
        return self.student_explanation


class EvaluationConfig(BaseModel):
    as_of_date: date = Field(default_factory=date.today)
    cgpa_to_percentage_formula: str = "cgpa * 10.0"
    allow_cgpa_rounding: bool = False
    lateral_entry_diploma_substitutes_12th: bool = True
    language: str = "en"


class DetailedEligibilityDecision(BaseModel):
    student_id: str
    student_roll_no: str
    student_name: str
    drive_id: str
    ruleset_id: str
    ruleset_version: int
    status: EligibilityStatus
    overall_student_reason: str
    passed_rules: list[RuleEvaluationResult] = Field(default_factory=list)
    failed_rules: list[RuleEvaluationResult] = Field(default_factory=list)
    review_reasons: list[str] = Field(default_factory=list)
    data_snapshot_hash: str
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def one_line_explanation(self) -> str:
        return self.overall_student_reason


class EligibilityEvaluator:
    """Evaluates a Student against a RuleSet deterministically."""

    def __init__(self, template_engine: TemplateEngine | None = None) -> None:
        self.templates = template_engine or TemplateEngine()

    def evaluate(
        self,
        student: Student,
        rule_set: RuleSet,
        drive_id: str,
        config: EvaluationConfig | None = None,
        as_of_date: date | None = None,
    ) -> DetailedEligibilityDecision:
        cfg = config or EvaluationConfig()
        if as_of_date is not None:
            cfg = cfg.model_copy(update={"as_of_date": as_of_date})
        as_of = cfg.as_of_date

        passed_rules: list[RuleEvaluationResult] = []
        failed_rules: list[RuleEvaluationResult] = []
        review_reasons: list[str] = []

        for rule in rule_set.rules:
            result = self._evaluate_node(student, rule, as_of, cfg)
            if result.status == RuleEvaluationStatus.PASSED:
                passed_rules.append(result)
            elif result.status == RuleEvaluationStatus.FAILED:
                failed_rules.append(result)
            elif result.status == RuleEvaluationStatus.REVIEW:
                failed_rules.append(result)
                if result.ambiguity_reason:
                    review_reasons.append(result.ambiguity_reason)

        # Determine overall status
        status: EligibilityStatus
        overall_reason: str

        hard_failures = [r for r in failed_rules if r.severity == RuleSeverity.HARD and r.status == RuleEvaluationStatus.FAILED]
        review_items = [r for r in failed_rules if r.status == RuleEvaluationStatus.REVIEW]

        if review_items:
            status = EligibilityStatus.FLAGGED
            overall_reason = f"Needs review: {review_items[0].student_explanation}"
        elif hard_failures:
            status = EligibilityStatus.INELIGIBLE
            # Use the most specific first hard failure for the one-line student explanation
            overall_reason = hard_failures[0].student_explanation
        else:
            status = EligibilityStatus.ELIGIBLE
            overall_reason = "Eligible: you meet all academic and backlog requirements for this drive."

        # Compute reproducible cryptographic snapshot hash
        snapshot_hash = self.compute_snapshot_hash(student, rule_set, as_of)

        return DetailedEligibilityDecision.model_construct(
            student_id=student.id,
            student_roll_no=student.roll_no,
            student_name=student.name,
            drive_id=drive_id,
            ruleset_id=rule_set.id,
            ruleset_version=rule_set.version,
            status=status,
            overall_student_reason=overall_reason,
            passed_rules=passed_rules,
            failed_rules=failed_rules,
            review_reasons=review_reasons,
            data_snapshot_hash=snapshot_hash,
            evaluated_at=datetime.utcnow(),
        )

    def _evaluate_node(
        self, student: Student, node: RuleNode, as_of: date, cfg: EvaluationConfig
    ) -> RuleEvaluationResult:
        if isinstance(node, CGPAMinRule):
            return self._eval_cgpa(student, node, cfg)
        elif isinstance(node, PercentageMinRule):
            return self._eval_percentage(student, node, cfg)
        elif isinstance(node, BranchInRule):
            return self._eval_branch(student, node)
        elif isinstance(node, ActiveBacklogsMaxRule):
            return self._eval_active_backlogs(student, node, as_of)
        elif isinstance(node, HistoricalBacklogsMaxRule):
            return self._eval_historical_backlogs(student, node)
        elif isinstance(node, GapYearsMaxRule):
            return self._eval_gap_years(student, node)
        elif isinstance(node, AgeMaxRule):
            return self._eval_age(student, node, as_of)
        elif isinstance(node, SemesterMinRule):
            return self._eval_semester(student, node)
        elif isinstance(node, ProgramInRule):
            return self._eval_program(student, node)
        elif isinstance(node, CustomFieldRule):
            return self._eval_custom_field(student, node)
        elif isinstance(node, AndRule):
            return self._eval_and(student, node, as_of, cfg)
        elif isinstance(node, OrRule):
            return self._eval_or(student, node, as_of, cfg)
        elif isinstance(node, NotRule):
            return self._eval_not(student, node, as_of, cfg)

        raise NotImplementedError(f"Unsupported rule node type: {type(node)}")

    def _eval_cgpa(self, student: Student, node: CGPAMinRule, cfg: EvaluationConfig) -> RuleEvaluationResult:
        actual = student.cgpa
        required = node.min_cgpa

        # Precision policy: strict comparison unless rounding explicitly configured
        effective_cgpa = round(actual, 1) if node.allow_rounding or cfg.allow_cgpa_rounding else actual

        passed = effective_cgpa >= required
        status = RuleEvaluationStatus.PASSED if passed else RuleEvaluationStatus.FAILED

        explanation = self.templates.render_student(
            "cgpa_min",
            status.value,
            actual=actual,
            required=required,
        )
        officer = self.templates.render_officer(
            node.id, "cgpa_min", status.value, "student.cgpa", actual=actual, required=required
        )

        return RuleEvaluationResult.model_construct(
            rule_id=node.id,
            rule_type=node.type,
            severity=node.severity,
            status=status,
            actual_value=actual,
            required_value=required,
            data_source="student.cgpa",
            student_explanation=explanation,
            officer_detail=officer,
            is_ambiguous=False,
            ambiguity_reason=None,
        )

    def _eval_percentage(
        self, student: Student, node: PercentageMinRule, cfg: EvaluationConfig
    ) -> RuleEvaluationResult:
        actual: float | None = None
        data_source = ""
        qual = node.qualification.lower()

        if qual in ("10th", "tenth", "10"):
            actual = student.tenth_percentage
            data_source = "student.tenth_percentage"
        elif qual in ("12th", "twelfth", "12"):
            actual = student.twelfth_percentage
            data_source = "student.twelfth_percentage"
            # Lateral entry check: no 12th but has diploma
            if actual is None and student.diploma_percentage is not None:
                if cfg.lateral_entry_diploma_substitutes_12th:
                    actual = student.diploma_percentage
                    data_source = "student.diploma_percentage (lateral entry equivalent)"
                else:
                    return RuleEvaluationResult.model_construct(
                        rule_id=node.id,
                        rule_type=node.type,
                        severity=node.severity,
                        status=RuleEvaluationStatus.REVIEW,
                        actual_value=None,
                        required_value=node.min_percentage,
                        data_source="student.twelfth_percentage",
                        student_explanation=f"Needs review: 12th marks missing; diploma ({student.diploma_percentage}%) requires college equivalency approval.",
                        officer_detail=f"[{node.id}][REVIEW] Student lacks 12th percentage; diploma is {student.diploma_percentage}%.",
                        is_ambiguous=True,
                        ambiguity_reason="12th percentage missing on lateral entry student without automatic substitution.",
                    )
        elif qual == "diploma":
            actual = student.diploma_percentage
            data_source = "student.diploma_percentage"
        elif qual in ("12th_or_diploma", "higher_secondary"):
            actual = student.twelfth_percentage if student.twelfth_percentage is not None else student.diploma_percentage
            data_source = "student.twelfth_percentage or diploma_percentage"

        if actual is None:
            return RuleEvaluationResult.model_construct(
                rule_id=node.id,
                rule_type=node.type,
                severity=node.severity,
                status=RuleEvaluationStatus.REVIEW,
                actual_value=None,
                required_value=node.min_percentage,
                data_source=data_source,
                student_explanation=f"Needs review: {node.qualification} percentage is missing from your academic profile.",
                officer_detail=f"[{node.id}][REVIEW] Missing record for {node.qualification}.",
                is_ambiguous=True,
                ambiguity_reason=f"Missing {node.qualification} percentage.",
            )

        passed = actual >= node.min_percentage
        status = RuleEvaluationStatus.PASSED if passed else RuleEvaluationStatus.FAILED

        explanation = self.templates.render_student(
            "percentage_min",
            status.value,
            qualification=node.qualification,
            actual=actual,
            required=node.min_percentage,
        )
        officer = self.templates.render_officer(
            node.id, "percentage_min", status.value, data_source, qualification=node.qualification, actual=actual, required=node.min_percentage
        )

        return RuleEvaluationResult.model_construct(
            rule_id=node.id,
            rule_type=node.type,
            severity=node.severity,
            status=status,
            actual_value=actual,
            required_value=node.min_percentage,
            data_source=data_source,
            student_explanation=explanation,
            officer_detail=officer,
        )

    def _eval_branch(self, student: Student, node: BranchInRule) -> RuleEvaluationResult:
        actual_branch = student.branch.strip()
        passed = is_branch_allowed(actual_branch, node.allowed_branches)
        status = RuleEvaluationStatus.PASSED if passed else RuleEvaluationStatus.FAILED

        explanation = self.templates.render_student(
            "branch_in",
            status.value,
            actual=actual_branch,
            required_list=", ".join(node.allowed_branches),
        )
        officer = self.templates.render_officer(
            node.id, "branch_in", status.value, "student.branch", actual=actual_branch, required_list=", ".join(node.allowed_branches)
        )

        return RuleEvaluationResult.model_construct(
            rule_id=node.id,
            rule_type=node.type,
            severity=node.severity,
            status=status,
            actual_value=actual_branch,
            required_value=node.allowed_branches,
            data_source="student.branch",
            student_explanation=explanation,
            officer_detail=officer,
        )

    def _eval_active_backlogs(
        self, student: Student, node: ActiveBacklogsMaxRule, as_of: date
    ) -> RuleEvaluationResult:
        # A backlog cleared on or before as_of is cleared; cleared after as_of is still active!
        active_count = student.active_backlog_count(as_of=as_of)
        passed = active_count <= node.max_backlogs
        status = RuleEvaluationStatus.PASSED if passed else RuleEvaluationStatus.FAILED

        explanation = self.templates.render_student(
            "active_backlogs_max",
            status.value,
            actual=active_count,
            required=node.max_backlogs,
        )
        officer = self.templates.render_officer(
            node.id, "active_backlogs_max", status.value, f"student.backlogs (as_of={as_of.isoformat()})", actual=active_count, required=node.max_backlogs
        )

        return RuleEvaluationResult.model_construct(
            rule_id=node.id,
            rule_type=node.type,
            severity=node.severity,
            status=status,
            actual_value=active_count,
            required_value=node.max_backlogs,
            data_source="student.backlogs",
            student_explanation=explanation,
            officer_detail=officer,
        )

    def _eval_historical_backlogs(
        self, student: Student, node: HistoricalBacklogsMaxRule
    ) -> RuleEvaluationResult:
        history_count = student.history_backlog_count()
        passed = history_count <= node.max_history
        status = RuleEvaluationStatus.PASSED if passed else RuleEvaluationStatus.FAILED

        explanation = self.templates.render_student(
            "historical_backlogs_max",
            status.value,
            actual=history_count,
            required=node.max_history,
        )
        officer = self.templates.render_officer(
            node.id, "historical_backlogs_max", status.value, "student.backlogs", actual=history_count, required=node.max_history
        )

        return RuleEvaluationResult.model_construct(
            rule_id=node.id,
            rule_type=node.type,
            severity=node.severity,
            status=status,
            actual_value=history_count,
            required_value=node.max_history,
            data_source="student.backlogs",
            student_explanation=explanation,
            officer_detail=officer,
        )

    def _eval_gap_years(self, student: Student, node: GapYearsMaxRule) -> RuleEvaluationResult:
        total_gaps = student.total_gap_years()
        passed = total_gaps <= node.max_gap_years
        status = RuleEvaluationStatus.PASSED if passed else RuleEvaluationStatus.FAILED

        explanation = self.templates.render_student(
            "gap_years_max",
            status.value,
            actual=total_gaps,
            required=node.max_gap_years,
        )
        officer = self.templates.render_officer(
            node.id, "gap_years_max", status.value, "student.gap_years", actual=total_gaps, required=node.max_gap_years
        )

        return RuleEvaluationResult.model_construct(
            rule_id=node.id,
            rule_type=node.type,
            severity=node.severity,
            status=status,
            actual_value=total_gaps,
            required_value=node.max_gap_years,
            data_source="student.gap_years",
            student_explanation=explanation,
            officer_detail=officer,
        )

    def _eval_age(self, student: Student, node: AgeMaxRule, as_of: date) -> RuleEvaluationResult:
        dob = student.date_of_birth
        days = (as_of - dob).days
        age_years = days / 365.25

        passed = age_years <= node.max_age_years
        status = RuleEvaluationStatus.PASSED if passed else RuleEvaluationStatus.FAILED

        explanation = self.templates.render_student(
            "age_max",
            status.value,
            actual=age_years,
            required=node.max_age_years,
        )
        officer = self.templates.render_officer(
            node.id, "age_max", status.value, "student.date_of_birth", actual=age_years, required=node.max_age_years
        )

        return RuleEvaluationResult.model_construct(
            rule_id=node.id,
            rule_type=node.type,
            severity=node.severity,
            status=status,
            actual_value=round(age_years, 2),
            required_value=node.max_age_years,
            data_source="student.date_of_birth",
            student_explanation=explanation,
            officer_detail=officer,
        )

    def _eval_semester(self, student: Student, node: SemesterMinRule) -> RuleEvaluationResult:
        current_sem = max(student.semester_sgpa.keys()) if student.semester_sgpa else 7
        passed = current_sem >= node.min_semester
        status = RuleEvaluationStatus.PASSED if passed else RuleEvaluationStatus.FAILED

        explanation = self.templates.render_student(
            "semester_min",
            status.value,
            actual=current_sem,
            required=node.min_semester,
        )
        officer = self.templates.render_officer(
            node.id, "semester_min", status.value, "student.semester_sgpa", actual=current_sem, required=node.min_semester
        )

        return RuleEvaluationResult.model_construct(
            rule_id=node.id,
            rule_type=node.type,
            severity=node.severity,
            status=status,
            actual_value=current_sem,
            required_value=node.min_semester,
            data_source="student.semester_sgpa",
            student_explanation=explanation,
            officer_detail=officer,
        )

    def _eval_program(self, student: Student, node: ProgramInRule) -> RuleEvaluationResult:
        actual = student.program
        passed = actual in node.allowed_programs
        status = RuleEvaluationStatus.PASSED if passed else RuleEvaluationStatus.FAILED

        explanation = self.templates.render_student(
            "program_in",
            status.value,
            actual=actual,
            required_list=", ".join(node.allowed_programs),
        )
        officer = self.templates.render_officer(
            node.id, "program_in", status.value, "student.program", actual=actual, required_list=", ".join(node.allowed_programs)
        )

        return RuleEvaluationResult.model_construct(
            rule_id=node.id,
            rule_type=node.type,
            severity=node.severity,
            status=status,
            actual_value=actual,
            required_value=node.allowed_programs,
            data_source="student.program",
            student_explanation=explanation,
            officer_detail=officer,
        )

    def _eval_custom_field(self, student: Student, node: CustomFieldRule) -> RuleEvaluationResult:
        field_val = getattr(student, node.field_name, None)
        passed = False
        if node.operator == "eq":
            passed = (field_val == node.expected_value)
        elif node.operator == "gte" and field_val is not None:
            passed = (field_val >= node.expected_value)
        elif node.operator == "lte" and field_val is not None:
            passed = (field_val <= node.expected_value)
        elif node.operator == "in" and isinstance(node.expected_value, (list, set)):
            passed = (field_val in node.expected_value)

        status = RuleEvaluationStatus.PASSED if passed else RuleEvaluationStatus.FAILED
        explanation = f"Custom rule {node.field_name} {node.operator} {node.expected_value}: actual={field_val}"
        return RuleEvaluationResult.model_construct(
            rule_id=node.id,
            rule_type=node.type,
            severity=node.severity,
            status=status,
            actual_value=field_val,
            required_value=node.expected_value,
            data_source=f"student.{node.field_name}",
            student_explanation=explanation,
            officer_detail=f"[{node.id}][{status.value.upper()}] {explanation}",
        )

    def _eval_and(
        self, student: Student, node: AndRule, as_of: date, cfg: EvaluationConfig
    ) -> RuleEvaluationResult:
        sub_results = [self._evaluate_node(student, r, as_of, cfg) for r in node.rules]
        all_passed = all(r.status == RuleEvaluationStatus.PASSED for r in sub_results)
        any_review = any(r.status == RuleEvaluationStatus.REVIEW for r in sub_results)

        if any_review:
            status = RuleEvaluationStatus.REVIEW
        elif all_passed:
            status = RuleEvaluationStatus.PASSED
        else:
            status = RuleEvaluationStatus.FAILED

        explanation = f"AND group ({len(sub_results)} sub-rules): {status.value}"
        return RuleEvaluationResult.model_construct(
            rule_id=node.id,
            rule_type=node.type,
            severity=node.severity,
            status=status,
            actual_value=[r.status.value for r in sub_results],
            required_value="ALL PASSED",
            data_source="composite.and",
            student_explanation=explanation,
            officer_detail=f"[{node.id}][{status.value.upper()}] sub-rules evaluated={len(sub_results)}",
        )

    def _eval_or(
        self, student: Student, node: OrRule, as_of: date, cfg: EvaluationConfig
    ) -> RuleEvaluationResult:
        sub_results = [self._evaluate_node(student, r, as_of, cfg) for r in node.rules]
        any_passed = any(r.status == RuleEvaluationStatus.PASSED for r in sub_results)
        any_review = any(r.status == RuleEvaluationStatus.REVIEW for r in sub_results)

        if any_passed:
            status = RuleEvaluationStatus.PASSED
        elif any_review:
            status = RuleEvaluationStatus.REVIEW
        else:
            status = RuleEvaluationStatus.FAILED

        explanation = f"OR group ({len(sub_results)} sub-rules): {status.value}"
        return RuleEvaluationResult.model_construct(
            rule_id=node.id,
            rule_type=node.type,
            severity=node.severity,
            status=status,
            actual_value=[r.status.value for r in sub_results],
            required_value="AT LEAST ONE PASSED",
            data_source="composite.or",
            student_explanation=explanation,
            officer_detail=f"[{node.id}][{status.value.upper()}] sub-rules evaluated={len(sub_results)}",
        )

    def _eval_not(
        self, student: Student, node: NotRule, as_of: date, cfg: EvaluationConfig
    ) -> RuleEvaluationResult:
        sub = self._evaluate_node(student, node.rule, as_of, cfg)
        if sub.status == RuleEvaluationStatus.REVIEW:
            status = RuleEvaluationStatus.REVIEW
        elif sub.status == RuleEvaluationStatus.PASSED:
            status = RuleEvaluationStatus.FAILED
        else:
            status = RuleEvaluationStatus.PASSED

        explanation = f"NOT condition on rule {node.rule.id}: {status.value}"
        return RuleEvaluationResult.model_construct(
            rule_id=node.id,
            rule_type=node.type,
            severity=node.severity,
            status=status,
            actual_value=sub.status.value,
            required_value="INVERTED STATUS",
            data_source="composite.not",
            student_explanation=explanation,
            officer_detail=f"[{node.id}][{status.value.upper()}] inverted child={node.rule.id}",
        )

    @staticmethod
    def compute_snapshot_hash(student: Student, rule_set: RuleSet, as_of: date) -> str:
        """Computes a SHA-256 fingerprint for reproducible audits."""
        backlog_sig = ",".join(f"{b.subject}:{b.status.value}:{b.cleared_on}" for b in student.backlogs)
        raw_str = (
            f"{student.id}|{student.roll_no}|{student.cgpa}|{student.tenth_percentage}|"
            f"{student.twelfth_percentage}|{student.diploma_percentage}|{student.branch}|"
            f"{backlog_sig}|{student.total_gap_years()}|{rule_set.id}|{rule_set.version}|"
            f"{as_of.isoformat()}"
        )
        return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()
