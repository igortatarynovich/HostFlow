"""
create candidate_stage_history table (PostgreSQL-safe, conditional FK)

Revision ID: c7c0b1f0d9a1
Revises: a1b2c3d4e5f6
Create Date: 2025-10-20 12:40:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7c0b1f0d9a1"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _stages_exists(conn) -> bool:
    # PostgreSQL: returns table name if exists, else None
    row = conn.exec_driver_sql("SELECT to_regclass('public.stages')").fetchone()
    return bool(row and row[0])


def upgrade() -> None:
    conn = op.get_bind()

    # base columns
    cols = [
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=36), nullable=False),
        sa.Column("from_code", sa.String(length=64), nullable=True),
        sa.Column("to_code", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("actor", sa.String(length=255), nullable=True),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
    ]

    fks = []
    if _stages_exists(conn):
        fks.append(
            sa.ForeignKeyConstraint(["to_code"], ["stages.code"], name="fk_stage_history_stage")
        )

    op.create_table("candidate_stage_history", *cols, *fks)

    # indexes
    op.create_index(
        "ix_candidate_stage_history_tenant_candidate",
        "candidate_stage_history",
        ["tenant_id", "candidate_id"],
    )
    op.create_index("ix_csh_tenant", "candidate_stage_history", ["tenant_id"])  # optional
    op.create_index("ix_csh_candidate", "candidate_stage_history", ["candidate_id"])  # optional
    op.create_index("ix_csh_at", "candidate_stage_history", ["at"])  # optional


def downgrade() -> None:
    op.drop_index("ix_csh_at", table_name="candidate_stage_history")
    op.drop_index("ix_csh_candidate", table_name="candidate_stage_history")
    op.drop_index("ix_csh_tenant", table_name="candidate_stage_history")
    op.drop_index("ix_candidate_stage_history_tenant_candidate", table_name="candidate_stage_history")
    op.drop_table("candidate_stage_history")
