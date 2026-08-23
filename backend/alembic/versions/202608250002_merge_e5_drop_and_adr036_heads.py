"""Merge E5 candidate_id drop with leftover ADR-036 head.

Revision ID: 202608250002_merge_e5_drop_and_adr036_heads
Revises: 202608250001_drop_documents_candidate_id, 202608100001_adr036_remap_legacy_trust_roles
Create Date: 2026-08-23 10:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

RevisionType = Union[str, Sequence[str], None]

revision: str = "202608250002_merge_e5_drop_and_adr036_heads"
down_revision: RevisionType = (
    "202608250001_drop_documents_candidate_id",
    "202608100001_adr036_remap_legacy_trust_roles",
)
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    return None


def downgrade() -> None:
    return None
