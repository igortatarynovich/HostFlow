"""Persist R5 tenant_delta overlay (RPM-2 operator writer).

Revision ID: 202609030001_tenant_document_policy_delta
Revises: 202609020001_intake_token_tenant_invites

One current overlay per tenant. JSONB is exactly the R5 delta contract
(candidate.overrides / vacancy.additions / validity). reason and actor
are sibling metadata — they must not enter tenant_delta or merge.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "202609030001_tenant_document_policy_delta"
down_revision: Union[str, None] = "202609020001_intake_token_tenant_invites"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "tenant_document_policy_deltas"


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
    uid = sa.String(36)
    ts = sa.TIMESTAMP(timezone=True)
    json_type = JSONB().with_variant(sa.JSON(), "sqlite")

    op.create_table(
        _TABLE,
        sa.Column("id", uid, primary_key=True, nullable=False),
        sa.Column(
            "tenant_id",
            uid,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tenant_delta", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "updated_by_user_id",
            uid,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", ts, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", ts, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index(
        "ix_tenant_document_policy_deltas_tenant_id",
        _TABLE,
        ["tenant_id"],
        unique=True,
    )
    _rls_tenant(_TABLE)


def downgrade() -> None:
    op.drop_index("ix_tenant_document_policy_deltas_tenant_id", table_name=_TABLE)
    op.drop_table(_TABLE)
