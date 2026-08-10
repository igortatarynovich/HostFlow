"""Merge ADR-036 remap heads (integration + ADR-035 bridge).

Revision ID: 202608101500_merge_adr036_remap_heads
Revises: 202608100001_adr036_remap_legacy_trust_roles, 202608110001_adr036_remap_legacy_trust_roles
Create Date: 2026-08-10 14:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

RevisionType = Union[str, Sequence[str], None]

revision: str = "202608101500_merge_adr036_remap_heads"
down_revision: RevisionType = (
    "202608100001_adr036_remap_legacy_trust_roles",
    "202608110001_adr036_remap_legacy_trust_roles",
)
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
