"""Workforce lifecycle ledger events.

Revision ID: 202605250002_workforce_lifecycle_ledger
Revises: 09ded874040a
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202605250002_workforce_lifecycle_ledger"
down_revision: Union[str, None] = "09ded874040a"
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
    op.create_table(
        "workforce_lifecycle_events",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column(
            "employee_id",
            sa.String(36),
            sa.ForeignKey("workforce_employees.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("event_code", sa.String(96), nullable=False, index=True),
        sa.Column("category", sa.String(32), nullable=False, index=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True, index=True),
        sa.Column("owner", sa.String(64), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True, index=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="open", index=True),
        sa.Column("dedupe_key", sa.String(160), nullable=True, index=True),
        sa.Column("source_type", sa.String(64), nullable=True),
        sa.Column("source_ref", sa.String(96), nullable=True),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("description", sa.String(2000), nullable=True),
        sa.Column("references_json", jtype, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("attachments_json", jtype, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("meta", jtype, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_unique_constraint(
        "uq_wf_lifecycle_dedupe",
        "workforce_lifecycle_events",
        ["tenant_id", "employee_id", "dedupe_key"],
    )
    _rls_tenant("workforce_lifecycle_events")


def downgrade() -> None:
    t = "workforce_lifecycle_events"
    if _is_postgres():
        op.execute(f'DROP POLICY IF EXISTS rls_{t}_tenant ON "{t}";')
        op.execute(f'ALTER TABLE "{t}" DISABLE ROW LEVEL SECURITY;')
    op.drop_table(t)
