"""Add funnel_id to candidate_profiles.

Revision ID: 202602040003
Revises: 202608090001
Create Date: 2026-02-04

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202602040003_profile_funnel_id"
down_revision = "202608090001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add funnel_id without FK to avoid dependency on funnels migration branch
    op.add_column(
        "candidate_profiles",
        sa.Column("funnel_id", sa.String(length=36), nullable=True, index=True),
    )


def downgrade() -> None:
    op.drop_column("candidate_profiles", "funnel_id")
