"""Add lead stage column for CRM funnel (new, contacted, qualified, converted, lost).

Revision ID: 202602040001
Revises: 202601010001_meta_webhook_verify_token
Create Date: 2026-02-04

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202602040001_leads_add_stage"
down_revision = "202601010001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "leads",
        sa.Column("stage", sa.String(length=32), nullable=True),
    )
    op.create_index("ix_leads_stage", "leads", ["stage"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_leads_stage", table_name="leads")
    op.drop_column("leads", "stage")
