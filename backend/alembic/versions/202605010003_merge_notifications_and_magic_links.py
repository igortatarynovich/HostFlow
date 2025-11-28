"""merge branches after notifications and magic links

Revision ID: 202605010003_merge_notifications_and_magic_links
Revises: 202502171200, 202605010002
Create Date: 2025-05-01 15:00:00
"""

from __future__ import annotations

from alembic import op  # noqa: F401


revision = "202605010003_merge_notifications_and_magic_links"
down_revision = ("202502171200", "202605010002")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

