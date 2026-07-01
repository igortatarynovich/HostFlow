"""companies.enabled_modules — company-level module access (ADR-003)

Revision ID: 202605070001_companies_em
Revises: 202605060004_funnel_processing_by_hr_stage
Create Date: 2026-05-07

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202605070001_companies_em"
down_revision: Union[str, None] = "202605060004_funnel_processing_by_hr_stage"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(conn: sa.Connection, name: str) -> bool:
    return name in sa.inspect(conn).get_table_names()


def _has_column(conn: sa.Connection, table: str, column: str) -> bool:
    try:
        return any(c["name"] == column for c in sa.inspect(conn).get_columns(table))
    except Exception:
        return False


def upgrade() -> None:
    conn = op.get_bind()
    if not _has_table(conn, "companies") or _has_column(conn, "companies", "enabled_modules"):
        return
    dialect = conn.dialect.name
    if dialect == "postgresql":
        col = sa.Column(
            "enabled_modules",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        )
    else:
        col = sa.Column("enabled_modules", sa.JSON(), nullable=True)
    op.add_column("companies", col)


def downgrade() -> None:
    conn = op.get_bind()
    if not _has_table(conn, "companies") or not _has_column(conn, "companies", "enabled_modules"):
        return
    try:
        op.drop_column("companies", "enabled_modules")
    except Exception:
        pass
