"""C0.3: delivery attempts + unresolved callback queue.

Revision ID: 202607200003_comm_delivery_diagnostics
Revises: 202607200002_comm_inbound_unresolved
Create Date: 2026-07-20 20:10:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


RevisionType = Union[str, Sequence[str], None]

revision: str = "202607200003_comm_delivery_diagnostics"
down_revision: RevisionType = "202607200002_comm_inbound_unresolved"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    op.create_table(
        "communication_delivery_attempts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("message_id", sa.String(length=36), nullable=False),
        sa.Column("delivery_id", sa.String(length=36), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("provider_account_id", sa.String(length=64), nullable=True),
        sa.Column("provider_message_id", sa.String(length=128), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canonical_result", sa.String(length=32), nullable=False),
        sa.Column("provider_status", sa.String(length=64), nullable=True),
        sa.Column("provider_code", sa.String(length=64), nullable=True),
        sa.Column("reason_code", sa.String(length=64), nullable=True),
        sa.Column("retryable", sa.Boolean(), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("safe_message", sa.Text(), nullable=True),
        sa.Column("raw_provider_payload", sa.JSON(), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=False),
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
        sa.UniqueConstraint(
            "tenant_id",
            "delivery_id",
            "attempt_number",
            name="uq_comm_delivery_attempt_number",
        ),
    )
    op.create_index(
        "ix_comm_delivery_attempts_tenant_delivery",
        "communication_delivery_attempts",
        ["tenant_id", "delivery_id", "attempt_number"],
        unique=False,
    )
    op.create_index(
        "ix_comm_delivery_attempts_tenant_message",
        "communication_delivery_attempts",
        ["tenant_id", "message_id"],
        unique=False,
    )
    op.create_index(
        "ix_comm_delivery_attempts_provider_msg",
        "communication_delivery_attempts",
        ["tenant_id", "provider", "provider_message_id"],
        unique=False,
    )
    op.create_index(
        "ix_communication_delivery_attempts_tenant_id",
        "communication_delivery_attempts",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_communication_delivery_attempts_message_id",
        "communication_delivery_attempts",
        ["message_id"],
        unique=False,
    )
    op.create_index(
        "ix_communication_delivery_attempts_delivery_id",
        "communication_delivery_attempts",
        ["delivery_id"],
        unique=False,
    )

    op.create_table(
        "communication_delivery_callback_unresolved",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("provider_account_id", sa.String(length=64), nullable=True),
        sa.Column("provider_event_id", sa.String(length=128), nullable=False),
        sa.Column("provider_message_id", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.String(length=64), nullable=False),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("resolved_delivery_id", sa.String(length=36), nullable=True),
        sa.Column("resolved_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint(
            "tenant_id",
            "provider",
            "provider_event_id",
            name="uq_comm_delivery_callback_event",
        ),
    )
    op.create_index(
        "ix_comm_delivery_cb_unresolved_tenant_status",
        "communication_delivery_callback_unresolved",
        ["tenant_id", "status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_communication_delivery_callback_unresolved_tenant_id",
        "communication_delivery_callback_unresolved",
        ["tenant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_communication_delivery_callback_unresolved_tenant_id",
        table_name="communication_delivery_callback_unresolved",
    )
    op.drop_index(
        "ix_comm_delivery_cb_unresolved_tenant_status",
        table_name="communication_delivery_callback_unresolved",
    )
    op.drop_table("communication_delivery_callback_unresolved")

    op.drop_index(
        "ix_communication_delivery_attempts_delivery_id",
        table_name="communication_delivery_attempts",
    )
    op.drop_index(
        "ix_communication_delivery_attempts_message_id",
        table_name="communication_delivery_attempts",
    )
    op.drop_index(
        "ix_communication_delivery_attempts_tenant_id",
        table_name="communication_delivery_attempts",
    )
    op.drop_index(
        "ix_comm_delivery_attempts_provider_msg",
        table_name="communication_delivery_attempts",
    )
    op.drop_index(
        "ix_comm_delivery_attempts_tenant_message",
        table_name="communication_delivery_attempts",
    )
    op.drop_index(
        "ix_comm_delivery_attempts_tenant_delivery",
        table_name="communication_delivery_attempts",
    )
    op.drop_table("communication_delivery_attempts")
