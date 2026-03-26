"""user_notifications.priority (UOS bell tier source of truth).

Revision ID: 202603251200_notif_priority
Revises: 202603241200_vacancy_headcount
Create Date: 2026-03-25
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "202603251200_notif_priority"
down_revision: Union[str, None] = "202603241200_vacancy_headcount"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    try:
        columns = [c["name"] for c in insp.get_columns(table)]
    except Exception:
        return False
    return column in columns


def upgrade() -> None:
    if _has_column("user_notifications", "priority"):
        return
    op.add_column(
        "user_notifications",
        sa.Column("priority", sa.String(length=16), nullable=True),
    )


def downgrade() -> None:
    if not _has_column("user_notifications", "priority"):
        return
    op.drop_column("user_notifications", "priority")
