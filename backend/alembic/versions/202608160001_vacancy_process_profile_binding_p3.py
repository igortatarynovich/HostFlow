"""Vacancy process profile binding (Process Engine P3).

Revision ID: 202608160001_vacancy_process_profile_binding_p3
Revises: 202608150002_merge_process_engine_workforce_heads
Create Date: 2026-08-16 10:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

RevisionType = Union[str, Sequence[str], None]

revision: str = "202608160001_vacancy_process_profile_binding_p3"
down_revision: RevisionType = "202608150002_merge_process_engine_workforce_heads"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    op.add_column(
        "vacancies",
        sa.Column("pe_process_profile_id", sa.String(length=36), nullable=True),
    )
    op.create_foreign_key(
        "fk_vacancies_pe_process_profile_id",
        "vacancies",
        "pe_process_profiles",
        ["pe_process_profile_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_vacancies_pe_process_profile_id",
        "vacancies",
        ["pe_process_profile_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_vacancies_pe_process_profile_id", table_name="vacancies")
    op.drop_constraint("fk_vacancies_pe_process_profile_id", "vacancies", type_="foreignkey")
    op.drop_column("vacancies", "pe_process_profile_id")
