"""Merge heads: party/lead/order pipeline + candidate pipeline overrides branch.

Revision ID: 202603221201_merge_party_pipeline_and_stages_head
Revises: 202603201001, 202603221200_party_lead_order_pipeline
Create Date: 2026-03-22

Resolves multiple Alembic heads after 202603221200_party_lead_order_pipeline was
chained from 202608120003 while 202603181200 → 202603201001 already extended
that same parent.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "202603221201_merge_party_pipeline_and_stages_head"
down_revision: Union[str, Sequence[str], None] = (
    "202603201001",
    "202603221200_party_lead_order_pipeline",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
