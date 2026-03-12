"""Add tenant_email_config table for per-tenant SMTP settings.

Revision ID: 202608050001
Revises: 202608040001_candidate_handoffs
Create Date: 2026-08-05 10:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

RevisionType = Union[str, Sequence[str], None]

revision: str = "202608050001_tenant_email_config"
down_revision: RevisionType = "202608040001_candidate_handoffs"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def _has_table(conn, table: str) -> bool:
    return table in sa.inspect(conn).get_table_names()


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    if not _has_table(conn, "tenant_email_config"):
        op.create_table(
            "tenant_email_config",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column("tenant_id", sa.String(length=36), nullable=False, index=True),
            sa.Column(
                "provider",
                sa.String(length=32),
                nullable=False,
                server_default="smtp",
                comment="smtp",
            ),
            sa.Column("smtp_host", sa.String(length=256), nullable=True),
            sa.Column("smtp_port", sa.Integer(), nullable=True, server_default=sa.text("587")),
            sa.Column("smtp_user", sa.String(length=256), nullable=True),
            sa.Column("smtp_password_encrypted", sa.Text(), nullable=True),
            sa.Column("from_email", sa.String(length=256), nullable=False),
            sa.Column("from_name", sa.String(length=128), nullable=True),
            sa.Column("use_tls", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
                name="fk_tenant_email_config_tenant",
                ondelete="CASCADE",
            ),
            sa.UniqueConstraint("tenant_id", name="uq_tenant_email_config_tenant"),
        )


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    if _has_table(conn, "tenant_email_config"):
        op.drop_table("tenant_email_config")
