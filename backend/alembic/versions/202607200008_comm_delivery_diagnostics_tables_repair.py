"""Repair: ensure C0.3 delivery diagnostics tables exist.

Production DBs may be Alembic-stamped past ``202607200003_comm_delivery_diagnostics``
while ``communication_delivery_attempts`` / callback unresolved tables were never
created (stamp drift). Questionnaire invite email send then 500s on
``record_delivery_attempt``. This revision is idempotent.

Revision ID: 202607200008_comm_delivery_diagnostics_tables_repair
Revises: 202607200007_comm_inbound_unresolved_resolved_cols_repair
Create Date: 2026-07-21
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


RevisionType = Union[str, Sequence[str], None]

revision: str = "202607200008_comm_delivery_diagnostics_tables_repair"
down_revision: RevisionType = "202607200007_comm_inbound_unresolved_resolved_cols_repair"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def _has_table(bind: sa.Connection, table: str) -> bool:
    return table in sa.inspect(bind).get_table_names()


def _has_index(bind: sa.Connection, table: str, name: str) -> bool:
    if not _has_table(bind, table):
        return False
    return any(idx.get("name") == name for idx in sa.inspect(bind).get_indexes(table))


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_table(bind, "communication_delivery_attempts"):
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

    for name, cols in (
        ("ix_comm_delivery_attempts_tenant_delivery", ["tenant_id", "delivery_id", "attempt_number"]),
        ("ix_comm_delivery_attempts_tenant_message", ["tenant_id", "message_id"]),
        ("ix_comm_delivery_attempts_provider_msg", ["tenant_id", "provider", "provider_message_id"]),
        ("ix_communication_delivery_attempts_tenant_id", ["tenant_id"]),
        ("ix_communication_delivery_attempts_message_id", ["message_id"]),
        ("ix_communication_delivery_attempts_delivery_id", ["delivery_id"]),
    ):
        if not _has_index(bind, "communication_delivery_attempts", name):
            op.create_index(name, "communication_delivery_attempts", cols, unique=False)

    if not _has_table(bind, "communication_delivery_callback_unresolved"):
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

    for name, cols in (
        ("ix_comm_delivery_cb_unresolved_tenant_status", ["tenant_id", "status", "created_at"]),
        ("ix_communication_delivery_callback_unresolved_tenant_id", ["tenant_id"]),
    ):
        if not _has_index(bind, "communication_delivery_callback_unresolved", name):
            op.create_index(name, "communication_delivery_callback_unresolved", cols, unique=False)


def downgrade() -> None:
    # Non-destructive repair: do not drop tables that may hold delivery diagnostics.
    return
