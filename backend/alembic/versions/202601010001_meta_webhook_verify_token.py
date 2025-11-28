"""Add verify token to meta lead settings and external_id for leads

Revision ID: 202601010001
Revises: 202512210001
Create Date: 2026-01-01 00:01:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202601010001"
down_revision = "e16f5834c752"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("meta_lead_settings", sa.Column("webhook_verify_token", sa.String(length=255), nullable=True))
    op.create_index(
        "ix_meta_lead_settings_verify_token",
        "meta_lead_settings",
        ["webhook_verify_token"],
        unique=False,
    )

    op.add_column("leads", sa.Column("external_id", sa.String(length=128), nullable=True))
    op.create_index("ix_leads_external_id", "leads", ["external_id"], unique=False)
    op.create_index(
        "uq_leads_tenant_source_external_id",
        "leads",
        ["tenant_id", "source", "external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_leads_tenant_source_external_id", table_name="leads")
    op.drop_index("ix_leads_external_id", table_name="leads")
    op.drop_column("leads", "external_id")

    op.drop_index("ix_meta_lead_settings_verify_token", table_name="meta_lead_settings")
    op.drop_column("meta_lead_settings", "webhook_verify_token")
