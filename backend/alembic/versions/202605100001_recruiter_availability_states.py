"""recruiter_availability_states — canonical recruitment auto-assign availability (not User.extra).

Revision ID: 202605100001_ras
Revises: 202602110001_hr_ctx_links
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202605100001_ras"
down_revision: Union[str, None] = "202602110001_hr_ctx_links"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _has_table(conn: sa.Connection, name: str) -> bool:
    return name in sa.inspect(conn).get_table_names()


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
    if _has_table(conn, "recruiter_availability_states"):
        _rls_tenant("recruiter_availability_states")
        return

    uid = sa.String(36)
    ts = sa.DateTime(timezone=True)

    op.create_table(
        "recruiter_availability_states",
        sa.Column("id", uid, primary_key=True, nullable=False),
        sa.Column(
            "tenant_id",
            uid,
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id",
            uid,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("state", sa.String(32), nullable=False, server_default=sa.text("'available'")),
        sa.Column(
            "updated_at",
            ts,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_recruiter_availability_tenant_user"),
    )
    op.create_index(
        "ix_recruiter_availability_tenant_user",
        "recruiter_availability_states",
        ["tenant_id", "user_id"],
    )
    _rls_tenant("recruiter_availability_states")


def downgrade() -> None:
    conn = op.get_bind()
    if not _has_table(conn, "recruiter_availability_states"):
        return
    if _is_postgres():
        op.execute("DROP POLICY IF EXISTS rls_recruiter_availability_states_tenant ON recruiter_availability_states;")
        op.execute("ALTER TABLE recruiter_availability_states DISABLE ROW LEVEL SECURITY;")
    op.drop_index("ix_recruiter_availability_tenant_user", table_name="recruiter_availability_states")
    op.drop_table("recruiter_availability_states")
