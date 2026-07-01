from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from typing import Iterable


def _db_path() -> str:
    return os.environ.get("DEV_DB_PATH") or os.path.join(os.getcwd(), "app.db")


def _table_exists(cur: sqlite3.Cursor, name: str) -> bool:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None


def _column_names(cur: sqlite3.Cursor, table: str) -> set[str]:
    cur.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cur.fetchall()}


def _add_column(cur: sqlite3.Cursor, table: str, column_def: str) -> None:
    cur.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")


def ensure_reminders_schema() -> None:
    """Ensure dev/test SQLite has expanded reminders + reminder_events."""
    path = _db_path()
    if not os.path.exists(path):
        return

    with closing(sqlite3.connect(path)) as conn:
        cur = conn.cursor()

        # reminders table
        if not _table_exists(cur, "reminders"):
            cur.execute(
                """
                CREATE TABLE reminders (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    title TEXT,
                    description TEXT,
                    owner_id TEXT,
                    assignee_id TEXT,
                    priority TEXT,
                    channel TEXT DEFAULT 'internal',
                    due_at TEXT NOT NULL,
                    remind_at TEXT,
                    duration_minutes INTEGER,
                    source TEXT,
                    snoozed_until TEXT,
                    completed_at TEXT,
                    recurrence_json TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    message TEXT,
                    payload TEXT,
                    created_by TEXT,
                    sent_at TEXT,
                    cancelled_at TEXT,
                    created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                    updated_at TEXT DEFAULT (CURRENT_TIMESTAMP)
                )
                """
            )
        else:
            existing_cols = _column_names(cur, "reminders")
            needed: Iterable[tuple[str, str]] = (
                ("title", "TEXT"),
                ("description", "TEXT"),
                ("owner_id", "TEXT"),
                ("assignee_id", "TEXT"),
                ("priority", "TEXT"),
                ("channel", "TEXT DEFAULT 'internal'"),
                ("remind_at", "TEXT"),
                ("duration_minutes", "INTEGER"),
                ("source", "TEXT"),
                ("snoozed_until", "TEXT"),
                ("completed_at", "TEXT"),
                ("recurrence_json", "TEXT"),
            )
            for name, coldef in needed:
                if name not in existing_cols:
                    _add_column(cur, "reminders", f"{name} {coldef}")

        cur.execute(
            "CREATE INDEX IF NOT EXISTS ix_reminders_assignee_remind ON reminders(tenant_id, assignee_id, remind_at)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ix_reminders_assignee_due ON reminders(tenant_id, assignee_id, due_at)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ix_reminders_status_due ON reminders(tenant_id, status, due_at)"
        )

        # reminder_events table
        if not _table_exists(cur, "reminder_events"):
            cur.execute(
                """
                CREATE TABLE reminder_events (
                    id TEXT PRIMARY KEY,
                    reminder_id TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload TEXT,
                    created_at TEXT DEFAULT (CURRENT_TIMESTAMP)
                )
                """
            )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ix_reminder_events_tenant ON reminder_events(tenant_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ix_reminder_events_reminder ON reminder_events(reminder_id)"
        )

        conn.commit()
        print("[reminders] ensure_reminders_schema executed")
