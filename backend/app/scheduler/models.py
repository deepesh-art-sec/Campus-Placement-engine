"""
Data models for the clash-free placement scheduler.
Includes room specifications, rounds, panels, drives, config parameters, and schedule results.
"""

from __future__ import annotations

import datetime
import uuid
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.app.domain.models import DriveMode, RoundType


class RoomType(StrEnum):
    HALL = "hall"
    LAB = "lab"
    CABIN = "cabin"
    CLASSROOM = "classroom"


class ScheduleStatus(StrEnum):
    OPTIMAL = "optimal"
    FEASIBLE = "feasible"
    FEASIBLE_HEURISTIC = "feasible_heuristic"
    INFEASIBLE = "infeasible"
    TIMEOUT = "timeout"


class TimeWindow(BaseModel):
    """Represents a time interval within a single day or across dates."""
    model_config = ConfigDict(frozen=True)

    start_time: datetime.datetime
    end_time: datetime.datetime

    def overlaps(self, other: TimeWindow) -> bool:
        return self.start_time < other.end_time and other.start_time < self.end_time

    def duration_minutes(self) -> int:
        return int((self.end_time - self.start_time).total_seconds() / 60)


class SchedulerRoom(BaseModel):
    """Physical room on campus available for recruitment rounds."""
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    building: str
    room_type: RoomType = RoomType.CLASSROOM
    capacity: int = Field(ge=1)
    has_computers: bool = False
    is_active: bool = True
    blackout_windows: list[TimeWindow] = Field(default_factory=list)


class SchedulerPanel(BaseModel):
    """Interview panel consisting of company recruiters."""
    model_config = ConfigDict(frozen=True)

    id: str
    drive_id: str
    round_number: int
    name: str
    interviewer_names: list[str] = Field(default_factory=list)
    preferred_room_id: str | None = None


class SchedulerRound(BaseModel):
    """A hiring round (online test, GD, technical interview, HR)."""
    model_config = ConfigDict(frozen=True)

    round_number: int
    name: str
    round_type: RoundType
    duration_minutes: int = Field(ge=15, le=360)
    required_room_type: RoomType | None = None
    requires_computers: bool = False
    is_group_round: bool = False  # True for aptitude/coding tests & GD; False for 1-on-1 interviews
    max_batch_size: int = 100
    panels: list[SchedulerPanel] = Field(default_factory=list)


class SchedulerDrive(BaseModel):
    """A company drive with its rounds and shortlisted eligible students."""
    id: str
    company_name: str
    drive_date: datetime.date
    mode: DriveMode = DriveMode.ON_CAMPUS
    rounds: list[SchedulerRound] = Field(default_factory=list)
    shortlisted_student_ids: list[str] = Field(default_factory=list)
    fixed_window: TimeWindow | None = None  # Fixed time window requested by company
    allowed_date_range: tuple[datetime.date, datetime.date] | None = None


class ScheduleConfig(BaseModel):
    """Configuration parameters and constraint toggles for the scheduling engine."""
    slot_duration_minutes: int = Field(default=15, ge=5, le=60)
    day_start_hour: int = Field(default=9, ge=6, le=12)
    day_end_hour: int = Field(default=18, ge=14, le=23)
    lunch_start_hour: int = Field(default=13, ge=11, le=14)
    lunch_duration_minutes: int = Field(default=60, ge=30, le=120)
    transition_buffer_minutes: int = Field(default=15, ge=0, le=60)
    max_rounds_per_student_per_day: int = Field(default=4, ge=1, le=10)
    solver_time_limit_seconds: float = Field(default=30.0, ge=1.0, le=300.0)
    random_seed: int = 42
    num_workers: int = 4
    allow_heuristic_fallback: bool = True
    stop_after_first_feasible: bool = False


class ScheduledItem(BaseModel):
    """A scheduled slot for one or more students in a room and optional panel."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    schedule_id: str
    drive_id: str
    round_number: int
    round_name: str
    student_ids: list[str] = Field(default_factory=list)
    room_id: str
    room_name: str
    panel_id: str | None = None
    panel_name: str | None = None
    start_time: datetime.datetime
    end_time: datetime.datetime
    is_group_session: bool = False

    def duration_minutes(self) -> int:
        return int((self.end_time - self.start_time).total_seconds() / 60)


class ClashVerificationResult(BaseModel):
    """Audit report produced by the independent verifier."""
    is_valid: bool
    clash_count: int = 0
    student_clashes: list[str] = Field(default_factory=list)
    room_clashes: list[str] = Field(default_factory=list)
    panel_clashes: list[str] = Field(default_factory=list)
    capacity_violations: list[str] = Field(default_factory=list)
    buffer_violations: list[str] = Field(default_factory=list)
    blackout_violations: list[str] = Field(default_factory=list)
    all_violations: list[str] = Field(default_factory=list)

    def summary(self) -> str:
        if self.is_valid:
            return "0 clashes verified"
        return f"{self.clash_count} clashes detected: {len(self.all_violations)} violations"


class StudentClashOption(BaseModel):
    """Actionable conflict alert when students are shortlisted for competing fixed-window drives."""
    student_id: str
    student_name: str
    drive_a_id: str
    drive_a_company: str
    drive_b_id: str
    drive_b_company: str
    overlap_window: str
    suggested_options: list[str] = Field(
        default_factory=lambda: [
            "Reschedule Drive to alternative slot",
            "Split shortlisted students into morning/afternoon batches",
            "Permit student to choose primary drive with recorded preference",
        ]
    )


class ScheduleDiff(BaseModel):
    """Diff report generated during incremental rescheduling."""
    total_slots_before: int
    total_slots_after: int
    moved_slots_count: int
    preserved_slots_count: int
    preserved_percentage: float
    moved_items: list[dict[str, Any]] = Field(default_factory=list)


class ScheduleResult(BaseModel):
    """Final output produced by the scheduling engine."""
    schedule_id: str
    status: ScheduleStatus
    items: list[ScheduledItem] = Field(default_factory=list)
    solver_time_seconds: float = 0.0
    solver_name: str = "cp-sat"  # "cp-sat" or "dsatur-heuristic"
    is_optimal: bool = False
    infeasibility_explanation: str | None = None
    verification: ClashVerificationResult | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
