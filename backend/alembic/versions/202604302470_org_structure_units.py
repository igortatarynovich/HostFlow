"""Tenant org structure: org_units tree, memberships, invite optional org_unit.

Revision ID: 202604302470_org_structure
Revises: 202604302460_fleet_managers
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202604302470_org_structure"
down_revision: Union[str, None] = "202604302460_fleet_managers"
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
    jtype = sa.JSON()
    if _is_postgres():
        jtype = sa.JSON().with_variant(postgresql.JSONB, "postgresql")
    uid = sa.String(36)
    ts = sa.TIMESTAMP(timezone=True)

    op.create_table(
        "org_units",
        sa.Column("id", uid, primary_key=True, nullable=False),
        sa.Column("tenant_id", uid, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("parent_id", uid, sa.ForeignKey("org_units.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("unit_type", sa.String(32), nullable=False, server_default="department"),
        sa.Column("code", sa.String(64), nullable=True),
        sa.Column("leader_user_id", uid, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("meta", jtype, nullable=True),
        sa.Column("created_at", ts, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", ts, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_org_units_tenant_parent", "org_units", ["tenant_id", "parent_id"])

    op.create_table(
        "org_unit_members",
        sa.Column("id", uid, primary_key=True, nullable=False),
        sa.Column("tenant_id", uid, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("org_unit_id", uid, sa.ForeignKey("org_units.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", uid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("role_in_unit", sa.String(32), nullable=False, server_default="member"),
        sa.Column("created_at", ts, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", ts, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("tenant_id", "org_unit_id", "user_id", name="uq_org_unit_member_tenant_unit_user"),
    )

    op.add_column(
        "user_invites",
        sa.Column("org_unit_id", uid, sa.ForeignKey("org_units.id", ondelete="SET NULL"), nullable=True, index=True),
    )

    _rls_tenant("org_units")
    _rls_tenant("org_unit_members")


def downgrade() -> None:
    if _is_postgres():
        for table in ("org_unit_members", "org_units"):
            op.execute(f'DROP POLICY IF EXISTS rls_{table}_tenant ON {table};')
            op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY;')

    op.drop_column("user_invites", "org_unit_id")
    op.drop_table("org_unit_members")
    op.drop_table("org_units")
