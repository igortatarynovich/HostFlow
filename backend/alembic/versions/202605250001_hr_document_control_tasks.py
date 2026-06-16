"""HR document control tasks (owner/action/due/status).

Revision ID: 202605250001_hr_document_control_tasks
Revises: 202605122000_hr_workforce_core
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202605250001_hr_document_control_tasks"
down_revision: Union[str, None] = "202605122000_hr_workforce_core"
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
        "workforce_hr_document_control_tasks",
        sa.Column("id", uid, primary_key=True, nullable=False),
        sa.Column("tenant_id", uid, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column(
            "employee_id",
            uid,
            sa.ForeignKey("workforce_employees.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("document_code", sa.String(64), nullable=False, index=True),
        sa.Column("owner", sa.String(64), nullable=True),
        sa.Column("next_action", sa.String(256), nullable=True),
        sa.Column("next_due_date", sa.Date(), nullable=True),
        sa.Column("comment", sa.String(2000), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_unique_constraint(
        "uq_wf_hr_doc_ctrl_task_employee_doc",
        "workforce_hr_document_control_tasks",
        ["tenant_id", "employee_id", "document_code"],
    )
    _rls_tenant("workforce_hr_document_control_tasks")


def downgrade() -> None:
    t = "workforce_hr_document_control_tasks"
    if _is_postgres():
        op.execute(f'DROP POLICY IF EXISTS rls_{t}_tenant ON "{t}";')
        op.execute(f'ALTER TABLE "{t}" DISABLE ROW LEVEL SECURITY;')
    op.drop_table(t)

