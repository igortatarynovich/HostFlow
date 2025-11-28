"""Admin users module: invites, audit log, refresh tokens.

Revision ID: 202512010001_admin_users_module
Revises: 20251021_merge_heads
Create Date: 2025-12-01 08:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202512010001_admin_users_module"
down_revision: str | None = "20251021_merge_heads"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    # SQLite: use PRAGMA to introspect table columns
    if bind.dialect.name == "sqlite":
        rows = bind.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
        return any(row[1] == column for row in rows)

    # PostgreSQL and others: query information_schema; use bind.execute with sa.text
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

    # users.tenant_id
    if not _has_column("users", "tenant_id"):
        op.add_column("users", sa.Column("tenant_id", sa.String(length=36), nullable=True))
    try:
        op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    except Exception:
        # index already exists (idempotent)
        pass

    # users.is_active
    if not _has_column("users", "is_active"):
        default_val = sa.text("1") if is_sqlite else sa.text("true")
        op.add_column(
            "users",
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=default_val,
            ),
        )

    json_type = sa.JSON().with_variant(postgresql.JSONB, "postgresql")

    op.create_table(
        "user_invites",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False, unique=True),
        sa.Column("invited_user_id", sa.String(length=36), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column(
            "metadata_json",
            json_type,
            nullable=True,
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
        sa.ForeignKeyConstraint(
            ("invited_user_id",),
            ("users.id",),
            name="fk_user_invites_user",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_user_invites_tenant", "user_invites", ["tenant_id"])
    op.create_index("ix_user_invites_email", "user_invites", ["email"])

    op.create_table(
        "auth_refresh_tokens",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False, unique=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by", sa.String(length=36), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("payload", json_type, nullable=True),
        sa.ForeignKeyConstraint(
            ("user_id",),
            ("users.id",),
            name="fk_auth_refresh_user",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_auth_refresh_user", "auth_refresh_tokens", ["user_id"])
    op.create_index("ix_auth_refresh_tenant", "auth_refresh_tokens", ["tenant_id"])

    op.create_table(
        "user_audit_log",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("actor_id", sa.String(length=36), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("payload", json_type, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ("user_id",),
            ("users.id",),
            name="fk_user_audit_user",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_user_audit_tenant", "user_audit_log", ["tenant_id"])
    op.create_index("ix_user_audit_user", "user_audit_log", ["user_id"])
    op.create_index("ix_user_audit_actor", "user_audit_log", ["actor_id"])


def downgrade() -> None:
    op.drop_index("ix_user_audit_actor", table_name="user_audit_log")
    op.drop_index("ix_user_audit_user", table_name="user_audit_log")
    op.drop_index("ix_user_audit_tenant", table_name="user_audit_log")
    op.drop_table("user_audit_log")

    op.drop_index("ix_auth_refresh_tenant", table_name="auth_refresh_tokens")
    op.drop_index("ix_auth_refresh_user", table_name="auth_refresh_tokens")
    op.drop_table("auth_refresh_tokens")

    op.drop_index("ix_user_invites_email", table_name="user_invites")
    op.drop_index("ix_user_invites_tenant", table_name="user_invites")
    op.drop_table("user_invites")

    if _has_column("users", "is_active"):
        op.drop_column("users", "is_active")

    try:
        op.drop_index("ix_users_tenant_id", table_name="users")
    except Exception:
        pass
    if _has_column("users", "tenant_id"):
        op.drop_column("users", "tenant_id")
