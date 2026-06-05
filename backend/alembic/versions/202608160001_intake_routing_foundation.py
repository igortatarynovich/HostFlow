"""Intake Routing Foundation schema (PR-2).

Revision ID: 202608160001_intake_routing_foundation
Revises: 202608150002_merge_process_engine_workforce_heads
Create Date: 2026-08-16
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "202608160001_intake_routing_foundation"
down_revision: Union[str, Sequence[str], None] = "202608150002_merge_process_engine_workforce_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _rls_tenant(table: str) -> None:
    if not _is_postgres():
        return
    op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY;')
    op.execute(
        f"""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE tablename = '{table}'
                AND policyname = 'rls_{table}_tenant'
            ) THEN
                CREATE POLICY rls_{table}_tenant ON {table}
                USING (tenant_id::uuid = current_setting('app.tenant_id')::uuid);
            END IF;
        END $$;
    """
    )


def upgrade() -> None:
    op.create_table(
        "intake_source_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False, server_default="unknown"),
        sa.Column("channel", sa.String(length=32), nullable=False, server_default="unknown"),
        sa.Column("own_company_id", sa.String(length=36), nullable=False),
        sa.Column("route_intent", sa.String(length=32), nullable=False, server_default="unknown"),
        sa.Column("pipeline_preset", sa.String(length=64), nullable=True),
        sa.Column("default_assignee_id", sa.String(length=36), nullable=True),
        sa.Column("default_language", sa.String(length=8), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["own_company_id"], ["own_companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["default_assignee_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_intake_source_profiles_tenant_code"),
    )
    op.create_index("ix_intake_source_profiles_tenant_id", "intake_source_profiles", ["tenant_id"])
    op.create_index(
        "ix_intake_source_profiles_tenant_active",
        "intake_source_profiles",
        ["tenant_id", "is_active"],
    )
    op.alter_column("intake_source_profiles", "provider", server_default=None)
    op.alter_column("intake_source_profiles", "channel", server_default=None)
    op.alter_column("intake_source_profiles", "route_intent", server_default=None)

    op.create_table(
        "intake_source_bindings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("intake_source_profile_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("external_key", sa.String(length=255), nullable=False),
        sa.Column("external_key_secondary", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
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
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["intake_source_profile_id"],
            ["intake_source_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "provider",
            "external_key",
            "external_key_secondary",
            name="uq_intake_source_bindings_tenant_provider_keys",
        ),
    )
    op.create_index("ix_intake_source_bindings_tenant_id", "intake_source_bindings", ["tenant_id"])
    op.create_index(
        "ix_intake_source_bindings_profile",
        "intake_source_bindings",
        ["intake_source_profile_id"],
    )
    op.create_index(
        "ix_intake_source_bindings_tenant_provider",
        "intake_source_bindings",
        ["tenant_id", "provider"],
    )
    op.alter_column("intake_source_bindings", "external_key_secondary", server_default=None)
    op.alter_column("intake_source_bindings", "priority", server_default=None)

    _rls_tenant("intake_source_profiles")
    _rls_tenant("intake_source_bindings")


def downgrade() -> None:
    op.drop_index("ix_intake_source_bindings_tenant_provider", table_name="intake_source_bindings")
    op.drop_index("ix_intake_source_bindings_profile", table_name="intake_source_bindings")
    op.drop_index("ix_intake_source_bindings_tenant_id", table_name="intake_source_bindings")
    op.drop_table("intake_source_bindings")

    op.drop_index("ix_intake_source_profiles_tenant_active", table_name="intake_source_profiles")
    op.drop_index("ix_intake_source_profiles_tenant_id", table_name="intake_source_profiles")
    op.drop_table("intake_source_profiles")
