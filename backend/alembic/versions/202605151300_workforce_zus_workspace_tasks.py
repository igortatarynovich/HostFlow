"""Workforce ZUS workspace operational tasks (MVP queue; no ZUS API).

Revision ID: 202605151300_zus_workspace_mvp
Revises: 202605122000_hr_workforce_core
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "202605151300_zus_workspace_mvp"
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
    jtype = sa.JSON()
    if _is_postgres():
        jtype = sa.JSON().with_variant(postgresql.JSONB, "postgresql")
    c_u = sa.TIMESTAMP(timezone=True)
    uid = sa.String(36)

    op.create_table(
        "workforce_zus_workspace_tasks",
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
        sa.Column("workspace_lane", sa.String(32), nullable=False, index=True),
        sa.Column("task_kind", sa.String(64), nullable=False, index=True),
        sa.Column("form_kind", sa.String(8), nullable=True, index=True),
        sa.Column("form_status", sa.String(32), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="open", index=True),
        sa.Column("due_at", c_u, nullable=True, index=True),
        sa.Column(
            "assigned_hr_user_id",
            uid,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("export_status", sa.String(32), nullable=True),
        sa.Column("checklist_json", jtype, nullable=True),
        sa.Column("title", sa.String(256), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", c_u, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", c_u, server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_zus_ws_tasks_tenant_lane_status",
        "workforce_zus_workspace_tasks",
        ["tenant_id", "workspace_lane", "status"],
    )
    _rls_tenant("workforce_zus_workspace_tasks")


def downgrade() -> None:
    if _is_postgres():
        op.execute("DROP POLICY IF EXISTS rls_workforce_zus_workspace_tasks_tenant ON workforce_zus_workspace_tasks;")
        op.execute("ALTER TABLE workforce_zus_workspace_tasks NO ROW LEVEL SECURITY;")
    op.drop_index("ix_zus_ws_tasks_tenant_lane_status", table_name="workforce_zus_workspace_tasks")
    op.drop_table("workforce_zus_workspace_tasks")
