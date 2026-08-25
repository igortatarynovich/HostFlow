"""C1.2: communication_thread_sla_events clock.

Revision ID: 202607200005_comm_thread_sla_events
Revises: 202607200004_comm_thread_next_action
Create Date: 2026-07-20 23:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


RevisionType = Union[str, Sequence[str], None]

revision: str = "202607200005_comm_thread_sla_events"
down_revision: RevisionType = "202607200004_comm_thread_next_action"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    op.create_table(
        "communication_thread_sla_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("thread_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column(
            "payload",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_comm_sla_ev_tenant_thread_at",
        "communication_thread_sla_events",
        ["tenant_id", "thread_id", "at"],
    )
    op.create_index(
        "ix_comm_sla_ev_tenant_type",
        "communication_thread_sla_events",
        ["tenant_id", "event_type", "at"],
    )


def downgrade() -> None:
    op.drop_index("ix_comm_sla_ev_tenant_type", table_name="communication_thread_sla_events")
    op.drop_index("ix_comm_sla_ev_tenant_thread_at", table_name="communication_thread_sla_events")
    op.drop_table("communication_thread_sla_events")
