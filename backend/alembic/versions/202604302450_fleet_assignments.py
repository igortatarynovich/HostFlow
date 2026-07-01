"""Fleet: operational assignments (vehicle + optional trailer/driver on a line).

Revision ID: 202604302450_fleet_assignments
Revises: 202604302440_fleet_operating_line_members
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202604302450_fleet_assignments"
down_revision: Union[str, None] = "202604302440_fleet_operating_line_members"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _index_names(bind, table: str) -> set[str]:
    insp = sa.inspect(bind)
    if not insp.has_table(table):
        return set()
    return {ix["name"] for ix in insp.get_indexes(table) if ix.get("name")}


def _column_names(bind, table: str) -> set[str]:
    insp = sa.inspect(bind)
    if not insp.has_table(table):
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def _ensure_assignments_columns(uid, ts) -> None:
    """Old DBs may have fleet_assignments from an earlier draft without line_id / FKs — add missing columns."""
    tbl = "fleet_assignments"
    bind = op.get_bind()
    cols = _column_names(bind, tbl)

    def add(name: str, column: sa.Column) -> None:
        nonlocal cols
        if name in cols:
            return
        op.add_column(tbl, column)
        cols.add(name)

    add(
        "tenant_id",
        sa.Column("tenant_id", uid, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True),
    )
    add(
        "line_id",
        sa.Column("line_id", uid, sa.ForeignKey("fleet_operating_lines.id", ondelete="CASCADE"), nullable=True),
    )
    add(
        "vehicle_id",
        sa.Column("vehicle_id", uid, sa.ForeignKey("fleet_vehicles.id", ondelete="CASCADE"), nullable=True),
    )
    add(
        "trailer_id",
        sa.Column("trailer_id", uid, sa.ForeignKey("fleet_trailers.id", ondelete="SET NULL"), nullable=True),
    )
    add(
        "primary_driver_id",
        sa.Column("primary_driver_id", uid, sa.ForeignKey("fleet_drivers.id", ondelete="SET NULL"), nullable=True),
    )
    add(
        "status",
        sa.Column("status", sa.String(32), nullable=True, server_default="planned"),
    )
    add("service_start", sa.Column("service_start", sa.Date(), nullable=True))
    add("service_end", sa.Column("service_end", sa.Date(), nullable=True))
    add("notes", sa.Column("notes", sa.Text(), nullable=True))
    add(
        "created_at",
        sa.Column("created_at", ts, nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    add(
        "updated_at",
        sa.Column("updated_at", ts, nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")),
    )


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

    tbl = "fleet_assignments"
    if not insp.has_table(tbl):
        op.create_table(
            tbl,
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
                "trailer_id",
                uid,
                sa.ForeignKey("fleet_trailers.id", ondelete="SET NULL"),
                nullable=True,
                index=True,
            ),
            sa.Column(
                "primary_driver_id",
                uid,
                sa.ForeignKey("fleet_drivers.id", ondelete="SET NULL"),
                nullable=True,
                index=True,
            ),
            sa.Column("status", sa.String(32), nullable=False, server_default="planned"),
            sa.Column("service_start", sa.Date(), nullable=False),
            sa.Column("service_end", sa.Date(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", ts, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", ts, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
    else:
        _ensure_assignments_columns(uid, ts)

    ix_name = "ix_fleet_assign_tenant_line_start"
    cols_ready = _column_names(bind, tbl)
    idx_cols = ("tenant_id", "line_id", "service_start")
    if all(c in cols_ready for c in idx_cols) and ix_name not in _index_names(bind, tbl):
        op.create_index(ix_name, tbl, list(idx_cols))
    _rls_tenant(tbl)


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    table = "fleet_assignments"
    if not insp.has_table(table):
        return
    if _is_postgres():
        op.execute(f"DROP POLICY IF EXISTS rls_{table}_tenant ON {table};")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
    ix_name = "ix_fleet_assign_tenant_line_start"
    if ix_name in _index_names(bind, table):
        op.drop_index(ix_name, table_name=table)
    op.drop_table(table)
