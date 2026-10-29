"""
What-If change impact preview engine.
Simulates candidate cut-offs, backlog rules, branch additions, date shifts,
room changes, and manual overrides WITHOUT persistence.
Produces explainable ImpactReport with dynamic headlines and second-order tracing.
"""

from __future__ import annotations

import copy
import datetime
from typing import Any

from backend.app.domain.eligibility.ast import RuleSet
from backend.app.domain.eligibility.evaluator import EligibilityEvaluator, EligibilityStatus
from backend.app.domain.impact.headline import generate_headline
from backend.app.domain.impact.models import (
    ChangeRequest,
    ChangeType,
    ImpactReport,
    StudentClashImpact,
    StudentImpactDetail,
)
from backend.app.domain.impact.second_order import SecondOrderAnalyzer
from backend.app.domain.models import Drive, RequirementSet, Student
from backend.app.domain.policy.checker import policy_check
from backend.app.domain.policy.models import CollegeOfferPolicy, PolicyCheckStatus
from backend.app.scheduler.engine import PlacementSchedulerEngine
from backend.app.scheduler.models import (
    ScheduleConfig,
    ScheduledItem,
    SchedulerDrive,
    SchedulerRoom,
    SchedulerRound,
)


class WhatIfEngine:
    """Evaluates proposed placement modifications purely in memory."""

    def __init__(self) -> None:
        self.evaluator = EligibilityEvaluator()
        self.scheduler_engine = PlacementSchedulerEngine()
        self.second_order_analyzer = SecondOrderAnalyzer()

    def apply_change(
        self,
        current_drive: Drive,
        all_drives: list[Drive],
        students: list[Student],
        rooms: list[SchedulerRoom],
        policy: CollegeOfferPolicy,
        current_shortlist: list[str],
        current_schedule_items: list[ScheduledItem],
        change: ChangeRequest,
        config: ScheduleConfig | None = None,
    ) -> ImpactReport:
        cfg = config or ScheduleConfig()

        # Step 1: Clone drive and requirements to ensure zero side-effects
        sim_drive = copy.deepcopy(current_drive)
        sim_req = copy.deepcopy(current_drive.requirements) or RequirementSet(
            id=f"req_{current_drive.id}",
            drive_id=current_drive.id,
            min_cgpa=0.0,
        )
        sim_policy = policy.model_copy(deep=True)

        # Step 2: Apply the change to simulated objects
        sim_drive, sim_req, sim_policy = self._mutate_simulated_state(sim_drive, sim_req, sim_policy, change)

        # Step 3: Compute candidate shortlist delta
        added_students: list[StudentImpactDetail] = []
        removed_students: list[StudentImpactDetail] = []

        if change.change_type == ChangeType.MANUAL_STUDENT_ADD:
            assert change.student_id is not None
            stu = next((s for s in students if s.id == change.student_id), None)
            if stu and stu.id not in current_shortlist:
                added_students.append(
                    StudentImpactDetail(
                        student_id=stu.id,
                        student_roll_no=stu.roll_no,
                        student_name=stu.name,
                        branch=stu.branch,
                        cgpa=stu.cgpa,
                        change_type="added",
                        reason=f"Manual inclusion: {change.mandatory_reason}",
                    )
                )

        elif change.change_type == ChangeType.MANUAL_STUDENT_REMOVE:
            assert change.student_id is not None
            stu = next((s for s in students if s.id == change.student_id), None)
            if stu and stu.id in current_shortlist:
                removed_students.append(
                    StudentImpactDetail(
                        student_id=stu.id,
                        student_roll_no=stu.roll_no,
                        student_name=stu.name,
                        branch=stu.branch,
                        cgpa=stu.cgpa,
                        change_type="removed",
                        reason=f"Manual exclusion: {change.mandatory_reason}",
                    )
                )

        elif change.change_type in (
            ChangeType.CGPA_CUTOFF,
            ChangeType.PERCENTAGE_CUTOFF,
            ChangeType.BACKLOG_RULE,
            ChangeType.BRANCH_ADDED,
            ChangeType.BRANCH_REMOVED,
            ChangeType.GAP_YEAR,
            ChangeType.POLICY_TOGGLE,
        ):
            # Re-evaluate all students against simulated criteria
            rule_set = self._build_ruleset_from_requirements(sim_req)

            for stu in students:
                was_in_shortlist = stu.id in current_shortlist

                # Academic check
                academic_res = self.evaluator.evaluate(stu, rule_set, drive_id=sim_drive.id)
                academic_ok = academic_res.status == EligibilityStatus.ELIGIBLE

                # Policy check
                policy_res = policy_check(
                    student=stu,
                    drive=sim_drive,
                    policy=sim_policy,
                    as_of=sim_drive.drive_date,
                )
                policy_ok = policy_res.status == PolicyCheckStatus.ALLOWED

                is_now_eligible = academic_ok and policy_ok

                if is_now_eligible and not was_in_shortlist:
                    reason = academic_res.overall_student_reason or f"Satisfies revised requirements for {sim_drive.company_name}"
                    added_students.append(
                        StudentImpactDetail(
                            student_id=stu.id,
                            student_roll_no=stu.roll_no,
                            student_name=stu.name,
                            branch=stu.branch,
                            cgpa=stu.cgpa,
                            change_type="added",
                            reason=reason,
                        )
                    )
                elif not is_now_eligible and was_in_shortlist:
                    reason = academic_res.overall_student_reason or policy_res.plain_english_reason
                    removed_students.append(
                        StudentImpactDetail(
                            student_id=stu.id,
                            student_roll_no=stu.roll_no,
                            student_name=stu.name,
                            branch=stu.branch,
                            cgpa=stu.cgpa,
                            change_type="removed",
                            reason=reason,
                        )
                    )

        # Step 4: Detect schedule clashes for newly added candidates
        newly_clashing: list[StudentClashImpact] = []
        simulated_shortlist = [
            sid for sid in current_shortlist if sid not in {r.student_id for r in removed_students}
        ] + [a.student_id for a in added_students]

        # Check newly added candidates against other published schedules
        for added_stu in added_students:
            for item in current_schedule_items:
                if item.drive_id != sim_drive.id and added_stu.student_id in item.student_ids:
                    # Conflict detected: student is already committed to another drive on that day
                    if item.start_time.date() == sim_drive.drive_date:
                        newly_clashing.append(
                            StudentClashImpact(
                                student_id=added_stu.student_id,
                                student_roll_no=added_stu.student_roll_no,
                                student_name=added_stu.student_name,
                                conflicting_drive_id=item.drive_id,
                                conflicting_drive_name=item.round_name,
                                conflicting_slot_time=item.start_time.strftime("%H:%M"),
                                details=f"Already scheduled for '{item.round_name}' at {item.start_time.strftime('%H:%M')} in {item.room_name}",
                            )
                        )

        # Step 5: Schedule moves required (minimal-disturbance simulation if dates or rooms mutated)
        schedule_moves: list[dict[str, Any]] = []
        if change.change_type in (ChangeType.DRIVE_DATE_SHIFT, ChangeType.ROOM_UNAVAILABLE, ChangeType.PANEL_COUNT):
            sim_scheduler_drives = [
                SchedulerDrive(
                    id=sim_drive.id,
                    company_name=sim_drive.company_name,
                    drive_date=sim_drive.drive_date,
                    shortlisted_student_ids=simulated_shortlist,
                    rounds=[
                        SchedulerRound(
                            round_number=1,
                            name="Assessment",
                            round_type=r.round_type,
                            duration_minutes=r.duration_minutes,
                            is_group_round=True,
                        ) for r in sim_drive.rounds
                    ],
                )
            ]
            sim_rooms = [r for r in rooms if r.id != change.room_id] if change.change_type == ChangeType.ROOM_UNAVAILABLE else rooms
            sim_sched_res = self.scheduler_engine.generate_schedule(sim_scheduler_drives, sim_rooms, cfg)
            schedule_moves = [it.model_dump() for it in sim_sched_res.items[:5]]

        # Step 6: Second-order downstream effects
        newly_eligible_objs = [
            s for s in students if s.id in {a.student_id for a in added_students}
        ]
        second_order_effects = self.second_order_analyzer.trace_downstream_effects(
            source_drive=sim_drive,
            newly_eligible_students=newly_eligible_objs,
            all_drives=all_drives,
            policy=sim_policy,
        )

        # Step 7: Dynamic Headline Computation
        clash_sample = newly_clashing[0] if newly_clashing else None
        headline = generate_headline(
            change=change,
            added_count=len(added_students),
            removed_count=len(removed_students),
            clashes_count=len(newly_clashing),
            clash_sample=clash_sample,
            second_order_count=len(second_order_effects),
        )

        return ImpactReport(
            change_summary=self._describe_change(change),
            headline=headline,
            drive_id=sim_drive.id,
            drive_name=sim_drive.company_name,
            students_added_count=len(added_students),
            students_removed_count=len(removed_students),
            clashes_count=len(newly_clashing),
            students_added=added_students,
            students_removed=removed_students,
            newly_clashing_students=newly_clashing,
            schedule_moves_required=schedule_moves,
            second_order_effects=second_order_effects,
            policy_conflicts=[],
        )

    def _mutate_simulated_state(
        self,
        drive: Drive,
        req: RequirementSet,
        policy: CollegeOfferPolicy,
        change: ChangeRequest,
    ) -> tuple[Drive, RequirementSet, CollegeOfferPolicy]:
        mutated_policy = policy

        if change.change_type == ChangeType.CGPA_CUTOFF:
            req.min_cgpa = float(change.new_value)
            drive.requirements = req

        elif change.change_type == ChangeType.PERCENTAGE_CUTOFF:
            if change.target_field == "10th":
                req.min_tenth_percentage = float(change.new_value)
            elif change.target_field == "12th":
                req.min_twelfth_percentage = float(change.new_value)
            drive.requirements = req

        elif change.change_type == ChangeType.BRANCH_ADDED:
            b_name = change.branch_name or (str(change.new_value) if change.new_value is not None else None)
            assert b_name is not None
            if b_name not in req.allowed_branches:
                req.allowed_branches = list(req.allowed_branches) + [b_name]
            drive.requirements = req

        elif change.change_type == ChangeType.BRANCH_REMOVED:
            b_name = change.branch_name or (str(change.new_value) if change.new_value is not None else None)
            assert b_name is not None
            req.allowed_branches = [b for b in req.allowed_branches if b != b_name]
            drive.requirements = req

        elif change.change_type == ChangeType.BACKLOG_RULE:
            if change.new_value is not None:
                req.max_active_backlogs = int(change.new_value)
            drive.requirements = req

        elif change.change_type == ChangeType.GAP_YEAR:
            if change.new_value is not None:
                req.max_gap_years = int(change.new_value)
            drive.requirements = req

        elif change.change_type == ChangeType.DRIVE_DATE_SHIFT:
            if isinstance(change.new_value, str):
                drive.drive_date = datetime.date.fromisoformat(change.new_value)
            elif isinstance(change.new_value, datetime.date):
                drive.drive_date = change.new_value

        elif change.change_type == ChangeType.POLICY_TOGGLE:
            if change.toggle_name:
                mutated_policy = policy.model_copy(update={change.toggle_name: change.new_value})

        return drive, req, mutated_policy

    def _build_ruleset_from_requirements(self, req: RequirementSet) -> RuleSet:
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
        if req.min_cgpa > 0:
            rules.append(CGPAMinRule(id="rule_cgpa", min_cgpa=req.min_cgpa, scale=10.0))
        if req.min_tenth_percentage > 0:
            rules.append(PercentageMinRule(id="rule_10th", qualification="10th", min_percentage=req.min_tenth_percentage))
        if req.min_twelfth_percentage is not None and req.min_twelfth_percentage > 0:
            rules.append(PercentageMinRule(id="rule_12th", qualification="12th", min_percentage=req.min_twelfth_percentage))
        if req.allowed_branches:
            rules.append(BranchInRule(id="rule_branches", allowed_branches=req.allowed_branches))
        if req.max_active_backlogs is not None:
            rules.append(ActiveBacklogsMaxRule(id="rule_active_backlogs", max_backlogs=req.max_active_backlogs))
        if req.max_history_backlogs is not None:
            rules.append(HistoricalBacklogsMaxRule(id="rule_hist_backlogs", max_history=req.max_history_backlogs))
        if req.max_gap_years is not None:
            rules.append(GapYearsMaxRule(id="rule_gap_years", max_gap_years=req.max_gap_years))

        return RuleSet(id=f"sim_rs_{req.drive_id}", name="Simulated Ruleset", version=1, rules=rules)

    def _describe_change(self, change: ChangeRequest) -> str:
        return f"{change.change_type.value}: old={change.old_value} -> new={change.new_value}"
