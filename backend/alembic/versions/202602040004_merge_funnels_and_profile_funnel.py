"""Merge heads: funnels_universal_model + profile_funnel_id

Revision ID: 202602040004
Revises: 202602040002_funnels_universal_model, 202602040003_profile_funnel_id
Create Date: 2026-02-04

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

RevisionType = Union[str, Sequence[str], None]

revision: str = "202602040004_merge_funnels_and_profile_funnel"
down_revision: RevisionType = (
    "202602040002_funnels_universal_model",
    "202602040003_profile_funnel_id",
)
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
