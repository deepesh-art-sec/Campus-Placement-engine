"""
Tests for Alembic migrations.
Verifies clean upgrade to head, complete downgrade to base, and re-upgrade.
"""

import os

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from backend.app.storage.database import engine

INI_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))


def test_migration_upgrade_and_downgrade_cycle() -> None:
    alembic_cfg = Config(INI_PATH)

    # 1. Upgrade to head
    command.upgrade(alembic_cfg, "head")

    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "students" in tables
    assert "drives" in tables
    assert "policies" in tables
    assert "eligibility_runs" in tables
    assert "eligibility_decisions" in tables
    assert "slots" in tables
    assert "rooms" in tables
    assert "events" in tables

    # 2. Downgrade to base
    command.downgrade(alembic_cfg, "base")
    inspector = inspect(engine)
    tables_after_downgrade = inspector.get_table_names()
    # All application tables should be dropped (only alembic_version might remain)
    assert "students" not in tables_after_downgrade
    assert "drives" not in tables_after_downgrade
    assert "policies" not in tables_after_downgrade

    # 3. Re-upgrade to head
    command.upgrade(alembic_cfg, "head")
    inspector = inspect(engine)
    re_tables = inspector.get_table_names()
    assert "students" in re_tables
    assert "drives" in re_tables
    assert "events" in re_tables
