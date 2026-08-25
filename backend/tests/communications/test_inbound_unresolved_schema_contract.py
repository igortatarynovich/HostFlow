"""Schema contract: communication_inbound_unresolved.resolved_* columns.

Guards against Alembic stamp drift where the table exists without C0.2
resolution-audit columns (UndefinedColumn at runtime).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text

from backend.app.models.communication_inbound_unresolved import CommunicationInboundUnresolved

REQUIRED_RESOLVED_COLUMNS = (
    "resolved_by_user_id",
    "resolved_at",
    "resolved_entity_type",
    "resolved_entity_id",
    "resolved_thread_id",
)


def _backend_root() -> Path:
    """Resolve backend root whether tests run from repo or /app container layout."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        versions = parent / "alembic" / "versions"
        if versions.is_dir() and (parent / "alembic.ini").is_file():
            return parent
        nested = parent / "backend" / "alembic" / "versions"
        if nested.is_dir() and (parent / "backend" / "alembic.ini").is_file():
            return parent / "backend"
    raise RuntimeError(f"cannot locate alembic versions from {here}")


BACKEND_ROOT = _backend_root()
REPAIR_MIGRATION = (
    BACKEND_ROOT / "alembic" / "versions" / "202607200007_comm_inbound_unresolved_resolved_cols_repair.py"
)
C0_2_MIGRATION = (
    BACKEND_ROOT / "alembic" / "versions" / "202607200002_comm_inbound_unresolved_c0_2.py"
)


def _load_repair_module():
    spec = importlib.util.spec_from_file_location(
        "comm_inbound_unresolved_resolved_cols_repair",
        REPAIR_MIGRATION,
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _table_columns(conn) -> set[str]:
    return {c["name"] for c in inspect(conn).get_columns("communication_inbound_unresolved")}


def _run_repair_upgrade(conn) -> None:
    repair = _load_repair_module()
    ctx = MigrationContext.configure(conn)
    with Operations.context(ctx):
        repair.upgrade()


def test_model_declares_resolved_audit_columns():
    cols = {c.name for c in CommunicationInboundUnresolved.__table__.columns}
    missing = [name for name in REQUIRED_RESOLVED_COLUMNS if name not in cols]
    assert missing == [], f"model missing resolved_* columns: {missing}"


def test_c0_2_and_repair_migrations_exist_and_mention_resolved_columns():
    assert C0_2_MIGRATION.is_file(), C0_2_MIGRATION
    assert REPAIR_MIGRATION.is_file(), REPAIR_MIGRATION
    c0_text = C0_2_MIGRATION.read_text(encoding="utf-8")
    repair_text = REPAIR_MIGRATION.read_text(encoding="utf-8")
    for name in REQUIRED_RESOLVED_COLUMNS:
        assert name in c0_text
        assert name in repair_text
    assert "ADD COLUMN IF NOT EXISTS" in repair_text
    assert "202607200006_comm_thread_work_version" in repair_text


def test_repair_migration_on_partial_sqlite_then_idempotent():
    """Partial table (stamp drift) → upgrade adds columns; second run is a no-op."""
    engine = sa.create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE communication_inbound_unresolved (
                    id VARCHAR(36) NOT NULL PRIMARY KEY,
                    tenant_id VARCHAR(36) NOT NULL,
                    thread_id VARCHAR(36) NOT NULL,
                    message_id VARCHAR(36) NOT NULL,
                    channel VARCHAR(32) NOT NULL,
                    provider VARCHAR(64),
                    external_message_ref VARCHAR(255),
                    sender_address VARCHAR(255),
                    resolution_reason VARCHAR(64) NOT NULL,
                    status VARCHAR(32) NOT NULL,
                    correlation_id VARCHAR(64),
                    details_json JSON NOT NULL,
                    notes TEXT,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
                """
            )
        )
        assert "resolved_by_user_id" not in _table_columns(conn)

        _run_repair_upgrade(conn)
        cols = _table_columns(conn)
        missing = [n for n in REQUIRED_RESOLVED_COLUMNS if n not in cols]
        assert missing == [], missing

        _run_repair_upgrade(conn)
        assert _table_columns(conn) == cols

    engine.dispose()


def test_repair_migration_noop_when_columns_already_present():
    """Mirrors production after manual ALTER — upgrade must not fail."""
    engine = sa.create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE communication_inbound_unresolved (
                    id VARCHAR(36) NOT NULL PRIMARY KEY,
                    tenant_id VARCHAR(36) NOT NULL,
                    thread_id VARCHAR(36) NOT NULL,
                    message_id VARCHAR(36) NOT NULL,
                    channel VARCHAR(32) NOT NULL,
                    resolution_reason VARCHAR(64) NOT NULL,
                    status VARCHAR(32) NOT NULL,
                    details_json JSON NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    resolved_by_user_id VARCHAR(36),
                    resolved_at DATETIME,
                    resolved_entity_type VARCHAR(64),
                    resolved_entity_id VARCHAR(120),
                    resolved_thread_id VARCHAR(36)
                )
                """
            )
        )
        before = _table_columns(conn)
        _run_repair_upgrade(conn)
        assert _table_columns(conn) == before

    engine.dispose()


def test_repair_migration_noop_when_table_missing():
    engine = sa.create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        _run_repair_upgrade(conn)
        assert "communication_inbound_unresolved" not in inspect(conn).get_table_names()
    engine.dispose()


@pytest.mark.asyncio
async def test_live_db_has_resolved_columns_when_table_exists(db):
    """On the session DB (sqlite create_all or postgres), columns must be present."""

    def _read_cols(sync_session):
        bind = sync_session.get_bind()
        insp = inspect(bind)
        if "communication_inbound_unresolved" not in insp.get_table_names():
            return None
        return {c["name"] for c in insp.get_columns("communication_inbound_unresolved")}

    cols = await db.run_sync(_read_cols)
    if cols is None:
        pytest.skip("table not created in this test DB")
    missing = [n for n in REQUIRED_RESOLVED_COLUMNS if n not in cols]
    assert missing == [], f"live DB missing resolved_* columns: {missing}"
