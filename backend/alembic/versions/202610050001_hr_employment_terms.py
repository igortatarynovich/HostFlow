"""Employment terms snapshot, separate from the labour relationship.

Revision ID: 202610050001_hr_employment_terms
Revises: 202610040001_hr_legal_eligibility_gate

hr_employment_terms stores employment_terms.v1 for one hr_employments row.
No backfill. Vacancy and contract-card blobs are not copied.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202610050001_hr_employment_terms"
down_revision: Union[str, None] = "202610040001_hr_legal_eligibility_gate"
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
        "hr_employment_terms",
        sa.Column("id", uid, primary_key=True, nullable=False),
        sa.Column("tenant_id", uid, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "employment_id",
            uid,
            sa.ForeignKey("hr_employments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("position", sa.String(255), nullable=False),
        sa.Column("contract_basis", sa.String(64), nullable=False),
        sa.Column("work_time_value", sa.Numeric(18, 4), nullable=False),
        sa.Column("work_time_unit", sa.String(32), nullable=False),
        sa.Column("workplace", sa.String(255), nullable=False),
        sa.Column("compensation_amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("compensation_currency", sa.String(8), nullable=False),
        sa.Column("compensation_unit", sa.String(32), nullable=False),
        sa.Column("duration", sa.String(16), nullable=False),
        sa.Column("fixed_term_end", sa.Date(), nullable=True),
        sa.Column("probation_status", sa.String(16), nullable=False),
        sa.Column("probation_end", sa.Date(), nullable=True),
        sa.Column("default_vacancy_id", uid, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "duration IN ('fixed', 'indefinite')",
            name="ck_hr_employment_terms_duration",
        ),
        sa.CheckConstraint(
            "(duration = 'fixed' AND fixed_term_end IS NOT NULL) "
            "OR (duration = 'indefinite' AND fixed_term_end IS NULL)",
            name="ck_hr_employment_terms_fixed_end",
        ),
        sa.CheckConstraint(
            "(probation_status = 'none' AND probation_end IS NULL) "
            "OR (probation_status = 'dated' AND probation_end IS NOT NULL) "
            "OR (probation_status = 'undetermined' AND probation_end IS NULL)",
            name="ck_hr_employment_terms_probation",
        ),
    )
    op.create_index("ix_hr_employment_terms_tenant_id", "hr_employment_terms", ["tenant_id"])
    op.create_index("ix_hr_employment_terms_employment_id", "hr_employment_terms", ["employment_id"])
    op.create_index(
        "uq_hr_employment_terms_one_current",
        "hr_employment_terms",
        ["employment_id"],
        unique=True,
        postgresql_where=sa.text("is_current"),
        sqlite_where=sa.text("is_current = 1"),
    )
    _rls_tenant("hr_employment_terms")


def downgrade() -> None:
    op.drop_index("uq_hr_employment_terms_one_current", table_name="hr_employment_terms")
    op.drop_index("ix_hr_employment_terms_employment_id", table_name="hr_employment_terms")
    op.drop_index("ix_hr_employment_terms_tenant_id", table_name="hr_employment_terms")
    op.drop_table("hr_employment_terms")
