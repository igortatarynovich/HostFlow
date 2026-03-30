from __future__ import annotations

import logging
import os
import sqlite3
from contextlib import closing

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from backend.app.db.base import Base
from ...models.document import Document
from ...models.document_check import DocumentCheck
from ...models.document_ruleset import (
    DocumentRulesetDiff,
    DocumentRulesetUsage,
    DocumentRulesetVersion,
)
from ...models.document_template import DocumentTemplate
from ...models.document_type import DocumentType
from ...models.document_reporting import (
    BulkOperation,
    BulkOperationItem,
    DocumentComplianceLog,
    DocumentMetricsDaily,
    ReportExport,
    ReportSummary,
)

logger = logging.getLogger(__name__)

DOCUMENT_TABLES = [
    Document.__table__,
    DocumentType.__table__,
    DocumentTemplate.__table__,
    DocumentCheck.__table__,
    DocumentRulesetVersion.__table__,
    DocumentRulesetUsage.__table__,
    DocumentRulesetDiff.__table__,
    DocumentComplianceLog.__table__,
    DocumentMetricsDaily.__table__,
    BulkOperation.__table__,
    BulkOperationItem.__table__,
    ReportExport.__table__,
    ReportSummary.__table__,
]

_RULESET_VERSIONS_TABLE = """
CREATE TABLE document_ruleset_versions (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    own_company_id TEXT,
    version INTEGER NOT NULL,
    json_data TEXT NOT NULL DEFAULT '{}',
    comment TEXT,
    created_by TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    signature TEXT NOT NULL DEFAULT '',
    origin_version_id TEXT,
    rollback_comment TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_document_ruleset_global_version
    ON document_ruleset_versions (tenant_id, version) WHERE own_company_id IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_document_ruleset_scoped_version
    ON document_ruleset_versions (tenant_id, own_company_id, version) WHERE own_company_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_document_ruleset_versions_tenant
    ON document_ruleset_versions (tenant_id);
CREATE INDEX IF NOT EXISTS ix_document_ruleset_versions_own_company_id
    ON document_ruleset_versions (own_company_id);
"""

_RULESET_USAGE_TABLE = """
CREATE TABLE document_ruleset_usage (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    ruleset_version_id TEXT NOT NULL,
    used_in TEXT NOT NULL,
    reference_id TEXT,
    used_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS ix_document_ruleset_usage_version
    ON document_ruleset_usage (ruleset_version_id);
CREATE INDEX IF NOT EXISTS ix_document_ruleset_usage_tenant
    ON document_ruleset_usage (tenant_id);
"""

_RULESET_DIFFS_TABLE = """
CREATE TABLE document_ruleset_diffs (
    id TEXT PRIMARY KEY,
    ruleset_id_from TEXT NOT NULL,
    ruleset_id_to TEXT NOT NULL,
    diff_json TEXT NOT NULL DEFAULT '{}',
    computed_with TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_document_ruleset_diffs_from
    ON document_ruleset_diffs (ruleset_id_from);
CREATE INDEX IF NOT EXISTS ix_document_ruleset_diffs_to
    ON document_ruleset_diffs (ruleset_id_to);
"""


def _db_path() -> str:
    return os.environ.get("DEV_DB_PATH") or os.path.join(os.getcwd(), "app.db")


def _table_exists(cur: sqlite3.Cursor, name: str) -> bool:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None


def _ensure_table(cur: sqlite3.Cursor, name: str, ddl: str) -> None:
    if not _table_exists(cur, name):
        cur.executescript(ddl)


def _ensure_sqlite_schema(path: str) -> None:
    with closing(sqlite3.connect(path)) as conn:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(documents)")
        existing = {row[1] for row in cur.fetchall()}

        def add(sql: str) -> None:
            cur.execute(sql)

        if "owner_type" not in existing:
            add("ALTER TABLE documents ADD COLUMN owner_type TEXT")
        if "owner_id" not in existing:
            add("ALTER TABLE documents ADD COLUMN owner_id TEXT")
        if "candidate_id" not in existing:
            add("ALTER TABLE documents ADD COLUMN candidate_id TEXT")
        if "meta_json" not in existing:
            add("ALTER TABLE documents ADD COLUMN meta_json TEXT DEFAULT '{}' NOT NULL")
        if "version" not in existing:
            add("ALTER TABLE documents ADD COLUMN version INTEGER DEFAULT 1 NOT NULL")
        if "ordered_at" not in existing:
            add("ALTER TABLE documents ADD COLUMN ordered_at TEXT")
        if "valid_from" not in existing:
            add("ALTER TABLE documents ADD COLUMN valid_from TEXT")

        # document_types adjustments
        cur.execute("PRAGMA table_info(document_types)")
        doc_type_cols = {row[1] for row in cur.fetchall()}
        if "default_expire_in_days" not in doc_type_cols and "valid_days" in doc_type_cols:
            add("ALTER TABLE document_types RENAME COLUMN valid_days TO default_expire_in_days")
            doc_type_cols.add("default_expire_in_days")
        if "kind" not in doc_type_cols:
            add("ALTER TABLE document_types ADD COLUMN kind TEXT DEFAULT 'driver'")
        if "process_type" not in doc_type_cols:
            add("ALTER TABLE document_types ADD COLUMN process_type TEXT DEFAULT 'none'")
        if "aliases" not in doc_type_cols:
            add("ALTER TABLE document_types ADD COLUMN aliases TEXT DEFAULT '[]'")
        if "required_meta" not in doc_type_cols:
            add("ALTER TABLE document_types ADD COLUMN required_meta TEXT DEFAULT '[]'")
        if "owner_summary_weight" not in doc_type_cols:
            add("ALTER TABLE document_types ADD COLUMN owner_summary_weight INTEGER DEFAULT 0")
        if "i18n_key" not in doc_type_cols:
            add("ALTER TABLE document_types ADD COLUMN i18n_key TEXT")
        if "requires_custom_name" not in doc_type_cols:
            add("ALTER TABLE document_types ADD COLUMN requires_custom_name INTEGER DEFAULT 0")

        add(
            """
            UPDATE document_types
            SET i18n_key = COALESCE(NULLIF(i18n_key, ''), 'documents.catalog.' || code)
            """
        )

        # Ensure auxiliary ruleset tables used by the documents module exist (for dev SQLite DBs)
        _ensure_table(cur, "document_ruleset_versions", _RULESET_VERSIONS_TABLE)
        _ensure_table(cur, "document_ruleset_usage", _RULESET_USAGE_TABLE)
        _ensure_table(cur, "document_ruleset_diffs", _RULESET_DIFFS_TABLE)

        # Backfill missing columns on existing ruleset tables (for previously created DBs)
        if _table_exists(cur, "document_ruleset_versions"):
            cur.execute("PRAGMA table_info(document_ruleset_versions)")
            cols_versions = {row[1] for row in cur.fetchall()}
            if "signature" not in cols_versions:
                add("ALTER TABLE document_ruleset_versions ADD COLUMN signature TEXT DEFAULT '' NOT NULL")
            if "origin_version_id" not in cols_versions:
                add("ALTER TABLE document_ruleset_versions ADD COLUMN origin_version_id TEXT")
            if "rollback_comment" not in cols_versions:
                add("ALTER TABLE document_ruleset_versions ADD COLUMN rollback_comment TEXT")
            if "own_company_id" not in cols_versions:
                add("ALTER TABLE document_ruleset_versions ADD COLUMN own_company_id TEXT")
                add("DROP INDEX IF EXISTS uq_document_ruleset_versions_tenant_version")
                add(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_document_ruleset_global_version "
                    "ON document_ruleset_versions (tenant_id, version) WHERE own_company_id IS NULL"
                )
                add(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_document_ruleset_scoped_version "
                    "ON document_ruleset_versions (tenant_id, own_company_id, version) WHERE own_company_id IS NOT NULL"
                )
                add(
                    "CREATE INDEX IF NOT EXISTS ix_document_ruleset_versions_own_company_id "
                    "ON document_ruleset_versions (own_company_id)"
                )

        if _table_exists(cur, "document_ruleset_usage"):
            cur.execute("PRAGMA table_info(document_ruleset_usage)")
            cols_usage = {row[1] for row in cur.fetchall()}
            if "metadata" not in cols_usage:
                add("ALTER TABLE document_ruleset_usage ADD COLUMN metadata TEXT DEFAULT '{}' NOT NULL")

        if _table_exists(cur, "document_ruleset_diffs"):
            cur.execute("PRAGMA table_info(document_ruleset_diffs)")
            cols_diffs = {row[1] for row in cur.fetchall()}
            if "computed_with" not in cols_diffs:
                add("ALTER TABLE document_ruleset_diffs ADD COLUMN computed_with TEXT")

        conn.commit()


def _ensure_postgres_schema(sync_url: str) -> None:
    try:
        engine = create_engine(sync_url)
    except Exception as exc:  # pragma: no cover - connection failure logged and ignored
        logger.warning("[documents.ensure_schema] failed to connect to %s: %s", sync_url, exc)
        return

    try:
        with engine.begin() as conn:
            insp = inspect(conn)
            if "documents" not in insp.get_table_names():
                return

            if "document_types" in insp.get_table_names():
                dt_cols = {col["name"] for col in insp.get_columns("document_types")}
                if "default_expire_in_days" not in dt_cols and "valid_days" in dt_cols:
                    conn.execute(text("ALTER TABLE document_types RENAME COLUMN valid_days TO default_expire_in_days"))
                    dt_cols.add("default_expire_in_days")
                if "kind" not in dt_cols:
                    conn.execute(
                        text(
                            "ALTER TABLE document_types "
                            "ADD COLUMN kind document_kind_enum DEFAULT 'driver'::document_kind_enum NOT NULL"
                        )
                    )
                if "process_type" not in dt_cols:
                    conn.execute(
                        text(
                            "ALTER TABLE document_types "
                            "ADD COLUMN process_type document_process_type_enum DEFAULT 'none'::document_process_type_enum"
                        )
                    )
                if "aliases" not in dt_cols:
                    conn.execute(
                        text(
                            "ALTER TABLE document_types "
                            "ADD COLUMN aliases JSONB DEFAULT '[]'::jsonb NOT NULL"
                        )
                    )
                if "required_meta" not in dt_cols:
                    conn.execute(
                        text(
                            "ALTER TABLE document_types "
                            "ADD COLUMN required_meta JSONB DEFAULT '[]'::jsonb NOT NULL"
                        )
                    )
                if "owner_summary_weight" not in dt_cols:
                    conn.execute(
                        text(
                            "ALTER TABLE document_types "
                            "ADD COLUMN owner_summary_weight SMALLINT DEFAULT 0 NOT NULL"
                        )
                    )
                if "i18n_key" not in dt_cols:
                    conn.execute(
                        text(
                            "ALTER TABLE document_types "
                            "ADD COLUMN i18n_key VARCHAR(160)"
                        )
                    )
                if "requires_custom_name" not in dt_cols:
                    conn.execute(
                        text(
                            "ALTER TABLE document_types "
                            "ADD COLUMN requires_custom_name BOOLEAN DEFAULT FALSE NOT NULL"
                        )
                    )

                conn.execute(
                    text(
                        """
                        UPDATE document_types
                        SET i18n_key = COALESCE(NULLIF(i18n_key, ''), 'documents.catalog.' || code),
                            aliases = COALESCE(aliases, '[]'::jsonb),
                            required_meta = COALESCE(required_meta, '[]'::jsonb),
                            owner_summary_weight = COALESCE(owner_summary_weight, 0),
                            process_type = COALESCE(process_type, 'none'::document_process_type_enum),
                            kind = COALESCE(kind, 'driver'::document_kind_enum),
                            requires_custom_name = COALESCE(requires_custom_name, FALSE)
                        """
                    )
                )

            columns = {col["name"] for col in insp.get_columns("documents")}
            if "status" not in columns and "status_new" in columns:
                conn.execute(text("ALTER TABLE documents RENAME COLUMN status_new TO status"))
                columns.remove("status_new")
                columns.add("status")

            if "status" not in columns:
                conn.execute(
                    text(
                        """
                        ALTER TABLE documents
                        ADD COLUMN status document_status_enum_v2 DEFAULT 'missing'::document_status_enum_v2
                        """
                    )
                )
                conn.execute(
                    text(
                        "UPDATE documents SET status = 'missing'::document_status_enum_v2 WHERE status IS NULL"
                    )
                )
                columns.add("status")

            if "ordered_at" not in columns:
                conn.execute(text("ALTER TABLE documents ADD COLUMN ordered_at DATE"))
                columns.add("ordered_at")
            if "valid_from" not in columns:
                conn.execute(text("ALTER TABLE documents ADD COLUMN valid_from DATE"))
                columns.add("valid_from")

            if "document_ruleset_versions" in insp.get_table_names():
                versions_cols = {col["name"] for col in insp.get_columns("document_ruleset_versions")}
                if "signature" not in versions_cols:
                    conn.execute(
                        text(
                            "ALTER TABLE document_ruleset_versions ADD COLUMN signature TEXT DEFAULT '' NOT NULL"
                        )
                    )
                if "origin_version_id" not in versions_cols:
                    conn.execute(
                        text(
                            "ALTER TABLE document_ruleset_versions ADD COLUMN origin_version_id VARCHAR(36)"
                        )
                    )
                if "rollback_comment" not in versions_cols:
                    conn.execute(
                        text(
                            "ALTER TABLE document_ruleset_versions ADD COLUMN rollback_comment TEXT"
                        )
                    )
                if "own_company_id" not in versions_cols:
                    conn.execute(
                        text(
                            "ALTER TABLE document_ruleset_versions ADD COLUMN own_company_id VARCHAR(36)"
                        )
                    )
                    conn.execute(
                        text("DROP INDEX IF EXISTS uq_document_ruleset_versions_tenant_version")
                    )
                    conn.execute(
                        text(
                            "CREATE UNIQUE INDEX IF NOT EXISTS uq_document_ruleset_global_version "
                            "ON document_ruleset_versions (tenant_id, version) "
                            "WHERE own_company_id IS NULL"
                        )
                    )
                    conn.execute(
                        text(
                            "CREATE UNIQUE INDEX IF NOT EXISTS uq_document_ruleset_scoped_version "
                            "ON document_ruleset_versions (tenant_id, own_company_id, version) "
                            "WHERE own_company_id IS NOT NULL"
                        )
                    )
                    conn.execute(
                        text(
                            "CREATE INDEX IF NOT EXISTS ix_document_ruleset_versions_own_company_id "
                            "ON document_ruleset_versions (own_company_id)"
                        )
                    )

            if "document_ruleset_usage" in insp.get_table_names():
                usage_cols = {col["name"] for col in insp.get_columns("document_ruleset_usage")}
                if "metadata" not in usage_cols:
                    conn.execute(
                        text(
                            "ALTER TABLE document_ruleset_usage ADD COLUMN metadata JSONB DEFAULT '{}'::jsonb NOT NULL"
                        )
                    )

            if "document_ruleset_diffs" in insp.get_table_names():
                diffs_cols = {col["name"] for col in insp.get_columns("document_ruleset_diffs")}
                if "computed_with" not in diffs_cols:
                    conn.execute(
                        text(
                            "ALTER TABLE document_ruleset_diffs ADD COLUMN computed_with TEXT"
                        )
                    )
    except SQLAlchemyError as exc:  # pragma: no cover - best effort for legacy DBs
        logger.warning("[documents.ensure_schema] postgres adjustments failed: %s", exc)
    finally:
        engine.dispose()


def _normalize_sqlite_url(url: str, path: str) -> str:
    if not url:
        return f"sqlite:///{path}"
    if url.startswith("sqlite+"):
        # Strip async driver suffix
        return url.replace("sqlite+aiosqlite", "sqlite", 1)
    return url


def ensure_documents_schema() -> None:
    path = _db_path()
    sync_url = (
        os.environ.get("ALEMBIC_DATABASE_URL")
        or os.environ.get("SQLALCHEMY_DATABASE_URI")
        or os.environ.get("DATABASE_URL")
        or ""
    ).strip()

    sync_url = _normalize_sqlite_url(sync_url, path)

    try:
        engine = create_engine(sync_url, future=True)
        Base.metadata.create_all(engine, tables=DOCUMENT_TABLES)
        engine.dispose()
    except Exception as exc:
        logger.warning("[documents.ensure_schema] create_all failed: %s", exc)

    if sync_url.lower().startswith("postgresql"):
        _ensure_postgres_schema(sync_url)
    else:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        _ensure_sqlite_schema(path)
