from __future__ import annotations

import os
import sqlite3
from contextlib import closing


def _db_path() -> str:
    return os.environ.get("DEV_DB_PATH") or os.path.join(os.getcwd(), "app.db")


def _table_exists(cur: sqlite3.Cursor, name: str) -> bool:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None


def _column_exists(cur: sqlite3.Cursor, table: str, column: str) -> bool:
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def ensure_leads_schema() -> None:
    """
    Ensure dev/test SQLite database has leads-related tables/columns for the Meta pipeline.
    """
    path = _db_path()
    if not os.path.exists(path):
        return

    with closing(sqlite3.connect(path)) as conn:
        cur = conn.cursor()

        # candidates.source / candidates.origin
        if _table_exists(cur, "candidates"):
            if not _column_exists(cur, "candidates", "source"):
                cur.execute("ALTER TABLE candidates ADD COLUMN source TEXT")
            if not _column_exists(cur, "candidates", "origin"):
                cur.execute("ALTER TABLE candidates ADD COLUMN origin TEXT")

        # meta_ads_map table
        if not _table_exists(cur, "meta_ads_map"):
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS meta_ads_map (
                    ad_id INTEGER PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    vacancy_id TEXT NOT NULL,
                    note TEXT,
                    created_at TEXT DEFAULT (CURRENT_TIMESTAMP)
                )
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS ix_meta_ads_map_tenant ON meta_ads_map(tenant_id)"
            )

        # leads table
        if not _table_exists(cur, "leads"):
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS leads (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    company_id TEXT NOT NULL,
                    vacancy_id TEXT,
                    source TEXT NOT NULL DEFAULT 'meta',
                    ad_id INTEGER,
                    payload TEXT NOT NULL,
                    normalized TEXT,
                    status TEXT NOT NULL DEFAULT 'new',
                    candidate_id TEXT,
                    external_id TEXT,
                    error TEXT,
                    last_routed_at TEXT,
                    created_at TEXT DEFAULT (CURRENT_TIMESTAMP)
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS ix_leads_tenant ON leads(tenant_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS ix_leads_status ON leads(status)")
            cur.execute("CREATE INDEX IF NOT EXISTS ix_leads_vacancy ON leads(vacancy_id)")
            cur.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_leads_tenant_source_external_id
                ON leads(tenant_id, source, external_id)
                WHERE external_id IS NOT NULL
                """
            )
        else:
            if not _column_exists(cur, "leads", "external_id"):
                cur.execute("ALTER TABLE leads ADD COLUMN external_id TEXT")
            if not _column_exists(cur, "leads", "last_routed_at"):
                cur.execute("ALTER TABLE leads ADD COLUMN last_routed_at TEXT")
            cur.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_leads_tenant_source_external_id
                ON leads(tenant_id, source, external_id)
                WHERE external_id IS NOT NULL
                """
            )

        if not _table_exists(cur, "lead_import_jobs"):
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS lead_import_jobs (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    total_rows INTEGER NOT NULL DEFAULT 0,
                    processed_rows INTEGER NOT NULL DEFAULT 0,
                    success_rows INTEGER NOT NULL DEFAULT 0,
                    duplicate_rows INTEGER NOT NULL DEFAULT 0,
                    failed_rows INTEGER NOT NULL DEFAULT 0,
                    started_at TEXT,
                    finished_at TEXT,
                    error_report TEXT,
                    meta TEXT,
                    created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                    updated_at TEXT DEFAULT (CURRENT_TIMESTAMP)
                )
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS ix_lead_import_jobs_tenant_status ON lead_import_jobs(tenant_id, status)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS ix_lead_import_jobs_tenant_creator ON lead_import_jobs(tenant_id, created_by)"
            )

        if _table_exists(cur, "user_company_access"):
            cur.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_user_company_access ON user_company_access(tenant_id, user_id, company_id)"
            )

        if not _table_exists(cur, "candidate_stage_history"):
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS candidate_stage_history (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    candidate_id TEXT NOT NULL,
                    from_code TEXT,
                    to_code TEXT NOT NULL,
                    reason TEXT,
                    actor TEXT,
                    at TEXT NOT NULL
                )
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS ix_candidate_stage_history_candidate ON candidate_stage_history(candidate_id)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS ix_candidate_stage_history_tenant ON candidate_stage_history(tenant_id)"
            )

        # meta_lead_credentials table
        if not _table_exists(cur, "meta_lead_credentials"):
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS meta_lead_credentials (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    label TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    encrypted_secret TEXT,
                    encrypted_access_token TEXT,
                    encrypted_ad_account_id TEXT,
                    encrypted_page_id TEXT,
                    last_verified_at TEXT,
                    last_rotation_at TEXT,
                    created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                    updated_at TEXT DEFAULT (CURRENT_TIMESTAMP)
                )
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS ix_meta_lead_credentials_tenant ON meta_lead_credentials(tenant_id)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS ix_meta_lead_credentials_status ON meta_lead_credentials(status)"
            )
        else:
            cur.execute(
                "CREATE INDEX IF NOT EXISTS ix_meta_lead_credentials_tenant ON meta_lead_credentials(tenant_id)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS ix_meta_lead_credentials_status ON meta_lead_credentials(status)"
            )

        # meta_lead_settings table
        if not _table_exists(cur, "meta_lead_settings"):
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS meta_lead_settings (
                    tenant_id TEXT PRIMARY KEY,
                    default_company_id TEXT,
                    fallback_recruiter_id TEXT,
                    auto_create_enabled INTEGER NOT NULL DEFAULT 1,
                    reroute_after_hours INTEGER,
                    mask_pii_in_logs INTEGER NOT NULL DEFAULT 1,
                    pull_field_data_from_graph INTEGER NOT NULL DEFAULT 1,
                    webhook_url TEXT,
                    last_webhook_check_at TEXT,
                    last_signature_status TEXT,
                    webhook_verify_token TEXT,
                    created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                    updated_at TEXT DEFAULT (CURRENT_TIMESTAMP)
                )
                """
            )
        else:
            if not _column_exists(cur, "meta_lead_settings", "webhook_verify_token"):
                cur.execute("ALTER TABLE meta_lead_settings ADD COLUMN webhook_verify_token TEXT")
            if not _column_exists(cur, "meta_lead_settings", "pull_field_data_from_graph"):
                cur.execute("ALTER TABLE meta_lead_settings ADD COLUMN pull_field_data_from_graph INTEGER DEFAULT 1")
            if not _column_exists(cur, "meta_lead_settings", "fallback_recruiter_id"):
                cur.execute("ALTER TABLE meta_lead_settings ADD COLUMN fallback_recruiter_id TEXT")
            if not _column_exists(cur, "meta_lead_settings", "last_webhook_check_at"):
                cur.execute("ALTER TABLE meta_lead_settings ADD COLUMN last_webhook_check_at TEXT")
            if not _column_exists(cur, "meta_lead_settings", "last_signature_status"):
                cur.execute("ALTER TABLE meta_lead_settings ADD COLUMN last_signature_status TEXT")

        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_meta_lead_settings_verify_token
            ON meta_lead_settings(webhook_verify_token)
            """
        )

        conn.commit()
