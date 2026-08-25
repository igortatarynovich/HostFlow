"""Backfill tenant_licenses usage limit columns on the active migration chain.

Revision ID: 202607141200_tenant_license_usage_limit_columns
Revises: 202607131402
Create Date: 2026-07-14 12:00:00.000000

The legacy revision 202501010000_add_tenant_limits_and_document_policies is not
reachable from the current head; tenant_management_phase1 created tenant_licenses
without max_candidates_active and related counters expected by TenantLicense ORM.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202607141200_tenant_license_usage_limit_columns"
down_revision: Union[str, Sequence[str], None] = "202607131402"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(conn, table: str) -> bool:
    return table in sa.inspect(conn).get_table_names()


def _has_column(conn, table: str, column: str) -> bool:
    return any(col["name"] == column for col in sa.inspect(conn).get_columns(table))


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql" or not _has_table(conn, "tenant_licenses"):
        return

    columns = (
        ("max_candidates_active", sa.Integer()),
        ("max_vacancies_active", sa.Integer()),
        ("max_documents", sa.Integer()),
        ("max_public_portal_links", sa.Integer()),
    )
    for name, col_type in columns:
        if not _has_column(conn, "tenant_licenses", name):
            op.add_column(
                "tenant_licenses",
                sa.Column(name, col_type, nullable=False, server_default="0"),
            )


def downgrade() -> None:
    conn = op.get_bind()
    if not _has_table(conn, "tenant_licenses"):
        return
    for name in (
        "max_public_portal_links",
        "max_documents",
        "max_vacancies_active",
        "max_candidates_active",
    ):
        if _has_column(conn, "tenant_licenses", name):
            op.drop_column("tenant_licenses", name)
