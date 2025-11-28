"""Merge document/candidate/vacancy heads

Revision ID: 20251021_merge_heads
Revises: 202409150001, c7c0b1f0d9a1, e88ddd40f226_fix_counters_docs_progress_vacancies_
Create Date: 2025-10-21 09:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20251021_merge_heads"
down_revision: Union[str, Sequence[str], None] = (
    "202409150001",
    "c7c0b1f0d9a1",
    "e88ddd40f226",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Pure merge revision – nothing to apply.
    pass


def downgrade() -> None:
    raise RuntimeError("Merge revision 20251021_merge_heads cannot be downgraded")
