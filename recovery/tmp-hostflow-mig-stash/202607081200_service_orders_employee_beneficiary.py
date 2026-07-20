"""service_orders: employee beneficiary + vacancy as optional context."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "202607081200_svc_emp_ben"
down_revision = "202607020001_ra_ext"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "service_orders",
        sa.Column("employee_id", sa.String(36), nullable=True),
    )
    op.create_foreign_key(
        "service_orders_employee_id_fkey",
        "service_orders",
        "workforce_employees",
        ["employee_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_service_orders_employee",
        "service_orders",
        ["tenant_id", "employee_id"],
    )
    op.drop_constraint("ck_service_orders_owner", "service_orders", type_="check")
    op.create_check_constraint(
        "ck_service_orders_beneficiary",
        "service_orders",
        "((CASE WHEN candidate_id IS NOT NULL THEN 1 ELSE 0 END) + "
        "(CASE WHEN company_id IS NOT NULL THEN 1 ELSE 0 END) + "
        "(CASE WHEN employee_id IS NOT NULL THEN 1 ELSE 0 END)) = 1",
    )


def downgrade() -> None:
    op.drop_constraint("ck_service_orders_beneficiary", "service_orders", type_="check")
    op.create_check_constraint(
        "ck_service_orders_owner",
        "service_orders",
        "((CASE WHEN candidate_id IS NOT NULL THEN 1 ELSE 0 END) + "
        "(CASE WHEN vacancy_id IS NOT NULL THEN 1 ELSE 0 END) + "
        "(CASE WHEN company_id IS NOT NULL THEN 1 ELSE 0 END)) = 1",
    )
    op.drop_index("ix_service_orders_employee", table_name="service_orders")
    op.drop_constraint("service_orders_employee_id_fkey", "service_orders", type_="foreignkey")
    op.drop_column("service_orders", "employee_id")
