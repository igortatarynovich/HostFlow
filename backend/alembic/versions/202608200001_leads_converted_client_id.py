"""Add converted_client_id to leads.

Revision ID: 202608200001_leads_converted_client_id
Revises: 202608190001_module_registry_p1
Create Date: 2026-08-20
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "202608200001_leads_converted_client_id"
down_revision: Union[str, Sequence[str], None] = "202608190001_module_registry_p1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "leads" not in insp.get_table_names():
        return
    dialect = bind.dialect.name
    if dialect == "postgresql":
        op.execute("ALTER TABLE leads ADD COLUMN IF NOT EXISTS converted_client_id VARCHAR(36)")
        op.execute("CREATE INDEX IF NOT EXISTS ix_leads_converted_client_id ON leads (converted_client_id)")
        return

    cols = {c["name"] for c in insp.get_columns("leads")}
    if "converted_client_id" not in cols:
        op.add_column("leads", sa.Column("converted_client_id", sa.String(length=36), nullable=True))
    indexes = {idx["name"] for idx in insp.get_indexes("leads")}
    if "ix_leads_converted_client_id" not in indexes:
        op.create_index("ix_leads_converted_client_id", "leads", ["converted_client_id"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "leads" not in insp.get_table_names():
        return
    indexes = {idx["name"] for idx in insp.get_indexes("leads")}
    if "ix_leads_converted_client_id" in indexes:
        op.drop_index("ix_leads_converted_client_id", table_name="leads")
    cols = {c["name"] for c in insp.get_columns("leads")}
    if "converted_client_id" in cols:
        op.drop_column("leads", "converted_client_id")
