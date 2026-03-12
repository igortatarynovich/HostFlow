"""Merge heads: legal_documents_rodo + add_candidate_is_favorite

Revision ID: 202608020002
Revises: 202608020001_legal_documents_rodo, 202607010004_add_candidate_is_favorite
Create Date: 2026-08-02 12:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

RevisionType = Union[str, Sequence[str], None]

revision: str = "202608020002_merge_heads"
down_revision: RevisionType = (
    "202608020001_legal_documents_rodo",
    "202607010004_add_candidate_is_favorite",
)
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
