"""Add tenant_links table for handoff infrastructure.

Revision ID: 202608010001
Revises: df8037565a0c
Create Date: 2026-08-01 10:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
RevisionType = Union[str, Sequence[str], None]

revision: str = "202608010001_tenant_links"
down_revision: RevisionType = "df8037565a0c"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def _has_table(conn, table: str) -> bool:
    return table in sa.inspect(conn).get_table_names()


def upgrade() -> None:
    conn = op.get_bind()
    if _has_table(conn, "tenant_links"):
        return

    # tenant_links: agency ↔ client (company or employer tenant)
    # agency_tenant_id: агентство (владелец кандидатов)
    # client_company_id: клиент как компания внутри agency (текущая модель)
    # client_tenant_id: клиент как отдельный employer tenant (будущее)
    op.create_table(
        "tenant_links",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("agency_tenant_id", sa.String(length=36), nullable=False, index=True),
        sa.Column(
            "client_company_id",
            sa.String(length=36),
            nullable=True,
            index=True,
            comment="Client as company under agency (current model)",
        ),
        sa.Column(
            "client_tenant_id",
            sa.String(length=36),
            nullable=True,
            index=True,
            comment="Client as separate employer tenant (future)",
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="active",
            index=True,
        ),
        sa.Column(
            "features_json",
            sa.JSON(),
            nullable=True,
            comment='{"handoff_enabled": false, "contact_policy": {}}',
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["agency_tenant_id"],
            ["tenants.id"],
            name="fk_tenant_links_agency",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["client_company_id"],
            ["companies.id"],
            name="fk_tenant_links_client_company",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["client_tenant_id"],
            ["tenants.id"],
            name="fk_tenant_links_client_tenant",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "(client_company_id IS NOT NULL AND client_tenant_id IS NULL) "
            "OR (client_company_id IS NULL AND client_tenant_id IS NOT NULL)",
            name="ck_tenant_links_client_exactly_one",
        ),
    )
    op.create_index(
        "ix_tenant_links_agency_client",
        "tenant_links",
        ["agency_tenant_id", "client_company_id", "client_tenant_id"],
        unique=False,
    )
    # Partial unique: one link per (agency, company)
    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX uq_tenant_links_agency_company ON tenant_links "
            "(agency_tenant_id, client_company_id) WHERE client_company_id IS NOT NULL"
        )
    )
    # Partial unique: one link per (agency, client_tenant)
    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX uq_tenant_links_agency_client_tenant ON tenant_links "
            "(agency_tenant_id, client_tenant_id) WHERE client_tenant_id IS NOT NULL"
        )
    )

    # Seed: create tenant_links for existing agency tenants and their companies
    # (handoff_enabled = false by default). PostgreSQL only (gen_random_uuid, partial indexes).
    if conn.dialect.name == "postgresql":
        op.execute(
            sa.text("""
            INSERT INTO tenant_links (id, agency_tenant_id, client_company_id, status, features_json, created_at, updated_at)
            SELECT
                gen_random_uuid()::text,
                c.tenant_id,
                c.id,
                'active',
                '{"handoff_enabled": false}'::json,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            FROM companies c
            JOIN tenants t ON t.id = c.tenant_id
            WHERE t.type = 'agency'
            AND c.is_archived = false
            AND NOT EXISTS (
                SELECT 1 FROM tenant_links tl
                WHERE tl.agency_tenant_id = c.tenant_id AND tl.client_company_id = c.id
            )
            """)
        )



def downgrade() -> None:
    conn = op.get_bind()
    if _has_table(conn, "tenant_links"):
        op.drop_index("uq_tenant_links_agency_company", table_name="tenant_links")
        op.drop_index("uq_tenant_links_agency_client_tenant", table_name="tenant_links")
        op.drop_index("ix_tenant_links_agency_client", table_name="tenant_links")
        op.drop_table("tenant_links")
