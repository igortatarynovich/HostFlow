"""Merge heads after document reference M2.

Revision ID: 202608130003_merge_document_reference_m2_head
Revises: 202605210001, 202608130002_document_reference_seed_sync
Create Date: 2026-08-13 11:20:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

RevisionType = Union[str, Sequence[str], None]

revision: str = "202608130003_merge_document_reference_m2_head"
down_revision: RevisionType = (
    "202605210001",
    "202608130002_document_reference_seed_sync",
)
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
