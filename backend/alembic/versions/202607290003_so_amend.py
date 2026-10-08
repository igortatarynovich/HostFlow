"""Sales order commercial version + amendment history (ADR-032).

Revision ID: 202607290003_so_amend
Revises: 202607290002_ca_comm_defaults
Create Date: 2026-07-29

NOTE: revision id ≤32 chars.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


RevisionType = Union[str, Sequence[str], None]

revision: str = "202607290003_so_amend"
down_revision: RevisionType = "202607290002_ca_comm_defaults"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    op.add_column(
        "sales_orders",
        sa.Column(
            "commercial_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.add_column(
        "sales_orders",
        sa.Column(
            "commercial_versions",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("sales_orders", "commercial_versions")
    op.drop_column("sales_orders", "commercial_version")
