from __future__ import annotations

import os
import sqlite3
from contextlib import closing


def _db_path() -> str:
    return os.environ.get("DEV_DB_PATH") or os.path.join(os.getcwd(), "app.db")


def _create_table(cur, sql: str) -> None:
    cur.execute(sql)


def ensure_candidate_children_schema() -> None:
    path = _db_path()
    if not os.path.exists(path):
        return

    with closing(sqlite3.connect(path)) as conn:
        cur = conn.cursor()
        _create_table(
            cur,
            """
            CREATE TABLE IF NOT EXISTS candidate_permits (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                candidate_id TEXT NOT NULL,
                permit_type TEXT NOT NULL,
                number TEXT,
                status TEXT NOT NULL,
                issued_on TEXT,
                expires_on TEXT,
                meta TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_candidate_permits_candidate ON candidate_permits(candidate_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_candidate_permits_tenant ON candidate_permits(tenant_id)"
        )

        _create_table(
            cur,
            """
            CREATE TABLE IF NOT EXISTS candidate_visas (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                candidate_id TEXT NOT NULL,
                visa_type TEXT NOT NULL,
                status TEXT NOT NULL,
                checkpoints TEXT,
                issued_on TEXT,
                meta TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_candidate_visas_candidate ON candidate_visas(candidate_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_candidate_visas_tenant ON candidate_visas(tenant_id)"
        )

        _create_table(
            cur,
            """
            CREATE TABLE IF NOT EXISTS candidate_tasks (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                candidate_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL,
                due_on TEXT,
                priority TEXT,
                assigned_to TEXT,
                completed INTEGER DEFAULT 0,
                meta TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_candidate_tasks_candidate ON candidate_tasks(candidate_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_candidate_tasks_tenant ON candidate_tasks(tenant_id)"
        )

        conn.commit()
