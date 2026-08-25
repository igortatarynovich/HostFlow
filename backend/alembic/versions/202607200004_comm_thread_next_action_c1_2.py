"""C1.2: communication_thread_next_actions entity.

Revision ID: 202607200004_comm_thread_next_action
Revises: 202607200003_comm_delivery_diagnostics
Create Date: 2026-07-20 22:50:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


RevisionType = Union[str, Sequence[str], None]

revision: str = "202607200004_comm_thread_next_action"
down_revision: RevisionType = "202607200003_comm_delivery_diagnostics"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    op.create_table(
        "communication_thread_next_actions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("thread_id", sa.String(length=36), nullable=False),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_by", sa.String(length=36), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
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
        "ix_comm_tna_tenant_thread_created",
        "communication_thread_next_actions",
        ["tenant_id", "thread_id", "created_at"],
    )
    op.create_index(
        "ix_comm_tna_tenant_status",
        "communication_thread_next_actions",
        ["tenant_id", "status", "due_at"],
    )
    op.create_index(
        "ix_comm_tna_tenant_thread_status",
        "communication_thread_next_actions",
        ["tenant_id", "thread_id", "status"],
    )
    # One active next action per thread (Postgres).
    op.execute(
        """
        CREATE UNIQUE INDEX uq_comm_tna_one_active_per_thread
        ON communication_thread_next_actions (tenant_id, thread_id)
        WHERE status = 'active'
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_comm_tna_one_active_per_thread")
    op.drop_index("ix_comm_tna_tenant_thread_status", table_name="communication_thread_next_actions")
    op.drop_index("ix_comm_tna_tenant_status", table_name="communication_thread_next_actions")
    op.drop_index("ix_comm_tna_tenant_thread_created", table_name="communication_thread_next_actions")
    op.drop_table("communication_thread_next_actions")
