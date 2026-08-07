"""Add funnel_stages.labels_i18n for per-locale stage titles.

Revision ID: 202608070002_funnel_stage_labels_i18n
Revises: 202608070001_adr035_pipe
Create Date: 2026-08-07
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

RevisionType = Union[str, Sequence[str], None]

revision: str = "202608070002_funnel_stage_labels_i18n"
down_revision: RevisionType = "202608070001_adr035_pipe"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    op.add_column(
        "funnel_stages",
        sa.Column(
            "labels_i18n",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment='Per-locale stage titles, e.g. {"pl":"…","ru":"…","en":"…"}',
        ),
    )


def downgrade() -> None:
    op.drop_column("funnel_stages", "labels_i18n")
