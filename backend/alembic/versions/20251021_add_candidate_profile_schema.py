"""Add personal_data, contacts, status columns to candidates

Revision ID: 20251021_add_candidate_profile_schema
Revises: 20251021_merge_heads
Create Date: 2025-10-21 10:15:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20251021_add_candidate_profile_schema"
down_revision: Union[str, Sequence[str], None] = "20251021_merge_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("candidates") as batch:
        batch.add_column(sa.Column("personal_data", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("contacts", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("status", sa.String(length=64), nullable=True))
        batch.create_index("ix_candidates_status", ["status"])

    conn = op.get_bind()
    conn.execute(sa.text("UPDATE candidates SET status = stage WHERE status IS NULL"))


def downgrade() -> None:
    with op.batch_alter_table("candidates") as batch:
        batch.drop_index("ix_candidates_status")
        batch.drop_column("status")
        batch.drop_column("contacts")
        batch.drop_column("personal_data")
