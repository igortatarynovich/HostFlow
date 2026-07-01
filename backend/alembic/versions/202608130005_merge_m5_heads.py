"""Merge heads after M5 eligibility runtime.

Revision ID: 202608130005_merge_m5_heads
Revises: 202605250002_workforce_lifecycle_ledger, 202608130004_applicability_packs_seed
Create Date: 2026-08-13 16:30:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

RevisionType = Union[str, Sequence[str], None]

revision: str = "202608130005_merge_m5_heads"
down_revision: RevisionType = (
    "202605250002_workforce_lifecycle_ledger",
    "202608130004_applicability_packs_seed",
)
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    return None


def downgrade() -> None:
    return None
