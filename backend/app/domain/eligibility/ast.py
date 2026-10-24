"""
Typed Abstract Syntax Tree (AST) for Placement Eligibility Rules.
Human-readable, form-editable, and pure domain.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.domain.exceptions import ProtectedAttributeViolationError

PROTECTED_FIELDS = frozenset({"gender", "caste", "religion", "category", "demographics"})


class RuleSeverity(StrEnum):
    HARD = "hard"         # Hard exclusion: failure makes student ineligible
    ADVISORY = "advisory" # Advisory: flags note or review without automatic disqualification


class BaseRuleNode(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    severity: RuleSeverity = RuleSeverity.HARD
    description: str = ""

    def to_plain_english(self) -> str:
        return self.description or f"Rule {self.id}"


class CGPAMinRule(BaseRuleNode):
    type: Literal["cgpa_min"] = "cgpa_min"
    min_cgpa: float = Field(ge=0.0, le=10.0)
    scale: float = 10.0
    allow_rounding: bool = False  # False means 6.995 is strictly < 7.0

    def to_plain_english(self) -> str:
        rounding_note = " (strict cut-off, no rounding)" if not self.allow_rounding else " (rounded to nearest 0.1)"
        return f"CGPA must be at least {self.min_cgpa:.2f} on a {self.scale:.1f} scale{rounding_note}."


class PercentageMinRule(BaseRuleNode):
    type: Literal["percentage_min"] = "percentage_min"
    qualification: str  # "10th", "12th", "diploma", "12th_or_diploma"
    min_percentage: float = Field(ge=0.0, le=100.0)

    def to_plain_english(self) -> str:
        qual_label = "12th or Diploma" if self.qualification == "12th_or_diploma" else self.qualification
        return f"{qual_label} aggregate percentage must be at least {self.min_percentage:.2f}%."


class BranchInRule(BaseRuleNode):
    type: Literal["branch_in"] = "branch_in"
    allowed_branches: list[str] = Field(min_length=1)

    def to_plain_english(self) -> str:
        return f"Branch must be one of: {', '.join(self.allowed_branches)}."


class ActiveBacklogsMaxRule(BaseRuleNode):
    type: Literal["active_backlogs_max"] = "active_backlogs_max"
    max_backlogs: int = Field(default=0, ge=0)
    reference_date_type: str = "drive_date"  # "drive_date" or "evaluation_date"

    def to_plain_english(self) -> str:
        if self.max_backlogs == 0:
            return "Must have 0 active/standing backlogs as of the drive date."
        return f"Maximum {self.max_backlogs} active backlog(s) permitted as of the drive date."


class HistoricalBacklogsMaxRule(BaseRuleNode):
    type: Literal["historical_backlogs_max"] = "historical_backlogs_max"
    max_history: int = Field(default=0, ge=0)

    def to_plain_english(self) -> str:
        if self.max_history == 0:
            return "Strictly zero historical backlogs (clean academic history with no backlogs throughout)."
        return f"Maximum {self.max_history} total backlogs allowed across all semesters."


class GapYearsMaxRule(BaseRuleNode):
    type: Literal["gap_years_max"] = "gap_years_max"
    max_gap_years: int = Field(default=0, ge=0)
    phase: str = "any"  # "any", "between_12th_and_degree", "during_degree"

    def to_plain_english(self) -> str:
        phase_str = f" ({self.phase})" if self.phase != "any" else ""
        if self.max_gap_years == 0:
            return f"No education gap years permitted{phase_str}."
        return f"Maximum {self.max_gap_years} year(s) of education gap permitted{phase_str}."


class AgeMaxRule(BaseRuleNode):
    type: Literal["age_max"] = "age_max"
    max_age_years: float = Field(ge=15.0, le=60.0)

    def to_plain_english(self) -> str:
        return f"Age must not exceed {self.max_age_years:.1f} years as of the drive date."


class SemesterMinRule(BaseRuleNode):
    type: Literal["semester_min"] = "semester_min"
    min_semester: int = Field(ge=1, le=12)

    def to_plain_english(self) -> str:
        return f"Student must currently be in semester {self.min_semester} or above."


class ProgramInRule(BaseRuleNode):
    type: Literal["program_in"] = "program_in"
    allowed_programs: list[str] = Field(min_length=1)

    def to_plain_english(self) -> str:
        return f"Degree program must be in: {', '.join(self.allowed_programs)}."


class CustomFieldRule(BaseRuleNode):
    type: Literal["custom_field"] = "custom_field"
    field_name: str
    operator: str  # "eq", "gte", "lte", "in"
    expected_value: Any

    @model_validator(mode="after")
    def guard_protected_attributes(self) -> CustomFieldRule:
        if self.field_name.lower() in PROTECTED_FIELDS:
            raise ProtectedAttributeViolationError(
                f"Rule violation: '{self.field_name}' is a protected demographic attribute and strictly prohibited."
            )
        return self

    def to_plain_english(self) -> str:
        return f"Field '{self.field_name}' must satisfy '{self.operator}' {self.expected_value}."


# Composite Boolean Nodes
class AndRule(BaseRuleNode):
    type: Literal["and"] = "and"
    rules: list[RuleNode]

    def to_plain_english(self) -> str:
        sub = [r.to_plain_english() for r in self.rules]
        return f"All of the following must be satisfied: ({'; '.join(sub)})"


class OrRule(BaseRuleNode):
    type: Literal["or"] = "or"
    rules: list[RuleNode]

    def to_plain_english(self) -> str:
        sub = [r.to_plain_english() for r in self.rules]
        return f"At least one of the following must be satisfied: ({' OR '.join(sub)})"


class NotRule(BaseRuleNode):
    type: Literal["not"] = "not"
    rule: RuleNode

    def to_plain_english(self) -> str:
        return f"Must NOT satisfy: {self.rule.to_plain_english()}"


RuleNode = Annotated[
    CGPAMinRule | PercentageMinRule | BranchInRule | ActiveBacklogsMaxRule | HistoricalBacklogsMaxRule | GapYearsMaxRule | AgeMaxRule | SemesterMinRule | ProgramInRule | CustomFieldRule | AndRule | OrRule | NotRule,
    Field(discriminator="type"),
]

AndRule.model_rebuild()
OrRule.model_rebuild()
NotRule.model_rebuild()


class RuleSet(BaseModel):
    id: str
    name: str
    company_id: str | None = None
    company_name: str | None = None
    version: int = 1
    rules: list[RuleNode] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_plain_english(self) -> list[str]:
        return [rule.to_plain_english() for rule in self.rules]
