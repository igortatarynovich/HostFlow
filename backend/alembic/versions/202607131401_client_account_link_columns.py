"""Stage 1A: leads/companies client_account_id link columns.

Revision ID: 202607131401_client_account_link_columns
Revises: 202607131400_client_accounts_stage_1a
Create Date: 2026-07-13
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "202607131401_client_account_link_columns"
down_revision: Union[str, Sequence[str], None] = "202607131400_client_accounts_stage_1a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(insp: sa.Inspector, table: str, column: str) -> bool:
    return column in {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    insp = sa.inspect(bind)

    if dialect == "postgresql":
        op.execute("SET lock_timeout TO '30s'")

    if "leads" in insp.get_table_names() and not _has_column(insp, "leads", "client_account_id"):
        op.add_column("leads", sa.Column("client_account_id", sa.String(length=36), nullable=True))
    if "leads" in insp.get_table_names():
        if dialect == "postgresql":
            op.execute("CREATE INDEX IF NOT EXISTS ix_leads_client_account_id ON leads (client_account_id)")
        else:
            op.create_index("ix_leads_client_account_id", "leads", ["client_account_id"], unique=False)

    if "companies" in insp.get_table_names() and not _has_column(insp, "companies", "client_account_id"):
        op.add_column("companies", sa.Column("client_account_id", sa.String(length=36), nullable=True))
    if "companies" in insp.get_table_names():
        if dialect == "postgresql":
            op.execute(
                "CREATE INDEX IF NOT EXISTS ix_companies_client_account_id ON companies (client_account_id)"
            )
        else:
            op.create_index(
                "ix_companies_client_account_id",
                "companies",
                ["client_account_id"],
                unique=False,
            )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    insp = sa.inspect(bind)

    if "companies" in insp.get_table_names() and _has_column(insp, "companies", "client_account_id"):
        if dialect == "postgresql":
            op.execute("DROP INDEX IF EXISTS ix_companies_client_account_id")
        else:
            op.drop_index("ix_companies_client_account_id", table_name="companies")
        op.drop_column("companies", "client_account_id")

    if "leads" in insp.get_table_names() and _has_column(insp, "leads", "client_account_id"):
        if dialect == "postgresql":
            op.execute("DROP INDEX IF EXISTS ix_leads_client_account_id")
        else:
            op.drop_index("ix_leads_client_account_id", table_name="leads")
        op.drop_column("leads", "client_account_id")
