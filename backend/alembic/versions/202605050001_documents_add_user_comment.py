"""Add user_comment column to documents

Revision ID: 202605050001
Revises: 202605010003_merge_notifications_and_magic_links
Create Date: 2025-11-09 22:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202605050001"
down_revision = "202605010003_merge_notifications_and_magic_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("user_comment", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "user_comment")

