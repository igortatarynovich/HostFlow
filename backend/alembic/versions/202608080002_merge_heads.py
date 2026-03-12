"""Merge heads: password_reset_tokens + candidates_rls_handoff_client

Revision ID: 202608080002
Revises: 202608070001, 202608080001
Create Date: 2026-02-04

"""
from typing import Sequence, Union

from alembic import op


revision: str = "202608080002"
down_revision: Union[str, Sequence[str], None] = ("202608070001", "202608080001")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
