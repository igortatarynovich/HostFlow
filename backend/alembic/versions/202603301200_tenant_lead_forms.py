"""tenant_lead_forms — §2.16 active lead forms cap (Solo 1 / Team 3 / Business 20 + pack).

Revision ID: 202603301200_tenant_lead_forms
Revises: 202603291900_doc_tsv_gin
Create Date: 2026-03-30
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "202603301200_tenant_lead_forms"
down_revision: Union[str, None] = "202603291900_doc_tsv_gin"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "tenant_lead_forms" in insp.get_table_names():
        return
    op.create_table(
        "tenant_lead_forms",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
    op.create_index("ix_tenant_lead_forms_tenant_active", "tenant_lead_forms", ["tenant_id", "is_active"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if "tenant_lead_forms" not in insp.get_table_names():
        return
    op.drop_index("ix_tenant_lead_forms_tenant_active", table_name="tenant_lead_forms")
    op.drop_table("tenant_lead_forms")
