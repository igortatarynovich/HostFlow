"""Workforce HR extension: employee links + employment / payroll / ZUS / absence / leave / onboarding task tables

Revision ID: 202604301500_workforce_hr_profiles
Revises: 202604301400_workforce_hr
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202604301500_workforce_hr_profiles"
down_revision: Union[str, None] = "202604301400_workforce_hr"
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
    jtype = sa.JSON()
    if _is_postgres():
        jtype = sa.JSON().with_variant(postgresql.JSONB, "postgresql")
    c_u = sa.TIMESTAMP(timezone=True)
    uid = sa.String(36)

    op.add_column("workforce_employees", sa.Column("vacancy_id", uid, nullable=True))
    op.add_column("workforce_employees", sa.Column("recruiter_user_id", uid, nullable=True))
    op.add_column("workforce_employees", sa.Column("candidate_snapshot", jtype, nullable=True))
    op.create_foreign_key(
        "fk_workforce_employees_vacancy",
        "workforce_employees",
        "vacancies",
        ["vacancy_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_workforce_employees_recruiter_user",
        "workforce_employees",
        "users",
        ["recruiter_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_workforce_employees_vacancy_id", "workforce_employees", ["vacancy_id"])
    op.create_index(
        "ix_workforce_employees_recruiter_user_id", "workforce_employees", ["recruiter_user_id"]
    )

    op.create_table(
        "workforce_employments",
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
        sa.Column("contract_type", sa.String(64), nullable=False, server_default="unknown"),
        sa.Column("rate_model", jtype, nullable=True),
        sa.Column("schedule", jtype, nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("conditions_text", sa.Text(), nullable=True),
        sa.Column("vacancy_id", uid, nullable=True),
        sa.Column("meta", jtype, nullable=True),
        sa.Column("created_at", c_u, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", c_u, server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_workforce_employments_tenant_employee",
        "workforce_employments",
        ["tenant_id", "employee_id"],
    )

    op.create_table(
        "workforce_payroll_profiles",
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
        sa.Column("pay_type", sa.String(64), nullable=False, server_default="mixed"),
        sa.Column("base_rate", sa.Numeric(18, 4), nullable=True),
        sa.Column("currency", sa.String(8), nullable=True, server_default="PLN"),
        sa.Column("calculation_system", sa.String(128), nullable=True),
        sa.Column("pay_day_note", sa.String(256), nullable=True),
        sa.Column("bank_account", sa.String(128), nullable=True),
        sa.Column("tax_status", sa.String(64), nullable=True),
        sa.Column("pit_declarations", jtype, nullable=True),
        sa.Column("allowances", jtype, nullable=True),
        sa.Column("deductions", jtype, nullable=True),
        sa.Column(
            "payroll_status",
            sa.String(64),
            nullable=False,
            server_default="missing_data",
        ),
        sa.Column("external_refs", jtype, nullable=True),
        sa.Column("meta", jtype, nullable=True),
        sa.Column("created_at", c_u, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", c_u, server_default=sa.text("now()"), nullable=False),
    )
    op.create_unique_constraint(
        "uq_workforce_payroll_profile_employee",
        "workforce_payroll_profiles",
        ["tenant_id", "employee_id"],
    )

    op.create_table(
        "workforce_zus_profiles",
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
        sa.Column(
            "registration_status",
            sa.String(64),
            nullable=False,
            server_default="not_submitted",
        ),
        sa.Column("submitted_at", sa.Date(), nullable=True),
        sa.Column("employment_basis", sa.String(64), nullable=True),
        sa.Column("responsible_party", sa.String(64), nullable=True),
        sa.Column("insurance_coverage", jtype, nullable=True),
        sa.Column("forms", jtype, nullable=True),
        sa.Column("meta", jtype, nullable=True),
        sa.Column("created_at", c_u, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", c_u, server_default=sa.text("now()"), nullable=False),
    )
    op.create_unique_constraint(
        "uq_workforce_zus_profile_employee",
        "workforce_zus_profiles",
        ["tenant_id", "employee_id"],
    )

    op.create_table(
        "workforce_absences",
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
        sa.Column("absence_type", sa.String(64), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("source", sa.String(64), nullable=False, server_default="manual"),
        sa.Column("status", sa.String(64), nullable=False, server_default="reported"),
        sa.Column("payer", sa.String(32), nullable=True),
        sa.Column("payroll_impact", sa.Text(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("meta", jtype, nullable=True),
        sa.Column("created_at", c_u, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", c_u, server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_workforce_absences_tenant_employee_dates",
        "workforce_absences",
        ["tenant_id", "employee_id", "start_date"],
    )

    op.create_table(
        "workforce_leave_requests",
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
        sa.Column("leave_type", sa.String(64), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(64), nullable=False, server_default="pending"),
        sa.Column("year_entitlement_days", sa.Numeric(10, 2), nullable=True),
        sa.Column("used_days_before", sa.Numeric(10, 2), nullable=True),
        sa.Column("conflict_flags", jtype, nullable=True),
        sa.Column("approver_user_id", uid, nullable=True),
        sa.Column("decided_at", c_u, nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("meta", jtype, nullable=True),
        sa.Column("created_at", c_u, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", c_u, server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_workforce_leave_requests_tenant_status",
        "workforce_leave_requests",
        ["tenant_id", "status"],
    )

    op.create_table(
        "workforce_onboarding_tasks",
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
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("due_at", c_u, nullable=True),
        sa.Column("completed_at", c_u, nullable=True),
        sa.Column("assignee_user_id", uid, nullable=True),
        sa.Column("meta", jtype, nullable=True),
        sa.Column("created_at", c_u, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", c_u, server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_workforce_onboarding_tasks_tenant_employee",
        "workforce_onboarding_tasks",
        ["tenant_id", "employee_id"],
    )

    for tbl in (
        "workforce_employments",
        "workforce_payroll_profiles",
        "workforce_zus_profiles",
        "workforce_absences",
        "workforce_leave_requests",
        "workforce_onboarding_tasks",
    ):
        _rls_tenant(tbl)


def downgrade() -> None:
    for tbl in (
        "workforce_onboarding_tasks",
        "workforce_leave_requests",
        "workforce_absences",
        "workforce_zus_profiles",
        "workforce_payroll_profiles",
        "workforce_employments",
    ):
        op.drop_table(tbl)

    op.drop_constraint("fk_workforce_employees_recruiter_user", "workforce_employees", type_="foreignkey")
    op.drop_constraint("fk_workforce_employees_vacancy", "workforce_employees", type_="foreignkey")
    op.drop_index("ix_workforce_employees_recruiter_user_id", table_name="workforce_employees")
    op.drop_index("ix_workforce_employees_vacancy_id", table_name="workforce_employees")
    op.drop_column("workforce_employees", "candidate_snapshot")
    op.drop_column("workforce_employees", "recruiter_user_id")
    op.drop_column("workforce_employees", "vacancy_id")
