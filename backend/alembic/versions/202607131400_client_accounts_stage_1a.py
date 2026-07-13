"""Stage 1A: client_accounts table (link columns via ensure_schema).

Revision ID: 202607131400_client_accounts_stage_1a
Revises: 202608250002_adr019_domain_event_outbox_3a1
Create Date: 2026-07-13
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "202607131400_client_accounts_stage_1a"
down_revision: Union[str, Sequence[str], None] = "202608240001_document_expiry_notification_events_p2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    insp = sa.inspect(bind)

    if "client_accounts" in insp.get_table_names():
        return

    op.create_table(
        "client_accounts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("own_company_id", sa.String(length=36), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="prospect"),
        sa.Column("owner_user_id", sa.String(length=36), nullable=True),
        sa.Column("primary_contact_id", sa.String(length=36), nullable=True),
        sa.Column("primary_company_id", sa.String(length=36), nullable=True),
        sa.Column("source_lead_id", sa.String(length=36), nullable=True),
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
    )
    op.create_index("ix_client_accounts_tenant_id", "client_accounts", ["tenant_id"])
    op.create_index("ix_client_accounts_tenant_status", "client_accounts", ["tenant_id", "status"])
    op.create_index(
        "ix_client_accounts_tenant_display_name",
        "client_accounts",
        ["tenant_id", "display_name"],
    )
    if dialect == "postgresql":
        op.execute(
            """
            CREATE UNIQUE INDEX uq_client_accounts_tenant_source_lead
            ON client_accounts (tenant_id, source_lead_id)
            WHERE source_lead_id IS NOT NULL
            """
        )
    else:
        op.create_index(
            "uq_client_accounts_tenant_source_lead",
            "client_accounts",
            ["tenant_id", "source_lead_id"],
            unique=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    insp = sa.inspect(bind)
    if "client_accounts" not in insp.get_table_names():
        return
    if dialect == "postgresql":
        op.execute("DROP INDEX IF EXISTS uq_client_accounts_tenant_source_lead")
    else:
        op.drop_index("uq_client_accounts_tenant_source_lead", table_name="client_accounts")
    op.drop_index("ix_client_accounts_tenant_display_name", table_name="client_accounts")
    op.drop_index("ix_client_accounts_tenant_status", table_name="client_accounts")
    op.drop_index("ix_client_accounts_tenant_id", table_name="client_accounts")
    op.drop_table("client_accounts")
