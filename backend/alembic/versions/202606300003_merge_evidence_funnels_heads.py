"""Merge parallel heads: candidate_evidence (Phase 2) + funnels default uniqueness.

Revision ID: 202606300003_merge_evidence_funnels_heads
Revises: 202606300002_candidate_evidence_p2, 202606300002_funnels_default_uniqueness_p0
Create Date: 2026-06-30
"""

from __future__ import annotations

from typing import Sequence, Union

revision: str = "202606300003_merge_evidence_funnels_heads"
down_revision: Union[str, Sequence[str], None] = (
    "202606300002_candidate_evidence_p2",
    "202606300002_funnels_default_uniqueness_p0",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
