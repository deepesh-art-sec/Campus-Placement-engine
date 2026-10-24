"""Initial schema with all placement engine entities

Revision ID: 0001_initial_schema
Revises: None
Create Date: 2026-10-22 20:53:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. students
    op.create_table(
        "students",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("roll_no", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("branch", sa.String(length=128), nullable=False),
        sa.Column("program", sa.String(length=64), nullable=False, server_default="B.Tech"),
        sa.Column("cgpa", sa.Float(), nullable=False),
        sa.Column("tenth_percentage", sa.Float(), nullable=False),
        sa.Column("twelfth_percentage", sa.Float(), nullable=True),
        sa.Column("diploma_percentage", sa.Float(), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("gender", sa.String(length=32), nullable=True),
        sa.Column("caste", sa.String(length=64), nullable=True),
        sa.Column("religion", sa.String(length=64), nullable=True),
        sa.Column("category", sa.String(length=32), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("roll_no"),
    )
    op.create_index("ix_students_branch", "students", ["branch"])
    op.create_index("ix_students_email", "students", ["email"])
    op.create_index("ix_students_roll_no", "students", ["roll_no"])

    # 2. academic_records
    op.create_table(
        "academic_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("student_id", sa.String(length=36), nullable=False),
        sa.Column("semester", sa.Integer(), nullable=False),
        sa.Column("sgpa", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "semester", name="uq_student_semester"),
    )
    op.create_index("ix_academic_records_student_id", "academic_records", ["student_id"])

    # 3. backlogs
    op.create_table(
        "backlogs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("student_id", sa.String(length=36), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("semester", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("cleared_on", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_backlogs_student_id", "backlogs", ["student_id"])

    # 4. gap_years
    op.create_table(
        "gap_years",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("student_id", sa.String(length=36), nullable=False),
        sa.Column("start_year", sa.Integer(), nullable=False),
        sa.Column("end_year", sa.Integer(), nullable=False),
        sa.Column("duration_years", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("phase", sa.String(length=64), nullable=False, server_default="general"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gap_years_student_id", "gap_years", ["student_id"])

    # 5. offers
    op.create_table(
        "offers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("student_id", sa.String(length=36), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("ctc_lpa", sa.Float(), nullable=False),
        sa.Column("fixed_pay_lpa", sa.Float(), nullable=True),
        sa.Column("offer_date", sa.Date(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="on_campus"),
        sa.Column("is_dream", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="offered"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_offers_student_id", "offers", ["student_id"])

    # 6. companies
    op.create_table(
        "companies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("industry", sa.String(length=128), nullable=True),
        sa.Column("tier", sa.String(length=64), nullable=True, server_default="Standard"),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_companies_name", "companies", ["name"])

    # 7. drives
    op.create_table(
        "drives",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("drive_date", sa.Date(), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False, server_default="on_campus"),
        sa.Column("ctc_lpa", sa.Float(), nullable=False),
        sa.Column("is_dream", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_drives_company_id", "drives", ["company_id"])
    op.create_index("ix_drives_drive_date", "drives", ["drive_date"])

    # 8. drive_requirement_versions
    op.create_table(
        "drive_requirement_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("drive_id", sa.String(length=36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("raw_source_text", sa.Text(), nullable=True),
        sa.Column("parse_confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("min_cgpa", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("min_tenth_percentage", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("min_twelfth_percentage", sa.Float(), nullable=True),
        sa.Column("min_diploma_percentage", sa.Float(), nullable=True),
        sa.Column("allowed_branches_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("allowed_programs_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("max_active_backlogs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("allow_history_backlogs", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("max_history_backlogs", sa.Integer(), nullable=True),
        sa.Column("max_gap_years", sa.Integer(), nullable=True),
        sa.Column("allow_gap_during_degree", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("custom_rules_json", sa.Text(), nullable=True, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["drive_id"], ["drives.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("drive_id", "version_number", name="uq_drive_requirement_version"),
    )
    op.create_index("ix_drive_requirement_versions_drive_id", "drive_requirement_versions", ["drive_id"])

    # 9. policies
    op.create_table(
        "policies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("max_offers_per_student", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("dream_tier_ctc_lpa", sa.Float(), nullable=False, server_default="10.0"),
        sa.Column("super_dream_tier_ctc_lpa", sa.Float(), nullable=True, server_default="20.0"),
        sa.Column("allow_dream_upgrade", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("upgrade_ctc_multiplier", sa.Float(), nullable=False, server_default="1.5"),
        sa.Column("strict_backlog_cutoff", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("allow_multiple_offers_if_different_tiers", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "version", name="uq_policy_name_version"),
    )

    # 10. eligibility_runs
    op.create_table(
        "eligibility_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("drive_id", sa.String(length=36), nullable=False),
        sa.Column("requirement_version_id", sa.String(length=36), nullable=False),
        sa.Column("policy_id", sa.String(length=36), nullable=False),
        sa.Column("executed_at", sa.DateTime(), nullable=False),
        sa.Column("total_evaluated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_eligible", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_ineligible", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("executed_by", sa.String(length=128), nullable=False, server_default="SYSTEM"),
        sa.ForeignKeyConstraint(["drive_id"], ["drives.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_eligibility_runs_drive_id", "eligibility_runs", ["drive_id"])

    # 11. eligibility_decisions
    op.create_table(
        "eligibility_decisions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("student_id", sa.String(length=36), nullable=False),
        sa.Column("drive_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reasons_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("rule_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("evaluated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["drive_id"], ["drives.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["eligibility_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "student_id", name="uq_run_student_decision"),
    )
    op.create_index("ix_eligibility_decisions_drive_id", "eligibility_decisions", ["drive_id"])
    op.create_index("ix_eligibility_decisions_run_id", "eligibility_decisions", ["run_id"])
    op.create_index("ix_eligibility_decisions_student_id", "eligibility_decisions", ["student_id"])

    # 12. rooms
    op.create_table(
        "rooms",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("building", sa.String(length=128), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("has_computers", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_rooms_name", "rooms", ["name"])

    # 13. panels
    op.create_table(
        "panels",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("drive_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("interviewers_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("room_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["drive_id"], ["drives.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_panels_drive_id", "panels", ["drive_id"])

    # 14. schedules
    op.create_table(
        "schedules",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("drive_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # 15. slots
    op.create_table(
        "slots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("schedule_id", sa.String(length=36), nullable=False),
        sa.Column("drive_id", sa.String(length=36), nullable=False),
        sa.Column("student_id", sa.String(length=36), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("room_id", sa.String(length=36), nullable=False),
        sa.Column("panel_id", sa.String(length=36), nullable=True),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["drive_id"], ["drives.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["panel_id"], ["panels.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["schedule_id"], ["schedules.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_slots_drive_id", "slots", ["drive_id"])
    op.create_index("ix_slots_end_time", "slots", ["end_time"])
    op.create_index("ix_slots_room_id", "slots", ["room_id"])
    op.create_index("ix_slots_schedule_id", "slots", ["schedule_id"])
    op.create_index("ix_slots_start_time", "slots", ["start_time"])
    op.create_index("ix_slots_student_id", "slots", ["student_id"])

    # 16. events (append-only)
    op.create_table(
        "events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("aggregate_type", sa.String(length=64), nullable=False),
        sa.Column("aggregate_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_events_aggregate_id", "events", ["aggregate_id"])
    op.create_index("ix_events_aggregate_type", "events", ["aggregate_type"])
    op.create_index("ix_events_event_type", "events", ["event_type"])
    op.create_index("ix_events_timestamp", "events", ["timestamp"])

    # 17. audit_log
    op.create_table(
        "audit_log",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("changes_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_log_entity_id", "audit_log", ["entity_id"])
    op.create_index("ix_audit_log_entity_type", "audit_log", ["entity_type"])
    op.create_index("ix_audit_log_timestamp", "audit_log", ["timestamp"])

    # 18. users
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("student_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_username", "users", ["username"])

    # 19. sessions
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"])
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])


def downgrade() -> None:
    op.drop_table("sessions")
    op.drop_table("users")
    op.drop_table("audit_log")
    op.drop_table("events")
    op.drop_table("slots")
    op.drop_table("schedules")
    op.drop_table("panels")
    op.drop_table("rooms")
    op.drop_table("eligibility_decisions")
    op.drop_table("eligibility_runs")
    op.drop_table("policies")
    op.drop_table("drive_requirement_versions")
    op.drop_table("drives")
    op.drop_table("companies")
    op.drop_table("offers")
    op.drop_table("gap_years")
    op.drop_table("backlogs")
    op.drop_table("academic_records")
    op.drop_table("students")
