from pathlib import Path

policy_routes_path = Path("backend/app/api/routes/policy_routes.py")
code = policy_routes_path.read_text(encoding="utf-8")

extra_imports = """from datetime import date
from sqlalchemy import select
from backend.app.storage.models.entities import DriveModel, StudentModel
from backend.app.storage.repositories.mappers import student_entity_to_domain
from backend.app.domain.models import Drive
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
from backend.app.domain.policy.checker import policy_check
from backend.app.domain.policy.models import PolicyCheckStatus
from backend.app.api.auth.dependencies import require_officer_or_coordinator
"""

# Insert imports if not present
if "from backend.app.storage.repositories.mappers import student_entity_to_domain" not in code:
    code = extra_imports + code

simulate_endpoint = '''

class PolicySimulateRequest(BaseModel):
    student_id: str
    drive_id: str
    policy_id: str | None = None
    override_policy: dict[str, Any] | None = None
    as_of_date: date | None = None


@router.post("/simulate")
def simulate_policy_check(
    req: PolicySimulateRequest,
    current_user: UserModel = Depends(require_officer_or_coordinator),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Interactive Policy Simulator: Evaluates candidate eligibility and offer policy enforcement
    with live parameter overrides, AST rule verdicts, and cited clauses.
    """
    global _active_policy

    # 1. Fetch Student
    s_stmt = select(StudentModel).where(
        (StudentModel.id == req.student_id) | (StudentModel.roll_no == req.student_id)
    )
    s_entity = db.execute(s_stmt).scalar_one_or_none()
    if not s_entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Student '{req.student_id}' not found.")
    student = student_entity_to_domain(s_entity)

    # 2. Fetch Drive
    d_stmt = select(DriveModel).where(DriveModel.id == req.drive_id)
    d_entity = db.execute(d_stmt).scalar_one_or_none()
    if not d_entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Drive '{req.drive_id}' not found.")

    drive = Drive(
        id=d_entity.id,
        company_id=d_entity.company_id,
        company_name=d_entity.company_name,
        drive_date=d_entity.drive_date,
        ctc_lpa=d_entity.ctc_lpa,
        fixed_pay_lpa=d_entity.ctc_lpa,
    )

    # 3. Determine Policy
    if req.override_policy:
        try:
            policy = CollegeOfferPolicy(**req.override_policy)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid override policy: {e}")
    elif req.policy_id:
        catalog = {
            STRICT_ONE_OFFER_POLICY.id: STRICT_ONE_OFFER_POLICY,
            PROGRESSIVE_MULTIPLIER_POLICY.id: PROGRESSIVE_MULTIPLIER_POLICY,
            TIERED_QUOTA_POLICY.id: TIERED_QUOTA_POLICY,
        }
        policy = catalog.get(req.policy_id, _active_policy)
    else:
        policy = _active_policy

    ref_date = req.as_of_date or drive.drive_date

    # 4. Run Policy Check
    pol_res = policy_check(student=student, drive=drive, policy=policy, as_of=ref_date)

    # 5. Run Academic Rule Check
    rules: list[RuleNode] = []
    latest_req = d_entity.requirement_versions[0] if d_entity.requirement_versions else None
    if latest_req:
        if latest_req.min_cgpa > 0:
            rules.append(CGPAMinRule(id="rule_cgpa", min_cgpa=latest_req.min_cgpa))
        if latest_req.min_tenth_percentage > 0:
            rules.append(PercentageMinRule(id="rule_10th", qualification="10th", min_percentage=latest_req.min_tenth_percentage))
        if latest_req.min_twelfth_percentage:
            rules.append(PercentageMinRule(id="rule_12th", qualification="12th", min_percentage=latest_req.min_twelfth_percentage))
        if latest_req.allowed_branches_json:
            rules.append(BranchInRule(id="rule_branches", allowed_branches=latest_req.allowed_branches_json))
        if latest_req.max_active_backlogs is not None:
            rules.append(ActiveBacklogsMaxRule(id="rule_backlogs", max_backlogs=latest_req.max_active_backlogs))
        if latest_req.max_gap_years is not None:
            rules.append(GapYearsMaxRule(id="rule_gap", max_gap_years=latest_req.max_gap_years))

    rule_set = RuleSet(id=f"rs_{d_entity.id}", name=f"{d_entity.company_name} Criteria", rules=rules)
    evaluator = EligibilityEvaluator()
    acad_res = evaluator.evaluate(student, rule_set, drive_id=d_entity.id, as_of_date=ref_date)

    # 6. Combined Status
    acad_ok = acad_res.status == EligibilityStatus.ELIGIBLE
    pol_ok = pol_res.status == PolicyCheckStatus.ALLOWED

    if acad_ok and pol_ok:
        combined_status = "ELIGIBLE"
    elif not pol_ok:
        combined_status = "POLICY_BLOCKED"
    elif acad_res.status == EligibilityStatus.FLAGGED:
        combined_status = "NEEDS_REVIEW"
    else:
        combined_status = "ACADEMICALLY_INELIGIBLE"

    return {
        "student": {
            "id": student.id,
            "roll_no": student.roll_no,
            "name": student.name,
            "branch": student.branch,
            "cgpa": student.cgpa,
            "tenth_percentage": student.tenth_percentage,
            "twelfth_percentage": student.twelfth_percentage,
            "diploma_percentage": student.diploma_percentage,
            "active_backlogs": len(student.active_backlogs),
            "history_backlogs": len(student.backlogs),
            "existing_offers": [
                {
                    "company": o.company,
                    "ctc_lpa": o.ctc_lpa,
                    "fixed_pay_lpa": o.fixed_pay_lpa,
                    "offer_date": o.offer_date.isoformat(),
                    "source": o.source.value,
                    "status": o.status.value,
                    "is_dream": o.is_dream,
                }
                for o in student.existing_offers
            ],
        },
        "drive": {
            "id": drive.id,
            "company_name": drive.company_name,
            "drive_date": drive.drive_date.isoformat(),
            "ctc_lpa": drive.ctc_lpa,
            "fixed_pay_lpa": getattr(drive, "fixed_pay_lpa", None),
        },
        "policy_used": {
            "id": policy.id,
            "name": policy.name,
            "max_total_offers": policy.max_total_offers,
            "max_dream_offers": policy.max_dream_offers,
            "dream_threshold_lpa": policy.dream_threshold_lpa,
            "allow_upgrade_to_dream": policy.allow_upgrade_to_dream,
            "upgrade_ctc_multiplier": policy.upgrade_ctc_multiplier,
            "threshold_basis": policy.threshold_basis.value,
            "is_threshold_inclusive": policy.is_threshold_inclusive,
            "count_off_campus_offers": policy.count_off_campus_offers,
            "count_rejected_offers": policy.count_rejected_offers,
            "count_revoked_offers": policy.count_revoked_offers,
            "cooling_period_days": policy.cooling_period_days,
        },
        "policy_decision": {
            "status": pol_res.status.value,
            "clause_id": pol_res.clause_id,
            "plain_english_reason": pol_res.plain_english_reason,
            "what_would_unblock": pol_res.what_would_unblock,
            "countable_offers_count": pol_res.countable_offers_count,
            "highest_current_ctc_lpa": pol_res.highest_current_ctc_lpa,
        },
        "academic_decision": {
            "status": acad_res.status.value,
            "overall_student_reason": acad_res.overall_student_reason,
            "passed_rules": [r.model_dump() for r in acad_res.passed_rules],
            "failed_rules": [r.model_dump() for r in acad_res.failed_rules],
            "data_snapshot_hash": acad_res.data_snapshot_hash,
        },
        "combined_status": combined_status,
    }
'''

code += simulate_endpoint
policy_routes_path.write_text(code, encoding="utf-8")
print("Added simulation endpoint to policy_routes.py")
