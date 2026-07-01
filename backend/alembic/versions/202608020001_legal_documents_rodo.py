"""Add legal_documents and rodo_notifications tables.

Revision ID: 202608020001
Revises: 202608010001_tenant_links
Create Date: 2026-08-02 10:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

RevisionType = Union[str, Sequence[str], None]

revision: str = "202608020001_legal_documents_rodo"
down_revision: RevisionType = "202608010001_tenant_links"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def _has_table(conn, table: str) -> bool:
    return table in sa.inspect(conn).get_table_names()


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    if not _has_table(conn, "legal_documents"):
        op.create_table(
            "legal_documents",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column("tenant_id", sa.String(length=36), nullable=False, index=True),
            sa.Column(
                "type",
                sa.String(length=32),
                nullable=False,
                index=True,
                comment="rodo_clause | privacy_policy",
            ),
            sa.Column("version_id", sa.String(length=64), nullable=False, index=True),
            sa.Column("content_html", sa.Text(), nullable=True),
            sa.Column("content_url", sa.String(length=512), nullable=True),
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
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
                ["tenant_id"],
                ["tenants.id"],
                name="fk_legal_documents_tenant",
                ondelete="CASCADE",
            ),
        )
        op.create_index(
            "ix_legal_documents_tenant_type_active",
            "legal_documents",
            ["tenant_id", "type", "is_active"],
        )

    if not _has_table(conn, "rodo_notifications"):
        op.create_table(
            "rodo_notifications",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column("candidate_id", sa.String(length=36), nullable=False, index=True),
            sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("sent_by_user_id", sa.String(length=36), nullable=True, index=True),
            sa.Column(
                "channel",
                sa.String(length=32),
                nullable=False,
                server_default="email",
                comment="email | sms | whatsapp",
            ),
            sa.Column("recipient", sa.String(length=255), nullable=False),
            sa.Column("rodo_version_id", sa.String(length=64), nullable=False),
            sa.Column(
                "status",
                sa.String(length=32),
                nullable=False,
                server_default="sent",
                comment="sent | failed",
            ),
            sa.Column("provider_message_id", sa.String(length=255), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(
                ["candidate_id"],
                ["candidates.id"],
                name="fk_rodo_notifications_candidate",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["sent_by_user_id"],
                ["users.id"],
                name="fk_rodo_notifications_sent_by",
                ondelete="SET NULL",
            ),
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _has_table(conn, "rodo_notifications"):
        op.drop_table("rodo_notifications")
    if _has_table(conn, "legal_documents"):
        op.drop_index("ix_legal_documents_tenant_type_active", table_name="legal_documents")
        op.drop_table("legal_documents")
