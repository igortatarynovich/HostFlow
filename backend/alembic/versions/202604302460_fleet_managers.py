"""Fleet: CRM users who manage vehicles and drivers (many-to-many).

Revision ID: 202604302460_fleet_managers
Revises: 202604302450_fleet_assignments
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202604302460_fleet_managers"
down_revision: Union[str, None] = "202604302450_fleet_assignments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _index_names(bind, table: str) -> set[str]:
    insp = sa.inspect(bind)
    if not insp.has_table(table):
        return set()
    return {ix["name"] for ix in insp.get_indexes(table) if ix.get("name")}


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

    tbl_v = "fleet_vehicle_managers"
    if not insp.has_table(tbl_v):
        op.create_table(
            tbl_v,
            sa.Column("id", uid, primary_key=True, nullable=False),
            sa.Column("tenant_id", uid, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column(
                "vehicle_id",
                uid,
                sa.ForeignKey("fleet_vehicles.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("user_id", uid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("created_at", ts, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", ts, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("vehicle_id", "user_id", name="uq_fleet_vehicle_managers_vehicle_user"),
        )
    ix_v = "ix_fleet_vehicle_mgr_tenant_vehicle"
    if ix_v not in _index_names(bind, tbl_v):
        op.create_index(ix_v, tbl_v, ["tenant_id", "vehicle_id"])
    _rls_tenant(tbl_v)

    tbl_d = "fleet_driver_managers"
    if not insp.has_table(tbl_d):
        op.create_table(
            tbl_d,
            sa.Column("id", uid, primary_key=True, nullable=False),
            sa.Column("tenant_id", uid, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column(
                "fleet_driver_id",
                uid,
                sa.ForeignKey("fleet_drivers.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("user_id", uid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("created_at", ts, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", ts, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("fleet_driver_id", "user_id", name="uq_fleet_driver_managers_driver_user"),
        )
    ix_d = "ix_fleet_driver_mgr_tenant_driver"
    if ix_d not in _index_names(bind, tbl_d):
        op.create_index(ix_d, tbl_d, ["tenant_id", "fleet_driver_id"])
    _rls_tenant(tbl_d)


def downgrade() -> None:
    bind = op.get_bind()

    def _drop_mgr(table: str, ix_name: str) -> None:
        insp = sa.inspect(bind)
        if not insp.has_table(table):
            return
        if _is_postgres():
            op.execute(f"DROP POLICY IF EXISTS rls_{table}_tenant ON {table};")
            op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
        if ix_name in _index_names(bind, table):
            op.drop_index(ix_name, table_name=table)
        op.drop_table(table)

    _drop_mgr("fleet_driver_managers", "ix_fleet_driver_mgr_tenant_driver")
    _drop_mgr("fleet_vehicle_managers", "ix_fleet_vehicle_mgr_tenant_vehicle")
