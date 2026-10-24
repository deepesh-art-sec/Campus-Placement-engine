"""
Batch Eligibility Evaluation Engine Routes.
Executes pure, deterministic evaluation across rule AST and college offer policies.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.auth.dependencies import require_officer_or_coordinator
from backend.app.domain.eligibility.ast import (
    ActiveBacklogsMaxRule,
    BranchInRule,
    CGPAMinRule,
    GapYearsMaxRule,
    PercentageMinRule,
    RuleNode,
    RuleSet,
)
from backend.app.domain.eligibility.evaluator import EligibilityEvaluator, EligibilityStatus
from backend.app.domain.models import Drive
from backend.app.domain.policy.catalog import STRICT_ONE_OFFER_POLICY
from backend.app.domain.policy.checker import policy_check
from backend.app.domain.policy.models import PolicyCheckStatus
from backend.app.storage.database import get_db
from backend.app.storage.models.entities import (
    DriveModel,
    EligibilityDecisionModel,
    EligibilityRunModel,
    StudentModel,
    UserModel,
)
from backend.app.storage.repositories.mappers import student_entity_to_domain

router = APIRouter(prefix="/api/eligibility", tags=["Eligibility Engine"])


class RunEligibilityRequest(BaseModel):
    drive_id: str
    policy_id: str | None = None


@router.post("/run")
def run_eligibility(
    req: RunEligibilityRequest,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Runs batch eligibility for a recruitment drive against academic rules and offer policy."""
    stmt_drive = select(DriveModel).where(DriveModel.id == req.drive_id)
    drive_entity = db.execute(stmt_drive).scalar_one_or_none()
    if not drive_entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recruitment drive not found.")

    # Load students
    student_entities = db.execute(select(StudentModel)).scalars().all()
    if not student_entities:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No students registered in database.")

    students = [student_entity_to_domain(s) for s in student_entities]

    # Build ruleset from drive requirements
    latest_req = drive_entity.requirement_versions[0] if drive_entity.requirement_versions else None
    rules: list[RuleNode] = []
    if latest_req:
        if latest_req.min_cgpa > 0:
            rules.append(CGPAMinRule(id="rule_cgpa", min_cgpa=latest_req.min_cgpa))
        if latest_req.min_tenth_percentage > 0:
            rules.append(PercentageMinRule(id="rule_10th", qualification="10th", min_percentage=latest_req.min_tenth_percentage))
        if latest_req.min_twelfth_percentage:
            rules.append(PercentageMinRule(id="rule_12th", qualification="12th", min_percentage=latest_req.min_twelfth_percentage))
        if latest_req.allowed_branches_json:
            branches = latest_req.allowed_branches_json
            if isinstance(branches, str):
                try:
                    branches = json.loads(branches)
                except Exception:
                    branches = [b.strip() for b in branches.split(",") if b.strip()]
            if branches and isinstance(branches, list):
                rules.append(BranchInRule(id="rule_branches", allowed_branches=branches))
        if latest_req.max_active_backlogs is not None:
            rules.append(ActiveBacklogsMaxRule(id="rule_backlogs", max_backlogs=latest_req.max_active_backlogs))
        if latest_req.max_gap_years is not None:
            rules.append(GapYearsMaxRule(id="rule_gap", max_gap_years=latest_req.max_gap_years))

    rule_set = RuleSet(id=f"rs_{drive_entity.id}", name=f"{drive_entity.company_name} Criteria", rules=rules)
    evaluator = EligibilityEvaluator()
    policy = STRICT_ONE_OFFER_POLICY

    drive_domain = Drive(
        id=drive_entity.id,
        company_id=drive_entity.company_id,
        company_name=drive_entity.company_name,
        drive_date=drive_entity.drive_date,
        ctc_lpa=drive_entity.ctc_lpa,
    )

    run_id = f"run_{uuid.uuid4().hex[:8]}"
    eligible_count = 0
    ineligible_count = 0
    policy_blocked_count = 0
    decisions_to_insert = []

    for stu in students:
        acad_res = evaluator.evaluate(stu, rule_set, drive_id=drive_entity.id)
        pol_res = policy_check(student=stu, drive=drive_domain, policy=policy)

        if acad_res.status == EligibilityStatus.ELIGIBLE and pol_res.status == PolicyCheckStatus.ALLOWED:
            final_status = "eligible"
            eligible_count += 1
            reason = acad_res.overall_student_reason or f"Fully eligible for {drive_entity.company_name}."
        elif acad_res.status != EligibilityStatus.ELIGIBLE:
            final_status = "ineligible"
            ineligible_count += 1
            reason = acad_res.overall_student_reason
        else:
            final_status = "policy_blocked"
            policy_blocked_count += 1
            reason = pol_res.plain_english_reason

        dec_entity = EligibilityDecisionModel(
            id=f"dec_{drive_entity.id}_{stu.id}",
            student_id=stu.id,
            drive_id=drive_entity.id,
            status=final_status,
            reasons_json=json.dumps([reason]),
            rule_ids_json=json.dumps([r.rule_id for r in acad_res.passed_rules]),
            run_id=run_id,
        )
        decisions_to_insert.append(dec_entity)

    # Save run record
    run_record = EligibilityRunModel(
        id=run_id,
        drive_id=drive_entity.id,
        requirement_version_id=latest_req.id if latest_req else "default",
        policy_id=policy.id,
        total_evaluated=len(students),
        total_eligible=eligible_count,
        total_ineligible=ineligible_count + policy_blocked_count,
        executed_by=current_user.username,
    )
    db.add(run_record)

    for d in decisions_to_insert:
        db.merge(d)

    db.commit()

    return {
        "run_id": run_id,
        "drive_id": drive_entity.id,
        "company_name": drive_entity.company_name,
        "total_evaluated": len(students),
        "eligible_count": eligible_count,
        "ineligible_count": ineligible_count,
        "policy_blocked_count": policy_blocked_count,
        "message": f"Evaluated {len(students)} candidates: {eligible_count} eligible, {ineligible_count} ineligible, {policy_blocked_count} policy blocked.",
    }


@router.get("/decisions/{drive_id}")
def get_decisions(
    drive_id: str,
    status_filter: str | None = None,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieves eligibility decisions for a drive with plain-English reasons."""
    stmt = select(EligibilityDecisionModel).where(EligibilityDecisionModel.drive_id == drive_id)
    if status_filter:
        stmt = stmt.where(EligibilityDecisionModel.status == status_filter)

    results = db.execute(stmt).scalars().all()
    output = []
    for d in results:
        reasons_list = json.loads(d.reasons_json) if d.reasons_json else []
        reason = reasons_list[0] if reasons_list else ""
        rule_ids = json.loads(d.rule_ids_json) if d.rule_ids_json else []
        output.append({
            "student_id": d.student_id,
            "student_name": d.student.name if d.student else "Unknown",
            "roll_no": d.student.roll_no if d.student else "",
            "branch": d.student.branch if d.student else "",
            "cgpa": d.student.cgpa if d.student else 0.0,
            "status": d.status,
            "reason": reason,
            "passed_rules": rule_ids,
            "failed_rules": [],
        })
    return output
