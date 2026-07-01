"""Party (Company) CRM fields, lead_type, order status pipeline, invoice FK.

Revision ID: 202603221200_party_lead_order_pipeline
Revises: 202608120003_merge_heads_reminders_and_own_company
Create Date: 2026-03-22
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "202603221200_party_lead_order_pipeline"
down_revision: Union[str, Sequence[str], None] = "202608120003_merge_heads_reminders_and_own_company"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "companies",
        sa.Column("party_entity_type", sa.String(length=16), nullable=False, server_default="company"),
    )
    op.add_column("companies", sa.Column("party_business_roles", sa.String(length=32), nullable=True))
    op.add_column("companies", sa.Column("client_stage", sa.String(length=32), nullable=True))
    op.add_column("companies", sa.Column("client_source", sa.String(length=64), nullable=True))
    op.create_index(
        "ix_companies_tenant_client_stage",
        "companies",
        ["tenant_id", "client_stage"],
        unique=False,
    )
    op.alter_column("companies", "party_entity_type", server_default=None)

    op.add_column(
        "leads",
        sa.Column("lead_type", sa.String(length=16), nullable=False, server_default="candidate"),
    )
    op.alter_column("leads", "company_id", existing_type=sa.String(length=36), nullable=True)
    op.create_index("ix_leads_tenant_lead_type", "leads", ["tenant_id", "lead_type"], unique=False)
    op.alter_column("leads", "lead_type", server_default=None)

    conn = op.get_bind()
    dialect = conn.dialect.name if conn is not None else ""

    # Canonical order pipeline: draft | confirmed | in_progress | completed | cancelled | on_hold
    for stmt in (
        "UPDATE service_orders SET status = 'confirmed' WHERE status IN ('quoted', 'approved')",
        "UPDATE service_orders SET status = 'in_progress' WHERE status = 'scheduled'",
        "UPDATE service_orders SET status = 'completed' WHERE status = 'delivered'",
        "UPDATE service_orders SET status = 'cancelled' WHERE status = 'refunded'",
    ):
        op.execute(sa.text(stmt))

    op.add_column("service_orders", sa.Column("start_date", sa.Date(), nullable=True))
    op.add_column("service_orders", sa.Column("end_date", sa.Date(), nullable=True))

    if dialect == "postgresql":
        try:
            op.create_foreign_key(
                "fk_invoices_service_order_id_service_orders",
                "invoices",
                "service_orders",
                ["service_order_id"],
                ["id"],
                ondelete="SET NULL",
            )
        except Exception:
            pass


def downgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name if conn is not None else ""

    if dialect == "postgresql":
        try:
            op.drop_constraint("fk_invoices_service_order_id_service_orders", "invoices", type_="foreignkey")
        except Exception:
            pass

    op.drop_column("service_orders", "end_date")
    op.drop_column("service_orders", "start_date")

    # Status rollback is intentionally partial (scheduled vs in_progress merge is lossy).
    op.execute(sa.text("UPDATE service_orders SET status = 'delivered' WHERE status = 'completed'"))
    op.execute(sa.text("UPDATE service_orders SET status = 'approved' WHERE status = 'confirmed'"))

    op.drop_index("ix_leads_tenant_lead_type", table_name="leads")
    op.alter_column("leads", "company_id", existing_type=sa.String(length=36), nullable=False)
    op.drop_column("leads", "lead_type")

    op.drop_index("ix_companies_tenant_client_stage", table_name="companies")
    op.drop_column("companies", "client_source")
    op.drop_column("companies", "client_stage")
    op.drop_column("companies", "party_business_roles")
    op.drop_column("companies", "party_entity_type")
