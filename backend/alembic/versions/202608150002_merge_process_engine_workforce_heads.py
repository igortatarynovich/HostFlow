"""Merge workforce lifecycle and Process Engine / meta form routes heads.

Revision ID: 202608150002_merge_process_engine_workforce_heads
Revises: 202605250003_workforce_contract_lifecycle_fields, 202608150001_meta_form_routes
Create Date: 2026-08-15 12:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

RevisionType = Union[str, Sequence[str], None]

revision: str = "202608150002_merge_process_engine_workforce_heads"
down_revision: RevisionType = (
    "202605250003_workforce_contract_lifecycle_fields",
    "202608150001_meta_form_routes",
)
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    return None


def downgrade() -> None:
    return None
