"""C1.2: communication_threads.work_version for optimistic concurrency.

Revision ID: 202607200006_comm_thread_work_version
Revises: 202607200005_comm_thread_sla_events
Create Date: 2026-07-20 23:30:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


RevisionType = Union[str, Sequence[str], None]

revision: str = "202607200006_comm_thread_work_version"
down_revision: RevisionType = "202607200005_comm_thread_sla_events"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    op.add_column(
        "communication_threads",
        sa.Column(
            "work_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )
    op.alter_column("communication_threads", "work_version", server_default=None)


def downgrade() -> None:
    op.drop_column("communication_threads", "work_version")
