"""Add intake/public application columns to candidates.

Revision ID: 202604050001_public_intake_columns
Revises: 202604020002_document_types_requested_from
Create Date: 2026-04-05 00:01:00.000000
"""

from __future__ import annotations

from typing import Any

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "202604050001_public_intake_columns"
down_revision = "202604020002_document_types_requested_from"
branch_labels = None
depends_on = None


def _json_type(dialect: str) -> Any:
    if dialect == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def _json_default(dialect: str) -> sa.sql.elements.TextClause:
    if dialect == "postgresql":
        return sa.text("'{}'::jsonb")
    return sa.text("'{}'")


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name if bind is not None else "postgresql"
    json_type = _json_type(dialect)
    json_default = _json_default(dialect)

    op.add_column("candidates", sa.Column("intake_token", sa.String(length=128), nullable=True))
    op.add_column(
        "candidates",
        sa.Column("intake_token_created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "candidates",
        sa.Column("intake_token_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "candidates",
        sa.Column("intake_submitted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "candidates",
        sa.Column(
            "intake_status",
            sa.String(length=32),
            nullable=True,
            server_default=sa.text("'draft'::varchar"),
        ),
    )
    op.add_column(
        "candidates",
        sa.Column(
            "intake_state",
            json_type,
            nullable=True,
            server_default=json_default,
        ),
    )

    op.create_unique_constraint("uq_candidates_intake_token", "candidates", ["intake_token"])


def downgrade() -> None:
    op.drop_constraint("uq_candidates_intake_token", "candidates", type_="unique")
    op.drop_column("candidates", "intake_state")
    op.drop_column("candidates", "intake_status")
    op.drop_column("candidates", "intake_submitted_at")
    op.drop_column("candidates", "intake_token_expires_at")
    op.drop_column("candidates", "intake_token_created_at")
    op.drop_column("candidates", "intake_token")
