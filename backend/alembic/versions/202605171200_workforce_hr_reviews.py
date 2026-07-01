"""workforce_hr_reviews — HR acceptance workflow (stage A).

Revision ID: 202605171200_hr_reviews
Revises: 202605170900_wel_payment_req
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "202605171200_hr_reviews"
down_revision: Union[str, None] = "202605170900_wel_payment_req"
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
    uid = sa.String(36)
    c_u = sa.TIMESTAMP(timezone=True)

    op.create_table(
        "workforce_hr_reviews",
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
            "handoff_id",
            uid,
            sa.ForeignKey("candidate_handoffs.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("status", sa.String(48), nullable=False, server_default="hr_review_in_progress"),
        sa.Column("checklist_json", jtype, nullable=True),
        sa.Column("decision_basis_json", jtype, nullable=True),
        sa.Column("blockers_json", jtype, nullable=True),
        sa.Column("corrections_note", sa.Text(), nullable=True),
        sa.Column("return_reason", sa.Text(), nullable=True),
        sa.Column("reject_reason", sa.Text(), nullable=True),
        sa.Column("decided_by_user_id", uid, nullable=True),
        sa.Column("decided_at", c_u, nullable=True),
        sa.Column("created_at", c_u, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", c_u, server_default=sa.text("now()"), nullable=False),
    )
    op.create_unique_constraint(
        "uq_workforce_hr_review_tenant_employee",
        "workforce_hr_reviews",
        ["tenant_id", "employee_id"],
    )
    _rls_tenant("workforce_hr_reviews")


def downgrade() -> None:
    op.drop_table("workforce_hr_reviews")
