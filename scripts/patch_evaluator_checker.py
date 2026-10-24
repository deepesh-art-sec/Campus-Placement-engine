"""
Patch script for evaluator.py and checker.py to ensure 100% compliance with edge cases.
"""
from pathlib import Path

# 1. Update evaluator.py
eval_path = Path("backend/app/domain/eligibility/evaluator.py")
eval_code = eval_path.read_text(encoding="utf-8")

if "def reason(self) -> str:" not in eval_code:
    eval_code = eval_code.replace(
        "    ambiguity_reason: str | None = None\n",
        "    ambiguity_reason: str | None = None\n\n    @property\n    def reason(self) -> str:\n        return self.student_explanation\n",
    )

if "def one_line_explanation(self) -> str:" not in eval_code:
    eval_code = eval_code.replace(
        "    evaluated_at: datetime = Field(default_factory=datetime.utcnow)\n",
        "    evaluated_at: datetime = Field(default_factory=datetime.utcnow)\n\n    @property\n    def one_line_explanation(self) -> str:\n        return self.overall_student_reason\n",
    )

# Support as_of_date param in evaluate()
old_evaluate = """    def evaluate(
        self,
        student: Student,
        rule_set: RuleSet,
        drive_id: str,
        config: EvaluationConfig | None = None,
    ) -> DetailedEligibilityDecision:
        cfg = config or EvaluationConfig()
        as_of = cfg.as_of_date"""

new_evaluate = """    def evaluate(
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
        as_of = cfg.as_of_date"""

eval_code = eval_code.replace(old_evaluate, new_evaluate)

# Support tenth/twelfth in _eval_percentage
old_qual = """        if qual == "10th":
            actual = student.tenth_percentage
            data_source = "student.tenth_percentage"
        elif qual == "12th":"""

new_qual = """        if qual in ("10th", "tenth", "10"):
            actual = student.tenth_percentage
            data_source = "student.tenth_percentage"
        elif qual in ("12th", "twelfth", "12"):"""

eval_code = eval_code.replace(old_qual, new_qual)

# Support wildcards and case-insensitive branch matching
old_branch = """        # Match either exact or canonical
        passed = (actual_branch in node.allowed_branches) or (canonical_student_branch in canonical_allowed)"""

new_branch = """        # Match wildcard (e.g. All Branches), exact, or canonical
        has_wildcard = any(b.lower() in ("all", "all branches", "any", "all branch") for b in node.allowed_branches)
        passed = has_wildcard or (actual_branch.lower() in [b.lower() for b in node.allowed_branches]) or (canonical_student_branch in canonical_allowed)"""

eval_code = eval_code.replace(old_branch, new_branch)

eval_path.write_text(eval_code, encoding="utf-8")
print("Updated evaluator.py")


# 2. Update checker.py
checker_path = Path("backend/app/domain/policy/checker.py")
checker_code = checker_path.read_text(encoding="utf-8")

old_metric_block = """    # Determine drive qualification metric (CTC or Fixed Pay)
    drive_val = drive.ctc_lpa
    if policy.threshold_basis == ThresholdBasis.FIXED_PAY:
        drive_val = drive.ctc_lpa

    drive_is_dream = is_dream_offer(drive_val, policy)"""

new_metric_block = """    # Determine drive qualification metric (CTC or Fixed Pay)
    def get_metric(val_ctc: float, val_fixed: float | None) -> float:
        if policy.threshold_basis == ThresholdBasis.FIXED_PAY and val_fixed is not None:
            return val_fixed
        return val_ctc

    drive_val = get_metric(drive.ctc_lpa, drive.fixed_pay_lpa)
    drive_is_dream = is_dream_offer(drive_val, policy)

    # 4b. Tier-based quota check
    if policy.tiers:
        for tier in policy.tiers:
            in_tier = (tier.min_ctc_lpa <= drive_val) and (tier.max_ctc_lpa is None or drive_val <= tier.max_ctc_lpa)
            if in_tier:
                tier_offers = [
                    o for o in countable_offers
                    if (tier.min_ctc_lpa <= get_metric(o.ctc_lpa, o.fixed_pay_lpa))
                    and (tier.max_ctc_lpa is None or get_metric(o.ctc_lpa, o.fixed_pay_lpa) <= tier.max_ctc_lpa)
                ]
                if len(tier_offers) >= tier.max_offers_allowed:
                    return PolicyCheckResult(
                        status=PolicyCheckStatus.BLOCKED,
                        clause_id="CLAUSE-2.5-TIER-QUOTA-EXHAUSTED",
                        plain_english_reason=(
                            f"Blocked under Policy Clause 2.5: You already hold {len(tier_offers)} offer(s) in tier '{tier.tier_name}' "
                            f"({', '.join(o.company for o in tier_offers)}), fulfilling your maximum allowed quota of {tier.max_offers_allowed} for this tier."
                        ),
                        what_would_unblock="Participation is permitted for drives in an unexhausted or higher tier.",
                        policy_id=policy.id,
                        policy_version=policy.version,
                        countable_offers_count=offers_count,
                        highest_current_ctc_lpa=highest_ctc,
                    )
                break"""

checker_code = checker_code.replace(old_metric_block, new_metric_block)

checker_path.write_text(checker_code, encoding="utf-8")
print("Updated checker.py")
