"""Add tags field to candidates table

Revision ID: 202607010003_add_candidate_tags
Revises: 202607010002_create_candidate_profile_history
Create Date: 2026-07-01 00:03:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "202607010003_add_candidate_tags"
down_revision: Union[str, None] = "202607010002_create_candidate_profile_history"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _json_list_type(dialect_name: str) -> any:
    """Returns JSON list type for the given dialect."""
    if dialect_name == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def _json_list_default(dialect_name: str) -> sa.sql.elements.TextClause:
    """Returns default value for JSON list."""
    if dialect_name == "postgresql":
        return sa.text("'[]'::jsonb")
    return sa.text("'[]'")


def upgrade() -> None:
    """Add tags column to candidates table."""
    conn = op.get_bind()
    dialect_name = conn.dialect.name
    
    op.add_column(
        "candidates",
        sa.Column(
            "tags",
            _json_list_type(dialect_name),
            nullable=True,
            server_default=_json_list_default(dialect_name),
            comment="Теги/метки для организации и фильтрации кандидатов",
        ),
    )
    
    # Создаем GIN индекс для быстрого поиска по тегам в PostgreSQL
    if dialect_name == "postgresql":
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_candidates_tags_gin ON candidates USING GIN (tags)"
        )


def downgrade() -> None:
    """Remove tags column from candidates table."""
    conn = op.get_bind()
    dialect_name = conn.dialect.name
    
    # Удаляем индекс перед удалением колонки
    if dialect_name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_candidates_tags_gin")
    
    op.drop_column("candidates", "tags")
