"""
SQLAlchemy ORM models.
Includes all entities, relationships, foreign keys, indexes, and version columns for optimistic concurrency.
"""

from __future__ import annotations

import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from backend.app.storage.database import Base


class StudentModel(Base):
    __tablename__ = "students"

    id = Column(String(36), primary_key=True)
    roll_no = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    normalized_name = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    branch = Column(String(128), nullable=False, index=True)
    program = Column(String(64), nullable=False, default="B.Tech")
    cgpa = Column(Float, nullable=False)
    tenth_percentage = Column(Float, nullable=False)
    twelfth_percentage = Column(Float, nullable=True)
    diploma_percentage = Column(Float, nullable=True)
    date_of_birth = Column(Date, nullable=False)

    # Protected demographics (NEVER accessed by eligibility rules)
    gender = Column(String(32), nullable=True)
    caste = Column(String(64), nullable=True)
    religion = Column(String(64), nullable=True)
    category = Column(String(32), nullable=True)

    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    def __init__(self, **kwargs):
        if "normalized_name" not in kwargs and "name" in kwargs and kwargs["name"]:
            import re
            kwargs["normalized_name"] = re.sub(r"\s+", " ", kwargs["name"].strip()).lower()
        super().__init__(**kwargs)

    # Relationships
    academic_records = relationship("AcademicRecordModel", back_populates="student", cascade="all, delete-orphan")
    backlogs = relationship("BacklogModel", back_populates="student", cascade="all, delete-orphan")
    gap_years = relationship("GapYearModel", back_populates="student", cascade="all, delete-orphan")
    offers = relationship("OfferModel", back_populates="student", cascade="all, delete-orphan")
    eligibility_decisions = relationship("EligibilityDecisionModel", back_populates="student", cascade="all, delete-orphan")
    applications = relationship("StudentApplicationModel", back_populates="student", cascade="all, delete-orphan")
    slots = relationship("SlotModel", back_populates="student", cascade="all, delete-orphan")


class AcademicRecordModel(Base):
    __tablename__ = "academic_records"

    id = Column(String(36), primary_key=True)
    student_id = Column(String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    semester = Column(Integer, nullable=False)
    sgpa = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("student_id", "semester", name="uq_student_semester"),
    )

    student = relationship("StudentModel", back_populates="academic_records")


class BacklogModel(Base):
    __tablename__ = "backlogs"

    id = Column(String(36), primary_key=True)
    student_id = Column(String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    subject = Column(String(255), nullable=False)
    semester = Column(Integer, nullable=False)
    status = Column(String(32), nullable=False)  # 'active', 'cleared'
    cleared_on = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    student = relationship("StudentModel", back_populates="backlogs")


class GapYearModel(Base):
    __tablename__ = "gap_years"

    id = Column(String(36), primary_key=True)
    student_id = Column(String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    start_year = Column(Integer, nullable=False)
    end_year = Column(Integer, nullable=False)
    duration_years = Column(Integer, nullable=False)
    reason = Column(Text, nullable=False)
    phase = Column(String(64), nullable=False, default="general")
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    student = relationship("StudentModel", back_populates="gap_years")


class OfferModel(Base):
    __tablename__ = "offers"

    id = Column(String(36), primary_key=True)
    student_id = Column(String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    company = Column(String(255), nullable=False)
    ctc_lpa = Column(Float, nullable=False)
    fixed_pay_lpa = Column(Float, nullable=True)
    offer_date = Column(Date, nullable=False)
    source = Column(String(32), nullable=False, default="on_campus")  # 'on_campus', 'off_campus'
    is_dream = Column(Boolean, nullable=False, default=False)
    status = Column(String(32), nullable=False, default="offered")     # 'offered', 'accepted', 'rejected', 'revoked'
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    student = relationship("StudentModel", back_populates="offers")


class CompanyModel(Base):
    __tablename__ = "companies"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    industry = Column(String(128), nullable=True)
    tier = Column(String(64), nullable=True, default="Standard")
    website = Column(String(255), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    drives = relationship("DriveModel", back_populates="company", cascade="all, delete-orphan")


class DriveModel(Base):
    __tablename__ = "drives"

    id = Column(String(36), primary_key=True)
    company_id = Column(String(36), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    company_name = Column(String(255), nullable=False)
    drive_date = Column(Date, nullable=False, index=True)
    mode = Column(String(32), nullable=False, default="on_campus")
    ctc_lpa = Column(Float, nullable=False)
    is_dream = Column(Boolean, nullable=False, default=False)
    status = Column(String(32), nullable=False, default="draft")
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    company = relationship("CompanyModel", back_populates="drives")
    requirement_versions = relationship("DriveRequirementVersionModel", back_populates="drive", cascade="all, delete-orphan")
    panels = relationship("PanelModel", back_populates="drive", cascade="all, delete-orphan")
    eligibility_runs = relationship("EligibilityRunModel", back_populates="drive", cascade="all, delete-orphan")
    eligibility_decisions = relationship("EligibilityDecisionModel", back_populates="drive", cascade="all, delete-orphan")
    applications = relationship("StudentApplicationModel", back_populates="drive", cascade="all, delete-orphan")
    slots = relationship("SlotModel", back_populates="drive", cascade="all, delete-orphan")


class DriveRequirementVersionModel(Base):
    __tablename__ = "drive_requirement_versions"

    id = Column(String(36), primary_key=True)
    drive_id = Column(String(36), ForeignKey("drives.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    raw_source_text = Column(Text, nullable=True)
    parse_confidence = Column(Float, nullable=False, default=1.0)
    min_cgpa = Column(Float, nullable=False, default=0.0)
    min_tenth_percentage = Column(Float, nullable=False, default=0.0)
    min_twelfth_percentage = Column(Float, nullable=True)
    min_diploma_percentage = Column(Float, nullable=True)
    allowed_branches_json = Column(Text, nullable=False, default="[]")
    allowed_programs_json = Column(Text, nullable=False, default="[]")
    max_active_backlogs = Column(Integer, nullable=False, default=0)
    allow_history_backlogs = Column(Boolean, nullable=False, default=True)
    max_history_backlogs = Column(Integer, nullable=True)
    max_gap_years = Column(Integer, nullable=True)
    allow_gap_during_degree = Column(Boolean, nullable=False, default=False)
    custom_rules_json = Column(Text, nullable=True, default="{}")
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("drive_id", "version_number", name="uq_drive_requirement_version"),
    )

    drive = relationship("DriveModel", back_populates="requirement_versions")


class PolicyModel(Base):
    __tablename__ = "policies"

    id = Column(String(36), primary_key=True)
    name = Column(String(128), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    max_offers_per_student = Column(Integer, nullable=False, default=1)
    dream_tier_ctc_lpa = Column(Float, nullable=False, default=10.0)
    super_dream_tier_ctc_lpa = Column(Float, nullable=True, default=20.0)
    allow_dream_upgrade = Column(Boolean, nullable=False, default=True)
    upgrade_ctc_multiplier = Column(Float, nullable=False, default=1.5)
    strict_backlog_cutoff = Column(Boolean, nullable=False, default=True)
    allow_multiple_offers_if_different_tiers = Column(Boolean, nullable=False, default=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_policy_name_version"),
    )


class EligibilityRunModel(Base):
    __tablename__ = "eligibility_runs"

    id = Column(String(36), primary_key=True)
    drive_id = Column(String(36), ForeignKey("drives.id", ondelete="CASCADE"), nullable=False, index=True)
    requirement_version_id = Column(String(36), nullable=False)
    policy_id = Column(String(36), nullable=False)
    executed_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    total_evaluated = Column(Integer, nullable=False, default=0)
    total_eligible = Column(Integer, nullable=False, default=0)
    total_ineligible = Column(Integer, nullable=False, default=0)
    executed_by = Column(String(128), nullable=False, default="SYSTEM")

    drive = relationship("DriveModel", back_populates="eligibility_runs")
    decisions = relationship("EligibilityDecisionModel", back_populates="run", cascade="all, delete-orphan")


class EligibilityDecisionModel(Base):
    __tablename__ = "eligibility_decisions"

    id = Column(String(36), primary_key=True)
    run_id = Column(String(36), ForeignKey("eligibility_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    drive_id = Column(String(36), ForeignKey("drives.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(32), nullable=False)  # 'eligible', 'ineligible', 'flagged'
    reasons_json = Column(Text, nullable=False, default="[]")
    rule_ids_json = Column(Text, nullable=False, default="[]")
    evaluated_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("run_id", "student_id", name="uq_run_student_decision"),
    )

    run = relationship("EligibilityRunModel", back_populates="decisions")
    student = relationship("StudentModel", back_populates="eligibility_decisions")
    drive = relationship("DriveModel", back_populates="eligibility_decisions")


class StudentApplicationModel(Base):
    __tablename__ = "student_applications"

    id = Column(String(36), primary_key=True)
    student_id = Column(String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    drive_id = Column(String(36), ForeignKey("drives.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="applied")  # 'applied', 'withdrawn'
    applied_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    notes = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("student_id", "drive_id", name="uq_student_drive_application"),
    )

    student = relationship("StudentModel", back_populates="applications")
    drive = relationship("DriveModel", back_populates="applications")


class RoomModel(Base):
    __tablename__ = "rooms"

    id = Column(String(36), primary_key=True)
    name = Column(String(128), unique=True, nullable=False, index=True)
    building = Column(String(128), nullable=False)
    capacity = Column(Integer, nullable=False, default=30)
    has_computers = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    panels = relationship("PanelModel", back_populates="room")
    slots = relationship("SlotModel", back_populates="room")


class PanelModel(Base):
    __tablename__ = "panels"

    id = Column(String(36), primary_key=True)
    drive_id = Column(String(36), ForeignKey("drives.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    interviewers_json = Column(Text, nullable=False, default="[]")
    room_id = Column(String(36), ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    drive = relationship("DriveModel", back_populates="panels")
    room = relationship("RoomModel", back_populates="panels")
    slots = relationship("SlotModel", back_populates="panel")


class ScheduleModel(Base):
    __tablename__ = "schedules"

    id = Column(String(36), primary_key=True)
    name = Column(String(128), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    status = Column(String(32), nullable=False, default="draft")
    drive_ids_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    slots = relationship("SlotModel", back_populates="schedule", cascade="all, delete-orphan")


class SlotModel(Base):
    __tablename__ = "slots"

    id = Column(String(36), primary_key=True)
    schedule_id = Column(String(36), ForeignKey("schedules.id", ondelete="CASCADE"), nullable=False, index=True)
    drive_id = Column(String(36), ForeignKey("drives.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    round_number = Column(Integer, nullable=False)
    room_id = Column(String(36), ForeignKey("rooms.id", ondelete="RESTRICT"), nullable=False, index=True)
    panel_id = Column(String(36), ForeignKey("panels.id", ondelete="SET NULL"), nullable=True)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    schedule = relationship("ScheduleModel", back_populates="slots")
    drive = relationship("DriveModel", back_populates="slots")
    student = relationship("StudentModel", back_populates="slots")
    room = relationship("RoomModel", back_populates="slots")
    panel = relationship("PanelModel", back_populates="slots")


class EventModel(Base):
    """Append-only event sourcing table."""
    __tablename__ = "events"

    id = Column(String(36), primary_key=True)
    aggregate_type = Column(String(64), nullable=False, index=True)
    aggregate_id = Column(String(64), nullable=False, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    actor = Column(String(128), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)
    payload_json = Column(Text, nullable=False, default="{}")


class AuditLogModel(Base):
    """Entity-level audit changes table."""
    __tablename__ = "audit_log"

    id = Column(String(36), primary_key=True)
    entity_type = Column(String(64), nullable=False, index=True)
    entity_id = Column(String(64), nullable=False, index=True)
    action = Column(String(32), nullable=False)  # CREATE, UPDATE, DELETE, OVERRIDE
    actor = Column(String(128), nullable=False)
    changes_json = Column(Text, nullable=False, default="{}")
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False, index=True)


class UserModel(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False)  # 'officer', 'coordinator', 'student', 'recruiter_readonly'
    is_active = Column(Boolean, nullable=False, default=True)
    student_id = Column(String(36), ForeignKey("students.id", ondelete="SET NULL"), nullable=True)
    company_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    sessions = relationship("SessionModel", back_populates="user", cascade="all, delete-orphan")


class CompanyExportMappingModel(Base):
    __tablename__ = "company_export_mappings"

    id = Column(String(36), primary_key=True)
    company_id = Column(String(64), nullable=False, unique=True, index=True)
    company_name = Column(String(255), nullable=False)
    sheet_name = Column(String(64), nullable=False, default="Candidates")
    date_format = Column(String(32), nullable=False, default="YYYY-MM-DD")
    column_mappings_json = Column(Text, nullable=False, default="{}")
    column_widths_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)




class SessionModel(Base):
    __tablename__ = "sessions"

    id = Column(String(128), primary_key=True)  # Cryptographic session token
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)

    user = relationship("UserModel", back_populates="sessions")


class CoordinatorRequestModel(Base):
    """Coordinator requests sent to the officer for approval/answers."""
    __tablename__ = "coordinator_requests"

    id = Column(String(36), primary_key=True)
    request_type = Column(String(64), nullable=False, index=True)  # student_data_correction, shortlist_override, rule_doubt, clash_preference, logistics
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    submitted_by = Column(String(128), nullable=False, index=True)
    submitted_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    status = Column(String(32), default="open", nullable=False, index=True)  # open, answered, approved, rejected
    target_id = Column(String(64), nullable=True)  # student_id, drive_id, slot_id
    payload_json = Column(Text, nullable=False, default="{}")
    officer_response = Column(Text, nullable=True)
    officer_name = Column(String(128), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    comments_json = Column(Text, nullable=False, default="[]")


class DriveAttendanceModel(Base):
    """Day-of-drive attendance log per student & room."""
    __tablename__ = "drive_attendance"

    id = Column(String(36), primary_key=True)
    drive_id = Column(String(36), ForeignKey("drives.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    slot_id = Column(String(36), nullable=True)
    room_name = Column(String(128), nullable=False)
    status = Column(String(32), default="pending", nullable=False)  # pending, present, absent, late
    marked_by = Column(String(128), nullable=False)
    marked_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    notes = Column(Text, nullable=True)


class NotificationModel(Base):
    """In-app notifications for officers and coordinators."""
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True)
    recipient_role = Column(String(32), nullable=False, index=True)  # 'coordinator', 'officer', 'all'
    recipient_username = Column(String(128), nullable=True, index=True)
    category = Column(String(64), nullable=False)  # 'needs_review', 'clash_alert', 'request_update', 'schedule_change'
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    metadata_json = Column(Text, nullable=False, default="{}")


class PendingResultModel(Base):
    """Coordinator submitted result entries awaiting Officer review."""
    __tablename__ = "pending_results"

    id = Column(String(36), primary_key=True)
    drive_id = Column(String(36), ForeignKey("drives.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(32), nullable=False)  # shortlisted, selected, offered, accepted, declined, revoked
    ctc_lpa = Column(Float, nullable=False)
    fixed_pay_lpa = Column(Float, nullable=True)
    is_dream = Column(Boolean, default=False)
    reason = Column(Text, nullable=False)
    submitted_by = Column(String(128), nullable=False)
    submitted_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    status = Column(String(32), default="pending", nullable=False)  # pending, approved, rejected
    officer_name = Column(String(128), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)


class PlacementRequestModel(Base):
    __tablename__ = "placement_requests"

    id = Column(String(36), primary_key=True)
    requester_id = Column(String(36), nullable=False, index=True)
    requester_role = Column(String(32), nullable=False)  # "student", "coordinator", "recruiter", "officer"
    requester_name = Column(String(128), nullable=False)
    request_type = Column(String(64), nullable=False)  # "DATA_CORRECTION", "RULE_DOUBT", "EXTRA_PANEL", "CLASH_PREFERENCE", "RECRUITER_QUERY", "ADD_REMOVE_STUDENT"
    drive_id = Column(String(36), nullable=True, index=True)
    student_id = Column(String(36), nullable=True, index=True)
    subject = Column(String(255), nullable=False)
    details_json = Column(Text, nullable=False, default="{}")
    status = Column(String(32), nullable=False, default="PENDING")  # "PENDING", "APPROVED", "REJECTED", "ANSWERED"
    officer_reply = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)




class AttendanceRecordModel(Base):
    __tablename__ = "attendance_records"

    id = Column(String(36), primary_key=True)
    drive_id = Column(String(36), nullable=False, index=True)
    student_id = Column(String(36), nullable=False, index=True)
    student_name = Column(String(128), nullable=False)
    roll_no = Column(String(64), nullable=False)
    room_name = Column(String(128), nullable=True)
    status = Column(String(32), nullable=False, default="PRESENT")  # "PRESENT", "ABSENT", "LATE"
    notes = Column(Text, nullable=True)
    marked_by = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)


