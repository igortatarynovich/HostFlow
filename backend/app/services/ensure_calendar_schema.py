from __future__ import annotations

import os
import sqlite3
from contextlib import closing

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine


def _db_path() -> str:
    return os.environ.get("DEV_DB_PATH") or os.path.join(os.getcwd(), "app.db")


def _table_exists(cur: sqlite3.Cursor, name: str) -> bool:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None


def _ensure_non_sqlite_schema() -> None:
    try:
        from backend.app.core.settings import settings
        from backend.app.db.base import Base
        from backend.app.models.calendar_integration import (
            CalendarChannel,
            CalendarConnection,
            CalendarItem,
            CalendarItemLink,
            CalendarSyncCursor,
            CalendarSyncJob,
            IntegrationActionLog,
        )
    except Exception as exc:
        print(f"[calendar] non-sqlite ensure skipped imports ({exc})")
        return

    async_url = str(getattr(settings, "ASYNC_DATABASE_URL", "") or "").strip()
    if not async_url or async_url.startswith("sqlite"):
        return

    async def _run() -> None:
        engine = create_async_engine(async_url, future=True)
        try:
            async with engine.begin() as conn:
                await conn.run_sync(
                    lambda sync_conn: Base.metadata.create_all(
                        sync_conn,
                        tables=[
                            CalendarConnection.__table__,
                            CalendarChannel.__table__,
                            CalendarItem.__table__,
                            CalendarItemLink.__table__,
                            CalendarSyncCursor.__table__,
                            CalendarSyncJob.__table__,
                            IntegrationActionLog.__table__,
                        ],
                    )
                )
        finally:
            await engine.dispose()

    try:
        asyncio.get_running_loop()
        # Lifespan already runs inside event loop; skip sync bootstrap path.
        # PostgreSQL deployments should rely on Alembic migrations.
        return
    except RuntimeError:
        asyncio.run(_run())


def ensure_calendar_schema() -> None:
    _ensure_non_sqlite_schema()
    path = _db_path()
    if not os.path.exists(path):
        return

    with closing(sqlite3.connect(path)) as conn:
        cur = conn.cursor()

        if not _table_exists(cur, "calendar_connections"):
            cur.execute(
                """
                CREATE TABLE calendar_connections (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    user_id TEXT,
                    provider TEXT NOT NULL,
                    account_ref TEXT,
                    status TEXT NOT NULL DEFAULT 'active',
                    scopes_json TEXT,
                    token_meta_json TEXT,
                    last_error TEXT,
                    created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                    updated_at TEXT DEFAULT (CURRENT_TIMESTAMP)
                )
                """
            )
        cur.execute("CREATE INDEX IF NOT EXISTS ix_calendar_connections_tenant_provider ON calendar_connections(tenant_id, provider, status)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_calendar_connections_tenant_user ON calendar_connections(tenant_id, user_id, status)")

        if not _table_exists(cur, "calendar_channels"):
            cur.execute(
                """
                CREATE TABLE calendar_channels (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    connection_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    resource_id TEXT,
                    channel_ref TEXT,
                    expires_at TEXT,
                    renew_after TEXT,
                    health_state TEXT NOT NULL DEFAULT 'healthy',
                    payload TEXT,
                    created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                    updated_at TEXT DEFAULT (CURRENT_TIMESTAMP)
                )
                """
            )
        cur.execute("CREATE INDEX IF NOT EXISTS ix_calendar_channels_conn_provider ON calendar_channels(connection_id, provider, health_state)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_calendar_channels_tenant_expires ON calendar_channels(tenant_id, expires_at)")

        if not _table_exists(cur, "calendar_items"):
            cur.execute(
                """
                CREATE TABLE calendar_items (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    owner_id TEXT,
                    assignee_id TEXT,
                    kind TEXT NOT NULL DEFAULT 'event',
                    status TEXT NOT NULL DEFAULT 'scheduled',
                    title TEXT NOT NULL,
                    description TEXT,
                    timezone TEXT NOT NULL DEFAULT 'UTC',
                    starts_at TEXT NOT NULL,
                    ends_at TEXT,
                    all_day INTEGER NOT NULL DEFAULT 0,
                    linked_entity_type TEXT,
                    linked_entity_id TEXT,
                    source TEXT NOT NULL DEFAULT 'hostflow',
                    payload TEXT,
                    created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                    updated_at TEXT DEFAULT (CURRENT_TIMESTAMP)
                )
                """
            )
        cur.execute("CREATE INDEX IF NOT EXISTS ix_calendar_items_tenant_start ON calendar_items(tenant_id, starts_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_calendar_items_tenant_owner ON calendar_items(tenant_id, owner_id, starts_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_calendar_items_tenant_kind_status ON calendar_items(tenant_id, kind, status, starts_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_calendar_items_tenant_entity ON calendar_items(tenant_id, linked_entity_type, linked_entity_id)")

        if not _table_exists(cur, "calendar_item_links"):
            cur.execute(
                """
                CREATE TABLE calendar_item_links (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    calendar_item_id TEXT NOT NULL,
                    connection_id TEXT,
                    provider TEXT NOT NULL,
                    provider_calendar_id TEXT,
                    provider_event_id TEXT NOT NULL,
                    provider_version TEXT,
                    sync_state TEXT NOT NULL DEFAULT 'synced',
                    payload TEXT,
                    created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                    updated_at TEXT DEFAULT (CURRENT_TIMESTAMP)
                )
                """
            )
        cur.execute("CREATE INDEX IF NOT EXISTS ix_calendar_item_links_item_provider ON calendar_item_links(calendar_item_id, provider)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_calendar_item_links_provider_event ON calendar_item_links(provider, provider_event_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_calendar_item_links_tenant_state ON calendar_item_links(tenant_id, sync_state, updated_at)")

        if not _table_exists(cur, "calendar_sync_cursors"):
            cur.execute(
                """
                CREATE TABLE calendar_sync_cursors (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    connection_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    calendar_ref TEXT,
                    cursor TEXT,
                    cursor_meta_json TEXT,
                    last_synced_at TEXT,
                    created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                    updated_at TEXT DEFAULT (CURRENT_TIMESTAMP)
                )
                """
            )
        cur.execute("CREATE INDEX IF NOT EXISTS ix_calendar_sync_cursors_connection ON calendar_sync_cursors(connection_id, provider, calendar_ref)")

        if not _table_exists(cur, "calendar_sync_jobs"):
            cur.execute(
                """
                CREATE TABLE calendar_sync_jobs (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    source_kind TEXT NOT NULL,
                    operation TEXT NOT NULL DEFAULT 'ingest',
                    status TEXT NOT NULL DEFAULT 'queued',
                    dedupe_key TEXT,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    scheduled_at TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    last_error TEXT,
                    payload TEXT,
                    created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                    updated_at TEXT DEFAULT (CURRENT_TIMESTAMP)
                )
                """
            )
        cur.execute("CREATE INDEX IF NOT EXISTS ix_calendar_sync_jobs_tenant_status ON calendar_sync_jobs(tenant_id, status, created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_calendar_sync_jobs_tenant_source ON calendar_sync_jobs(tenant_id, source_kind, created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_calendar_sync_jobs_dedupe ON calendar_sync_jobs(dedupe_key)")

        if not _table_exists(cur, "integration_action_logs"):
            cur.execute(
                """
                CREATE TABLE integration_action_logs (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    calendar_item_id TEXT,
                    source TEXT NOT NULL DEFAULT 'hostflow',
                    action TEXT NOT NULL,
                    actor_user_id TEXT,
                    idempotency_key TEXT,
                    payload TEXT,
                    outcome TEXT,
                    created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                    updated_at TEXT DEFAULT (CURRENT_TIMESTAMP)
                )
                """
            )
        cur.execute("CREATE INDEX IF NOT EXISTS ix_integration_action_logs_tenant_created ON integration_action_logs(tenant_id, created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_integration_action_logs_tenant_source ON integration_action_logs(tenant_id, source, created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_integration_action_logs_tenant_item ON integration_action_logs(tenant_id, calendar_item_id, created_at)")

        conn.commit()
