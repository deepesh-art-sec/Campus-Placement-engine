"""
Tests for Alembic migrations.
Verifies clean upgrade to head, complete downgrade to base, and re-upgrade.
"""

import os
import tempfile

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

INI_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))


def test_migration_upgrade_and_downgrade_cycle() -> None:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        temp_db_path = tf.name

    test_db_url = f"sqlite:///{temp_db_path.replace(os.sep, '/')}"
    test_engine = create_engine(test_db_url)

    try:
        alembic_cfg = Config(INI_PATH)
        alembic_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "alembic"))
        alembic_cfg.set_main_option("script_location", alembic_dir)
        alembic_cfg.set_main_option("version_locations", os.path.join(alembic_dir, "versions"))
        alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)

        # 1. Upgrade to head
        command.upgrade(alembic_cfg, "head")

        inspector = inspect(test_engine)
        tables = inspector.get_table_names()
        assert "students" in tables
        assert "drives" in tables
        assert "policies" in tables
        assert "eligibility_runs" in tables
        assert "eligibility_decisions" in tables
        assert "slots" in tables
        assert "rooms" in tables
        assert "events" in tables
        assert "company_export_mappings" in tables

        # 2. Downgrade to base
        command.downgrade(alembic_cfg, "base")
        inspector = inspect(test_engine)
        tables_after_downgrade = inspector.get_table_names()
        # All application tables should be dropped (only alembic_version might remain)
        assert "students" not in tables_after_downgrade
        assert "drives" not in tables_after_downgrade
        assert "policies" not in tables_after_downgrade
        assert "company_export_mappings" not in tables_after_downgrade

        # 3. Re-upgrade to head
        command.upgrade(alembic_cfg, "head")
        inspector = inspect(test_engine)
        re_tables = inspector.get_table_names()
        assert "students" in re_tables
        assert "drives" in re_tables
        assert "events" in re_tables
        assert "company_export_mappings" in re_tables
    finally:
        test_engine.dispose()
        if os.path.exists(temp_db_path):
            try:
                os.remove(temp_db_path)
            except OSError:
                pass
