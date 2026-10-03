"""Schema checks. These tests move the test database between revisions and
always leave it at head for the tests that follow."""
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import inspect, text
from conftest import alembic_config

from app.models.database import Base, engine

APP_TABLES = {t.name for t in Base.metadata.sorted_tables}

STEP3_MANUAL_ALTER = """
ALTER TABLE documents
  ADD COLUMN IF NOT EXISTS processing_status VARCHAR(20) NOT NULL DEFAULT 'processing',
  ADD COLUMN IF NOT EXISTS processing_error TEXT;
UPDATE documents SET processing_status='ready' WHERE embedding_complete;
"""


def _drift() -> list:
    with engine.connect() as conn:
        ctx = MigrationContext.configure(
            conn, opts={"compare_type": True, "compare_server_default": True}
        )
        return compare_metadata(ctx, Base.metadata)


def test_models_match_head():
    assert _drift() == []


def test_alembic_check_passes():
    command.check(alembic_config())


def test_downgrade_base_drops_everything_and_upgrade_restores_it():
    cfg = alembic_config()
    try:
        command.downgrade(cfg, "base")
        assert set(inspect(engine).get_table_names()) == {"alembic_version"}
    finally:
        command.upgrade(cfg, "head")
    assert APP_TABLES <= set(inspect(engine).get_table_names())


def _seed_legacy_rows(conn) -> None:
    conn.execute(text("INSERT INTO users (id, email) VALUES (1, 'legacy@example.com')"))
    conn.execute(text(
        "INSERT INTO documents (id, owner_id, filename, embedding_complete) VALUES "
        "(1, 1, 'done.pdf', true), (2, 1, 'stuck.pdf', false), (3, 1, 'null.pdf', NULL)"
    ))


def _statuses() -> dict:
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT id, processing_status, processing_error FROM documents ORDER BY id"))
        return {r.id: (r.processing_status, r.processing_error) for r in rows}


def _run_0002_from_baseline(with_manual_alter: bool) -> dict:
    cfg = alembic_config()
    try:
        command.downgrade(cfg, "base")
        command.upgrade(cfg, "0001_baseline")
        with engine.begin() as conn:
            _seed_legacy_rows(conn)
            if with_manual_alter:
                conn.execute(text(STEP3_MANUAL_ALTER))
        command.upgrade(cfg, "head")
        assert _drift() == []
        return _statuses()
    finally:
        command.downgrade(cfg, "base")
        command.upgrade(cfg, "head")


LEGACY = "Uploaded before processing fix; please reprocess"


def test_0002_backfills_status_on_baseline_database():
    assert _run_0002_from_baseline(with_manual_alter=False) == {
        1: ("ready", None),
        2: ("failed", LEGACY),
        3: ("failed", LEGACY),
    }


def test_0002_is_idempotent_after_step3_manual_alter():
    assert _run_0002_from_baseline(with_manual_alter=True) == {
        1: ("ready", None),
        2: ("failed", LEGACY),
        3: ("failed", LEGACY),
    }
