"""Meta leads admin console: credentials, settings, SLA fields.

Revision ID: 202512200001_meta_leads_admin_console
Revises: 202512160001_user_profile_preferences
Create Date: 2025-12-20 09:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "202512200001_meta_leads_admin_console"
down_revision: str | None = "202512160001_user_profile_preferences"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        rows = bind.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
        return any(row[1] == column for row in rows)

    row = bind.execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = :t
              AND column_name = :c
            LIMIT 1
            """
        ),
        {"t": table, "c": column},
    ).fetchone()
    return row is not None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    true_default = sa.text("1") if is_sqlite else sa.text("true")

    if not _has_column("leads", "last_routed_at"):
        op.add_column(
            "leads",
            sa.Column("last_routed_at", sa.DateTime(timezone=True), nullable=True),
        )

    op.create_table(
        "meta_lead_credentials",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("label", sa.String(length=128), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column("encrypted_secret", sa.Text(), nullable=True),
        sa.Column("encrypted_access_token", sa.Text(), nullable=True),
        sa.Column("encrypted_ad_account_id", sa.Text(), nullable=True),
        sa.Column("encrypted_page_id", sa.Text(), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_rotation_at", sa.DateTime(timezone=True), nullable=True),
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
    )
    op.create_index("ix_meta_lead_credentials_tenant", "meta_lead_credentials", ["tenant_id"])
    op.create_index("ix_meta_lead_credentials_status", "meta_lead_credentials", ["status"])

    op.create_table(
        "meta_lead_settings",
        sa.Column("tenant_id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "default_company_id",
            sa.String(length=36),
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "fallback_recruiter_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "auto_create_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=true_default,
        ),
        sa.Column("reroute_after_hours", sa.Integer(), nullable=True),
        sa.Column(
            "mask_pii_in_logs",
            sa.Boolean(),
            nullable=False,
            server_default=true_default,
        ),
        sa.Column("webhook_url", sa.String(length=512), nullable=True),
        sa.Column("last_webhook_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_signature_status", sa.String(length=32), nullable=True),
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
    )


def downgrade() -> None:
    if _has_column("leads", "last_routed_at"):
        op.drop_column("leads", "last_routed_at")

    op.drop_table("meta_lead_settings")
    op.drop_index("ix_meta_lead_credentials_status", table_name="meta_lead_credentials")
    op.drop_index("ix_meta_lead_credentials_tenant", table_name="meta_lead_credentials")
    op.drop_table("meta_lead_credentials")
