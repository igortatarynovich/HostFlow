"""merge communications heads

Revision ID: 202608100002
Revises: 202602261300, 202608100001
Create Date: 2026-02-27

"""
from typing import Sequence, Union


revision: str = "202608100002"
down_revision: Union[str, Sequence[str], None] = ("202602261300", "202608100001")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
