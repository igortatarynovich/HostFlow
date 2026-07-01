"""Fleet work models (rotation / coverage templates: work + rest == cycle).

Revision ID: 202604302430_fleet_work_models
Revises: 202604302420_fleet_park_core
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202604302430_fleet_work_models"
down_revision: Union[str, None] = "202604302420_fleet_park_core"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _fleet_work_models_index_names(bind) -> set[str]:
    insp = sa.inspect(bind)
    if not insp.has_table("fleet_work_models"):
        return set()
    return {ix.get("name") for ix in insp.get_indexes("fleet_work_models") if ix.get("name")}


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
    bind = op.get_bind()
    insp = sa.inspect(bind)
    uid = sa.String(36)
    ts = sa.TIMESTAMP(timezone=True)

    # Table may already exist if the DB was partially migrated or manually aligned with ORM.
    if not insp.has_table("fleet_work_models"):
        op.create_table(
            "fleet_work_models",
            sa.Column("id", uid, primary_key=True, nullable=False),
            sa.Column("tenant_id", uid, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("work_days", sa.Integer(), nullable=False),
            sa.Column("rest_days", sa.Integer(), nullable=False),
            sa.Column("cycle_length", sa.Integer(), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", ts, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", ts, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )

    idx_name = "ix_fleet_work_models_tenant_name"
    if idx_name not in _fleet_work_models_index_names(bind):
        op.create_index(idx_name, "fleet_work_models", ["tenant_id", "name"])

    # Table may have existed before this revision; ensure ORM columns (e.g. notes) exist.
    insp2 = sa.inspect(op.get_bind())
    if insp2.has_table("fleet_work_models"):
        col_names = {c["name"] for c in insp2.get_columns("fleet_work_models")}
        if "notes" not in col_names:
            op.add_column("fleet_work_models", sa.Column("notes", sa.Text(), nullable=True))

    _rls_tenant("fleet_work_models")


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("fleet_work_models"):
        return
    if _is_postgres():
        op.execute("DROP POLICY IF EXISTS rls_fleet_work_models_tenant ON fleet_work_models;")
        op.execute("ALTER TABLE fleet_work_models DISABLE ROW LEVEL SECURITY;")
    idx_name = "ix_fleet_work_models_tenant_name"
    if idx_name in _fleet_work_models_index_names(bind):
        op.drop_index(idx_name, table_name="fleet_work_models")
    op.drop_table("fleet_work_models")
