"""Ready to Start decisions for one Employment.

Revision ID: 202610070001_hr_ready_to_start
Revises: 202610060001_hr_employment_requirements

hr_ready_to_start_decisions stores ready_to_start.v1.
No backfill. A new decision does not rewrite an older one.
Employment.state is not updated here.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202610070001_hr_ready_to_start"
down_revision: Union[str, None] = "202610060001_hr_employment_requirements"
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
    uid = sa.String(36)
    op.create_table(
        "hr_ready_to_start_decisions",
        sa.Column("id", uid, primary_key=True, nullable=False),
        sa.Column("tenant_id", uid, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "employment_id",
            uid,
            sa.ForeignKey("hr_employments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("actor_user_id", uid, nullable=False),
        sa.Column("decided_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("legal_result", sa.String(16), nullable=False),
        sa.Column(
            "legal_decision_id",
            uid,
            sa.ForeignKey("hr_legal_eligibility_gate_decisions.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("legal_fingerprint", sa.String(64), nullable=True),
        sa.Column("employee_data_result", sa.String(16), nullable=False),
        sa.Column("employee_data_fingerprint", sa.String(64), nullable=False),
        sa.Column("terms_result", sa.String(16), nullable=False),
        sa.Column(
            "terms_id",
            uid,
            sa.ForeignKey("hr_employment_terms.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("terms_fingerprint", sa.String(64), nullable=False),
        sa.Column("requirements_result", sa.String(16), nullable=False),
        sa.Column("requirements_fingerprint", sa.String(64), nullable=False),
        sa.Column("blocked_reasons", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "outcome IN ('pass', 'blocked')",
            name="ck_hr_ready_to_start_outcome",
        ),
        sa.CheckConstraint(
            "legal_result IN ('pass', 'blocked') "
            "AND employee_data_result IN ('pass', 'blocked') "
            "AND terms_result IN ('pass', 'blocked') "
            "AND requirements_result IN ('pass', 'blocked')",
            name="ck_hr_ready_to_start_inputs",
        ),
        sa.CheckConstraint(
            "(outcome = 'pass' AND legal_result = 'pass' AND employee_data_result = 'pass' "
            "AND terms_result = 'pass' AND requirements_result = 'pass' AND blocked_reasons = '[]') "
            "OR (outcome = 'blocked' AND blocked_reasons <> '[]' AND ("
            "legal_result = 'blocked' OR employee_data_result = 'blocked' "
            "OR terms_result = 'blocked' OR requirements_result = 'blocked'))",
            name="ck_hr_ready_to_start_outcome_matches_inputs",
        ),
    )
    op.create_index(
        "ix_hr_ready_to_start_decisions_tenant_id",
        "hr_ready_to_start_decisions",
        ["tenant_id"],
    )
    op.create_index(
        "ix_hr_ready_to_start_decisions_employment_id",
        "hr_ready_to_start_decisions",
        ["employment_id"],
    )
    _rls_tenant("hr_ready_to_start_decisions")


def downgrade() -> None:
    op.drop_index("ix_hr_ready_to_start_decisions_employment_id", table_name="hr_ready_to_start_decisions")
    op.drop_index("ix_hr_ready_to_start_decisions_tenant_id", table_name="hr_ready_to_start_decisions")
    op.drop_table("hr_ready_to_start_decisions")
