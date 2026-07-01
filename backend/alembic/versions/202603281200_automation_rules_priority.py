"""automation_rules table (if missing) + priority — §2.10 lead.qualification

Revision ID: 202603281200_ar_priority
Revises: 202603271300_generic_inbound_wh
Create Date: 2026-03-28

Note: `automation_rules` was previously created only via dev SQLite `ensure_automation_rules_schema`.
PostgreSQL installs need the full table here before `priority` can be added.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "202603281200_ar_priority"
down_revision: Union[str, None] = "202603271300_generic_inbound_wh"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    tables = insp.get_table_names()

    if "automation_rules" not in tables:
        op.create_table(
            "automation_rules",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("tenant_id", sa.String(length=36), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("trigger", sa.String(length=64), nullable=False),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("title", sa.String(length=256), nullable=True),
            sa.Column("conditions_json", sa.Text(), nullable=True),
            sa.Column("actions_json", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            ),
        )
        op.create_index("ix_automation_rules_tenant_trigger", "automation_rules", ["tenant_id", "trigger"])
        op.create_index("ix_automation_rules_tenant_enabled", "automation_rules", ["tenant_id", "enabled"])
        return

    cols = {c["name"] for c in insp.get_columns("automation_rules")}
    if "priority" not in cols:
        op.add_column(
            "automation_rules",
            sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        )

    existing_ix = {ix["name"] for ix in insp.get_indexes("automation_rules")}
    if "ix_automation_rules_tenant_trigger" not in existing_ix:
        op.create_index("ix_automation_rules_tenant_trigger", "automation_rules", ["tenant_id", "trigger"])
    if "ix_automation_rules_tenant_enabled" not in existing_ix:
        op.create_index("ix_automation_rules_tenant_enabled", "automation_rules", ["tenant_id", "enabled"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "automation_rules" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("automation_rules")}
    if "priority" in cols:
        op.drop_column("automation_rules", "priority")
