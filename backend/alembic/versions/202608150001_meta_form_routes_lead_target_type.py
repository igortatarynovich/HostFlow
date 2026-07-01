"""Meta form intake routes + Lead.lead_target_type.

Revision ID: 202608150001_meta_form_routes
Revises: 202608140001_process_engine_registry_p1
Create Date: 2026-08-15
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "202608150001_meta_form_routes"
down_revision: Union[str, Sequence[str], None] = "202608140001_process_engine_registry_p1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "meta_form_routes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="meta"),
        sa.Column("page_id", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("form_id", sa.String(length=64), nullable=False),
        sa.Column("own_company_id", sa.String(length=36), nullable=False),
        sa.Column("lead_target_type", sa.String(length=32), nullable=False, server_default="candidate"),
        sa.Column("pipeline_preset", sa.String(length=64), nullable=True),
        sa.Column("default_assignee_id", sa.String(length=36), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
        sa.ForeignKeyConstraint(["own_company_id"], ["own_companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["default_assignee_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "source",
            "form_id",
            "page_id",
            name="uq_meta_form_routes_tenant_source_form_page",
        ),
    )
    op.create_index("ix_meta_form_routes_tenant", "meta_form_routes", ["tenant_id"])
    op.create_index("ix_meta_form_routes_form_id", "meta_form_routes", ["form_id"])

    op.add_column(
        "leads",
        sa.Column("lead_target_type", sa.String(length=32), nullable=False, server_default="candidate"),
    )
    op.create_index("ix_leads_tenant_lead_target_type", "leads", ["tenant_id", "lead_target_type"])
    op.alter_column("leads", "lead_target_type", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_leads_tenant_lead_target_type", table_name="leads")
    op.drop_column("leads", "lead_target_type")
    op.drop_index("ix_meta_form_routes_form_id", table_name="meta_form_routes")
    op.drop_index("ix_meta_form_routes_tenant", table_name="meta_form_routes")
    op.drop_table("meta_form_routes")
