from __future__ import annotations

import os
import sqlite3
from contextlib import closing


def _db_path() -> str:
    return os.environ.get("DEV_DB_PATH") or os.path.join(os.getcwd(), "app.db")


def _table_exists(cur: sqlite3.Cursor, name: str) -> bool:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None


def ensure_automation_rules_schema() -> None:
    """Ensure dev/test SQLite has automation_rules table for minimal rules builder."""
    path = _db_path()
    if not os.path.exists(path):
        return

    with closing(sqlite3.connect(path)) as conn:
        cur = conn.cursor()
        if not _table_exists(cur, "automation_rules"):
            cur.execute(
                """
                CREATE TABLE automation_rules (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    trigger TEXT NOT NULL,
                    title TEXT,
                    conditions_json TEXT,
                    actions_json TEXT,
                    created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                    updated_at TEXT DEFAULT (CURRENT_TIMESTAMP)
                )
                """
            )
        cur.execute("CREATE INDEX IF NOT EXISTS ix_automation_rules_tenant_trigger ON automation_rules(tenant_id, trigger)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_automation_rules_tenant_enabled ON automation_rules(tenant_id, enabled)")
        conn.commit()
        print("[automation_rules] ensure_automation_rules_schema executed")

