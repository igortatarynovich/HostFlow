"""Vacancy headcount_target (planned positions to fill).

Revision ID: 202603241200_vacancy_headcount
Revises: 202603221400_risk_intel_hourly_shadow
Create Date: 2026-03-24
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "202603241200_vacancy_headcount"
down_revision: Union[str, None] = "202603221400_risk_intel_hourly_shadow"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    try:
        columns = [c["name"] for c in insp.get_columns(table)]
    except Exception:
        return False
    return column in columns


def upgrade() -> None:
    if _has_column("vacancies", "headcount_target"):
        return
    op.add_column(
        "vacancies",
        sa.Column("headcount_target", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    if not _has_column("vacancies", "headcount_target"):
        return
    op.drop_column("vacancies", "headcount_target")
