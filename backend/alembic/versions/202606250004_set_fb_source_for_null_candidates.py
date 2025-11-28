"""Set FB source for legacy candidates with missing source.

Revision ID: 202606250004_set_fb_source_for_null_candidates
Revises: 202606250003_backfill_candidate_sources_from_origin
Create Date: 2025-06-25 12:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202606250004_set_fb_source_for_null_candidates"
down_revision = "202606250003_backfill_candidate_sources_from_origin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE candidates
            SET source = 'FB'
            WHERE source IS NULL OR source = ''
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE candidates
            SET source = NULL
            WHERE source = 'FB'
            """
        )
    )

