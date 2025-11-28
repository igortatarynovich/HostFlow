from __future__ import annotations

import os
import sqlite3
from contextlib import closing


def _db_path() -> str:
    return os.environ.get("DEV_DB_PATH") or os.path.join(os.getcwd(), "app.db")


def _table_exists(cur: sqlite3.Cursor, name: str) -> bool:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None


def ensure_notifications_schema() -> None:
    """Ensure SQLite dev/test database has user_notifications table."""
    path = _db_path()
    if not os.path.exists(path):
        return

    with closing(sqlite3.connect(path)) as conn:
        cur = conn.cursor()
        if not _table_exists(cur, "user_notifications"):
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS user_notifications (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    entity_type TEXT,
                    entity_id TEXT,
                    payload TEXT,
                    channel TEXT NOT NULL DEFAULT 'in_app',
                    is_read INTEGER NOT NULL DEFAULT 0,
                    delivered_at TEXT,
                    read_at TEXT,
                    created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                    updated_at TEXT DEFAULT (CURRENT_TIMESTAMP)
                )
                """
            )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ix_user_notifications_tenant_user_read ON user_notifications(tenant_id, user_id, is_read)"
        )
        conn.commit()
        print("[notifications] ensure_notifications_schema executed")
