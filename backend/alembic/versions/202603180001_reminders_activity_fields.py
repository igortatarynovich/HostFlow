"""Add activity fields to reminders (duration/source).

Revision ID: 202603180001_reminders_activity_fields
Revises: 202608110004_services_cost_basis
Create Date: 2026-03-18 00:01:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision: str = "202603180001_reminders_activity_fields"
down_revision: Union[str, Sequence[str], None] = "202608110004_services_cost_basis"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    conn = op.get_bind()
    dialect = conn.dialect.name
    if dialect == "sqlite":
        rows = conn.exec_driver_sql(f"PRAGMA table_info({table});").fetchall()
        return any(row[1] == column for row in rows)
    row = conn.execute(
        text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = :t
              AND column_name = :c
            """
        ),
        {"t": table, "c": column},
    ).fetchone()
    return bool(row)


def upgrade() -> None:
    with op.batch_alter_table("reminders", recreate="auto") as batch:
        if not _has_column("reminders", "duration_minutes"):
            batch.add_column(sa.Column("duration_minutes", sa.Integer(), nullable=True))
        if not _has_column("reminders", "source"):
            batch.add_column(sa.Column("source", sa.String(length=32), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("reminders", recreate="auto") as batch:
        if _has_column("reminders", "source"):
            batch.drop_column("source")
        if _has_column("reminders", "duration_minutes"):
            batch.drop_column("duration_minutes")

