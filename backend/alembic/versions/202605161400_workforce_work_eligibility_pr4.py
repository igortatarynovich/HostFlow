"""Work eligibility profiles + work permit submission channels (PR-4 foundation).

Revision ID: 202605161400_work_eligibility_pr4
Revises: 202605161200_widen_zus_ws_form_kind
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "202605161400_work_eligibility_pr4"
down_revision: Union[str, None] = "202605161200_widen_zus_ws_form_kind"
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
    jtype = sa.JSON()
    if _is_postgres():
        jtype = sa.JSON().with_variant(postgresql.JSONB, "postgresql")
    c_u = sa.TIMESTAMP(timezone=True)
    d = sa.Date()
    uid = sa.String(36)

    op.create_table(
        "workforce_work_eligibility_profiles",
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
        sa.Column("citizenship", sa.String(8), nullable=True),
        sa.Column("residence_status", sa.String(32), nullable=True),
        sa.Column("legal_stay_document_type", sa.String(64), nullable=True),
        sa.Column("legal_stay_valid_to", d, nullable=True),
        sa.Column("requires_work_permit", sa.Boolean(), nullable=True),
        sa.Column("work_permit_type", sa.String(64), nullable=True),
        sa.Column("work_permit_submission_method", sa.String(64), nullable=True),
        sa.Column("work_permit_application_status", sa.String(64), nullable=True),
        sa.Column("work_permit_submitted_at", d, nullable=True),
        sa.Column("work_permit_received_at", d, nullable=True),
        sa.Column("work_permit_valid_to", d, nullable=True),
        sa.Column("red_paper_required", sa.Boolean(), nullable=True),
        sa.Column("red_paper_status", sa.String(32), nullable=True),
        sa.Column(
            "eligibility_status",
            sa.String(32),
            nullable=False,
            server_default="not_evaluated",
            index=True,
        ),
        sa.Column("position_category", sa.String(32), nullable=True, index=True),
        sa.Column("work_country", sa.String(8), nullable=True),
        sa.Column("employer_country", sa.String(8), nullable=True),
        sa.Column("contract_type", sa.String(64), nullable=True),
        sa.Column("meta", jtype, nullable=True),
        sa.Column("created_at", c_u, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", c_u, server_default=sa.text("now()"), nullable=False),
    )
    op.create_unique_constraint(
        "uq_workforce_work_eligibility_employee",
        "workforce_work_eligibility_profiles",
        ["tenant_id", "employee_id"],
    )
    _rls_tenant("workforce_work_eligibility_profiles")

    op.create_table(
        "work_permit_submission_channels",
        sa.Column("id", uid, primary_key=True, nullable=False),
        sa.Column("country", sa.String(8), nullable=False, index=True),
        sa.Column("voivodeship", sa.String(64), nullable=True),
        sa.Column("permit_type", sa.String(64), nullable=False, index=True),
        sa.Column("submission_method", sa.String(64), nullable=False),
        sa.Column("portal_url", sa.Text(), nullable=True),
        sa.Column("office_name", sa.String(256), nullable=True),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("required_forms", jtype, nullable=True),
        sa.Column("expected_processing_days", sa.Integer(), nullable=True),
        sa.Column("created_at", c_u, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", c_u, server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    if _is_postgres():
        op.execute(
            "DROP POLICY IF EXISTS rls_workforce_work_eligibility_profiles_tenant ON workforce_work_eligibility_profiles;"
        )
        op.execute("ALTER TABLE workforce_work_eligibility_profiles NO ROW LEVEL SECURITY;")
    op.drop_table("work_permit_submission_channels")
    op.drop_constraint(
        "uq_workforce_work_eligibility_employee",
        "workforce_work_eligibility_profiles",
        type_="unique",
    )
    op.drop_table("workforce_work_eligibility_profiles")
