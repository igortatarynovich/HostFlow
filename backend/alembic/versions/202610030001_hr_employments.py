"""Employment persistence: labour relationship separate from contract cards.

Revision ID: 202610030001_hr_employments
Revises: 202609220001_documents_status_column

One hr_employments row per existing workforce employee. Every
workforce_employments card points at that row. Relationship columns
leave workforce_employees in the same migration.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from backend.app.reference.employment_persistence import (
    LEGACY_EMPLOYEE_COLUMNS,
    apply_employment_backfill,
)

revision: str = "202610030001_hr_employments"
down_revision: Union[str, None] = "202609220001_documents_status_column"
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
        "hr_employments",
        sa.Column("id", uid, primary_key=True, nullable=False),
        sa.Column("tenant_id", uid, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "employee_id",
            uid,
            sa.ForeignKey("workforce_employees.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("client_company_id", uid, nullable=True),
        sa.Column("started_on", sa.Date(), nullable=True),
        sa.Column("ended_on", sa.Date(), nullable=True),
        sa.Column("vacancy_id", uid, sa.ForeignKey("vacancies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("recruiter_user_id", uid, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("handoff_at", c_u, nullable=True),
        sa.Column("handoff_by_user_id", uid, nullable=True),
        sa.Column("handoff_id", uid, nullable=True),
        sa.Column("candidate_snapshot", jtype, nullable=True),
        sa.Column("created_at", c_u, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", c_u, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "state IN ('preparing', 'active', 'ended')",
            name="ck_hr_employments_state",
        ),
    )
    op.create_index("ix_hr_employments_tenant_id", "hr_employments", ["tenant_id"])
    op.create_index("ix_hr_employments_employee_id", "hr_employments", ["employee_id"])
    op.create_index("ix_hr_employments_client_company_id", "hr_employments", ["client_company_id"])
    op.create_index("ix_hr_employments_vacancy_id", "hr_employments", ["vacancy_id"])
    op.create_index("ix_hr_employments_recruiter_user_id", "hr_employments", ["recruiter_user_id"])
    op.create_index("ix_hr_employments_handoff_id", "hr_employments", ["handoff_id"])
    _rls_tenant("hr_employments")

    op.add_column("workforce_employments", sa.Column("employment_id", uid, nullable=True))
    op.create_foreign_key(
        "fk_workforce_employments_employment",
        "workforce_employments",
        "hr_employments",
        ["employment_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_workforce_employments_employment_id",
        "workforce_employments",
        ["employment_id"],
    )

    apply_employment_backfill(op.get_bind())

    op.alter_column("workforce_employments", "employment_id", existing_type=uid, nullable=False)

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for fk in inspector.get_foreign_keys("workforce_employees"):
        cols = list(fk.get("constrained_columns") or [])
        if cols and cols[0] in LEGACY_EMPLOYEE_COLUMNS and fk.get("name"):
            op.drop_constraint(fk["name"], "workforce_employees", type_="foreignkey")
    for index in inspector.get_indexes("workforce_employees"):
        cols = list(index.get("column_names") or [])
        if cols and set(cols) <= set(LEGACY_EMPLOYEE_COLUMNS) and index.get("name"):
            op.drop_index(index["name"], table_name="workforce_employees")
    for column in LEGACY_EMPLOYEE_COLUMNS:
        op.drop_column("workforce_employees", column)


def downgrade() -> None:
    uid = sa.String(36)
    jtype = sa.JSON()
    if _is_postgres():
        jtype = sa.JSON().with_variant(postgresql.JSONB, "postgresql")
    c_u = sa.TIMESTAMP(timezone=True)
    op.add_column("workforce_employees", sa.Column("hire_date", sa.Date(), nullable=True))
    op.add_column("workforce_employees", sa.Column("probation_end", sa.Date(), nullable=True))
    op.add_column("workforce_employees", sa.Column("termination_date", sa.Date(), nullable=True))
    op.add_column("workforce_employees", sa.Column("company_id", uid, nullable=True))
    op.add_column("workforce_employees", sa.Column("vacancy_id", uid, nullable=True))
    op.add_column("workforce_employees", sa.Column("recruiter_user_id", uid, nullable=True))
    op.add_column("workforce_employees", sa.Column("handoff_at", c_u, nullable=True))
    op.add_column("workforce_employees", sa.Column("handoff_by_user_id", uid, nullable=True))
    op.add_column("workforce_employees", sa.Column("candidate_snapshot", jtype, nullable=True))
    op.execute(
        """
        UPDATE workforce_employees AS e
        SET hire_date = h.started_on,
            termination_date = h.ended_on,
            company_id = h.client_company_id,
            vacancy_id = h.vacancy_id,
            recruiter_user_id = h.recruiter_user_id,
            handoff_at = h.handoff_at,
            handoff_by_user_id = h.handoff_by_user_id,
            candidate_snapshot = h.candidate_snapshot
        FROM hr_employments AS h
        WHERE h.employee_id = e.id
          AND h.created_at = (
              SELECT MAX(h2.created_at) FROM hr_employments AS h2 WHERE h2.employee_id = e.id
          )
        """
        if _is_postgres()
        else """
        UPDATE workforce_employees
        SET hire_date = (
                SELECT started_on FROM hr_employments h
                WHERE h.employee_id = workforce_employees.id
                ORDER BY created_at DESC LIMIT 1
            ),
            termination_date = (
                SELECT ended_on FROM hr_employments h
                WHERE h.employee_id = workforce_employees.id
                ORDER BY created_at DESC LIMIT 1
            ),
            company_id = (
                SELECT client_company_id FROM hr_employments h
                WHERE h.employee_id = workforce_employees.id
                ORDER BY created_at DESC LIMIT 1
            ),
            vacancy_id = (
                SELECT vacancy_id FROM hr_employments h
                WHERE h.employee_id = workforce_employees.id
                ORDER BY created_at DESC LIMIT 1
            ),
            recruiter_user_id = (
                SELECT recruiter_user_id FROM hr_employments h
                WHERE h.employee_id = workforce_employees.id
                ORDER BY created_at DESC LIMIT 1
            ),
            handoff_at = (
                SELECT handoff_at FROM hr_employments h
                WHERE h.employee_id = workforce_employees.id
                ORDER BY created_at DESC LIMIT 1
            ),
            handoff_by_user_id = (
                SELECT handoff_by_user_id FROM hr_employments h
                WHERE h.employee_id = workforce_employees.id
                ORDER BY created_at DESC LIMIT 1
            ),
            candidate_snapshot = (
                SELECT candidate_snapshot FROM hr_employments h
                WHERE h.employee_id = workforce_employees.id
                ORDER BY created_at DESC LIMIT 1
            )
        """
    )
    op.drop_constraint("fk_workforce_employments_employment", "workforce_employments", type_="foreignkey")
    op.drop_index("ix_workforce_employments_employment_id", table_name="workforce_employments")
    op.drop_column("workforce_employments", "employment_id")
    op.drop_index("ix_hr_employments_handoff_id", table_name="hr_employments")
    op.drop_index("ix_hr_employments_recruiter_user_id", table_name="hr_employments")
    op.drop_index("ix_hr_employments_vacancy_id", table_name="hr_employments")
    op.drop_index("ix_hr_employments_client_company_id", table_name="hr_employments")
    op.drop_index("ix_hr_employments_employee_id", table_name="hr_employments")
    op.drop_index("ix_hr_employments_tenant_id", table_name="hr_employments")
    op.drop_table("hr_employments")
