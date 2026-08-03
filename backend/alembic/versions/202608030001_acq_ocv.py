"""Stage 6 PR-6a — Outcome commercial value snapshot columns.

Revision ID: 202608030001_acq_ocv
Revises: 202607290002_ca_comm_defaults
Create Date: 2026-08-03

NOTE: revision id kept ≤32 chars for alembic_version.version_num VARCHAR(32).
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


RevisionType = Union[str, Sequence[str], None]

revision: str = "202608030001_acq_ocv"
down_revision: RevisionType = "202607290002_ca_comm_defaults"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    op.add_column(
        "acq_outcomes",
        sa.Column("commercial_value_amount", sa.Numeric(precision=18, scale=4), nullable=True),
    )
    op.add_column(
        "acq_outcomes",
        sa.Column("commercial_value_currency", sa.String(length=3), nullable=True),
    )
    op.add_column(
        "acq_outcomes",
        sa.Column("commercial_value_source", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "acq_outcomes",
        sa.Column("commercial_value_set_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("acq_outcomes", "commercial_value_set_at")
    op.drop_column("acq_outcomes", "commercial_value_source")
    op.drop_column("acq_outcomes", "commercial_value_currency")
    op.drop_column("acq_outcomes", "commercial_value_amount")
