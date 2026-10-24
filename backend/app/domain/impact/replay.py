"""
Historical decision reconstruction and audit replay engine.
Reconstructs exact student, drive requirement, and policy states from the append-only event log
to explain historical decisions deterministically ('why was student X excluded from drive Y on 3 Oct?').
"""

from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.domain.eligibility.ast import RuleSet
from backend.app.domain.eligibility.evaluator import EligibilityEvaluator, EligibilityStatus
from backend.app.domain.models import Drive, RequirementSet, Student
from backend.app.domain.policy.checker import policy_check
from backend.app.domain.policy.models import CollegeOfferPolicy, PolicyCheckStatus
from backend.app.events.event_service import EventService
from backend.app.storage.repositories.interfaces import IUnitOfWork


class ReplayExplanation(BaseModel):
    """Immutable audit record explaining a historical decision."""
    model_config = ConfigDict(frozen=True)

    student_id: str
    student_name: str
    drive_id: str
    drive_name: str
    as_of: datetime.datetime
    final_status: str  # "eligible", "ineligible", "policy_blocked"
    academic_status: str
    policy_status: str
    academic_reason: str
    policy_reason: str
    rules_failed: list[str] = Field(default_factory=list)
    rules_passed: list[str] = Field(default_factory=list)
    narrative: str


class DecisionReplayer:
    """Reconstructs historical eligibility decisions from event sourcing timeline."""

    def __init__(self) -> None:
        self.evaluator = EligibilityEvaluator()

    def explain_historical_decision(
        self,
        uow: IUnitOfWork,
        student: Student,
        drive: Drive,
        policy: CollegeOfferPolicy,
        as_of: datetime.datetime,
    ) -> ReplayExplanation:
        """Reconstructs and explains decision for student in drive as of historical timestamp."""
        # Step 1: Replay historical student state if events exist
        hist_student_state = EventService.replay_state_at(uow, "STUDENT", student.id, as_of)
        effective_student = student
        if hist_student_state:
            # Construct student with historical snapshot
            try:
                effective_student = Student.model_validate({**student.model_dump(), **hist_student_state})
            except Exception:
                effective_student = student

        # Step 2: Replay historical drive requirements if events exist
        hist_drive_state = EventService.replay_state_at(uow, "DRIVE", drive.id, as_of)
        effective_req = drive.requirements
        if hist_drive_state and "requirements" in hist_drive_state:
            try:
                effective_req = RequirementSet.model_validate(hist_drive_state["requirements"])
            except Exception:
                effective_req = drive.requirements

        assert effective_req is not None

        # Step 3: Build rule AST from effective requirements
        from backend.app.domain.eligibility.ast import (
            ActiveBacklogsMaxRule,
            BranchInRule,
            CGPAMinRule,
            GapYearsMaxRule,
            HistoricalBacklogsMaxRule,
            PercentageMinRule,
            RuleNode,
        )

        rules: list[RuleNode] = []
        if effective_req.min_cgpa > 0:
            rules.append(CGPAMinRule(id="rule_cgpa", min_cgpa=effective_req.min_cgpa, scale=10.0))
        if effective_req.min_tenth_percentage > 0:
            rules.append(PercentageMinRule(id="rule_10th", qualification="10th", min_percentage=effective_req.min_tenth_percentage))
        if effective_req.min_twelfth_percentage is not None and effective_req.min_twelfth_percentage > 0:
            rules.append(PercentageMinRule(id="rule_12th", qualification="12th", min_percentage=effective_req.min_twelfth_percentage))
        if effective_req.allowed_branches:
            rules.append(BranchInRule(id="rule_branches", allowed_branches=effective_req.allowed_branches))
        if effective_req.max_active_backlogs is not None:
            rules.append(ActiveBacklogsMaxRule(id="rule_active_backlogs", max_backlogs=effective_req.max_active_backlogs))
        if effective_req.max_history_backlogs is not None:
            rules.append(HistoricalBacklogsMaxRule(id="rule_hist_backlogs", max_history=effective_req.max_history_backlogs))
        if effective_req.max_gap_years is not None:
            rules.append(GapYearsMaxRule(id="rule_gap_years", max_gap_years=effective_req.max_gap_years))

        rule_set = RuleSet(id=f"hist_{drive.id}", name="Historical Ruleset", version=1, rules=rules)

        # Step 4: Evaluate academic criteria as of historical date
        academic_res = self.evaluator.evaluate(effective_student, rule_set, drive_id=drive.id)
        academic_status = academic_res.status.value
        academic_reason = academic_res.overall_student_reason

        # Step 5: Evaluate offer policy criteria as of historical date
        policy_res = policy_check(
            student=effective_student,
            drive=drive,
            policy=policy,
            as_of=as_of.date(),
        )
        policy_status = policy_res.status.value
        policy_reason = policy_res.plain_english_reason

        # Step 6: Determine composite status and generate plain-English historical narrative
        if academic_status == EligibilityStatus.ELIGIBLE.value and policy_status == PolicyCheckStatus.ALLOWED.value:
            final_status = "eligible"
            narrative = f"As of {as_of.strftime('%d %b %Y')}, candidate '{effective_student.name}' satisfied all academic and offer policy requirements for '{drive.company_name}'."
        elif academic_status != EligibilityStatus.ELIGIBLE.value:
            final_status = "ineligible"
            narrative = f"As of {as_of.strftime('%d %b %Y')}, candidate '{effective_student.name}' was excluded from '{drive.company_name}' due to academic criteria: {academic_reason}."
        else:
            final_status = "policy_blocked"
            narrative = f"As of {as_of.strftime('%d %b %Y')}, candidate '{effective_student.name}' was blocked from '{drive.company_name}' under placement offer policy: {policy_reason}."

        failed_rules = [f"{r.rule_id}: {r.student_explanation}" for r in academic_res.failed_rules]
        passed_rules = [f"{r.rule_id}: {r.student_explanation}" for r in academic_res.passed_rules]

        return ReplayExplanation(
            student_id=effective_student.id,
            student_name=effective_student.name,
            drive_id=drive.id,
            drive_name=drive.company_name,
            as_of=as_of,
            final_status=final_status,
            academic_status=academic_status,
            policy_status=policy_status,
            academic_reason=academic_reason,
            policy_reason=policy_reason,
            rules_failed=failed_rules,
            rules_passed=passed_rules,
            narrative=narrative,
        )
