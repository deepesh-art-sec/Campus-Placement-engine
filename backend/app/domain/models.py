"""
Domain models for Placement Eligibility, Audit & Scheduling Engine.
PURE DOMAIN: No database, I/O, or framework dependencies.
All models are validated using Pydantic v2.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.domain.exceptions import ProtectedAttributeViolationError

# ---------------------------------------------------------
# Enums
# ---------------------------------------------------------

class BacklogStatus(StrEnum):
    ACTIVE = "active"
    CLEARED = "cleared"


class OfferSource(StrEnum):
    ON_CAMPUS = "on_campus"
    OFF_CAMPUS = "off_campus"


class OfferStatus(StrEnum):
    OFFERED = "offered"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    REVOKED = "revoked"


class DriveMode(StrEnum):
    ON_CAMPUS = "on_campus"
    VIRTUAL = "virtual"
    HYBRID = "hybrid"


class DriveStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RoundType(StrEnum):
    ONLINE_TEST = "online_test"
    TECHNICAL_INTERVIEW = "technical_interview"
    HR_INTERVIEW = "hr_interview"
    GROUP_DISCUSSION = "group_discussion"
    MANAGERIAL_INTERVIEW = "managerial_interview"


class EligibilityStatus(StrEnum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    FLAGGED = "flagged"


# ---------------------------------------------------------
# Protected Demographics
# Note: Stored for institutional records, but explicitly blocked
# from being referenced in any eligibility rule evaluation.
# ---------------------------------------------------------

PROTECTED_ATTRIBUTES = frozenset({"gender", "caste", "religion", "category", "demographics"})


class ProtectedDemographics(BaseModel):
    model_config = ConfigDict(frozen=True)

    gender: str | None = None
    caste: str | None = None
    religion: str | None = None
    category: str | None = None  # e.g., GEN, OBC, SC, ST, EWS


# ---------------------------------------------------------
# Student Sub-records
# ---------------------------------------------------------

class BacklogRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    subject: str
    semester: int = Field(ge=1, le=12)
    status: BacklogStatus
    cleared_on: date | None = None

    @model_validator(mode="after")
    def validate_cleared_date(self) -> BacklogRecord:
        if self.status == BacklogStatus.CLEARED and self.cleared_on is None:
            # If cleared, cleared_on is strongly recommended/tracked
            pass
        return self


class OfferRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str | None = None
    company: str
    ctc_lpa: float = Field(ge=0.0)
    fixed_pay_lpa: float | None = Field(default=None, ge=0.0)
    offer_date: date
    source: OfferSource = OfferSource.ON_CAMPUS
    is_dream: bool = False
    status: OfferStatus = OfferStatus.ACCEPTED


class GapYearRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    start_year: int
    end_year: int
    duration_years: int = Field(ge=1)
    reason: str
    phase: str = "general"  # e.g., 'between_12th_and_degree', 'during_degree'


class EducationTimelineEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    qualification: str  # '10th', '12th', 'Diploma', 'Undergraduate', 'Postgraduate'
    institution: str
    board_or_university: str
    start_year: int
    end_year: int
    percentage: float | None = Field(default=None, ge=0.0, le=100.0)
    cgpa: float | None = Field(default=None, ge=0.0, le=10.0)


# ---------------------------------------------------------
# Student Aggregate
# ---------------------------------------------------------

class Student(BaseModel):
    model_config = ConfigDict(frozen=False)

    id: str
    roll_no: str
    name: str
    email: str
    branch: str
    program: str = "B.Tech"
    semester_sgpa: dict[int, float] = Field(default_factory=dict)
    cgpa: float = Field(ge=0.0, le=10.0)
    tenth_percentage: float = Field(ge=0.0, le=100.0)
    twelfth_percentage: float | None = Field(default=None, ge=0.0, le=100.0)
    diploma_percentage: float | None = Field(default=None, ge=0.0, le=100.0)
    date_of_birth: date
    education_timeline: list[EducationTimelineEntry] = Field(default_factory=list)
    gap_years: list[GapYearRecord] = Field(default_factory=list)
    backlogs: list[BacklogRecord] = Field(default_factory=list)
    existing_offers: list[OfferRecord] = Field(default_factory=list)
    protected_demographics: ProtectedDemographics | None = None
    version: int = 1

    @property
    def active_backlogs(self) -> list[BacklogRecord]:
        return [b for b in self.backlogs if b.status == BacklogStatus.ACTIVE]

    @property
    def cleared_backlogs(self) -> list[BacklogRecord]:
        return [b for b in self.backlogs if b.status == BacklogStatus.CLEARED]

    def has_active_backlogs(self, as_of: date | None = None) -> bool:
        if as_of is None:
            return len(self.active_backlogs) > 0
        # If checked as of a historical date, consider backlogs that were cleared AFTER as_of as active as of that date
        for b in self.backlogs:
            if b.status == BacklogStatus.ACTIVE:
                return True
            if b.status == BacklogStatus.CLEARED and b.cleared_on and b.cleared_on > as_of:
                return True
        return False

    def active_backlog_count(self, as_of: date | None = None) -> int:
        if as_of is None:
            return len(self.active_backlogs)
        count = 0
        for b in self.backlogs:
            if b.status == BacklogStatus.ACTIVE:
                count += 1
            elif b.status == BacklogStatus.CLEARED and b.cleared_on and b.cleared_on > as_of:
                count += 1
        return count

    def history_backlog_count(self) -> int:
        return len(self.backlogs)

    def total_gap_years(self) -> int:
        if self.gap_years:
            return sum(g.duration_years for g in self.gap_years)
        # Infer from timeline if available
        if len(self.education_timeline) >= 2:
            sorted_entries = sorted(self.education_timeline, key=lambda e: e.start_year)
            inferred_gaps = 0
            for i in range(len(sorted_entries) - 1):
                gap = sorted_entries[i + 1].start_year - sorted_entries[i].end_year
                if gap > 0:
                    inferred_gaps += gap
            return inferred_gaps
        return 0

    def active_accepted_offers(self) -> list[OfferRecord]:
        return [o for o in self.existing_offers if o.status in (OfferStatus.ACCEPTED, OfferStatus.OFFERED)]

    def highest_current_ctc(self) -> float:
        offers = self.active_accepted_offers()
        if not offers:
            return 0.0
        return max(o.ctc_lpa for o in offers)


# ---------------------------------------------------------
# Company & Drive
# ---------------------------------------------------------

class Company(BaseModel):
    id: str
    name: str
    industry: str | None = None
    tier: str | None = "Standard"  # e.g., "Tier 1", "Tier 2", "Dream", "Super Dream"
    website: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1


class DriveRound(BaseModel):
    model_config = ConfigDict(frozen=True)

    round_number: int
    name: str
    round_type: RoundType
    duration_minutes: int = 60


class Panel(BaseModel):
    id: str
    drive_id: str
    name: str
    interviewer_names: list[str] = Field(default_factory=list)
    room_id: str | None = None


# ---------------------------------------------------------
# Drive Requirement Set (Versioned & Explainable)
# ---------------------------------------------------------

class RequirementSet(BaseModel):
    id: str
    drive_id: str
    version_number: int = 1
    raw_source_text: str | None = None
    parse_confidence: float = 1.0
    min_cgpa: float = Field(default=0.0, ge=0.0, le=10.0)
    min_tenth_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    min_twelfth_percentage: float | None = Field(default=None, ge=0.0, le=100.0)
    min_diploma_percentage: float | None = Field(default=None, ge=0.0, le=100.0)
    allowed_branches: list[str] = Field(default_factory=list)  # Empty means all branches eligible
    allowed_programs: list[str] = Field(default_factory=list)  # Empty means all programs eligible
    max_active_backlogs: int = Field(default=0, ge=0)
    allow_history_backlogs: bool = True
    max_history_backlogs: int | None = None
    max_gap_years: int | None = None
    allow_gap_during_degree: bool = False
    custom_rules: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @model_validator(mode="after")
    def guard_protected_attributes(self) -> RequirementSet:
        """
        STRICT REQUIREMENT: Protected demographic attributes (gender, caste, religion, category)
        MUST NOT be usable by any eligibility rule.
        """
        for field in PROTECTED_ATTRIBUTES:
            if field in self.custom_rules:
                raise ProtectedAttributeViolationError(
                    f"Rule violation: '{field}' is a protected demographic attribute and strictly prohibited in eligibility criteria."
                )
        return self


class Drive(BaseModel):
    id: str
    company_id: str
    company_name: str
    drive_date: date
    mode: DriveMode = DriveMode.ON_CAMPUS
    ctc_lpa: float = Field(ge=0.0)
    fixed_pay_lpa: float | None = None
    is_dream: bool = False
    status: DriveStatus = DriveStatus.DRAFT
    rounds: list[DriveRound] = Field(default_factory=list)
    panels: list[Panel] = Field(default_factory=list)
    requirements: RequirementSet | None = None
    requirement_versions: list[RequirementSet] = Field(default_factory=list)
    version: int = 1


# ---------------------------------------------------------
# Offer Policy Model (College Placement Rules)
# ---------------------------------------------------------

class OfferPolicy(BaseModel):
    id: str
    name: str
    version: int = 1
    max_offers_per_student: int = 1
    dream_tier_ctc_lpa: float = 10.0
    super_dream_tier_ctc_lpa: float = 20.0
    allow_dream_upgrade: bool = True
    upgrade_ctc_multiplier: float = 1.5  # Next offer must be >= current_ctc * multiplier
    strict_backlog_cutoff: bool = True  # Backlog must be cleared strictly before drive date
    allow_multiple_offers_if_different_tiers: bool = True
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------
# Eligibility Run & Decision
# ---------------------------------------------------------

class EligibilityDecision(BaseModel):
    student_id: str
    student_roll_no: str
    student_name: str
    drive_id: str
    run_id: str
    status: EligibilityStatus
    reasons: list[str] = Field(default_factory=list)
    rule_ids_triggered: list[str] = Field(default_factory=list)
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------
# Scheduling Models
# ---------------------------------------------------------

class Room(BaseModel):
    id: str
    name: str
    building: str
    capacity: int = Field(ge=1)
    has_computers: bool = False
    is_active: bool = True


class Slot(BaseModel):
    id: str
    schedule_id: str
    drive_id: str
    round_number: int
    student_id: str
    room_id: str
    panel_id: str | None = None
    start_time: datetime
    end_time: datetime


class Schedule(BaseModel):
    id: str
    name: str
    version: int = 1
    drive_ids: list[str] = Field(default_factory=list)
    slots: list[Slot] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------
# Audit & Event Sourcing
# ---------------------------------------------------------

class Event(BaseModel):
    id: str
    aggregate_type: str  # 'student', 'drive', 'policy', 'eligibility', 'schedule'
    aggregate_id: str
    event_type: str      # e.g., 'STUDENT_IMPORTED', 'RULE_REVISED', 'POLICY_UPDATED'
    actor: str           # User roll/email or 'SYSTEM'
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    payload: dict[str, Any] = Field(default_factory=dict)
