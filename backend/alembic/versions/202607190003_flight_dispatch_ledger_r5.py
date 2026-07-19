"""R5: Flights dispatch provenance ledger.

Revision ID: 202607190003_flight_dispatch_ledger_r5
Revises: 202607190002_sales_inquiries_r4
Create Date: 2026-07-19
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "202607190003_flight_dispatch_ledger_r5"
down_revision: Union[str, Sequence[str], None] = "202607190002_sales_inquiries_r4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    insp = sa.inspect(bind)
    if "acq_flight_dispatch_ledger" in insp.get_table_names():
        return

    json_type = postgresql.JSONB() if dialect == "postgresql" else sa.JSON()

    op.create_table(
        "acq_flight_dispatch_ledger",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("idempotency_key", sa.String(length=191), nullable=False),
        sa.Column("handoff_id", sa.String(length=64), nullable=True),
        sa.Column("transport_lead_id", sa.String(length=36), nullable=False),
        sa.Column("route_intent", sa.String(length=64), nullable=False),
        sa.Column("destination", sa.String(length=32), nullable=False),
        sa.Column("dispatcher_id", sa.String(length=128), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("module_owner", sa.String(length=32), nullable=True),
        sa.Column("result_type", sa.String(length=64), nullable=True),
        sa.Column("result_id", sa.String(length=64), nullable=True),
        sa.Column("failure_code", sa.String(length=128), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("meta", json_type, nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index(
        "ix_acq_flight_dispatch_ledger_tenant_id",
        "acq_flight_dispatch_ledger",
        ["tenant_id"],
    )
    op.create_index(
        "ix_acq_flight_dispatch_ledger_handoff_id",
        "acq_flight_dispatch_ledger",
        ["handoff_id"],
    )
    op.create_index(
        "ix_acq_flight_dispatch_ledger_tenant_status",
        "acq_flight_dispatch_ledger",
        ["tenant_id", "status"],
    )
    op.create_index(
        "ix_acq_flight_dispatch_ledger_tenant_transport",
        "acq_flight_dispatch_ledger",
        ["tenant_id", "transport_lead_id"],
    )
    op.create_unique_constraint(
        "uq_acq_flight_dispatch_ledger_tenant_idempotency",
        "acq_flight_dispatch_ledger",
        ["tenant_id", "idempotency_key"],
    )

    if dialect == "postgresql":
        op.execute("ALTER TABLE acq_flight_dispatch_ledger ENABLE ROW LEVEL SECURITY")
        op.execute(
            """
            DO $$
            BEGIN
              IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE tablename = 'acq_flight_dispatch_ledger'
                  AND policyname = 'tenant_isolation'
              ) THEN
                CREATE POLICY tenant_isolation ON acq_flight_dispatch_ledger
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
    if "acq_flight_dispatch_ledger" not in insp.get_table_names():
        return
    if dialect == "postgresql":
        op.execute("DROP POLICY IF EXISTS tenant_isolation ON acq_flight_dispatch_ledger")
        op.execute("ALTER TABLE acq_flight_dispatch_ledger DISABLE ROW LEVEL SECURITY")
    op.drop_table("acq_flight_dispatch_ledger")
