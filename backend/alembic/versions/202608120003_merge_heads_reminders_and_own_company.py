"""Merge heads: reminders activity fields + own-company scoping

Revision ID: 202608120003_merge_heads_reminders_and_own_company
Revises: 202603180001_reminders_activity_fields, 202608120002
Create Date: 2026-08-12 00:03:00.000000+00:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "202608120003_merge_heads_reminders_and_own_company"
down_revision: Union[str, Sequence[str], None] = (
    "202603180001_reminders_activity_fields",
    "202608120002",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # This is a merge revision (no schema changes).
    pass


def downgrade() -> None:
    # Downgrade is not supported for merge-only revisions.
    pass

