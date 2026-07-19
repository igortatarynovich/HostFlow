"""C1: communication_thread_result_links — Thread ↔ opaque result ref.

Revision ID: 202607190004_thread_result_link_c1
Revises: 202607190003_flight_dispatch_ledger_r5
Create Date: 2026-07-19
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "202607190004_thread_result_link_c1"
down_revision: Union[str, Sequence[str], None] = "202607190003_flight_dispatch_ledger_r5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    insp = sa.inspect(bind)
    if "communication_thread_result_links" in insp.get_table_names():
        return

    json_type = postgresql.JSONB() if dialect == "postgresql" else sa.JSON()

    op.create_table(
        "communication_thread_result_links",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("thread_id", sa.String(length=36), nullable=False),
        sa.Column("module_owner", sa.String(length=32), nullable=False),
        sa.Column("result_type", sa.String(length=64), nullable=False),
        sa.Column("result_id", sa.String(length=64), nullable=False),
        sa.Column("ledger_id", sa.String(length=36), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="confirmed",
        ),
        sa.Column("meta", json_type, nullable=True),
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
            ["thread_id"],
            ["communication_threads.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "thread_id",
            name="uq_comm_thread_result_links_tenant_thread",
        ),
    )
    op.create_index(
        "ix_comm_thread_result_links_tenant_id",
        "communication_thread_result_links",
        ["tenant_id"],
    )
    op.create_index(
        "ix_comm_thread_result_links_thread_id",
        "communication_thread_result_links",
        ["thread_id"],
    )
    op.create_index(
        "ix_comm_thread_result_links_tenant_result",
        "communication_thread_result_links",
        ["tenant_id", "module_owner", "result_type", "result_id"],
    )
    op.create_index(
        "ix_comm_thread_result_links_tenant_ledger",
        "communication_thread_result_links",
        ["tenant_id", "ledger_id"],
    )

    if dialect == "postgresql":
        op.execute(
            "ALTER TABLE communication_thread_result_links ENABLE ROW LEVEL SECURITY"
        )
        op.execute(
            """
            DO $$
            BEGIN
              IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE tablename = 'communication_thread_result_links'
                  AND policyname = 'tenant_isolation'
              ) THEN
                CREATE POLICY tenant_isolation ON communication_thread_result_links
                  USING (tenant_id = current_setting('app.tenant_id', true))
                  WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
              END IF;
            END $$;
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    insp = sa.inspect(bind)
    if "communication_thread_result_links" not in insp.get_table_names():
        return
    if dialect == "postgresql":
        op.execute(
            "DROP POLICY IF EXISTS tenant_isolation ON communication_thread_result_links"
        )
        op.execute(
            "ALTER TABLE communication_thread_result_links DISABLE ROW LEVEL SECURITY"
        )
    op.drop_table("communication_thread_result_links")
