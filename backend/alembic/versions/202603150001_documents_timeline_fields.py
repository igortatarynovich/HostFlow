"""Add ordered_at and valid_from columns to documents."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202603150001"
down_revision = "202603010001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("documents") as batch:
        batch.add_column(sa.Column("ordered_at", sa.Date(), nullable=True))
        batch.add_column(sa.Column("valid_from", sa.Date(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("documents") as batch:
        batch.drop_column("valid_from")
        batch.drop_column("ordered_at")
