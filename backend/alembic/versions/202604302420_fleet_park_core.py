"""Fleet park core: vehicles, trailers, drivers (tenant-scoped).

Revision ID: 202604302420_fleet_park_core
Revises: 202604302410_fleet_operating_lines
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202604302420_fleet_park_core"
down_revision: Union[str, None] = "202604302410_fleet_operating_lines"
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


def _ensure_fleet_vehicles_pg() -> None:
    op.execute(
        """
        ALTER TABLE fleet_vehicles ADD COLUMN IF NOT EXISTS internal_code VARCHAR(64);
        ALTER TABLE fleet_vehicles ADD COLUMN IF NOT EXISTS registration_plate VARCHAR(32);
        ALTER TABLE fleet_vehicles ADD COLUMN IF NOT EXISTS vin VARCHAR(32);
        ALTER TABLE fleet_vehicles ADD COLUMN IF NOT EXISTS brand VARCHAR(64);
        ALTER TABLE fleet_vehicles ADD COLUMN IF NOT EXISTS model VARCHAR(64);
        ALTER TABLE fleet_vehicles ADD COLUMN IF NOT EXISTS year SMALLINT;
        ALTER TABLE fleet_vehicles ADD COLUMN IF NOT EXISTS status VARCHAR(32) NOT NULL DEFAULT 'active';
        ALTER TABLE fleet_vehicles ADD COLUMN IF NOT EXISTS operating_company_id VARCHAR(36);
        ALTER TABLE fleet_vehicles ADD COLUMN IF NOT EXISTS notes TEXT;
        ALTER TABLE fleet_vehicles ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
        ALTER TABLE fleet_vehicles ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
        """
    )
    op.execute(
        """
        DO $body$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fleet_vehicles_operating_company_id_fkey'
            ) THEN
                ALTER TABLE fleet_vehicles
                    ADD CONSTRAINT fleet_vehicles_operating_company_id_fkey
                    FOREIGN KEY (operating_company_id) REFERENCES companies(id) ON DELETE SET NULL;
            END IF;
        END
        $body$;
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_fleet_vehicles_tenant_status ON fleet_vehicles (tenant_id, status);")


def _ensure_fleet_trailers_pg() -> None:
    op.execute(
        """
        ALTER TABLE fleet_trailers ADD COLUMN IF NOT EXISTS internal_code VARCHAR(64);
        ALTER TABLE fleet_trailers ADD COLUMN IF NOT EXISTS registration_plate VARCHAR(32);
        ALTER TABLE fleet_trailers ADD COLUMN IF NOT EXISTS trailer_type VARCHAR(64);
        ALTER TABLE fleet_trailers ADD COLUMN IF NOT EXISTS status VARCHAR(32) NOT NULL DEFAULT 'active';
        ALTER TABLE fleet_trailers ADD COLUMN IF NOT EXISTS operating_company_id VARCHAR(36);
        ALTER TABLE fleet_trailers ADD COLUMN IF NOT EXISTS notes TEXT;
        ALTER TABLE fleet_trailers ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
        ALTER TABLE fleet_trailers ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
        """
    )
    op.execute(
        """
        DO $body$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fleet_trailers_operating_company_id_fkey'
            ) THEN
                ALTER TABLE fleet_trailers
                    ADD CONSTRAINT fleet_trailers_operating_company_id_fkey
                    FOREIGN KEY (operating_company_id) REFERENCES companies(id) ON DELETE SET NULL;
            END IF;
        END
        $body$;
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_fleet_trailers_tenant_status ON fleet_trailers (tenant_id, status);")


def _ensure_fleet_drivers_pg() -> None:
    op.execute(
        """
        ALTER TABLE fleet_drivers ADD COLUMN IF NOT EXISTS display_code VARCHAR(64);
        ALTER TABLE fleet_drivers ADD COLUMN IF NOT EXISTS first_name VARCHAR(128);
        ALTER TABLE fleet_drivers ADD COLUMN IF NOT EXISTS last_name VARCHAR(128);
        ALTER TABLE fleet_drivers ADD COLUMN IF NOT EXISTS status VARCHAR(32) NOT NULL DEFAULT 'active';
        ALTER TABLE fleet_drivers ADD COLUMN IF NOT EXISTS operating_company_id VARCHAR(36);
        ALTER TABLE fleet_drivers ADD COLUMN IF NOT EXISTS workforce_employee_id VARCHAR(36);
        ALTER TABLE fleet_drivers ADD COLUMN IF NOT EXISTS phone VARCHAR(64);
        ALTER TABLE fleet_drivers ADD COLUMN IF NOT EXISTS notes TEXT;
        ALTER TABLE fleet_drivers ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
        ALTER TABLE fleet_drivers ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
        """
    )
    op.execute(
        """
        DO $body$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fleet_drivers_operating_company_id_fkey'
            ) THEN
                ALTER TABLE fleet_drivers
                    ADD CONSTRAINT fleet_drivers_operating_company_id_fkey
                    FOREIGN KEY (operating_company_id) REFERENCES companies(id) ON DELETE SET NULL;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fleet_drivers_workforce_employee_id_fkey'
            ) THEN
                ALTER TABLE fleet_drivers
                    ADD CONSTRAINT fleet_drivers_workforce_employee_id_fkey
                    FOREIGN KEY (workforce_employee_id) REFERENCES workforce_employees(id) ON DELETE SET NULL;
            END IF;
        END
        $body$;
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_fleet_drivers_tenant_status ON fleet_drivers (tenant_id, status);")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_fleet_drivers_tenant_workforce ON fleet_drivers (tenant_id, workforce_employee_id);"
    )


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    uid = sa.String(36)
    ts = sa.TIMESTAMP(timezone=True)

    if not insp.has_table("fleet_vehicles"):
        op.create_table(
            "fleet_vehicles",
            sa.Column("id", uid, primary_key=True, nullable=False),
            sa.Column("tenant_id", uid, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("internal_code", sa.String(64), nullable=True),
            sa.Column("registration_plate", sa.String(32), nullable=True),
            sa.Column("vin", sa.String(32), nullable=True),
            sa.Column("brand", sa.String(64), nullable=True),
            sa.Column("model", sa.String(64), nullable=True),
            sa.Column("year", sa.SmallInteger(), nullable=True),
            sa.Column(
                "status",
                sa.String(32),
                nullable=False,
                server_default=sa.text("'active'"),
            ),
            sa.Column(
                "operating_company_id",
                uid,
                sa.ForeignKey("companies.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", ts, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", ts, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index("ix_fleet_vehicles_tenant_status", "fleet_vehicles", ["tenant_id", "status"])
    elif _is_postgres():
        _ensure_fleet_vehicles_pg()
    _rls_tenant("fleet_vehicles")

    if not insp.has_table("fleet_trailers"):
        op.create_table(
            "fleet_trailers",
            sa.Column("id", uid, primary_key=True, nullable=False),
            sa.Column("tenant_id", uid, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("internal_code", sa.String(64), nullable=True),
            sa.Column("registration_plate", sa.String(32), nullable=True),
            sa.Column("trailer_type", sa.String(64), nullable=True),
            sa.Column(
                "status",
                sa.String(32),
                nullable=False,
                server_default=sa.text("'active'"),
            ),
            sa.Column(
                "operating_company_id",
                uid,
                sa.ForeignKey("companies.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", ts, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", ts, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index("ix_fleet_trailers_tenant_status", "fleet_trailers", ["tenant_id", "status"])
    elif _is_postgres():
        _ensure_fleet_trailers_pg()
    _rls_tenant("fleet_trailers")

    if not insp.has_table("fleet_drivers"):
        op.create_table(
            "fleet_drivers",
            sa.Column("id", uid, primary_key=True, nullable=False),
            sa.Column("tenant_id", uid, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("display_code", sa.String(64), nullable=True),
            sa.Column("first_name", sa.String(128), nullable=True),
            sa.Column("last_name", sa.String(128), nullable=True),
            sa.Column(
                "status",
                sa.String(32),
                nullable=False,
                server_default=sa.text("'active'"),
            ),
            sa.Column(
                "operating_company_id",
                uid,
                sa.ForeignKey("companies.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "workforce_employee_id",
                uid,
                sa.ForeignKey("workforce_employees.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("phone", sa.String(64), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", ts, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", ts, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index("ix_fleet_drivers_tenant_status", "fleet_drivers", ["tenant_id", "status"])
        op.create_index("ix_fleet_drivers_tenant_workforce", "fleet_drivers", ["tenant_id", "workforce_employee_id"])
    elif _is_postgres():
        _ensure_fleet_drivers_pg()
    _rls_tenant("fleet_drivers")


def downgrade() -> None:
    for table in ("fleet_drivers", "fleet_trailers", "fleet_vehicles"):
        if _is_postgres():
            op.execute(f"DROP POLICY IF EXISTS rls_{table}_tenant ON {table};")
            op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
    op.drop_index("ix_fleet_drivers_tenant_workforce", table_name="fleet_drivers")
    op.drop_index("ix_fleet_drivers_tenant_status", table_name="fleet_drivers")
    op.drop_table("fleet_drivers")
    op.drop_index("ix_fleet_trailers_tenant_status", table_name="fleet_trailers")
    op.drop_table("fleet_trailers")
    op.drop_index("ix_fleet_vehicles_tenant_status", table_name="fleet_vehicles")
    op.drop_table("fleet_vehicles")
