"""Expand reminders.entity_id to 120 chars

Revision ID: 202512010300_expand_reminder_entity_id
Revises: 202512010200_admin_v2
Create Date: 2025-10-28 12:10:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202512010300_expand_reminder_entity_id"
down_revision = "202512010200_admin_v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "reminders",
        "entity_id",
        existing_type=sa.String(length=36),
        type_=sa.String(length=120),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "reminders",
        "entity_id",
        existing_type=sa.String(length=120),
        type_=sa.String(length=36),
        existing_nullable=False,
    )
