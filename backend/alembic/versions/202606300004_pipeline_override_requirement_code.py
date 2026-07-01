"""Add requirement_code to candidate_pipeline_overrides (Phase 3c waivers).

Revision ID: 202606300004
Revises: 202606300003_merge_evidence_funnels_heads
Create Date: 2026-06-30
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "202606300004"
down_revision: Union[str, Sequence[str], None] = "202606300003_merge_evidence_funnels_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(conn, table: str, column: str) -> bool:
    insp = sa.inspect(conn)
    if table not in insp.get_table_names():
        return False
    return column in {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    conn = op.get_bind()
    if not _has_column(conn, "candidate_pipeline_overrides", "requirement_code"):
        op.add_column(
            "candidate_pipeline_overrides",
            sa.Column("requirement_code", sa.String(length=128), nullable=True),
        )
        op.create_index(
            "ix_cp_overrides_requirement_code",
            "candidate_pipeline_overrides",
            ["requirement_code"],
        )
    # Requirement-centric waivers may omit doc_type_code.
    op.alter_column(
        "candidate_pipeline_overrides",
        "doc_type_code",
        existing_type=sa.String(length=128),
        nullable=True,
    )


def downgrade() -> None:
    conn = op.get_bind()
    if _has_column(conn, "candidate_pipeline_overrides", "requirement_code"):
        try:
            op.drop_index("ix_cp_overrides_requirement_code", table_name="candidate_pipeline_overrides")
        except Exception:
            pass
        op.drop_column("candidate_pipeline_overrides", "requirement_code")
