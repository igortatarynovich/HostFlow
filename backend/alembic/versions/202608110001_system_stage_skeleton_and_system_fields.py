"""Add funnel system_stage skeleton and immutable custom field flag.

Revision ID: 202608110001
Revises: 202608100002_merge_communications_heads
Create Date: 2026-08-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202608110001"
down_revision = "202608100002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "funnel_stages",
        sa.Column(
            "system_stage",
            sa.String(length=32),
            nullable=False,
            server_default="in_progress",
        ),
    )

    # Backfill canonical system skeleton buckets for existing stages.
    op.execute(
        sa.text(
            """
            UPDATE funnel_stages
            SET system_stage = CASE
              WHEN lower(code) IN ('new') THEN 'new'
              WHEN lower(code) IN ('employed', 'hired', 'probation_ok') THEN 'hired'
              WHEN lower(code) IN ('declined', 'rejected') THEN 'declined_rejected'
              ELSE 'in_progress'
            END
            """
        )
    )

    op.add_column(
        "custom_field_definitions",
        sa.Column(
            "is_system",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("custom_field_definitions", "is_system")
    op.drop_column("funnel_stages", "system_stage")
