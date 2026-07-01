"""company_module_settings — per-company module JSON (ADR-005)

Revision ID: 202605080001_cms
Revises: 202605070001_companies_em
Create Date: 2026-05-08

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202605080001_cms"
down_revision: Union[str, None] = "202605070001_companies_em"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(conn: sa.Connection, name: str) -> bool:
    return name in sa.inspect(conn).get_table_names()


def upgrade() -> None:
    conn = op.get_bind()
    if _has_table(conn, "company_module_settings"):
        return
    dialect = conn.dialect.name
    json_t = postgresql.JSONB(astext_type=sa.Text()) if dialect == "postgresql" else sa.JSON()
    op.create_table(
        "company_module_settings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False, index=True),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("module_key", sa.String(length=32), nullable=False),
        sa.Column("settings_json", json_t, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("configured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "company_id", "module_key", name="uq_company_module_settings_scope"),
    )
    op.create_index(
        "ix_company_module_settings_company_module",
        "company_module_settings",
        ["company_id", "module_key"],
    )


def downgrade() -> None:
    conn = op.get_bind()
    if not _has_table(conn, "company_module_settings"):
        return
    op.drop_index("ix_company_module_settings_company_module", table_name="company_module_settings")
    op.drop_table("company_module_settings")
