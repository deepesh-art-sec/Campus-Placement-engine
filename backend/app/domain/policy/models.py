"""
College Offer Policy Models.
Pure domain logic: No database or network I/O dependencies.
Typed JSON AST, renderable as plain English, and form-editable.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PolicyCheckStatus(StrEnum):
    ALLOWED = "allowed"
    BLOCKED = "blocked"
    NEEDS_REVIEW = "needs_review"


class ThresholdBasis(StrEnum):
    CTC = "ctc"
    FIXED_PAY = "fixed_pay"


class DateTriggerType(StrEnum):
    OFFER_DATE = "offer_date"
    ACCEPTANCE_DATE = "acceptance_date"


class PolicyTier(BaseModel):
    model_config = ConfigDict(frozen=True)

    tier_name: str  # e.g., "Standard", "Dream", "Super Dream"
    min_ctc_lpa: float = Field(ge=0.0)
    max_ctc_lpa: float | None = Field(default=None, ge=0.0)
    max_offers_allowed: int = Field(default=1, ge=1)


class CollegeOfferPolicy(BaseModel):
    """
    Comprehensive, configurable placement offer policy model.
    Encapsulates all collegiate placement rules and ambiguous interpretations as explicit toggles.
    """
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    version: int = 1
    description: str = ""

    # Quota constraints
    max_total_offers: int = Field(default=1, ge=1)
    max_dream_offers: int = Field(default=1, ge=0)

    # Dream company exception rules
    dream_threshold_lpa: float = Field(default=10.0, ge=0.0)
    super_dream_threshold_lpa: float = Field(default=20.0, ge=0.0)
    allow_upgrade_to_dream: bool = True
    upgrade_ctc_multiplier: float = Field(default=1.0, ge=1.0)  # e.g., 1.5x current CTC

    # Configurable Interpretation Toggles (resolving real-world ambiguities)
    threshold_basis: ThresholdBasis = ThresholdBasis.CTC
    is_threshold_inclusive: bool = True  # True: CTC >= threshold; False: CTC > threshold
    count_off_campus_offers: bool = True
    count_rejected_offers: bool = False
    count_revoked_offers: bool = False
    date_trigger_type: DateTriggerType = DateTriggerType.OFFER_DATE

    # Time boundaries & cooling
    cooling_period_days: int = Field(default=0, ge=0)
    effective_from: date | None = None
    effective_to: date | None = None

    # Multi-tier configuration
    tiers: list[PolicyTier] = Field(default_factory=list)
    custom_clauses: dict[str, Any] = Field(default_factory=dict)

    def to_plain_english(self) -> list[str]:
        clauses = []
        # Max offers clause
        if self.max_total_offers == 1:
            clauses.append("Core Policy: 'One Student, One Offer' — students are de-registered upon securing an offer.")
        else:
            clauses.append(f"Core Policy: Students may hold a maximum of {self.max_total_offers} offers across the season.")

        # Dream company exception
        basis_label = "Total CTC" if self.threshold_basis == ThresholdBasis.CTC else "Fixed Base Salary"
        inclusive_str = "inclusive (>=)" if self.is_threshold_inclusive else "strictly above (>)"
        if self.allow_upgrade_to_dream:
            upgrade_msg = f"Dream Exception: Students holding an offer may participate in Dream drives where {basis_label} is {inclusive_str} {self.dream_threshold_lpa:.1f} LPA."
            if self.upgrade_ctc_multiplier > 1.0:
                upgrade_msg += f" (Next offer must also be at least {self.upgrade_ctc_multiplier:.1f}x the existing offer CTC)."
            clauses.append(upgrade_msg)
            if self.max_dream_offers > 0:
                clauses.append(f"Dream Quota: A student can secure at most {self.max_dream_offers} Dream offer(s).")
        else:
            clauses.append("No upgrades permitted: First offer locks the student permanently.")

        # Off-campus & status toggles
        off_campus_str = "ARE counted against your offer quota" if self.count_off_campus_offers else "are NOT counted"
        clauses.append(f"Off-Campus Policy: Off-campus offers {off_campus_str}.")

        revoked_str = "do NOT count once official revocation is verified" if not self.count_revoked_offers else "continue to count"
        clauses.append(f"Revocation Policy: Revoked offers {revoked_str}.")

        if self.cooling_period_days > 0:
            clauses.append(f"Cooling Window: A mandatory {self.cooling_period_days}-day cooling window applies between receiving an offer and appearing in subsequent drives.")

        return clauses
