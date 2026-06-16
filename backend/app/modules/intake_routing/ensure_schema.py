"""Ensure intake routing tables exist in dev/test SQLite."""

from __future__ import annotations

import os
import sqlite3
from contextlib import closing


def _db_path() -> str:
    return os.environ.get("DEV_DB_PATH") or os.path.join(os.getcwd(), "app.db")


def _table_exists(cur: sqlite3.Cursor, name: str) -> bool:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None


def ensure_intake_routing_schema() -> None:
    path = _db_path()
    if not os.path.exists(path):
        return

    with closing(sqlite3.connect(path)) as conn:
        cur = conn.cursor()

        if not _table_exists(cur, "intake_source_profiles"):
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS intake_source_profiles (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    code TEXT NOT NULL,
                    name TEXT NOT NULL,
                    provider TEXT NOT NULL DEFAULT 'unknown',
                    channel TEXT NOT NULL DEFAULT 'unknown',
                    own_company_id TEXT NOT NULL,
                    route_intent TEXT NOT NULL DEFAULT 'unknown',
                    pipeline_preset TEXT,
                    public_slug TEXT,
                    form_type TEXT,
                    lead_type TEXT,
                    lead_target_type TEXT,
                    source TEXT,
                    default_assignee_id TEXT,
                    default_language TEXT,
                    supported_languages TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    notes TEXT,
                    created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                    updated_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                    UNIQUE(tenant_id, code)
                )
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS ix_intake_source_profiles_tenant_id "
                "ON intake_source_profiles(tenant_id)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS ix_intake_source_profiles_public_slug "
                "ON intake_source_profiles(public_slug)"
            )
        else:
            cur.execute("PRAGMA table_info(intake_source_profiles)")
            cols = {row[1] for row in cur.fetchall()}
            for name in (
                "public_slug",
                "form_type",
                "lead_type",
                "lead_target_type",
                "source",
                "supported_languages",
            ):
                if name not in cols:
                    cur.execute(f"ALTER TABLE intake_source_profiles ADD COLUMN {name} TEXT")
            cur.execute(
                "CREATE INDEX IF NOT EXISTS ix_intake_source_profiles_public_slug "
                "ON intake_source_profiles(public_slug)"
            )

        if not _table_exists(cur, "intake_source_bindings"):
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS intake_source_bindings (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    intake_source_profile_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    external_key TEXT NOT NULL,
                    external_key_secondary TEXT NOT NULL DEFAULT '',
                    label TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    priority INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                    updated_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                    UNIQUE(tenant_id, provider, external_key, external_key_secondary),
                    FOREIGN KEY(intake_source_profile_id) REFERENCES intake_source_profiles(id)
                )
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS ix_intake_source_bindings_tenant_id "
                "ON intake_source_bindings(tenant_id)"
            )

        conn.commit()
