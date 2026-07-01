"""Create legacy stages table.

Revision ID: 202603181200
Revises: 202608120003_merge_heads_reminders_and_own_company
Create Date: 2026-03-18

This table is still referenced by parts of the codebase (seed/meta) as a legacy
dictionary. Some deployments may miss it entirely which causes repeated DB
errors and aborted transactions.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202603181200"
down_revision = "202608120003_merge_heads_reminders_and_own_company"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stages",
        sa.Column("code", sa.String(length=64), primary_key=True),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("sort", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("need_work_permit", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("need_visa", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("need_red_paper", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_terminal", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_stages_label", "stages", ["label"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_stages_label", table_name="stages")
    op.drop_table("stages")

