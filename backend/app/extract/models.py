"""
Data models for requirement extraction, AST translation, review queue, and feedback tracking.
"""

from __future__ import annotations

import datetime
import uuid
from enum import StrEnum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from backend.app.domain.eligibility.ast import (
    ActiveBacklogsMaxRule,
    BranchInRule,
    CGPAMinRule,
    GapYearsMaxRule,
    HistoricalBacklogsMaxRule,
    PercentageMinRule,
    ProgramInRule,
    RuleNode,
    RuleSet,
)
from backend.app.domain.models import DriveMode, RequirementSet, RoundType

T = TypeVar("T")


class ExtractedField(BaseModel, Generic[T]):
    """Represents a single extracted entity with provenance, confidence, and ambiguity flags."""
    model_config = ConfigDict(frozen=True)

    field_name: str
    value: T
    confidence: float = Field(ge=0.0, le=1.0)
    source_sentence: str
    page_number: int | None = 1
    extraction_method: str = "regex_rule"
    is_ambiguous: bool = False
    ambiguity_reason: str | None = None
    is_missing: bool = False


class AmbiguityItem(BaseModel):
    """An ambiguity detected in the announcement that requires officer clarification."""
    model_config = ConfigDict(frozen=True)

    field_name: str
    raw_text: str
    source_sentence: str
    reason: str
    suggested_action: str


class ExtractedRound(BaseModel):
    """A hiring selection round extracted from the recruitment schedule."""
    model_config = ConfigDict(frozen=True)

    round_number: int
    name: str
    round_type: RoundType
    duration_minutes: int = 60
    source_sentence: str


class FieldReviewStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EDITED = "edited"
    REJECTED = "rejected"


class ExtractedFieldReview(BaseModel):
    """Review item presented in the UI review queue for officer acceptance, edit, or rejection."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    field_name: str
    extracted_value: Any
    confidence: float = Field(ge=0.0, le=1.0)
    source_sentence: str
    page_number: int | None = 1
    extraction_method: str = "regex_rule"
    status: FieldReviewStatus = FieldReviewStatus.PENDING
    correction: Any | None = None
    is_ambiguous: bool = False
    ambiguity_reason: str | None = None
    is_missing: bool = False
    officer_notes: str | None = None


class ExtractionFeedback(BaseModel):
    """Audit feedback record storing human corrections to extracted fields."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    announcement_id: str
    field_name: str
    source_text: str
    extracted_value: Any
    corrected_value: Any
    status: FieldReviewStatus
    reviewed_by: str = "TPO_OFFICER"
    reviewed_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


class ExtractedRequirements(BaseModel):
    """
    Complete structured requirement extraction output from an announcement.
    Contains parsed metadata, academic cutoffs, review items, ambiguities, and AST converters.
    """
    # Drive Metadata
    company_name: ExtractedField[str] | None = None
    drive_date: ExtractedField[datetime.date] | None = None
    drive_time: ExtractedField[str] | None = None
    application_deadline: ExtractedField[datetime.date] | None = None
    mode: ExtractedField[DriveMode] | None = None
    ctc_lpa: ExtractedField[float] | None = None
    ctc_min_lpa: ExtractedField[float] | None = None
    ctc_max_lpa: ExtractedField[float] | None = None
    stipend_monthly: ExtractedField[float] | None = None
    role: ExtractedField[str] | None = None
    location: ExtractedField[str] | None = None
    bond_details: ExtractedField[str] | None = None
    rounds: list[ExtractedRound] = Field(default_factory=list)

    # Academic Criteria
    cgpa_min: ExtractedField[float] | None = None
    cgpa_max: ExtractedField[float] | None = None
    tenth_percentage_min: ExtractedField[float] | None = None
    twelfth_percentage_min: ExtractedField[float] | None = None
    diploma_percentage_min: ExtractedField[float] | None = None
    allowed_branches: ExtractedField[list[str]] | None = None
    allowed_programs: ExtractedField[list[str]] | None = None
    batch_year: ExtractedField[int] | None = None
    active_backlogs_max: ExtractedField[int] | None = None
    historical_backlogs_max: ExtractedField[int] | None = None
    gap_years_max: ExtractedField[int] | None = None
    allow_gap_during_degree: ExtractedField[bool] | None = None

    # Skills & Restrictions
    skills_required: ExtractedField[list[str]] | None = None
    experience_required: ExtractedField[str] | None = None
    other_restrictions: ExtractedField[list[str]] | None = None

    # Processing metadata
    page_count: int = 1
    raw_text: str = ""
    source_sentences: list[str] = Field(default_factory=list)
    ambiguities: list[AmbiguityItem] = Field(default_factory=list)
    review_queue: list[ExtractedFieldReview] = Field(default_factory=list)
    overall_confidence: float = 1.0

    def to_rule_set(self, rule_set_id: str, name: str) -> RuleSet:
        """Translates extracted criteria into pure domain Part 2 RuleSet AST."""
        rules: list[RuleNode] = []

        if self.cgpa_min and self.cgpa_min.value > 0.0:
            rules.append(
                CGPAMinRule(
                    id=f"{rule_set_id}_cgpa",
                    min_cgpa=self.cgpa_min.value,
                    scale=10.0,
                    allow_rounding=False,
                    description=f"CGPA cut-off >= {self.cgpa_min.value:.2f}",
                )
            )

        if self.tenth_percentage_min and self.tenth_percentage_min.value > 0.0:
            rules.append(
                PercentageMinRule(
                    id=f"{rule_set_id}_tenth",
                    qualification="10th",
                    min_percentage=self.tenth_percentage_min.value,
                    description=f"10th cut-off >= {self.tenth_percentage_min.value:.1f}%",
                )
            )

        if self.twelfth_percentage_min and self.twelfth_percentage_min.value > 0.0:
            rules.append(
                PercentageMinRule(
                    id=f"{rule_set_id}_twelfth",
                    qualification="12th",
                    min_percentage=self.twelfth_percentage_min.value,
                    description=f"12th cut-off >= {self.twelfth_percentage_min.value:.1f}%",
                )
            )

        if self.allowed_branches and self.allowed_branches.value:
            # "All Branches" means no restrictive branch rule needed
            norm_branches = [b.strip() for b in self.allowed_branches.value]
            if norm_branches != ["All Branches"]:
                rules.append(
                    BranchInRule(
                        id=f"{rule_set_id}_branches",
                        allowed_branches=norm_branches,
                        description=f"Eligible branches: {', '.join(norm_branches)}",
                    )
                )

        if self.active_backlogs_max is not None:
            rules.append(
                ActiveBacklogsMaxRule(
                    id=f"{rule_set_id}_active_backlogs",
                    max_backlogs=self.active_backlogs_max.value,
                    description=f"Max active backlogs: {self.active_backlogs_max.value}",
                )
            )

        if self.historical_backlogs_max is not None:
            rules.append(
                HistoricalBacklogsMaxRule(
                    id=f"{rule_set_id}_history_backlogs",
                    max_history=self.historical_backlogs_max.value,
                    description=f"Max historical backlogs: {self.historical_backlogs_max.value}",
                )
            )

        if self.gap_years_max is not None:
            phase = "between_12th_and_degree" if (
                self.allow_gap_during_degree and not self.allow_gap_during_degree.value
            ) else "any"
            rules.append(
                GapYearsMaxRule(
                    id=f"{rule_set_id}_gap_years",
                    max_gap_years=self.gap_years_max.value,
                    phase=phase,
                    description=f"Max education gap years: {self.gap_years_max.value} ({phase})",
                )
            )

        if self.allowed_programs and self.allowed_programs.value:
            rules.append(
                ProgramInRule(
                    id=f"{rule_set_id}_programs",
                    allowed_programs=self.allowed_programs.value,
                    description=f"Eligible degree programs: {', '.join(self.allowed_programs.value)}",
                )
            )

        return RuleSet(
            id=rule_set_id,
            name=name,
            version=1,
            rules=rules,
            metadata={
                "overall_confidence": self.overall_confidence,
                "company_name": self.company_name.value if self.company_name else None,
                "ctc_lpa": self.ctc_lpa.value if self.ctc_lpa else None,
                "ambiguity_count": len(self.ambiguities),
                "review_queue_count": len(self.review_queue),
            },
        )

    def to_domain_requirement_set(self, drive_id: str) -> RequirementSet:
        """Translates extracted criteria into domain RequirementSet model."""
        norm_branches = []
        if self.allowed_branches and self.allowed_branches.value:
            if self.allowed_branches.value != ["All Branches"]:
                norm_branches = [b.strip() for b in self.allowed_branches.value]

        return RequirementSet(
            id=f"req_{drive_id}",
            drive_id=drive_id,
            version_number=1,
            raw_source_text=self.raw_text,
            parse_confidence=self.overall_confidence,
            min_cgpa=self.cgpa_min.value if self.cgpa_min else 0.0,
            min_tenth_percentage=self.tenth_percentage_min.value if self.tenth_percentage_min else 0.0,
            min_twelfth_percentage=self.twelfth_percentage_min.value if self.twelfth_percentage_min else None,
            min_diploma_percentage=self.diploma_percentage_min.value if self.diploma_percentage_min else None,
            allowed_branches=norm_branches,
            allowed_programs=self.allowed_programs.value if self.allowed_programs else [],
            max_active_backlogs=self.active_backlogs_max.value if self.active_backlogs_max is not None else 0,
            allow_history_backlogs=(self.historical_backlogs_max is None or self.historical_backlogs_max.value > 0),
            max_history_backlogs=self.historical_backlogs_max.value if self.historical_backlogs_max is not None else None,
            max_gap_years=self.gap_years_max.value if self.gap_years_max is not None else None,
            allow_gap_during_degree=self.allow_gap_during_degree.value if self.allow_gap_during_degree else False,
        )
