"""TikTok ad account connection for Instant Form sources.

Revision ID: 202610200002_tiktok_lead_connections
Revises: 202610200001_candidate_declared_facts
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202610200002_tiktok_lead_connections"
down_revision: Union[str, None] = "202610200001_candidate_declared_facts"
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
        "tiktok_lead_connections",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("own_company_id", sa.String(36), nullable=False),
        sa.Column("advertiser_id", sa.String(64), nullable=False),
        sa.Column("encrypted_access_token", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="connected"),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("tenant_id", "own_company_id", name="uq_tiktok_lead_connections_company"),
    )
    op.create_index("ix_tiktok_lead_connections_tenant_id", "tiktok_lead_connections", ["tenant_id"])
    _rls_tenant("tiktok_lead_connections")


def downgrade() -> None:
    op.drop_index("ix_tiktok_lead_connections_tenant_id", table_name="tiktok_lead_connections")
    op.drop_table("tiktok_lead_connections")
