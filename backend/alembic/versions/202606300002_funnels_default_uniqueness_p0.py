"""Enforce one default funnel per (company_id, module_key, type) scope.

Revision ID: 202606300002_funnels_default_uniqueness_p0
Revises: 202606300001_funnels_company_module_scope_p0
Create Date: 2026-06-30

Dedupes duplicate is_default rows introduced by multi-company clone backfill, then
adds partial unique indexes for company-scoped and legacy tenant-scoped defaults.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202606300002_funnels_default_uniqueness_p0"
down_revision: Union[str, None] = "202606300001_funnels_company_module_scope_p0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(conn: sa.Connection, name: str) -> bool:
    return name in sa.inspect(conn).get_table_names()


def _dedupe_company_defaults(conn: sa.Connection) -> None:
    """Keep a single is_default per (company_id, module_key, type); clear the rest."""
    conn.execute(
        sa.text(
            """
            WITH ranked AS (
                SELECT
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY company_id, module_key, type
                        ORDER BY is_default DESC, name ASC, id ASC
                    ) AS rn
                FROM funnels
                WHERE company_id IS NOT NULL
                  AND module_key IS NOT NULL
                  AND type IS NOT NULL
                  AND is_default = true
            )
            UPDATE funnels f
            SET is_default = false
            FROM ranked r
            WHERE f.id = r.id
              AND r.rn > 1
            """
        )
    )


def _dedupe_legacy_tenant_defaults(conn: sa.Connection) -> None:
    """Keep a single legacy default per (tenant_id, module_key, type)."""
    conn.execute(
        sa.text(
            """
            WITH ranked AS (
                SELECT
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY tenant_id, module_key, type
                        ORDER BY is_default DESC, name ASC, id ASC
                    ) AS rn
                FROM funnels
                WHERE company_id IS NULL
                  AND module_key IS NOT NULL
                  AND type IS NOT NULL
                  AND is_default = true
                  AND tenant_id IS NOT NULL
            )
            UPDATE funnels f
            SET is_default = false
            FROM ranked r
            WHERE f.id = r.id
              AND r.rn > 1
            """
        )
    )


def upgrade() -> None:
    conn = op.get_bind()
    if not _has_table(conn, "funnels"):
        return

    _dedupe_company_defaults(conn)
    _dedupe_legacy_tenant_defaults(conn)

    dialect = conn.dialect.name
    if dialect == "postgresql":
        op.execute(
            sa.text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_funnels_company_default_scope
                ON funnels (company_id, module_key, type)
                WHERE is_default = true
                  AND company_id IS NOT NULL
                  AND module_key IS NOT NULL
                """
            )
        )
        op.execute(
            sa.text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_funnels_tenant_legacy_default_scope
                ON funnels (tenant_id, module_key, type)
                WHERE is_default = true
                  AND company_id IS NULL
                  AND module_key IS NOT NULL
                """
            )
        )
    else:
        # SQLite / dev: best-effort non-partial unique indexes are too strict; rely on dedupe + app checks.
        pass


def downgrade() -> None:
    conn = op.get_bind()
    if not _has_table(conn, "funnels"):
        return
    if conn.dialect.name == "postgresql":
        op.execute(sa.text("DROP INDEX IF EXISTS uq_funnels_tenant_legacy_default_scope"))
        op.execute(sa.text("DROP INDEX IF EXISTS uq_funnels_company_default_scope"))
