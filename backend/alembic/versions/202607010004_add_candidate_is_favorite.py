"""Add is_favorite field to candidates

Revision ID: 202607010004_add_candidate_is_favorite
Revises: 202607010003_add_candidate_tags
Create Date: 2026-07-01 00:04:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202607010004_add_candidate_is_favorite"
down_revision: Union[str, None] = "202607010003_add_candidate_tags"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "candidates",
        sa.Column(
            "is_favorite",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index("ix_candidates_is_favorite", "candidates", ["is_favorite"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_candidates_is_favorite", table_name="candidates")
    op.drop_column("candidates", "is_favorite")
