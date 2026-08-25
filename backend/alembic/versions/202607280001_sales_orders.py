"""Sales orders / lines / billable items + vacancies.order_line_id (ADR-032).

Revision ID: 202607280001_sales_orders
Revises: 202607230001_acq_ad_bind
Create Date: 2026-07-28

NOTE: revision id ≤32 chars. Tables named sales_* to avoid Services service_orders.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


RevisionType = Union[str, Sequence[str], None]

revision: str = "202607280001_sales_orders"
down_revision: RevisionType = "202607230001_acq_ad_bind"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    op.create_table(
        "sales_orders",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("own_company_id", sa.String(length=36), nullable=True),
        sa.Column("client_account_id", sa.String(length=36), nullable=True),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("payer_company_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("currency", sa.String(length=16), nullable=True),
        sa.Column("payment_term_days", sa.Integer(), nullable=True),
        sa.Column("payment_model", sa.String(length=64), nullable=True),
        sa.Column("vat_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("guarantee_days", sa.Integer(), nullable=True),
        sa.Column("invoice_right_policy", sa.String(length=64), nullable=True),
        sa.Column("billing_notes", sa.Text(), nullable=True),
        sa.Column("commercial_snapshot", sa.JSON(), nullable=True),
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
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["client_account_id"], ["client_accounts.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["payer_company_id"], ["companies.id"], ondelete="SET NULL"
        ),
        sa.CheckConstraint(
            "status IN ('open', 'in_progress', 'completed', 'cancelled')",
            name="ck_sales_orders_status",
        ),
    )
    op.create_index("ix_sales_orders_tenant_id", "sales_orders", ["tenant_id"])
    op.create_index(
        "ix_sales_orders_tenant_company", "sales_orders", ["tenant_id", "company_id"]
    )
    op.create_index(
        "ix_sales_orders_tenant_status", "sales_orders", ["tenant_id", "status"]
    )

    op.create_table(
        "sales_order_lines",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("sales_order_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("role_label", sa.String(length=128), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("quantity_needed", sa.Integer(), nullable=False),
        sa.Column("unit_rate", sa.Numeric(12, 2), nullable=True),
        sa.Column("charge_unit", sa.String(length=32), nullable=True),
        sa.Column(
            "billing_trigger",
            sa.String(length=64),
            nullable=False,
            server_default="headcount_completed",
        ),
        sa.Column("guarantee_days", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
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
            ["sales_order_id"], ["sales_orders.id"], ondelete="CASCADE"
        ),
        sa.CheckConstraint(
            "quantity_needed >= 1", name="ck_sales_order_lines_quantity"
        ),
        sa.CheckConstraint(
            "status IN ('open', 'in_progress', 'completed', 'cancelled')",
            name="ck_sales_order_lines_status",
        ),
        sa.CheckConstraint(
            "billing_trigger IN ("
            "'candidate_hired', 'candidate_started_work', 'guarantee_period_passed', "
            "'milestone_accepted', 'headcount_completed', 'monthly_service_period_closed'"
            ")",
            name="ck_sales_order_lines_billing_trigger",
        ),
    )
    op.create_index(
        "ix_sales_order_lines_tenant_id", "sales_order_lines", ["tenant_id"]
    )
    op.create_index(
        "ix_sales_order_lines_order", "sales_order_lines", ["sales_order_id"]
    )

    op.create_table(
        "sales_billable_items",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("sales_order_id", sa.String(length=36), nullable=False),
        sa.Column("sales_order_line_id", sa.String(length=36), nullable=True),
        sa.Column("trigger_code", sa.String(length=64), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=16), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False, server_default="1"),
        sa.Column("source_entity_type", sa.String(length=64), nullable=True),
        sa.Column("source_entity_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("invoice_id", sa.String(length=36), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["sales_order_id"], ["sales_orders.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["sales_order_line_id"], ["sales_order_lines.id"], ondelete="SET NULL"
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'invoiced', 'void')",
            name="ck_sales_billable_items_status",
        ),
    )
    op.create_index(
        "ix_sales_billable_items_tenant", "sales_billable_items", ["tenant_id"]
    )
    op.create_index(
        "ix_sales_billable_items_order", "sales_billable_items", ["sales_order_id"]
    )

    op.add_column(
        "vacancies",
        sa.Column("order_line_id", sa.String(length=36), nullable=True),
    )
    op.create_foreign_key(
        "fk_vacancies_order_line_id",
        "vacancies",
        "sales_order_lines",
        ["order_line_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "uq_vacancies_order_line_id",
        "vacancies",
        ["order_line_id"],
        unique=True,
        postgresql_where=sa.text("order_line_id IS NOT NULL"),
        sqlite_where=sa.text("order_line_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_vacancies_order_line_id", table_name="vacancies")
    op.drop_constraint("fk_vacancies_order_line_id", "vacancies", type_="foreignkey")
    op.drop_column("vacancies", "order_line_id")
    op.drop_index("ix_sales_billable_items_order", table_name="sales_billable_items")
    op.drop_index("ix_sales_billable_items_tenant", table_name="sales_billable_items")
    op.drop_table("sales_billable_items")
    op.drop_index("ix_sales_order_lines_order", table_name="sales_order_lines")
    op.drop_index("ix_sales_order_lines_tenant_id", table_name="sales_order_lines")
    op.drop_table("sales_order_lines")
    op.drop_index("ix_sales_orders_tenant_status", table_name="sales_orders")
    op.drop_index("ix_sales_orders_tenant_company", table_name="sales_orders")
    op.drop_index("ix_sales_orders_tenant_id", table_name="sales_orders")
    op.drop_table("sales_orders")
