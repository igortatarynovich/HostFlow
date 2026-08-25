"""C0.2: communication_inbound_unresolved queue table.

Revision ID: 202607200002_comm_inbound_unresolved
Revises: 202607200001_ca_manual_origin
Create Date: 2026-07-20 19:50:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


RevisionType = Union[str, Sequence[str], None]

revision: str = "202607200002_comm_inbound_unresolved"
down_revision: RevisionType = "202607200001_ca_manual_origin"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    op.create_table(
        "communication_inbound_unresolved",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("thread_id", sa.String(length=36), nullable=False),
        sa.Column("message_id", sa.String(length=36), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("external_message_ref", sa.String(length=255), nullable=True),
        sa.Column("sender_address", sa.String(length=255), nullable=True),
        sa.Column("resolution_reason", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("details_json", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("resolved_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_entity_type", sa.String(length=64), nullable=True),
        sa.Column("resolved_entity_id", sa.String(length=120), nullable=True),
        sa.Column("resolved_thread_id", sa.String(length=36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_comm_inbound_unresolved_tenant_status",
        "communication_inbound_unresolved",
        ["tenant_id", "status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_comm_inbound_unresolved_tenant_thread",
        "communication_inbound_unresolved",
        ["tenant_id", "thread_id"],
        unique=False,
    )
    op.create_index(
        "ix_comm_inbound_unresolved_tenant_message",
        "communication_inbound_unresolved",
        ["tenant_id", "message_id"],
        unique=True,
    )
    op.create_index(
        "ix_communication_inbound_unresolved_tenant_id",
        "communication_inbound_unresolved",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_communication_inbound_unresolved_thread_id",
        "communication_inbound_unresolved",
        ["thread_id"],
        unique=False,
    )
    op.create_index(
        "ix_communication_inbound_unresolved_message_id",
        "communication_inbound_unresolved",
        ["message_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_communication_inbound_unresolved_message_id",
        table_name="communication_inbound_unresolved",
    )
    op.drop_index(
        "ix_communication_inbound_unresolved_thread_id",
        table_name="communication_inbound_unresolved",
    )
    op.drop_index(
        "ix_communication_inbound_unresolved_tenant_id",
        table_name="communication_inbound_unresolved",
    )
    op.drop_index(
        "ix_comm_inbound_unresolved_tenant_message",
        table_name="communication_inbound_unresolved",
    )
    op.drop_index(
        "ix_comm_inbound_unresolved_tenant_thread",
        table_name="communication_inbound_unresolved",
    )
    op.drop_index(
        "ix_comm_inbound_unresolved_tenant_status",
        table_name="communication_inbound_unresolved",
    )
    op.drop_table("communication_inbound_unresolved")
