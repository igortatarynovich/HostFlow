"""workforce_employees + users.role hr_officer (HR workspace, isolated from recruitment)

Revision ID: 202604301400_workforce_hr
Revises: 202604301300_compliance_officer
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202604301400_workforce_hr"
down_revision: Union[str, None] = "202604301300_compliance_officer"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _pg_enum_type_for_column(conn, table: str, column: str) -> str | None:
    row = conn.execute(
        sa.text(
            """
            SELECT pg_type.typname
            FROM pg_attribute
            JOIN pg_class ON pg_class.oid = pg_attribute.attrelid
            JOIN pg_type ON pg_type.oid = pg_attribute.atttypid
            WHERE pg_class.relname = :t
              AND pg_attribute.attname = :c
              AND pg_type.typtype = 'e'
            """
        ),
        {"t": table, "c": column},
    ).fetchone()
    return str(row[0]) if row and row[0] else None


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
    conn = op.get_bind()
    if _is_postgres():
        enum_type = _pg_enum_type_for_column(conn, "users", "role")
        if enum_type:
            ctx = op.get_context()
            with ctx.autocommit_block():
                conn.exec_driver_sql(
                    f"ALTER TYPE {enum_type} ADD VALUE IF NOT EXISTS 'hr_officer';"
                )

    jtype = sa.JSON()
    if _is_postgres():
        jtype = sa.JSON().with_variant(postgresql.JSONB, "postgresql")
    c_u = sa.TIMESTAMP(timezone=True)
    uid = sa.String(36)

    op.create_table(
        "workforce_employees",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column(
            "tenant_id",
            sa.String(36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("own_company_id", uid, nullable=True, index=True),
        sa.Column("candidate_id", uid, sa.ForeignKey("candidates.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("company_id", uid, nullable=True, index=True),
        sa.Column("display_name", sa.String(512), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="onboarding"),
        sa.Column("hire_date", sa.Date(), nullable=True),
        sa.Column("probation_end", sa.Date(), nullable=True),
        sa.Column("termination_date", sa.Date(), nullable=True),
        sa.Column("handoff_at", c_u, nullable=True),
        sa.Column("handoff_by_user_id", uid, nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("meta", jtype, nullable=True),
        sa.Column("created_at", c_u, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", c_u, server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_workforce_employees_tenant_status",
        "workforce_employees",
        ["tenant_id", "status"],
    )
    if _is_postgres():
        op.execute(
            """
            CREATE UNIQUE INDEX uq_workforce_employee_candidate
            ON workforce_employees (tenant_id, candidate_id)
            WHERE candidate_id IS NOT NULL;
            """
        )
    _rls_tenant("workforce_employees")


def downgrade() -> None:
    op.drop_table("workforce_employees")
    # PostgreSQL: no safe removal of enum value for hr_officer
