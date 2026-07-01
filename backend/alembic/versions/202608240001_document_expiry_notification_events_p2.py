"""Notification events registry table (P2).

Revision ID: 202608240001_document_expiry_notification_events_p2
Revises: 202608230001_requirement_rules_tenant_overrides_p3b
Create Date: 2026-06-24 12:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


RevisionType = Union[str, Sequence[str], None]

revision: str = "202608240001_document_expiry_notification_events_p2"
down_revision: RevisionType = "202608230001_requirement_rules_tenant_overrides_p3b"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    op.create_table(
        "notification_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("event_key", sa.String(length=512), nullable=False),
        sa.Column(
            "evaluation_version",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'notification_event_v1'"),
        ),
        sa.Column("event_code", sa.String(length=64), nullable=False),
        sa.Column(
            "source_layer",
            sa.String(length=64),
            nullable=False,
            server_default=sa.text("'document_expiry_notifications'"),
        ),
        sa.Column("owner_type", sa.String(length=32), nullable=False),
        sa.Column("owner_id", sa.String(length=64), nullable=False),
        sa.Column("document_id", sa.String(length=64), nullable=True),
        sa.Column("document_type_code", sa.String(length=128), nullable=True),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column(
            "document_runtime",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=False,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=True,
        ),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'open'"),
        ),
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
        sa.UniqueConstraint("tenant_id", "event_key", name="uq_notification_events_tenant_event_key"),
    )
    op.create_index(
        "ix_notification_events_tenant_id",
        "notification_events",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_notification_events_event_key",
        "notification_events",
        ["event_key"],
        unique=False,
    )
    op.create_index(
        "ix_notification_events_event_code",
        "notification_events",
        ["event_code"],
        unique=False,
    )
    op.create_index(
        "ix_notification_events_source_layer",
        "notification_events",
        ["source_layer"],
        unique=False,
    )
    op.create_index(
        "ix_notification_events_status",
        "notification_events",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_notification_events_owner",
        "notification_events",
        ["tenant_id", "owner_type", "owner_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_notification_events_owner", table_name="notification_events")
    op.drop_index("ix_notification_events_status", table_name="notification_events")
    op.drop_index("ix_notification_events_source_layer", table_name="notification_events")
    op.drop_index("ix_notification_events_event_code", table_name="notification_events")
    op.drop_index("ix_notification_events_event_key", table_name="notification_events")
    op.drop_index("ix_notification_events_tenant_id", table_name="notification_events")
    op.drop_table("notification_events")
