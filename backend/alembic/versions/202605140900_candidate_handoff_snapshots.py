"""candidate_handoff_snapshots — immutable payload at handoff create.

Revision ID: 202605140900_ch_snap
Revises: 202605130001_ch_ra_handoff
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202605140900_ch_snap"
down_revision: Union[str, None] = "202605130001_ch_ra_handoff"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "candidate_handoff_snapshots",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("handoff_id", sa.String(length=36), nullable=False),
        sa.Column("agency_tenant_id", sa.String(length=36), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["handoff_id"],
            ["candidate_handoffs.id"],
            name="fk_candidate_handoff_snapshots_handoff_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["agency_tenant_id"],
            ["tenants.id"],
            name="fk_candidate_handoff_snapshots_agency_tenant_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "uq_candidate_handoff_snapshots_handoff_id",
        "candidate_handoff_snapshots",
        ["handoff_id"],
        unique=True,
    )
    op.create_index(
        "ix_candidate_handoff_snapshots_agency_tenant_id",
        "candidate_handoff_snapshots",
        ["agency_tenant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_candidate_handoff_snapshots_agency_tenant_id", table_name="candidate_handoff_snapshots")
    op.drop_index("uq_candidate_handoff_snapshots_handoff_id", table_name="candidate_handoff_snapshots")
    op.drop_table("candidate_handoff_snapshots")
