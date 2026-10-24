"""
Combined Placement Decision Engine.
Integrates Part 2 Academic Eligibility and Part 3 College Offer Policy.
Guarantees that both independent decisions and their respective explanations
are preserved separately and never conflated or masked.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.domain.eligibility.ast import RuleSet
from backend.app.domain.eligibility.evaluator import (
    DetailedEligibilityDecision,
    EligibilityEvaluator,
    EvaluationConfig,
)
from backend.app.domain.models import Drive, EligibilityStatus, Student
from backend.app.domain.policy.checker import PolicyCheckResult, policy_check
from backend.app.domain.policy.models import CollegeOfferPolicy, PolicyCheckStatus


class CombinedDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    student_id: str
    student_roll_no: str
    student_name: str
    drive_id: str
    company_name: str

    # Combined Verdict
    final_status: EligibilityStatus
    is_academic_eligible: bool
    is_policy_allowed: bool

    # Discrete Academic Breakdown (Part 2)
    academic_decision: DetailedEligibilityDecision
    academic_reason_summary: str

    # Discrete Policy Breakdown (Part 3)
    policy_decision: PolicyCheckResult
    policy_reason_summary: str

    # Comprehensive Dual Explanation
    overall_explanation: str
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


class CombinedDecisionEvaluator:
    """Evaluates both academic eligibility and college offer policy simultaneously."""

    def __init__(self, academic_evaluator: EligibilityEvaluator | None = None) -> None:
        self.academic_evaluator = academic_evaluator or EligibilityEvaluator()

    def evaluate_combined(
        self,
        student: Student,
        drive: Drive,
        rule_set: RuleSet,
        policy: CollegeOfferPolicy,
        as_of: date | None = None,
        eval_config: EvaluationConfig | None = None,
    ) -> CombinedDecision:
        ref_date = as_of or drive.drive_date

        # 1. Evaluate Academic Eligibility (Part 2)
        academic_res = self.academic_evaluator.evaluate(
            student=student,
            rule_set=rule_set,
            drive_id=drive.id,
            config=eval_config,
        )

        # 2. Evaluate College Offer Policy (Part 3)
        policy_res = policy_check(
            student=student,
            drive=drive,
            policy=policy,
            as_of=ref_date,
        )

        is_acad_ok = (academic_res.status == EligibilityStatus.ELIGIBLE)
        is_pol_ok = (policy_res.status == PolicyCheckStatus.ALLOWED)

        # 3. Determine Combined Final Status
        final_status: EligibilityStatus
        if academic_res.status == EligibilityStatus.FLAGGED or policy_res.status == PolicyCheckStatus.NEEDS_REVIEW:
            final_status = EligibilityStatus.FLAGGED
            overall_msg = (
                f"Needs Review: Academic status is '{academic_res.status.value}' and "
                f"Policy status is '{policy_res.status.value}'. Administrative verification required."
            )
        elif is_acad_ok and is_pol_ok:
            final_status = EligibilityStatus.ELIGIBLE
            overall_msg = "Eligible & Approved: Meets all academic requirements and conforms to college placement policy."
        else:
            final_status = EligibilityStatus.INELIGIBLE
            if not is_acad_ok and not is_pol_ok:
                overall_msg = (
                    f"Ineligible: Disqualified on ACADEMIC criteria ({academic_res.overall_student_reason}) "
                    f"AND blocked by COLLEGE OFFER POLICY ({policy_res.plain_english_reason})."
                )
            elif not is_acad_ok:
                overall_msg = f"Ineligible (Academic criteria failed): {academic_res.overall_student_reason}"
            else:
                overall_msg = f"Ineligible (College policy blocked): {policy_res.plain_english_reason}"

        return CombinedDecision(
            student_id=student.id,
            student_roll_no=student.roll_no,
            student_name=student.name,
            drive_id=drive.id,
            company_name=drive.company_name,
            final_status=final_status,
            is_academic_eligible=is_acad_ok,
            is_policy_allowed=is_pol_ok,
            academic_decision=academic_res,
            academic_reason_summary=academic_res.overall_student_reason,
            policy_decision=policy_res,
            policy_reason_summary=policy_res.plain_english_reason,
            overall_explanation=overall_msg,
        )
