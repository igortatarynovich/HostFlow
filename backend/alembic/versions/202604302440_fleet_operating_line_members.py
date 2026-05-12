"""Fleet: vehicle and driver membership on operating lines.

Revision ID: 202604302440_fleet_operating_line_members
Revises: 202604302430_fleet_work_models
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202604302440_fleet_operating_line_members"
down_revision: Union[str, None] = "202604302430_fleet_work_models"
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

    tbl_veh = "fleet_operating_line_vehicles"
    if not insp.has_table(tbl_veh):
        op.create_table(
            tbl_veh,
            sa.Column("id", uid, primary_key=True, nullable=False),
            sa.Column("tenant_id", uid, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column(
                "line_id",
                uid,
                sa.ForeignKey("fleet_operating_lines.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "vehicle_id",
                uid,
                sa.ForeignKey("fleet_vehicles.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "default_work_model_id",
                uid,
                sa.ForeignKey("fleet_work_models.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("created_at", ts, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", ts, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("line_id", "vehicle_id", name="uq_fleet_olv_line_vehicle"),
        )
    ix_olv = "ix_fleet_olv_tenant_line"
    if ix_olv not in _index_names(bind, tbl_veh):
        op.create_index(ix_olv, tbl_veh, ["tenant_id", "line_id"])
    _rls_tenant(tbl_veh)

    tbl_drv = "fleet_operating_line_drivers"
    if not insp.has_table(tbl_drv):
        op.create_table(
            tbl_drv,
            sa.Column("id", uid, primary_key=True, nullable=False),
            sa.Column("tenant_id", uid, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column(
                "line_id",
                uid,
                sa.ForeignKey("fleet_operating_lines.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "fleet_driver_id",
                uid,
                sa.ForeignKey("fleet_drivers.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "work_model_id",
                uid,
                sa.ForeignKey("fleet_work_models.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("effective_from", sa.Date(), nullable=True),
            sa.Column("effective_to", sa.Date(), nullable=True),
            sa.Column("created_at", ts, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", ts, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("line_id", "fleet_driver_id", name="uq_fleet_old_line_driver"),
        )
    ix_old = "ix_fleet_old_tenant_line"
    if ix_old not in _index_names(bind, tbl_drv):
        op.create_index(ix_old, tbl_drv, ["tenant_id", "line_id"])
    _rls_tenant(tbl_drv)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    def _drop_line_members(table: str, ix_name: str) -> None:
        if not insp.has_table(table):
            return
        if _is_postgres():
            op.execute(f"DROP POLICY IF EXISTS rls_{table}_tenant ON {table};")
            op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
        if ix_name in _index_names(bind, table):
            op.drop_index(ix_name, table_name=table)
        op.drop_table(table)

    _drop_line_members("fleet_operating_line_drivers", "ix_fleet_old_tenant_line")
    _drop_line_members("fleet_operating_line_vehicles", "ix_fleet_olv_tenant_line")
