"""Entity Profile P9 — intake source mapping_rules.

Revision ID: 202608220004_entity_profile_p9
Revises: 202608220003_entity_profile_p8
Create Date: 2026-06-22 18:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


RevisionType = Union[str, Sequence[str], None]

revision: str = "202608220004_entity_profile_p9"
down_revision: RevisionType = "202608220003_entity_profile_p8"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    op.add_column(
        "intake_source_profiles",
        sa.Column(
            "mapping_rules",
            JSONB().with_variant(sa.JSON(), "sqlite"),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("intake_source_profiles", "mapping_rules")
