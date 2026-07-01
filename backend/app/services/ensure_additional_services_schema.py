from __future__ import annotations

import os
import sqlite3
from contextlib import closing


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


def ensure_additional_services_schema() -> None:
    """Ensure dev/test SQLite has additional services tables/columns.

    This is a safety net for environments that run on SQLite without applying Alembic migrations.
    """
    path = _db_path()
    if not os.path.exists(path):
        return

    with closing(sqlite3.connect(path)) as conn:
        cur = conn.cursor()

        if not _table_exists(cur, "services"):
            cur.execute(
                """
                CREATE TABLE services (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    code TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    category TEXT,
                    unit TEXT,
                    base_price NUMERIC NOT NULL DEFAULT 0,
                    estimated_cost NUMERIC NOT NULL DEFAULT 0,
                    cost_currency TEXT NOT NULL DEFAULT 'PLN',
                    currency TEXT NOT NULL DEFAULT 'PLN',
                    vat_rate NUMERIC NOT NULL DEFAULT 23,
                    requires_schedule INTEGER NOT NULL DEFAULT 0,
                    requires_candidate INTEGER NOT NULL DEFAULT 0,
                    result_document_type TEXT,
                    requires_documents TEXT,
                    sla_hours INTEGER,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    meta TEXT,
                    created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                    updated_at TEXT DEFAULT (CURRENT_TIMESTAMP)
                )
                """
            )
        else:
            cols = _column_names(cur, "services")
            for name, coldef in (
                ("estimated_cost", "NUMERIC NOT NULL DEFAULT 0"),
                ("cost_currency", "TEXT NOT NULL DEFAULT 'PLN'"),
            ):
                if name not in cols:
                    _add_column(cur, "services", f"{name} {coldef}")

        if not _table_exists(cur, "service_orders"):
            cur.execute(
                """
                CREATE TABLE service_orders (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    candidate_id TEXT,
                    vacancy_id TEXT,
                    company_id TEXT,
                    status TEXT NOT NULL DEFAULT 'draft',
                    total_amount NUMERIC NOT NULL DEFAULT 0,
                    currency TEXT NOT NULL DEFAULT 'PLN',
                    vat_total NUMERIC NOT NULL DEFAULT 0,
                    requested_by TEXT,
                    assigned_to TEXT,
                    notes TEXT,
                    audit TEXT,
                    created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                    updated_at TEXT DEFAULT (CURRENT_TIMESTAMP)
                )
                """
            )
        else:
            cols = _column_names(cur, "service_orders")
            for name, coldef in (
                ("total_amount", "NUMERIC NOT NULL DEFAULT 0"),
                ("vat_total", "NUMERIC NOT NULL DEFAULT 0"),
                ("currency", "TEXT NOT NULL DEFAULT 'PLN'"),
                ("status", "TEXT NOT NULL DEFAULT 'draft'"),
                ("requested_by", "TEXT"),
                ("start_date", "TEXT"),
                ("end_date", "TEXT"),
                ("own_company_id", "TEXT"),
            ):
                if name not in cols:
                    _add_column(cur, "service_orders", f"{name} {coldef}")

        if not _table_exists(cur, "service_items"):
            cur.execute(
                """
                CREATE TABLE service_items (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    order_id TEXT NOT NULL,
                    service_id TEXT NOT NULL,
                    qty NUMERIC NOT NULL DEFAULT 1,
                    unit_price NUMERIC NOT NULL DEFAULT 0,
                    estimated_cost NUMERIC NOT NULL DEFAULT 0,
                    actual_cost NUMERIC,
                    cost_currency TEXT NOT NULL DEFAULT 'PLN',
                    cost_source TEXT,
                    cost_status TEXT NOT NULL DEFAULT 'missing',
                    vat_rate NUMERIC NOT NULL DEFAULT 0,
                    amount NUMERIC NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'pending',
                    required_documents TEXT,
                    result_document_type TEXT,
                    meta TEXT,
                    created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                    updated_at TEXT DEFAULT (CURRENT_TIMESTAMP)
                )
                """
            )
        else:
            cols = _column_names(cur, "service_items")
            for name, coldef in (
                ("estimated_cost", "NUMERIC NOT NULL DEFAULT 0"),
                ("actual_cost", "NUMERIC"),
                ("cost_currency", "TEXT NOT NULL DEFAULT 'PLN'"),
                ("cost_source", "TEXT"),
                ("cost_status", "TEXT NOT NULL DEFAULT 'missing'"),
            ):
                if name not in cols:
                    _add_column(cur, "service_items", f"{name} {coldef}")

        if not _table_exists(cur, "service_schedule"):
            cur.execute(
                """
                CREATE TABLE service_schedule (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    provider TEXT,
                    slot_start TEXT,
                    slot_end TEXT,
                    location TEXT,
                    status TEXT NOT NULL DEFAULT 'reserved',
                    meta TEXT,
                    created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                    updated_at TEXT DEFAULT (CURRENT_TIMESTAMP)
                )
                """
            )

        if not _table_exists(cur, "service_attachments"):
            cur.execute(
                """
                CREATE TABLE service_attachments (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    file_id TEXT NOT NULL,
                    label TEXT,
                    created_at TEXT DEFAULT (CURRENT_TIMESTAMP)
                )
                """
            )

        conn.commit()
        print("[additional-services] ensure_additional_services_schema executed")


def _postgres_sync_engine_url(raw: str) -> str:
    """SQLAlchemy sync URL using psycopg3 (``psycopg[binary]``), not psycopg2."""
    u = (raw or "").strip()
    if not u:
        return u
    if u.startswith("postgresql+asyncpg://"):
        return "postgresql+psycopg://" + u.split("postgresql+asyncpg://", 1)[1]
    if u.startswith("postgresql://") and "+" not in u.split("://", 1)[0]:
        return "postgresql+psycopg://" + u.split("postgresql://", 1)[1]
    return u


def ensure_service_orders_own_company_id_column() -> None:
    """Ensure ``service_orders.own_company_id`` exists on PostgreSQL (§2.4).

    Dev/test DBs may lag behind Alembic; SQLite is handled in ``ensure_additional_services_schema``.
    """
    try:
        from sqlalchemy import create_engine, inspect, text

        from backend.app.core.settings import settings
    except Exception:
        return

    raw = getattr(settings, "ASYNC_DATABASE_URL", None) or getattr(
        settings, "SYNC_DATABASE_URL", None
    )
    url = _postgres_sync_engine_url(str(raw or ""))
    if not url or "postgresql" not in url:
        return
    try:
        eng = create_engine(url)
        insp = inspect(eng)
        if "service_orders" not in insp.get_table_names():
            return
        cols = {c["name"] for c in insp.get_columns("service_orders")}
        if "own_company_id" in cols:
            return
        with eng.begin() as conn:
            conn.execute(
                text("ALTER TABLE service_orders ADD COLUMN own_company_id VARCHAR(36)")
            )
            try:
                conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_service_orders_own_company_id "
                        "ON service_orders (own_company_id)"
                    )
                )
            except Exception:
                pass
        print("[additional-services] added service_orders.own_company_id (postgres ensure)")
    except Exception as exc:  # pragma: no cover - best-effort
        print(f"[additional-services] service_orders.own_company_id ensure skipped: {exc}")

