"""Add candidate_handoffs.destination for client vs internal HR handoff.

Revision ID: 202604302510_handoff_destination
Revises: 202604302500_fleet_assignments_not_null
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202604302510_handoff_destination"
down_revision: Union[str, None] = "202604302500_fleet_assignments_not_null"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "candidate_handoffs",
        sa.Column(
            "destination",
            sa.String(length=32),
            nullable=False,
            server_default="client_portal",
        ),
    )
    op.create_index(
        "ix_candidate_handoffs_destination",
        "candidate_handoffs",
        ["destination"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_candidate_handoffs_destination", table_name="candidate_handoffs")
    op.drop_column("candidate_handoffs", "destination")
