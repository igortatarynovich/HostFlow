"""Entity Profile P8 — intake source presentation_code binding.

Revision ID: 202608220003_entity_profile_p8
Revises: 202608220002_entity_profile_p2
Create Date: 2026-06-22 16:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


RevisionType = Union[str, Sequence[str], None]

revision: str = "202608220003_entity_profile_p8"
down_revision: RevisionType = "202608220002_entity_profile_p2"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    op.add_column(
        "intake_source_profiles",
        sa.Column("presentation_code", sa.String(length=128), nullable=True),
    )
    op.create_index(
        "ix_intake_source_profiles_presentation_code",
        "intake_source_profiles",
        ["presentation_code"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_intake_source_profiles_presentation_code", table_name="intake_source_profiles")
    op.drop_column("intake_source_profiles", "presentation_code")
