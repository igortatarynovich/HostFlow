"""B-1-SMS: communication_deliveries, short_links, tenant_sms_usage_ledger.

Revision ID: 202607151200_b1_sms
Revises: 202607151000_adr022_form_purpose
Create Date: 2026-07-15 12:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


RevisionType = Union[str, Sequence[str], None]

revision: str = "202607151200_b1_sms"
down_revision: RevisionType = "202607151000_adr022_form_purpose"
branch_labels: RevisionType = None
depends_on: RevisionType = None

JSONType = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def _has_table(conn, table: str) -> bool:
    return table in sa.inspect(conn).get_table_names()


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    if not _has_table(conn, "communication_deliveries"):
        op.create_table(
            "communication_deliveries",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("tenant_id", sa.String(length=36), nullable=False),
            sa.Column("company_id", sa.String(length=36), nullable=True),
            sa.Column("entity_type", sa.String(length=32), nullable=False),
            sa.Column("entity_id", sa.String(length=36), nullable=False),
            sa.Column("purpose", sa.String(length=64), nullable=False),
            sa.Column("channel", sa.String(length=32), nullable=False),
            sa.Column("provider", sa.String(length=32), nullable=False),
            sa.Column("invite_id", sa.String(length=36), nullable=True),
            sa.Column("recipient_normalized", sa.String(length=32), nullable=False),
            sa.Column("template_key", sa.String(length=128), nullable=False),
            sa.Column("template_version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("message_hash", sa.String(length=64), nullable=False),
            sa.Column("encoding", sa.String(length=16), nullable=False, server_default="gsm7"),
            sa.Column("parts_count", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("external_message_id", sa.String(length=128), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
            sa.Column("error_code", sa.String(length=64), nullable=True),
            sa.Column("error_detail", sa.Text(), nullable=True),
            sa.Column("sent_by_user_id", sa.String(length=36), nullable=True),
            sa.Column("idempotency_key", sa.String(length=128), nullable=True),
            sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("meta", JSONType, nullable=True),
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
            sa.ForeignKeyConstraint(
                ["invite_id"],
                ["lead_questionnaire_invites.id"],
                name="fk_communication_deliveries_invite",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["sent_by_user_id"],
                ["users.id"],
                name="fk_communication_deliveries_sent_by",
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_communication_deliveries_company_id", "communication_deliveries", ["company_id"])
        op.create_index(
            "ix_communication_deliveries_external_message_id",
            "communication_deliveries",
            ["external_message_id"],
        )
        op.create_index("ix_communication_deliveries_invite_id", "communication_deliveries", ["invite_id"])
        op.create_index(
            "ix_communication_deliveries_sent_by_user_id",
            "communication_deliveries",
            ["sent_by_user_id"],
        )
        op.create_index(
            "ix_communication_deliveries_tenant_entity",
            "communication_deliveries",
            ["tenant_id", "entity_type", "entity_id"],
        )
        op.create_index("ix_communication_deliveries_tenant_id", "communication_deliveries", ["tenant_id"])
        op.create_index(
            "uq_communication_deliveries_idempotency",
            "communication_deliveries",
            ["tenant_id", "idempotency_key"],
            unique=True,
            postgresql_where=sa.text("idempotency_key IS NOT NULL"),
        )

    if not _has_table(conn, "short_links"):
        op.create_table(
            "short_links",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("token", sa.String(length=32), nullable=False),
            sa.Column("tenant_id", sa.String(length=36), nullable=False),
            sa.Column("target_url", sa.String(length=2048), nullable=False),
            sa.Column("purpose", sa.String(length=64), nullable=False),
            sa.Column("entity_type", sa.String(length=32), nullable=True),
            sa.Column("entity_id", sa.String(length=36), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_short_links_tenant_entity", "short_links", ["tenant_id", "entity_type", "entity_id"])
        op.create_index("ix_short_links_tenant_id", "short_links", ["tenant_id"])
        op.create_index("ix_short_links_token", "short_links", ["token"], unique=True)

    if not _has_table(conn, "tenant_sms_usage_ledger"):
        op.create_table(
            "tenant_sms_usage_ledger",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("tenant_id", sa.String(length=36), nullable=False),
            sa.Column("delivery_id", sa.String(length=36), nullable=False),
            sa.Column("parts_count", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("provider_points", sa.Numeric(precision=12, scale=4), nullable=True),
            sa.Column(
                "recorded_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(
                ["delivery_id"],
                ["communication_deliveries.id"],
                name="fk_tenant_sms_usage_delivery",
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("delivery_id", name="tenant_sms_usage_ledger_delivery_id_key"),
        )
        op.create_index("ix_tenant_sms_usage_ledger_tenant_id", "tenant_sms_usage_ledger", ["tenant_id"])


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    if _has_table(conn, "tenant_sms_usage_ledger"):
        op.drop_index("ix_tenant_sms_usage_ledger_tenant_id", table_name="tenant_sms_usage_ledger")
        op.drop_table("tenant_sms_usage_ledger")

    if _has_table(conn, "short_links"):
        op.drop_index("ix_short_links_token", table_name="short_links")
        op.drop_index("ix_short_links_tenant_id", table_name="short_links")
        op.drop_index("ix_short_links_tenant_entity", table_name="short_links")
        op.drop_table("short_links")

    if _has_table(conn, "communication_deliveries"):
        op.drop_index("uq_communication_deliveries_idempotency", table_name="communication_deliveries")
        op.drop_index("ix_communication_deliveries_tenant_id", table_name="communication_deliveries")
        op.drop_index("ix_communication_deliveries_tenant_entity", table_name="communication_deliveries")
        op.drop_index("ix_communication_deliveries_sent_by_user_id", table_name="communication_deliveries")
        op.drop_index("ix_communication_deliveries_invite_id", table_name="communication_deliveries")
        op.drop_index("ix_communication_deliveries_external_message_id", table_name="communication_deliveries")
        op.drop_index("ix_communication_deliveries_company_id", table_name="communication_deliveries")
        op.drop_table("communication_deliveries")
