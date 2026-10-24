"""Add company_export_mappings and company_id to users

Revision ID: 0002_add_company_export_mappings
Revises: 0001_initial_schema
Create Date: 2026-10-22 22:42:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_add_company_export_mappings"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add company_id to users
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("company_id", sa.String(length=64), nullable=True))

    # 2. Create company_export_mappings
    op.create_table(
        "company_export_mappings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=64), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("sheet_name", sa.String(length=64), nullable=False, server_default="Candidates"),
        sa.Column("date_format", sa.String(length=32), nullable=False, server_default="YYYY-MM-DD"),
        sa.Column("column_mappings_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("column_widths_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id"),
    )
    op.create_index("ix_company_export_mappings_company_id", "company_export_mappings", ["company_id"])


def downgrade() -> None:
    op.drop_table("company_export_mappings")
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("company_id")
