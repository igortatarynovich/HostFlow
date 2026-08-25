"""Merge alembic heads before Stage 1A client_accounts.

Revision ID: 202607131399_stage_1a_merge_heads
Revises: 202607020001_ra_ext, 202608240001_document_expiry_notification_events_p2
Create Date: 2026-07-13
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "202607131399_stage_1a_merge_heads"
down_revision: Union[str, Sequence[str], None] = (
    "202607020001_ra_ext",
    "202608240001_document_expiry_notification_events_p2",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
