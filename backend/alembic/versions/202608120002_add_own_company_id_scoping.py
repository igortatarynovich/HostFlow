"""add own_company_id to ops tables

Revision ID: 202608120002
Revises: 202608120001
Create Date: 2026-08-12 00:02:00.000000+00:00
"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202608120002"
down_revision: Union[str, Sequence[str], None] = "202608120001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(conn, table: str) -> bool:
    return table in sa.inspect(conn).get_table_names()


def _has_column(conn, table: str, column: str) -> bool:
    insp = sa.inspect(conn)
    try:
        return any(c["name"] == column for c in insp.get_columns(table))
    except Exception:
        return False


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    # 1) Add own_company_id columns (nullable for safety; we backfill below).
    targets: list[tuple[str, str]] = [
        ("vacancies", "own_company_id"),
        ("candidates", "own_company_id"),
        ("leads", "own_company_id"),
        ("documents", "own_company_id"),
        ("invoices", "own_company_id"),
        ("communication_threads", "own_company_id"),
        ("communication_messages", "own_company_id"),
    ]
    for table, col in targets:
        if not _has_table(conn, table) or _has_column(conn, table, col):
            continue
        op.add_column(table, sa.Column(col, sa.String(length=36), nullable=True))
        try:
            op.create_index(f"ix_{table}_{col}", table, [col])
        except Exception:
            pass

    # 2) Backfill: create a default own_company per tenant and attach all rows.
    if not _has_table(conn, "tenants") or not _has_table(conn, "own_companies"):
        return

    tenant_ids = []
    try:
        tenant_ids = [r[0] for r in conn.execute(sa.text("SELECT id FROM tenants")).fetchall()]
    except Exception:
        tenant_ids = []

    for tenant_id in tenant_ids:
        if not tenant_id:
            continue
        existing = conn.execute(
            sa.text("SELECT id FROM own_companies WHERE tenant_id = :tid ORDER BY created_at ASC LIMIT 1"),
            {"tid": tenant_id},
        ).fetchone()
        if existing and existing[0]:
            own_id = existing[0]
        else:
            own_id = str(uuid.uuid4())
            name_row = conn.execute(
                sa.text("SELECT name FROM tenants WHERE id = :tid LIMIT 1"),
                {"tid": tenant_id},
            ).fetchone()
            tenant_name = name_row[0] if name_row and name_row[0] else "My company"
            conn.execute(
                sa.text(
                    """
                    INSERT INTO own_companies (id, tenant_id, name, is_archived, contacts, extra, bank_details, created_at, updated_at)
                    VALUES (:id, :tid, :name, false, '{}'::json, '{}'::json, '{}'::json, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """
                    if conn.dialect.name == "postgresql"
                    else """
                    INSERT INTO own_companies (id, tenant_id, name, is_archived, contacts, extra, bank_details, created_at, updated_at)
                    VALUES (:id, :tid, :name, 0, '{}', '{}', '{}', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """
                ),
                {"id": own_id, "tid": tenant_id, "name": tenant_name},
            )

        # Apply own_company_id to tenant-scoped tables where missing.
        for table, col in targets:
            if not _has_table(conn, table) or not _has_column(conn, table, col):
                continue
            try:
                conn.execute(
                    sa.text(
                        f"UPDATE {table} SET {col} = :own_id WHERE tenant_id = :tid AND ({col} IS NULL OR {col} = '')"
                    ),
                    {"own_id": own_id, "tid": tenant_id},
                )
            except Exception:
                continue


def downgrade() -> None:
    conn = op.get_bind()
    targets: list[tuple[str, str]] = [
        ("communication_messages", "own_company_id"),
        ("communication_threads", "own_company_id"),
        ("invoices", "own_company_id"),
        ("documents", "own_company_id"),
        ("leads", "own_company_id"),
        ("candidates", "own_company_id"),
        ("vacancies", "own_company_id"),
    ]
    for table, col in targets:
        if not _has_table(conn, table) or not _has_column(conn, table, col):
            continue
        try:
            op.drop_index(f"ix_{table}_{col}", table_name=table)
        except Exception:
            pass
        op.drop_column(table, col)

