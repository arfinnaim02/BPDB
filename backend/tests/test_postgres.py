"""Opt-in real PostgreSQL checks; never use a production TEST_DATABASE_URL."""

import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from app.db.models import Base
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError


@pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not configured; live PostgreSQL not verified",
)
def test_real_migration_and_constraints():
    engine = create_engine(
        os.environ["TEST_DATABASE_URL"], hide_parameters=True, connect_args={"connect_timeout": 10}
    )
    schema = "bpdb_test_" + uuid4().hex
    try:
        with engine.begin() as c:
            c.execute(text(f'CREATE SCHEMA "{schema}"'))
        with engine.connect() as c:
            c.execute(text(f'SET search_path TO "{schema}"'))
            c.commit()
            config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
            config.attributes["connection"] = c
            command.upgrade(config, "head")
            assert compare_metadata(MigrationContext.configure(c), Base.metadata) == []
            c.execute(
                text("""INSERT INTO daily_reports
                (id, created_at, report_date, dataset_grain)
                VALUES ('first', CURRENT_TIMESTAMP, '2026-01-01', 'national_daily')""")
            )
            with pytest.raises(IntegrityError), c.begin_nested():
                c.execute(
                    text("""INSERT INTO daily_reports
                    (id, created_at, report_date, dataset_grain)
                    VALUES ('duplicate', CURRENT_TIMESTAMP, '2026-01-01', 'national_daily')""")
                )
            c.execute(
                text("""INSERT INTO daily_reports
                (id, created_at, report_date, dataset_grain)
                VALUES ('second', CURRENT_TIMESTAMP, '2026-01-02', 'national_daily')""")
            )
            c.execute(
                text("""INSERT INTO daily_report_versions
                (id, created_at, report_id, version_number, quality_status, parser_version)
                VALUES ('v2', CURRENT_TIMESTAMP, 'second', 1, 'validated', 'test-only')""")
            )
            with pytest.raises(IntegrityError), c.begin_nested():
                c.execute(text("UPDATE daily_reports SET current_version_id='v2' WHERE id='first'"))
            c.rollback()
            command.downgrade(config, "base")
    finally:
        with engine.begin() as c:
            c.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        engine.dispose()
