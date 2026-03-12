"""Remove Citronex from company names

Rename companies with CITRONEX/Citronex in name to generic 'Client Company'.

Revision ID: 202608090001
Revises: 202608080003
Create Date: 2026-02-04

"""
from typing import Sequence, Union

from alembic import op


revision: str = "202608090001"
down_revision: Union[str, None] = "202608080003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        UPDATE companies
        SET name = 'Client Company'
        WHERE LOWER(TRIM(name)) IN ('citronex', 'citronex trans logistic')
    """)


def downgrade() -> None:
    pass  # Cannot restore original names
