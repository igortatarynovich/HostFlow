"""Ensure dev/test SQLite has domain event outbox tables (PR 3A-1).

Production schema is owned exclusively by Alembic — this helper must never run DDL
against PostgreSQL or in production-like environments.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import closing


def _db_path() -> str:
    return os.environ.get("DEV_DB_PATH") or os.path.join(os.getcwd(), "app.db")


def _table_exists(cur: sqlite3.Cursor, name: str) -> bool:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None


def _runtime_environment() -> str:
    return (
        os.environ.get("ENVIRONMENT")
        or os.environ.get("ENV")
        or os.environ.get("APP_ENV")
        or "development"
    ).strip().lower()


def should_run_domain_events_schema_fallback() -> bool:
    """True only for local SQLite dev/test — never PostgreSQL or production."""
    env = _runtime_environment()
    if env in {"production", "prod", "staging", "stage"}:
        return False

    db_url = (
        os.environ.get("DATABASE_URL")
        or os.environ.get("ASYNC_DATABASE_URL")
        or os.environ.get("SQLALCHEMY_DATABASE_URI")
        or ""
    ).strip().lower()
    if db_url.startswith(("postgresql", "postgres")):
        return False

    path = _db_path()
    if not path or path == ":memory:":
        return False
    if not os.path.exists(path):
        return False
    return path.endswith(".db") or "sqlite" in db_url


def ensure_domain_events_schema() -> None:
    if not should_run_domain_events_schema_fallback():
        return

    path = _db_path()
    with closing(sqlite3.connect(path)) as conn:
        cur = conn.cursor()
        if not _table_exists(cur, "domain_event_outbox"):
            cur.execute(
                """
                CREATE TABLE domain_event_outbox (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    event_version TEXT NOT NULL,
                    aggregate_type TEXT NOT NULL,
                    aggregate_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    company_id TEXT,
                    payload TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    correlation_id TEXT NOT NULL,
                    causation_id TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    available_at TEXT NOT NULL,
                    processed_at TEXT,
                    last_error TEXT,
                    locked_at TEXT,
                    locked_by TEXT,
                    created_at TEXT DEFAULT (CURRENT_TIMESTAMP)
                )
                """
            )
        if not _table_exists(cur, "domain_event_consumer_receipts"):
            cur.execute(
                """
                CREATE TABLE domain_event_consumer_receipts (
                    id TEXT PRIMARY KEY,
                    consumer_name TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    processed_at TEXT NOT NULL,
                    UNIQUE(consumer_name, event_id)
                )
                """
            )
        if not _table_exists(cur, "requirement_evaluation_results"):
            cur.execute(
                """
                CREATE TABLE requirement_evaluation_results (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    company_id TEXT,
                    policy_ref TEXT NOT NULL,
                    policy_version TEXT NOT NULL,
                    target_stage TEXT NOT NULL,
                    entity_revision TEXT NOT NULL,
                    can_transition INTEGER NOT NULL,
                    blocker_codes TEXT NOT NULL,
                    result_snapshot TEXT NOT NULL,
                    evaluated_at TEXT NOT NULL,
                    created_at TEXT DEFAULT (CURRENT_TIMESTAMP)
                )
                """
            )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ix_domain_event_outbox_status_available "
            "ON domain_event_outbox(status, available_at)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ix_domain_event_outbox_tenant_type "
            "ON domain_event_outbox(tenant_id, event_type)"
        )
        cur.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_domain_event_consumer_receipt "
            "ON domain_event_consumer_receipts(consumer_name, event_id)"
        )
        conn.commit()
        print("[domain_events] ensure_domain_events_schema executed")
