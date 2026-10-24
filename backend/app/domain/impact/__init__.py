"""
Change impact preview, what-if simulation, versioning, safeguards, and replay module.
"""

from backend.app.domain.impact.headline import generate_headline
from backend.app.domain.impact.models import (
    ChangeRequest,
    ChangeType,
    DriveVersionState,
    ImpactReport,
    PublishValidationResult,
    RecruiterRosterExport,
    SecondOrderEffect,
    StudentClashImpact,
    StudentImpactDetail,
    StudentNotification,
)
from backend.app.domain.impact.output_queue import OutputQueueService
from backend.app.domain.impact.replay import DecisionReplayer, ReplayExplanation
from backend.app.domain.impact.safeguards import PublishSafeguards
from backend.app.domain.impact.second_order import SecondOrderAnalyzer
from backend.app.domain.impact.what_if import WhatIfEngine

__all__ = [
    "ChangeType",
    "ChangeRequest",
    "StudentImpactDetail",
    "StudentClashImpact",
    "SecondOrderEffect",
    "ImpactReport",
    "DriveVersionState",
    "PublishValidationResult",
    "StudentNotification",
    "RecruiterRosterExport",
    "generate_headline",
    "SecondOrderAnalyzer",
    "WhatIfEngine",
    "PublishSafeguards",
    "OutputQueueService",
    "DecisionReplayer",
    "ReplayExplanation",
]
