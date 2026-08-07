"""ADR-035: funnel_transition_edges + candidate lifecycle / pipeline_stage_id.

Revision ID: 202608070001_adr035_pipe
Revises: 202608030002_comm_c2_3
Create Date: 2026-08-07
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

RevisionType = Union[str, Sequence[str], None]

revision: str = "202608070001_adr035_pipe"
down_revision: RevisionType = "202608030002_comm_c2_3"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")

    op.add_column(
        "funnels",
        sa.Column("template_key", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_funnels_template_key", "funnels", ["template_key"])

    op.create_table(
        "funnel_transition_edges",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("funnel_id", sa.String(length=36), nullable=False),
        sa.Column("catalog_key", sa.String(length=64), nullable=False),
        sa.Column("from_stage_id", sa.String(length=36), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("config_json", json_type, nullable=True),
        sa.ForeignKeyConstraint(["funnel_id"], ["funnels.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["from_stage_id"], ["funnel_stages.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "funnel_id",
            "catalog_key",
            "from_stage_id",
            name="uq_funnel_transition_edge",
        ),
    )
    op.create_index(
        "ix_funnel_transition_edges_funnel_id",
        "funnel_transition_edges",
        ["funnel_id"],
    )
    op.create_index(
        "ix_funnel_transition_edges_from_stage_id",
        "funnel_transition_edges",
        ["from_stage_id"],
    )

    op.add_column(
        "candidates",
        sa.Column(
            "lifecycle_status",
            sa.String(length=32),
            nullable=True,
            server_default="active",
        ),
    )
    op.create_index("ix_candidates_lifecycle_status", "candidates", ["lifecycle_status"])
    op.add_column(
        "candidates",
        sa.Column("pipeline_stage_id", sa.String(length=36), nullable=True),
    )
    op.create_index("ix_candidates_pipeline_stage_id", "candidates", ["pipeline_stage_id"])
    op.create_foreign_key(
        "fk_candidates_pipeline_stage_id",
        "candidates",
        "funnel_stages",
        ["pipeline_stage_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Backfill pipeline_stage_id from funnel_id + stage code where possible
    op.execute(
        sa.text(
            """
            UPDATE candidates c
            SET pipeline_stage_id = fs.id
            FROM funnel_stages fs
            WHERE c.funnel_id IS NOT NULL
              AND c.stage IS NOT NULL
              AND fs.funnel_id = c.funnel_id
              AND fs.code = c.stage
              AND c.pipeline_stage_id IS NULL
            """
        )
    )
    # Closed-like legacy stages → lifecycle closed
    op.execute(
        sa.text(
            """
            UPDATE candidates
            SET lifecycle_status = 'closed'
            WHERE stage IN (
              'hired', 'employed', 'rejected', 'declined',
              'ready_for_hr', 'processing_by_hr', 'processing_by_client'
            )
            """
        )
    )


def downgrade() -> None:
    op.drop_constraint("fk_candidates_pipeline_stage_id", "candidates", type_="foreignkey")
    op.drop_index("ix_candidates_pipeline_stage_id", table_name="candidates")
    op.drop_column("candidates", "pipeline_stage_id")
    op.drop_index("ix_candidates_lifecycle_status", table_name="candidates")
    op.drop_column("candidates", "lifecycle_status")
    op.drop_index("ix_funnel_transition_edges_from_stage_id", table_name="funnel_transition_edges")
    op.drop_index("ix_funnel_transition_edges_funnel_id", table_name="funnel_transition_edges")
    op.drop_table("funnel_transition_edges")
    op.drop_index("ix_funnels_template_key", table_name="funnels")
    op.drop_column("funnels", "template_key")
