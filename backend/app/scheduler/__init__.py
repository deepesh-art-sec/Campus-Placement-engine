"""
Clash-free recruitment drive scheduler using OR-Tools CP-SAT and DSatur heuristic fallback.
"""

from backend.app.scheduler.clash_detector import detect_student_fixed_window_clashes
from backend.app.scheduler.engine import PlacementSchedulerEngine
from backend.app.scheduler.heuristic import DSaturHeuristicScheduler
from backend.app.scheduler.infeasibility import InfeasibilityExplainer
from backend.app.scheduler.models import (
    ClashVerificationResult,
    RoomType,
    ScheduleConfig,
    ScheduleDiff,
    ScheduledItem,
    SchedulerDrive,
    ScheduleResult,
    SchedulerPanel,
    SchedulerRoom,
    SchedulerRound,
    ScheduleStatus,
    StudentClashOption,
    TimeWindow,
)
from backend.app.scheduler.rescheduler import IncrementalRescheduler
from backend.app.scheduler.solver import CpSatPlacementScheduler
from backend.app.scheduler.verifier import verify_schedule

__all__ = [
    "RoomType",
    "ScheduleStatus",
    "TimeWindow",
    "SchedulerRoom",
    "SchedulerPanel",
    "SchedulerRound",
    "SchedulerDrive",
    "ScheduleConfig",
    "ScheduledItem",
    "ClashVerificationResult",
    "StudentClashOption",
    "ScheduleDiff",
    "ScheduleResult",
    "verify_schedule",
    "InfeasibilityExplainer",
    "detect_student_fixed_window_clashes",
    "DSaturHeuristicScheduler",
    "CpSatPlacementScheduler",
    "IncrementalRescheduler",
    "PlacementSchedulerEngine",
]
