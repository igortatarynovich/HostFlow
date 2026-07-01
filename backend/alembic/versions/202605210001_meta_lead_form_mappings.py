"""Per-form Meta lead field mapping templates.

Revision ID: 202605210001
Revises: 202605181500_hr_verified
Create Date: 2026-05-21
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "202605210001"
down_revision = "202605181500_hr_verified"
branch_labels = None
depends_on = None


def upgrade() -> None:
    json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")
    op.create_table(
        "meta_lead_form_mappings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="meta"),
        sa.Column("page_id", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("form_id", sa.String(length=64), nullable=False),
        sa.Column("form_name", sa.String(length=255), nullable=True),
        sa.Column("mapping_rules", json_type, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("last_sample_lead_id", sa.String(length=36), nullable=True),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
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
        sa.ForeignKeyConstraint(["last_sample_lead_id"], ["leads.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "source",
            "form_id",
            "page_id",
            name="uq_meta_lead_form_mappings_tenant_source_form_page",
        ),
    )
    op.create_index(
        "ix_meta_lead_form_mappings_tenant",
        "meta_lead_form_mappings",
        ["tenant_id"],
    )
    op.create_index(
        "ix_meta_lead_form_mappings_form_id",
        "meta_lead_form_mappings",
        ["form_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_meta_lead_form_mappings_form_id", table_name="meta_lead_form_mappings")
    op.drop_index("ix_meta_lead_form_mappings_tenant", table_name="meta_lead_form_mappings")
    op.drop_table("meta_lead_form_mappings")
