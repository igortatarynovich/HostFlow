"""HR Legal Eligibility Gate decisions for one Employment.

Revision ID: 202610040001_hr_legal_eligibility_gate
Revises: 202610030001_hr_employments

The checkpoint is audit of an HR reading of legal_eligibility.v1.
It does not add an Employment state.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202610040001_hr_legal_eligibility_gate"
down_revision: Union[str, None] = "202610030001_hr_employments"
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
        "hr_legal_eligibility_gate_decisions",
        sa.Column("id", uid, primary_key=True, nullable=False),
        sa.Column("tenant_id", uid, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "employment_id",
            uid,
            sa.ForeignKey("hr_employments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("policy_id", sa.String(64), nullable=False),
        sa.Column("citizenship_class", sa.String(32), nullable=True),
        sa.Column("stay_basis", sa.String(32), nullable=True),
        sa.Column("work_authorization_basis", sa.String(32), nullable=True),
        sa.Column("valid_for_this_employment", sa.String(32), nullable=True),
        sa.Column("client_company_id", uid, nullable=True),
        sa.Column("vacancy_id", uid, nullable=True),
        sa.Column("planned_start", sa.Date(), nullable=True),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("actor_user_id", uid, nullable=False),
        sa.Column("decided_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.CheckConstraint(
            "outcome IN ('pass', 'fail', 'blocked')",
            name="ck_hr_legal_eligibility_gate_outcome",
        ),
    )
    op.create_index(
        "ix_hr_legal_eligibility_gate_tenant_id",
        "hr_legal_eligibility_gate_decisions",
        ["tenant_id"],
    )
    op.create_index(
        "ix_hr_legal_eligibility_gate_employment_id",
        "hr_legal_eligibility_gate_decisions",
        ["employment_id"],
    )
    _rls_tenant("hr_legal_eligibility_gate_decisions")


def downgrade() -> None:
    op.drop_index(
        "ix_hr_legal_eligibility_gate_employment_id",
        table_name="hr_legal_eligibility_gate_decisions",
    )
    op.drop_index(
        "ix_hr_legal_eligibility_gate_tenant_id",
        table_name="hr_legal_eligibility_gate_decisions",
    )
    op.drop_table("hr_legal_eligibility_gate_decisions")
