"""service_orders: Bill-To customer + per-line beneficiary (Variant B).

Splits the single order owner into two independent roles:
  * ServiceOrder.customer_kind/customer_id  -> who pays (Bill-To)
  * ServiceItem.beneficiary_kind/beneficiary_id -> who receives each line

Backfill keeps existing orders valid:
  * order customer = existing single typed owner (company/candidate/employee)
  * each line beneficiary = the order's customer
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "202607081300_svc_cust_ben"
down_revision = "202607081200_svc_emp_ben"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- ServiceOrder: Bill-To / Customer ---------------------------------
    op.add_column("service_orders", sa.Column("customer_kind", sa.String(16), nullable=True))
    op.add_column("service_orders", sa.Column("customer_id", sa.String(36), nullable=True))
    op.create_index(
        "ix_service_orders_customer",
        "service_orders",
        ["tenant_id", "customer_kind", "customer_id"],
    )

    # --- ServiceItem: Beneficiary -----------------------------------------
    op.add_column("service_items", sa.Column("beneficiary_kind", sa.String(16), nullable=True))
    op.add_column("service_items", sa.Column("beneficiary_id", sa.String(36), nullable=True))
    op.create_index(
        "ix_service_items_beneficiary",
        "service_items",
        ["tenant_id", "beneficiary_kind", "beneficiary_id"],
    )

    # --- Backfill customer from existing single owner ----------------------
    op.execute(
        """
        UPDATE service_orders
        SET customer_kind = CASE
                WHEN company_id IS NOT NULL THEN 'client'
                WHEN candidate_id IS NOT NULL THEN 'candidate'
                WHEN employee_id IS NOT NULL THEN 'employee'
                ELSE customer_kind
            END,
            customer_id = COALESCE(company_id, candidate_id, employee_id, customer_id)
        WHERE customer_id IS NULL
        """
    )

    # --- Backfill each line beneficiary from the order customer ------------
    op.execute(
        """
        UPDATE service_items AS si
        SET beneficiary_kind = so.customer_kind,
            beneficiary_id = so.customer_id
        FROM service_orders AS so
        WHERE si.order_id = so.id
          AND si.beneficiary_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_service_items_beneficiary", table_name="service_items")
    op.drop_column("service_items", "beneficiary_id")
    op.drop_column("service_items", "beneficiary_kind")
    op.drop_index("ix_service_orders_customer", table_name="service_orders")
    op.drop_column("service_orders", "customer_id")
    op.drop_column("service_orders", "customer_kind")
