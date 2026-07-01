"""tenant_integration_installations + company_integration_enablements (ADR-006 MVP)

Revision ID: 202605090001_tint_ce
Revises: 202605080001_cms
Create Date: 2026-05-09

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202605090001_tint_ce"
down_revision: Union[str, None] = "202605080001_cms"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(conn: sa.Connection, name: str) -> bool:
    return name in sa.inspect(conn).get_table_names()


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name
    json_t = postgresql.JSONB(astext_type=sa.Text()) if dialect == "postgresql" else sa.JSON()

    if not _has_table(conn, "tenant_integration_installations"):
        op.create_table(
            "tenant_integration_installations",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("tenant_id", sa.String(length=36), nullable=False, index=True),
            sa.Column("offer_key", sa.String(length=64), nullable=False),
            sa.Column("offer_kind", sa.String(length=32), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False, server_default=sa.text("'active'")),
            sa.Column("settings_json", json_t, nullable=False, server_default=sa.text("'{}'")),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("tenant_id", "offer_key", name="uq_tenant_integration_installation"),
        )
        op.create_index(
            "ix_tenant_integration_tenant_offer",
            "tenant_integration_installations",
            ["tenant_id", "offer_key"],
        )

    if not _has_table(conn, "company_integration_enablements"):
        op.create_table(
            "company_integration_enablements",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("tenant_id", sa.String(length=36), nullable=False, index=True),
            sa.Column("company_id", sa.String(length=36), nullable=False, index=True),
            sa.Column("offer_key", sa.String(length=64), nullable=False),
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("usage_json", json_t, nullable=False, server_default=sa.text("'{}'")),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("company_id", "offer_key", name="uq_company_integration_enablement"),
        )
        op.create_index(
            "ix_company_integration_company_offer",
            "company_integration_enablements",
            ["company_id", "offer_key"],
        )
        op.create_index(
            "ix_company_integration_tenant_company",
            "company_integration_enablements",
            ["tenant_id", "company_id"],
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _has_table(conn, "company_integration_enablements"):
        op.drop_index("ix_company_integration_tenant_company", table_name="company_integration_enablements")
        op.drop_index("ix_company_integration_company_offer", table_name="company_integration_enablements")
        op.drop_table("company_integration_enablements")
    if _has_table(conn, "tenant_integration_installations"):
        op.drop_index("ix_tenant_integration_tenant_offer", table_name="tenant_integration_installations")
        op.drop_table("tenant_integration_installations")
