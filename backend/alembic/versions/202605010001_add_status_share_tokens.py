"""add status share tokens to candidates

Revision ID: 202605010001
Revises: 202604050001_public_intake_columns
Create Date: 2025-05-01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202605010001"
down_revision = "202604050001_public_intake_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "candidates",
        sa.Column("status_share_token", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "candidates",
        sa.Column("status_share_token_created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "candidates",
        sa.Column("status_share_token_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint(
        "uq_candidates_status_share_token",
        "candidates",
        ["status_share_token"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_candidates_status_share_token", "candidates", type_="unique")
    op.drop_column("candidates", "status_share_token_expires_at")
    op.drop_column("candidates", "status_share_token_created_at")
    op.drop_column("candidates", "status_share_token")
