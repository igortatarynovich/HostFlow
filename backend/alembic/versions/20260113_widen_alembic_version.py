"""Widen alembic_version.version_num for long revision labels.

PostgreSQL default Alembic table uses VARCHAR(32); some revision IDs exceed
that (e.g. 20251021_add_candidate_profile_schema), breaking fresh installs.

Revision ID: 20260113_widen_alembic_ver
Revises: 20251021_merge_heads
Create Date: 2026-01-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260113_widen_alembic_ver"
down_revision: Union[str, Sequence[str], None] = "20251021_merge_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(
        sa.text("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(255)"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(
        sa.text("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(32)"),
    )
