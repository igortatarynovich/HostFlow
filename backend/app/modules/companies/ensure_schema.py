from __future__ import annotations

import os
import sqlite3
from contextlib import closing


def _db_path() -> str:
    return os.environ.get("DEV_DB_PATH") or os.path.join(os.getcwd(), "app.db")


def ensure_companies_schema() -> None:
    """Idempotently add missing columns to the companies table (dev/test only)."""
    path = _db_path()
    if not os.path.exists(path):
        return

    with closing(sqlite3.connect(path)) as conn:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(companies)")
        existing = {row[1] for row in cur.fetchall()}

        def add_column(sql: str) -> None:
            cur.execute(sql)

        if "legal_name" not in existing:
            add_column("ALTER TABLE companies ADD COLUMN legal_name TEXT")
        if "owner_user_id" not in existing:
            add_column("ALTER TABLE companies ADD COLUMN owner_user_id TEXT")
        if "manager_user_id" not in existing:
            add_column("ALTER TABLE companies ADD COLUMN manager_user_id TEXT")
        if "tax_id" not in existing:
            add_column("ALTER TABLE companies ADD COLUMN tax_id TEXT")
        if "phone" not in existing:
            add_column("ALTER TABLE companies ADD COLUMN phone TEXT")
        if "email" not in existing:
            add_column("ALTER TABLE companies ADD COLUMN email TEXT")
        if "website" not in existing:
            add_column("ALTER TABLE companies ADD COLUMN website TEXT")
        if "notes" not in existing:
            add_column("ALTER TABLE companies ADD COLUMN notes TEXT")
        if "country_code" not in existing:
            add_column("ALTER TABLE companies ADD COLUMN country_code TEXT")
        if "is_archived" not in existing:
            add_column(
                "ALTER TABLE companies ADD COLUMN is_archived INTEGER DEFAULT 0 NOT NULL"
            )
        conn.commit()
