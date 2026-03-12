"""Create candidate_profile_history table for tracking profile changes

Revision ID: 202607010002_create_candidate_profile_history
Revises: 202607010001_create_candidate_stage_dict
Create Date: 2026-07-01 00:02:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "202607010002_create_candidate_profile_history"
down_revision: Union[str, None] = "202607010001_create_candidate_stage_dict"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create candidate_profile_history table."""
    op.create_table(
        "candidate_profile_history",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False, comment="Действие: 'created', 'updated', 'deleted', 'activated', 'deactivated'"),
        sa.Column("old_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="Данные профиля до изменения"),
        sa.Column("new_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="Данные профиля после изменения"),
        sa.Column("changes", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="Детали изменений (diff)"),
        sa.Column("comment", sa.Text(), nullable=True, comment="Комментарий к изменению"),
        sa.Column("actor_id", sa.String(length=36), nullable=True, comment="ID пользователя, который внес изменение"),
        sa.Column("actor_name", sa.String(length=255), nullable=True, comment="Имя пользователя (для отображения)"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["candidate_profiles.id"],
            ondelete="CASCADE",
            name="fk_profile_history_profile",
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            ondelete="SET NULL",
            name="fk_profile_history_actor",
        ),
    )
    # Create indexes
    op.create_index("ix_candidate_profile_history_tenant_id", "candidate_profile_history", ["tenant_id"])
    op.create_index("ix_candidate_profile_history_profile_id", "candidate_profile_history", ["profile_id"])
    op.create_index("ix_candidate_profile_history_actor_id", "candidate_profile_history", ["actor_id"])
    op.create_index("ix_candidate_profile_history_created_at", "candidate_profile_history", ["created_at"])
    op.create_index("ix_cph_tenant_profile", "candidate_profile_history", ["tenant_id", "profile_id"])


def downgrade() -> None:
    """Drop candidate_profile_history table."""
    op.drop_index("ix_cph_tenant_profile", table_name="candidate_profile_history")
    op.drop_index("ix_candidate_profile_history_created_at", table_name="candidate_profile_history")
    op.drop_index("ix_candidate_profile_history_actor_id", table_name="candidate_profile_history")
    op.drop_index("ix_candidate_profile_history_profile_id", table_name="candidate_profile_history")
    op.drop_index("ix_candidate_profile_history_tenant_id", table_name="candidate_profile_history")
    op.drop_table("candidate_profile_history")
