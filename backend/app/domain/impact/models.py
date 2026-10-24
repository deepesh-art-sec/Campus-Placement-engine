"""
Domain models for what-if simulation, change impact preview, publish safeguards,
second-order effect tracking, output queue, and audit versioning.
"""

from __future__ import annotations

import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.domain.models import RequirementSet
from backend.app.scheduler.models import ScheduledItem


class ChangeType(StrEnum):
    CGPA_CUTOFF = "cgpa_cutoff"
    PERCENTAGE_CUTOFF = "percentage_cutoff"
    BACKLOG_RULE = "backlog_rule"
    BRANCH_ADDED = "branch_added"
    BRANCH_REMOVED = "branch_removed"
    GAP_YEAR = "gap_year"
    POLICY_TOGGLE = "policy_toggle"
    DRIVE_DATE_SHIFT = "drive_date_shift"
    PANEL_COUNT = "panel_count"
    ROOM_UNAVAILABLE = "room_unavailable"
    MANUAL_STUDENT_ADD = "manual_student_add"
    MANUAL_STUDENT_REMOVE = "manual_student_remove"


class ChangeRequest(BaseModel):
    """Encapsulates a proposed what-if modification prior to commit."""
    model_config = ConfigDict(frozen=True)

    change_type: ChangeType
    drive_id: str
    target_field: str | None = None
    old_value: Any = None
    new_value: Any = None
    branch_name: str | None = None
    student_id: str | None = None
    mandatory_reason: str | None = None
    policy_id: str | None = None
    toggle_name: str | None = None
    room_id: str | None = None
    requested_by: str = "TPO_OFFICER"
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    @field_validator("mandatory_reason")
    @classmethod
    def validate_mandatory_reason_for_manual_actions(cls, v: str | None, info: Any) -> str | None:
        values = info.data
        c_type = values.get("change_type")
        if c_type in (ChangeType.MANUAL_STUDENT_ADD, ChangeType.MANUAL_STUDENT_REMOVE):
            if not v or len(v.strip()) < 5:
                raise ValueError("Manual student inclusion or exclusion strictly requires a mandatory rationale of at least 5 characters.")
        return v


class StudentImpactDetail(BaseModel):
    """Detailed record of a student added to or removed from the shortlist."""
    model_config = ConfigDict(frozen=True)

    student_id: str
    student_roll_no: str
    student_name: str
    branch: str
    cgpa: float
    change_type: Literal["added", "removed"]
    reason: str


class StudentClashImpact(BaseModel):
    """Details of a student who experiences a schedule clash due to a proposed change."""
    model_config = ConfigDict(frozen=True)

    student_id: str
    student_roll_no: str
    student_name: str
    conflicting_drive_id: str
    conflicting_drive_name: str
    conflicting_slot_time: str
    details: str


class SecondOrderEffect(BaseModel):
    """
    Traces downstream offer policy interactions triggered across drives.
    Example: Drive A shortlist -> Offer at 12 LPA -> Blocks student from Drive B.
    """
    model_config = ConfigDict(frozen=True)

    student_id: str
    student_name: str
    source_drive_id: str
    source_drive_name: str
    target_drive_id: str
    target_drive_name: str
    causal_chain: str
    clause_cited: str
    action_required: str


class ImpactReport(BaseModel):
    """Comprehensive what-if impact report computed dynamically from live data."""
    change_summary: str
    headline: str
    drive_id: str
    drive_name: str
    students_added_count: int
    students_removed_count: int
    clashes_count: int
    students_added: list[StudentImpactDetail] = Field(default_factory=list)
    students_removed: list[StudentImpactDetail] = Field(default_factory=list)
    newly_clashing_students: list[StudentClashImpact] = Field(default_factory=list)
    schedule_moves_required: list[dict[str, Any]] = Field(default_factory=list)
    second_order_effects: list[SecondOrderEffect] = Field(default_factory=list)
    policy_conflicts: list[str] = Field(default_factory=list)
    generated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


class DriveVersionState(BaseModel):
    """Immutable versioned snapshot of a drive's requirements, shortlist, and schedule."""
    drive_id: str
    version: int
    is_published: bool = False
    published_at: datetime.datetime | None = None
    published_by: str | None = None
    requirements: RequirementSet
    shortlist_student_ids: list[str] = Field(default_factory=list)
    schedule_items: list[ScheduledItem] = Field(default_factory=list)
    audit_hash: str = ""


class PublishValidationResult(BaseModel):
    """Safeguard report verifying eligibility for publication."""
    can_publish: bool
    block_reasons: list[str] = Field(default_factory=list)
    unresolved_reviews: list[str] = Field(default_factory=list)
    unresolved_clashes: list[str] = Field(default_factory=list)
    stale_version_detected: bool = False
    requires_confirmation: bool = True
    impact_summary: str = ""


class StudentNotification(BaseModel):
    """Student-facing status notification generated offline."""
    student_id: str
    student_roll_no: str
    student_email: str
    subject: str
    message: str
    scheduled_slot: str | None = None
    room_name: str | None = None
    panel_name: str | None = None
    generated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


class RecruiterRosterExport(BaseModel):
    """Recruiter roster export prepared offline for campus placement coordinators."""
    drive_id: str
    company_name: str
    drive_date: datetime.date
    total_candidates: int
    csv_content: str
    clipboard_text: str
    generated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
