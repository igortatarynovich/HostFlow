"""RPM-2 document_policy_tenant_overlays (R5 tenant_delta store).

Revision ID: 202609020002_document_policy_tenant_overlays_rpm2
Revises: 202608310001_bootstrap_admin_schema
Create Date: 2026-09-02

One row per tenant. RLS on app.tenant_id. Not P3B overrides. Not ruleset JSON.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202609020002_document_policy_tenant_overlays_rpm2"
down_revision: Union[str, None] = "202608310001_bootstrap_admin_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "document_policy_tenant_overlays"


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _rls_tenant(table: str) -> None:
    if not _is_postgres():
        return
    op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY;')
    # TI-4 pattern: FORCE so table owner cannot silently bypass policies.
    # Not listed in rls_force_exceptions / rls_uncovered_tables allowlists.
    op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY;')
    op.execute(
        f"""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE tablename = '{table}'
                AND policyname = 'rls_{table}_tenant'
            ) THEN
                CREATE POLICY rls_{table}_tenant ON {table}
                USING (tenant_id::uuid = current_setting('app.tenant_id')::uuid)
                WITH CHECK (tenant_id::uuid = current_setting('app.tenant_id')::uuid);
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    json_type = (
        postgresql.JSONB(astext_type=sa.Text())
        if _is_postgres()
        else sa.JSON()
    )
    op.create_table(
        _TABLE,
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("delta", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("updated_by_user_id", sa.String(length=36), nullable=True),
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
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("tenant_id"),
    )
    _rls_tenant(_TABLE)


def downgrade() -> None:
    if _is_postgres():
        op.execute(f'DROP POLICY IF EXISTS rls_{_TABLE}_tenant ON "{_TABLE}";')
        op.execute(f'ALTER TABLE "{_TABLE}" NO FORCE ROW LEVEL SECURITY;')
        op.execute(f'ALTER TABLE "{_TABLE}" DISABLE ROW LEVEL SECURITY;')
    op.drop_table(_TABLE)
