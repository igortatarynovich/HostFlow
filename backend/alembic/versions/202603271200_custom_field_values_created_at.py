"""custom_field_values.created_at — align DB with TimestampMixin (ORM expects created_at + updated_at)

Revision ID: 202603271200_cfv_created_at
Revises: 202603270000_conv_root
Create Date: 2026-03-27

Original table (202501010000) only had updated_at; model uses TimestampMixin → GET /leads failed with
UndefinedColumnError on custom_field_values.created_at.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "202603271200_cfv_created_at"
down_revision: Union[str, None] = "202603270000_conv_root"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    try:
        return insp.has_table(table)
    except Exception:
        return False


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    try:
        return column in [c["name"] for c in insp.get_columns(table)]
    except Exception:
        return False


def upgrade() -> None:
    if not _has_table("custom_field_values"):
        return
    if _has_column("custom_field_values", "created_at"):
        return

    op.add_column(
        "custom_field_values",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(sa.text("UPDATE custom_field_values SET created_at = updated_at WHERE created_at IS NULL"))
    op.alter_column(
        "custom_field_values",
        "created_at",
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )


def downgrade() -> None:
    if not _has_table("custom_field_values"):
        return
    if not _has_column("custom_field_values", "created_at"):
        return
    op.drop_column("custom_field_values", "created_at")
