"""Add student normalized_name

Revision ID: 0003_add_student_normalized_name
Revises: 0002_add_company_export_mappings
Create Date: 2026-10-29 16:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_add_student_normalized_name"
down_revision: str | None = "0002_add_company_export_mappings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("students", schema=None) as batch_op:
        batch_op.add_column(sa.Column("normalized_name", sa.String(length=255), nullable=True))
        batch_op.create_index("ix_students_normalized_name", ["normalized_name"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("students", schema=None) as batch_op:
        batch_op.drop_index("ix_students_normalized_name")
        batch_op.drop_column("normalized_name")
