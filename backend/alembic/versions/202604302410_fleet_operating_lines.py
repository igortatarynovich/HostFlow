"""Fleet: operating lines table (idempotent if created in an older branch).

Revision ID: 202604302410_fleet_operating_lines
Revises: 202604302400_fleet_operating_line_seasonality
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202604302410_fleet_operating_lines"
down_revision: Union[str, None] = "202604302400_fleet_operating_line_seasonality"
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
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("fleet_operating_lines"):
        if _is_postgres():
            op.execute(
                """
                DO $body$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = 'fleet_operating_lines'
                          AND column_name = 'seasonality_month_factors'
                    ) THEN
                        ALTER TABLE fleet_operating_lines
                            ADD COLUMN seasonality_month_factors JSONB;
                    END IF;
                END
                $body$;
                """
            )
        _rls_tenant("fleet_operating_lines")
        return

    uid = sa.String(36)
    ts = sa.TIMESTAMP(timezone=True)
    seasonality_col = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")

    op.create_table(
        "fleet_operating_lines",
        sa.Column("id", uid, primary_key=True, nullable=False),
        sa.Column("tenant_id", uid, sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
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
            "client_company_id",
            uid,
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("seasonality_month_factors", seasonality_col, nullable=True),
        sa.Column("created_at", ts, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", ts, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index(
        "ix_fleet_operating_lines_tenant_op_co",
        "fleet_operating_lines",
        ["tenant_id", "operating_company_id"],
    )
    op.create_index(
        "ix_fleet_operating_lines_tenant_client_co",
        "fleet_operating_lines",
        ["tenant_id", "client_company_id"],
    )
    _rls_tenant("fleet_operating_lines")


def downgrade() -> None:
    if _is_postgres():
        op.execute("DROP POLICY IF EXISTS rls_fleet_operating_lines_tenant ON fleet_operating_lines;")
        op.execute("ALTER TABLE fleet_operating_lines DISABLE ROW LEVEL SECURITY;")
    op.drop_index("ix_fleet_operating_lines_tenant_client_co", table_name="fleet_operating_lines")
    op.drop_index("ix_fleet_operating_lines_tenant_op_co", table_name="fleet_operating_lines")
    op.drop_table("fleet_operating_lines")
