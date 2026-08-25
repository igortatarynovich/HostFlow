"""G19: Message Context columns on communication_messages + backfill.

Revision ID: 202607160002_comm_message_context
Revises: 202607160001_comm_thread_entity_links
Create Date: 2026-07-16 15:20:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


RevisionType = Union[str, Sequence[str], None]

revision: str = "202607160002_comm_message_context"
down_revision: RevisionType = "202607160001_comm_thread_entity_links"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    op.add_column(
        "communication_messages",
        sa.Column("context_entity_type", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "communication_messages",
        sa.Column("context_entity_id", sa.String(length=120), nullable=True),
    )
    op.create_index(
        "ix_comm_messages_tenant_context",
        "communication_messages",
        ["tenant_id", "context_entity_type", "context_entity_id"],
        unique=False,
    )

    # Backfill from legacy thread primary entity when message context is empty.
    op.execute(
        sa.text(
            """
            UPDATE communication_messages AS m
            SET
                context_entity_type = CASE
                    WHEN lower(btrim(t.entity_type)) IN ('inquiry', 'sales_inquiry') THEN 'lead'
                    WHEN lower(btrim(t.entity_type)) IN ('client', 'clientaccount') THEN 'client_account'
                    WHEN lower(btrim(t.entity_type)) IN ('order', 'serviceorder') THEN 'service_order'
                    ELSE lower(btrim(t.entity_type))
                END,
                context_entity_id = btrim(t.entity_id)
            FROM communication_threads AS t
            WHERE m.thread_id = t.id
              AND m.tenant_id = t.tenant_id
              AND m.context_entity_type IS NULL
              AND m.context_entity_id IS NULL
              AND t.entity_type IS NOT NULL
              AND btrim(t.entity_type) <> ''
              AND t.entity_id IS NOT NULL
              AND btrim(t.entity_id) <> ''
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_comm_messages_tenant_context", table_name="communication_messages")
    op.drop_column("communication_messages", "context_entity_id")
    op.drop_column("communication_messages", "context_entity_type")
