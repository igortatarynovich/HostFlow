"""HR workforce core: tax, insurance, HR document context, compliance state tables.

Revision ID: 202605122000_hr_workforce_core
Revises: 202605121400_def_ruleset
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "202605122000_hr_workforce_core"
down_revision: Union[str, None] = "202605121400_def_ruleset"
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

    op.create_table(
        "workforce_tax_profiles",
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
        sa.Column("tax_residency_country", sa.String(8), nullable=True),
        sa.Column("tax_office", sa.String(64), nullable=True),
        sa.Column("pit2_submitted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("pit2_monthly_amount", sa.Numeric(12, 4), nullable=True),
        sa.Column("tax_deductible_costs_type", sa.String(32), nullable=True),
        sa.Column("young_person_relief", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", c_u, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", c_u, server_default=sa.text("now()"), nullable=False),
    )
    op.create_unique_constraint(
        "uq_workforce_tax_profile_employee",
        "workforce_tax_profiles",
        ["tenant_id", "employee_id"],
    )
    _rls_tenant("workforce_tax_profiles")

    op.create_table(
        "workforce_insurance_profiles",
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
        sa.Column("zus_title_code", sa.String(32), nullable=True),
        sa.Column("social_insurance", sa.String(32), nullable=True),
        sa.Column("health_insurance", sa.String(32), nullable=True),
        sa.Column("sickness_insurance", sa.String(32), nullable=True),
        sa.Column("accident_insurance", sa.String(32), nullable=True),
        sa.Column("zus_registration_type", sa.String(64), nullable=True),
        sa.Column("registered_at", sa.Date(), nullable=True),
        sa.Column("deregistered_at", sa.Date(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("created_at", c_u, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", c_u, server_default=sa.text("now()"), nullable=False),
    )
    op.create_unique_constraint(
        "uq_workforce_insurance_profile_employee",
        "workforce_insurance_profiles",
        ["tenant_id", "employee_id"],
    )
    _rls_tenant("workforce_insurance_profiles")

    op.create_table(
        "workforce_hr_document_contexts",
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
            "document_id",
            uid,
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("context_type", sa.String(64), nullable=False),
        sa.Column("legal_category", sa.String(64), nullable=True),
        sa.Column("document_group", sa.String(64), nullable=True),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("verification_status", sa.String(32), nullable=True),
        sa.Column("expires_at", c_u, nullable=True),
        sa.Column("source", sa.String(64), nullable=True),
        sa.Column("created_at", c_u, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", c_u, server_default=sa.text("now()"), nullable=False),
    )
    op.create_unique_constraint(
        "uq_workforce_hr_doc_ctx_employee_document",
        "workforce_hr_document_contexts",
        ["tenant_id", "employee_id", "document_id"],
    )
    op.create_index(
        "ix_workforce_hr_doc_ctx_tenant_employee",
        "workforce_hr_document_contexts",
        ["tenant_id", "employee_id"],
    )
    _rls_tenant("workforce_hr_document_contexts")

    op.create_table(
        "workforce_compliance_states",
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
        sa.Column("status", sa.String(32), nullable=False, server_default="not_evaluated"),
        sa.Column("missing_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expired_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expiring_soon_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("high_risk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cannot_work", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("last_evaluated_at", c_u, nullable=True),
        sa.Column("reasons", jtype, nullable=True),
        sa.Column("created_at", c_u, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", c_u, server_default=sa.text("now()"), nullable=False),
    )
    op.create_unique_constraint(
        "uq_workforce_compliance_state_employee",
        "workforce_compliance_states",
        ["tenant_id", "employee_id"],
    )
    _rls_tenant("workforce_compliance_states")


def downgrade() -> None:
    for t in (
        "workforce_compliance_states",
        "workforce_hr_document_contexts",
        "workforce_insurance_profiles",
        "workforce_tax_profiles",
    ):
        if _is_postgres():
            op.execute(f'DROP POLICY IF EXISTS rls_{t}_tenant ON "{t}";')
            op.execute(f'ALTER TABLE "{t}" DISABLE ROW LEVEL SECURITY;')
        op.drop_table(t)
