"""
College Placement Offer Policy Engine.
"""

from backend.app.domain.policy.catalog import (
    PROGRESSIVE_MULTIPLIER_POLICY,
    STRICT_ONE_OFFER_POLICY,
    TIERED_QUOTA_POLICY,
)
from backend.app.domain.policy.checker import (
    PolicyCheckResult,
    StudentComparisonResult,
    compare_students,
    filter_countable_offers,
    policy_check,
)
from backend.app.domain.policy.combined import (
    CombinedDecision,
    CombinedDecisionEvaluator,
)
from backend.app.domain.policy.enforcement import (
    LiveOfferEnforcementEngine,
    OfferLifecycleEvent,
    OfferLifecycleEventType,
    PolicyChangeSet,
    PublishedConflict,
)
from backend.app.domain.policy.models import (
    CollegeOfferPolicy,
    DateTriggerType,
    PolicyCheckStatus,
    PolicyTier,
    ThresholdBasis,
)

__all__ = [
    "CollegeOfferPolicy",
    "CombinedDecision",
    "CombinedDecisionEvaluator",
    "DateTriggerType",
    "LiveOfferEnforcementEngine",
    "OfferLifecycleEvent",
    "OfferLifecycleEventType",
    "PROGRESSIVE_MULTIPLIER_POLICY",
    "PolicyChangeSet",
    "PolicyCheckResult",
    "PolicyCheckStatus",
    "PolicyTier",
    "PublishedConflict",
    "STRICT_ONE_OFFER_POLICY",
    "StudentComparisonResult",
    "TIERED_QUOTA_POLICY",
    "ThresholdBasis",
    "compare_students",
    "filter_countable_offers",
    "policy_check",
]
