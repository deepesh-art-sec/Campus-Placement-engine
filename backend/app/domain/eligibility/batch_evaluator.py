"""
High-Performance Batch and Incremental Eligibility Evaluation Engine.
Designed to evaluate 1,800+ students across dozens of drives in sub-seconds.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.app.domain.eligibility.evaluator import (
    DetailedEligibilityDecision,
    EligibilityEvaluator,
    EvaluationConfig,
)

if TYPE_CHECKING:
    from backend.app.domain.eligibility.ast import RuleSet
    from backend.app.domain.models import Student


class BatchEligibilityEvaluator:
    """Orchestrates batch evaluations and targeted incremental updates."""

    def __init__(self, evaluator: EligibilityEvaluator | None = None) -> None:
        self.evaluator = evaluator or EligibilityEvaluator()

    def evaluate_drive_batch(
        self,
        students: list[Student],
        rule_set: RuleSet,
        drive_id: str,
        config: EvaluationConfig | None = None,
    ) -> list[DetailedEligibilityDecision]:
        """Evaluates an entire student directory against a single recruitment drive."""
        cfg = config or EvaluationConfig()
        results: list[DetailedEligibilityDecision] = []
        for student in students:
            decision = self.evaluator.evaluate(student, rule_set, drive_id, cfg)
            results.append(decision)
        return results

    def evaluate_multi_drives(
        self,
        students: list[Student],
        drive_rulesets: list[tuple[str, RuleSet]],
        config: EvaluationConfig | None = None,
    ) -> dict[str, list[DetailedEligibilityDecision]]:
        """
        Evaluates a student cohort across multiple company drives simultaneously.
        Returns a mapping of {drive_id: list[DetailedEligibilityDecision]}.
        """
        cfg = config or EvaluationConfig()
        drive_results: dict[str, list[DetailedEligibilityDecision]] = {}

        for drive_id, rule_set in drive_rulesets:
            drive_results[drive_id] = self.evaluate_drive_batch(students, rule_set, drive_id, cfg)

        return drive_results

    def re_evaluate_modified_students(
        self,
        modified_students: list[Student],
        drive_rulesets: list[tuple[str, RuleSet]],
        existing_decisions: dict[tuple[str, str], DetailedEligibilityDecision],
        config: EvaluationConfig | None = None,
    ) -> dict[tuple[str, str], DetailedEligibilityDecision]:
        """
        Incrementally re-evaluates ONLY modified students across all active drives.
        Key is (student_id, drive_id).
        """
        cfg = config or EvaluationConfig()
        updated_decisions = dict(existing_decisions)

        for student in modified_students:
            for drive_id, rule_set in drive_rulesets:
                new_decision = self.evaluator.evaluate(student, rule_set, drive_id, cfg)
                updated_decisions[(student.id, drive_id)] = new_decision

        return updated_decisions

    def re_evaluate_single_drive_rule_change(
        self,
        students: list[Student],
        drive_id: str,
        new_rule_set: RuleSet,
        existing_decisions: dict[tuple[str, str], DetailedEligibilityDecision],
        config: EvaluationConfig | None = None,
    ) -> dict[tuple[str, str], DetailedEligibilityDecision]:
        """
        Incrementally updates decisions when ONLY one drive's rules change,
        preserving all decisions for other drives intact.
        """
        cfg = config or EvaluationConfig()
        updated = dict(existing_decisions)

        for student in students:
            new_decision = self.evaluator.evaluate(student, new_rule_set, drive_id, cfg)
            updated[(student.id, drive_id)] = new_decision

        return updated
