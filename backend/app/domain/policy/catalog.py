"""
Canonical College Placement Offer Policies Catalog.
Provides standard, institutional-grade policy definitions with versioning and unambiguous semantics.
"""

from __future__ import annotations

from backend.app.domain.policy.models import (
    CollegeOfferPolicy,
    DateTriggerType,
    PolicyTier,
    ThresholdBasis,
)

# Policy 1: Strict One-Offer Policy with Dream Tier Exception
STRICT_ONE_OFFER_POLICY = CollegeOfferPolicy(
    id="policy-001-strict-one-offer",
    name="Strict One-Offer with Dream Tier Exception",
    version=1,
    description="Standard collegiate policy: Max 1 offer per student. Exception granted for Dream companies offering >= 10.0 LPA.",
    max_total_offers=1,
    max_dream_offers=1,
    dream_threshold_lpa=10.0,
    super_dream_threshold_lpa=20.0,
    allow_upgrade_to_dream=True,
    upgrade_ctc_multiplier=1.0,
    threshold_basis=ThresholdBasis.CTC,
    is_threshold_inclusive=True,  # Exactly 10.0 LPA is treated as Dream
    count_off_campus_offers=True,
    count_rejected_offers=False,
    count_revoked_offers=False,
    date_trigger_type=DateTriggerType.OFFER_DATE,
    cooling_period_days=0,
)

# Policy 2: Progressive Salary Multiplier Policy (1.5x Rule)
PROGRESSIVE_MULTIPLIER_POLICY = CollegeOfferPolicy(
    id="policy-002-progressive-multiplier",
    name="Progressive Salary Multiplier Policy (1.5x Rule)",
    version=1,
    description="Students may secure up to 2 offers, provided each subsequent offer is at least 1.5x the CTC of the existing offer.",
    max_total_offers=2,
    max_dream_offers=2,
    dream_threshold_lpa=12.0,
    super_dream_threshold_lpa=24.0,
    allow_upgrade_to_dream=True,
    upgrade_ctc_multiplier=1.5,  # Must be >= 1.5x existing offer
    threshold_basis=ThresholdBasis.CTC,
    is_threshold_inclusive=True,
    count_off_campus_offers=True,
    count_rejected_offers=False,
    count_revoked_offers=False,
    date_trigger_type=DateTriggerType.OFFER_DATE,
    cooling_period_days=0,
)

# Policy 3: Tier-Based Quota Policy (Standard, Dream, Super-Dream)
TIERED_QUOTA_POLICY = CollegeOfferPolicy(
    id="policy-003-tiered-quota",
    name="Tier-Based Quota Policy (Standard, Dream, Super-Dream)",
    version=1,
    description="Students may secure at most 1 offer in each tier: Standard (< 8 LPA), Dream (8-18 LPA), and Super-Dream (> 18 LPA).",
    max_total_offers=3,
    max_dream_offers=2,
    dream_threshold_lpa=8.0,
    super_dream_threshold_lpa=18.0,
    allow_upgrade_to_dream=True,
    upgrade_ctc_multiplier=1.0,
    threshold_basis=ThresholdBasis.CTC,
    is_threshold_inclusive=True,
    count_off_campus_offers=False,  # Deliberate choice: off-campus does not consume campus quota in Policy 3
    count_rejected_offers=False,
    count_revoked_offers=False,
    date_trigger_type=DateTriggerType.OFFER_DATE,
    cooling_period_days=0,
    tiers=[
        PolicyTier(tier_name="Standard", min_ctc_lpa=0.0, max_ctc_lpa=8.0, max_offers_allowed=1),
        PolicyTier(tier_name="Dream", min_ctc_lpa=8.0, max_ctc_lpa=18.0, max_offers_allowed=1),
        PolicyTier(tier_name="Super-Dream", min_ctc_lpa=18.0, max_ctc_lpa=None, max_offers_allowed=1),
    ],
)
