"""users: add short_id, full_name

Revision ID: 5dad3d78dd72
Revises: 20250902_pipeline_scale
Create Date: 2025-09-06 11:32:27.116774+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5dad3d78dd72"
down_revision: Union[str, Sequence[str], None] = "20250902_pipeline_scale"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns(table)}
    return column in cols


def upgrade() -> None:
    """Upgrade schema (idempotent)."""

    # short_id
    if not _has_column("users", "short_id"):
        op.add_column(
            "users",
            sa.Column("short_id", sa.String(length=64), nullable=True),
        )

    # full_name
    if not _has_column("users", "full_name"):
        op.add_column(
            "users",
            sa.Column("full_name", sa.String(length=255), nullable=True),
        )


def downgrade() -> None:
    """Downgrade schema (idempotent)."""

    if _has_column("users", "full_name"):
        op.drop_column("users", "full_name")

    if _has_column("users", "short_id"):
        op.drop_column("users", "short_id")
