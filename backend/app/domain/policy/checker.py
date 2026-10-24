"""
College Offer Policy Checker and Student Dispute Comparison Engine.
Provides deterministic enforcement of collegiate offer policies with clause-level defensibility.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.domain.models import Drive, OfferRecord, OfferSource, OfferStatus, Student
from backend.app.domain.policy.models import (
    CollegeOfferPolicy,
    DateTriggerType,
    PolicyCheckStatus,
    ThresholdBasis,
)


class PolicyCheckResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: PolicyCheckStatus
    clause_id: str
    plain_english_reason: str
    what_would_unblock: str
    policy_id: str
    policy_version: int
    countable_offers_count: int = 0
    highest_current_ctc_lpa: float = 0.0
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


class StudentComparisonResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    drive_id: str
    drive_company: str
    drive_ctc_lpa: float
    student_a_roll_no: str
    student_a_status: PolicyCheckStatus
    student_a_reason: str
    student_a_clause: str
    student_b_roll_no: str
    student_b_status: PolicyCheckStatus
    student_b_reason: str
    student_b_clause: str
    comparative_summary: str


def filter_countable_offers(
    offers: list[OfferRecord],
    policy: CollegeOfferPolicy,
    as_of: date,
) -> list[OfferRecord]:
    """Filters offers based on policy toggles and reference date."""
    countable: list[OfferRecord] = []

    for o in offers:
        # Check revocation
        if o.status == OfferStatus.REVOKED and not policy.count_revoked_offers:
            continue

        # Check rejection
        if o.status == OfferStatus.REJECTED and not policy.count_rejected_offers:
            continue

        # Check off-campus
        if o.source == OfferSource.OFF_CAMPUS and not policy.count_off_campus_offers:
            continue

        # Check date trigger against reference date
        # If offer date is strictly in the future relative to as_of, it has not occurred yet!
        if policy.date_trigger_type == DateTriggerType.OFFER_DATE:
            if o.offer_date > as_of:
                continue

        countable.append(o)

    return countable


def is_dream_offer(ctc_or_fixed: float, policy: CollegeOfferPolicy) -> bool:
    if policy.is_threshold_inclusive:
        return ctc_or_fixed >= policy.dream_threshold_lpa
    return ctc_or_fixed > policy.dream_threshold_lpa


def policy_check(
    student: Student,
    drive: Drive,
    policy: CollegeOfferPolicy,
    as_of: date | None = None,
) -> PolicyCheckResult:
    """
    Evaluates whether a student is allowed to participate in a drive under institutional offer policy.
    Deterministic and pure domain logic.
    """
    ref_date = as_of or drive.drive_date

    # 1. Check policy effective dates if configured
    if policy.effective_from and ref_date < policy.effective_from:
        return PolicyCheckResult(
            status=PolicyCheckStatus.ALLOWED,
            clause_id="CLAUSE-0.1-PRE-EFFECTIVE",
            plain_english_reason=f"Policy {policy.name} is not yet effective as of {ref_date.isoformat()}.",
            what_would_unblock="N/A (policy not active).",
            policy_id=policy.id,
            policy_version=policy.version,
        )

    # 2. Extract and filter countable offers
    countable_offers = filter_countable_offers(student.existing_offers, policy, ref_date)
    offers_count = len(countable_offers)

    # 3. Case A: Zero active countable offers
    if offers_count == 0:
        return PolicyCheckResult(
            status=PolicyCheckStatus.ALLOWED,
            clause_id="CLAUSE-1.0-NO-OFFERS",
            plain_english_reason="Allowed: You currently hold 0 countable offers and are permitted to participate.",
            what_would_unblock="N/A (already permitted).",
            policy_id=policy.id,
            policy_version=policy.version,
            countable_offers_count=0,
            highest_current_ctc_lpa=0.0,
        )

    # Calculate metrics on countable offers
    highest_ctc = max(o.ctc_lpa for o in countable_offers)
    latest_offer = max(countable_offers, key=lambda o: o.offer_date)
    dream_offers = [o for o in countable_offers if is_dream_offer(o.ctc_lpa, policy)]
    dream_count = len(dream_offers)

    # 4. Cooling period check
    if policy.cooling_period_days > 0:
        days_since_offer = (ref_date - latest_offer.offer_date).days
        if days_since_offer < policy.cooling_period_days:
            days_left = policy.cooling_period_days - days_since_offer
            return PolicyCheckResult(
                status=PolicyCheckStatus.BLOCKED,
                clause_id="CLAUSE-3.1-COOLING-PERIOD",
                plain_english_reason=(
                    f"Blocked under Policy Clause 3.1: You received an offer from {latest_offer.company} on {latest_offer.offer_date}. "
                    f"A mandatory {policy.cooling_period_days}-day cooling window is active ({days_left} day(s) remaining)."
                ),
                what_would_unblock=f"Cooling period will expire on {(latest_offer.offer_date).isoformat()}.",
                policy_id=policy.id,
                policy_version=policy.version,
                countable_offers_count=offers_count,
                highest_current_ctc_lpa=highest_ctc,
            )

    # Determine drive qualification metric (CTC or Fixed Pay)
    def get_metric(val_ctc: float, val_fixed: float | None) -> float:
        if policy.threshold_basis == ThresholdBasis.FIXED_PAY and val_fixed is not None:
            return val_fixed
        return val_ctc

    drive_val = get_metric(drive.ctc_lpa, getattr(drive, 'fixed_pay_lpa', None))
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
                break

    # 5. Check upgrade multiplier rule (e.g. 1.5x rule) whenever an existing offer is held
    if offers_count > 0 and policy.upgrade_ctc_multiplier > 1.0:
        required_min_ctc = round(highest_ctc * policy.upgrade_ctc_multiplier, 2)
        if drive.ctc_lpa < required_min_ctc:
            return PolicyCheckResult(
                status=PolicyCheckStatus.BLOCKED,
                clause_id="CLAUSE-2.3-MULTIPLIER-NOT-MET",
                plain_english_reason=(
                    f"Blocked under Policy Clause 2.3: Your current offer from {latest_offer.company} is {highest_ctc:.1f} LPA. "
                    f"Under the {policy.upgrade_ctc_multiplier:.1f}x upgrade policy, any subsequent drive must offer at least {required_min_ctc:.1f} LPA. "
                    f"This drive offers {drive.ctc_lpa:.1f} LPA."
                ),
                what_would_unblock=f"Participation permitted for companies offering >= {required_min_ctc:.1f} LPA.",
                policy_id=policy.id,
                policy_version=policy.version,
                countable_offers_count=offers_count,
                highest_current_ctc_lpa=highest_ctc,
            )

    # 6. Check offer quota
    if offers_count >= policy.max_total_offers:
        # The Dream exception allows a student holding a non-Dream offer to appear for a Dream drive
        can_upgrade = (
            policy.allow_upgrade_to_dream
            and policy.max_total_offers == 1
            and offers_count == 1
            and dream_count < policy.max_dream_offers
            and highest_ctc < policy.dream_threshold_lpa
        )

        if can_upgrade:
            # Check 1: Is the drive a Dream drive?
            if not drive_is_dream:
                inclusive_text = ">=" if policy.is_threshold_inclusive else ">"
                return PolicyCheckResult(
                    status=PolicyCheckStatus.BLOCKED,
                    clause_id="CLAUSE-2.2-DRIVE-BELOW-DREAM-THRESHOLD",
                    plain_english_reason=(
                        f"Blocked under Policy Clause 2.2: You hold an offer from {latest_offer.company} ({latest_offer.ctc_lpa:.1f} LPA). "
                        f"Under the One-Offer policy, you may only appear for Dream companies offering {inclusive_text} {policy.dream_threshold_lpa:.1f} LPA. "
                        f"This drive offers {drive.ctc_lpa:.1f} LPA, which is below the Dream exception threshold ({policy.dream_threshold_lpa:.1f} LPA)."
                    ),
                    what_would_unblock=f"Participation is permitted for drives offering {inclusive_text} {policy.dream_threshold_lpa:.1f} LPA.",
                    policy_id=policy.id,
                    policy_version=policy.version,
                    countable_offers_count=offers_count,
                    highest_current_ctc_lpa=highest_ctc,
                )

            # Check 2: Multiplier check
            required_min_ctc = round(highest_ctc * policy.upgrade_ctc_multiplier, 2)
            if drive.ctc_lpa < required_min_ctc:
                return PolicyCheckResult(
                    status=PolicyCheckStatus.BLOCKED,
                    clause_id="CLAUSE-2.3-MULTIPLIER-NOT-MET",
                    plain_english_reason=(
                        f"Blocked under Policy Clause 2.3: Your current offer from {latest_offer.company} is {highest_ctc:.1f} LPA. "
                        f"Under the {policy.upgrade_ctc_multiplier:.1f}x upgrade policy, the new drive must offer at least {required_min_ctc:.1f} LPA. "
                        f"This drive offers {drive.ctc_lpa:.1f} LPA."
                    ),
                    what_would_unblock=f"Participation permitted for companies offering >= {required_min_ctc:.1f} LPA.",
                    policy_id=policy.id,
                    policy_version=policy.version,
                    countable_offers_count=offers_count,
                    highest_current_ctc_lpa=highest_ctc,
                )

            # Dream upgrade approved!
            return PolicyCheckResult(
                status=PolicyCheckStatus.ALLOWED,
                clause_id="CLAUSE-2.1-DREAM-UPGRADE-PERMITTED",
                plain_english_reason=(
                    f"Allowed under Policy Clause 2.1: Dream exception approved. Drive CTC of {drive.ctc_lpa:.1f} LPA meets "
                    f"the Dream threshold ({policy.dream_threshold_lpa:.1f} LPA) and satisfies the {policy.upgrade_ctc_multiplier:.1f}x upgrade rule over your {highest_ctc:.1f} LPA offer."
                ),
                what_would_unblock="N/A (already permitted).",
                policy_id=policy.id,
                policy_version=policy.version,
                countable_offers_count=offers_count,
                highest_current_ctc_lpa=highest_ctc,
            )

        # Quota reached and upgrade not applicable
        if dream_count >= policy.max_dream_offers and dream_count > 0:
            return PolicyCheckResult(
                status=PolicyCheckStatus.BLOCKED,
                clause_id="CLAUSE-2.4-DREAM-QUOTA-EXHAUSTED",
                plain_english_reason=(
                    f"Blocked under Policy Clause 2.4: You have already secured {dream_count} Dream offer(s) "
                    f"({', '.join(o.company for o in dream_offers)}), which fulfills your maximum permitted Dream quota ({policy.max_dream_offers})."
                ),
                what_would_unblock="Administrative exception granted by the Placement Directorate.",
                policy_id=policy.id,
                policy_version=policy.version,
                countable_offers_count=offers_count,
                highest_current_ctc_lpa=highest_ctc,
            )

        return PolicyCheckResult(
            status=PolicyCheckStatus.BLOCKED,
            clause_id="CLAUSE-1.1-MAX-OFFERS-REACHED",
            plain_english_reason=(
                f"Blocked under Policy Clause 1.1: You have reached the maximum allowed offer quota of {policy.max_total_offers} offer(s) "
                f"({', '.join(f'{o.company} ({o.ctc_lpa} LPA)' for o in countable_offers)})."
            ),
            what_would_unblock="Official offer revocation verified by the Training & Placement Cell.",
            policy_id=policy.id,
            policy_version=policy.version,
            countable_offers_count=offers_count,
            highest_current_ctc_lpa=highest_ctc,
        )

        # No upgrade permitted and quota reached
        return PolicyCheckResult(
            status=PolicyCheckStatus.BLOCKED,
            clause_id="CLAUSE-1.1-MAX-OFFERS-REACHED",
            plain_english_reason=(
                f"Blocked under Policy Clause 1.1: You have reached the maximum allowed offer quota of {policy.max_total_offers} offer(s) "
                f"({', '.join(f'{o.company} ({o.ctc_lpa} LPA)' for o in countable_offers)})."
            ),
            what_would_unblock="Official offer revocation verified by the Training & Placement Cell.",
            policy_id=policy.id,
            policy_version=policy.version,
            countable_offers_count=offers_count,
            highest_current_ctc_lpa=highest_ctc,
        )

    # Count is less than max_total_offers
    return PolicyCheckResult(
        status=PolicyCheckStatus.ALLOWED,
        clause_id="CLAUSE-1.0-WITHIN-OFFER-QUOTA",
        plain_english_reason=f"Allowed: You hold {offers_count} offer(s), which is within your season quota of {policy.max_total_offers}.",
        what_would_unblock="N/A (already permitted).",
        policy_id=policy.id,
        policy_version=policy.version,
        countable_offers_count=offers_count,
        highest_current_ctc_lpa=highest_ctc,
    )


def compare_students(
    student_a: Student,
    student_b: Student,
    drive: Drive,
    policy: CollegeOfferPolicy,
    as_of: date | None = None,
) -> StudentComparisonResult:
    """
    Generates a written comparative explanation for two students regarding the same drive.
    Resolves disputes like: 'Why was my classmate allowed to sit for Company X while I was blocked?'
    """
    res_a = policy_check(student_a, drive, policy, as_of)
    res_b = policy_check(student_b, drive, policy, as_of)

    # Construct plain-English comparative narrative
    if res_a.status == res_b.status:
        summary = (
            f"Both students received the identical policy status ({res_a.status.value.upper()}) "
            f"under Policy '{policy.name}'."
        )
    elif res_a.status == PolicyCheckStatus.BLOCKED and res_b.status == PolicyCheckStatus.ALLOWED:
        summary = (
            f"Student {student_a.name} ({student_a.roll_no}) was BLOCKED while Student {student_b.name} ({student_b.roll_no}) was ALLOWED. "
            f"Explanation: Student {student_a.name} holds {res_a.countable_offers_count} offer(s) (highest CTC: {res_a.highest_current_ctc_lpa:.1f} LPA) "
            f"and triggered {res_a.clause_id} ({res_a.plain_english_reason}). "
            f"In contrast, Student {student_b.name} holds {res_b.countable_offers_count} offer(s) (highest CTC: {res_b.highest_current_ctc_lpa:.1f} LPA), "
            f"satisfying {res_b.clause_id}."
        )
    else:
        summary = (
            f"Student {student_a.name} ({student_a.roll_no}) was {res_a.status.value.upper()} "
            f"while Student {student_b.name} ({student_b.roll_no}) was {res_b.status.value.upper()}."
        )

    return StudentComparisonResult(
        drive_id=drive.id,
        drive_company=drive.company_name,
        drive_ctc_lpa=drive.ctc_lpa,
        student_a_roll_no=student_a.roll_no,
        student_a_status=res_a.status,
        student_a_reason=res_a.plain_english_reason,
        student_a_clause=res_a.clause_id,
        student_b_roll_no=student_b.roll_no,
        student_b_status=res_b.status,
        student_b_reason=res_b.plain_english_reason,
        student_b_clause=res_b.clause_id,
        comparative_summary=summary,
    )
