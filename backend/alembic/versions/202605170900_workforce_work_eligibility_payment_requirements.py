"""Work eligibility fee payment requirements (foreign driver flow).

Revision ID: 202605170900_wel_payment_req
Revises: 202605161400_work_eligibility_pr4
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "202605170900_wel_payment_req"
down_revision: Union[str, None] = "202605161400_work_eligibility_pr4"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


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
    c_u = sa.TIMESTAMP(timezone=True)
    d = sa.Date()
    uid = sa.String(36)
    amt = sa.Numeric(12, 2)

    op.create_table(
        "workforce_work_eligibility_payment_requirements",
        sa.Column("id", uid, primary_key=True, nullable=False),
        sa.Column(
            "tenant_id",
            uid,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "employee_id",
            uid,
            sa.ForeignKey("workforce_employees.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("requirement_type", sa.String(32), nullable=False),
        sa.Column("amount", amt, nullable=True),
        sa.Column("currency", sa.String(8), nullable=False, server_default="PLN"),
        sa.Column(
            "payment_status",
            sa.String(16),
            nullable=False,
            server_default="not_required",
        ),
        sa.Column("due_at", d, nullable=True),
        sa.Column("paid_at", c_u, nullable=True),
        sa.Column("payment_reference", sa.String(256), nullable=True),
        sa.Column("receipt_document_id", sa.String(36), nullable=True),
        sa.Column("blocks_step", sa.String(64), nullable=True),
        sa.Column("created_at", c_u, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", c_u, server_default=sa.text("now()"), nullable=False),
    )
    op.create_unique_constraint(
        "uq_wel_payment_req_employee_type",
        "workforce_work_eligibility_payment_requirements",
        ["tenant_id", "employee_id", "requirement_type"],
    )
    op.create_index(
        "ix_wel_payment_req_tenant_employee",
        "workforce_work_eligibility_payment_requirements",
        ["tenant_id", "employee_id"],
    )
    _rls_tenant("workforce_work_eligibility_payment_requirements")


def downgrade() -> None:
    if _is_postgres():
        op.execute(
            "DROP POLICY IF EXISTS rls_workforce_work_eligibility_payment_requirements_tenant "
            "ON workforce_work_eligibility_payment_requirements;"
        )
        op.execute(
            "ALTER TABLE workforce_work_eligibility_payment_requirements NO ROW LEVEL SECURITY;"
        )
    op.drop_index(
        "ix_wel_payment_req_tenant_employee",
        table_name="workforce_work_eligibility_payment_requirements",
    )
    op.drop_constraint(
        "uq_wel_payment_req_employee_type",
        "workforce_work_eligibility_payment_requirements",
        type_="unique",
    )
    op.drop_table("workforce_work_eligibility_payment_requirements")
