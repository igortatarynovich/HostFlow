"""ADR-024 Stage 3D PR-2 — Outcome + Result ledger tables.

Revision ID: 202607180005_acq_3d_o
Revises: 202607180004_acq_3d
Create Date: 2026-07-18

NOTE: revision id kept ≤32 chars for alembic_version.version_num VARCHAR(32).
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


RevisionType = Union[str, Sequence[str], None]

revision: str = "202607180005_acq_3d_o"
down_revision: RevisionType = "202607180004_acq_3d"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    op.create_table(
        "acq_outcomes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("campaign_id", sa.String(length=36), nullable=False),
        sa.Column("campaign_run_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'created'")),
        sa.Column("progress_current", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("progress_target", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["campaign_id"], ["acq_campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["campaign_run_id"], ["acq_campaign_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_acq_outcomes_tenant_id", "acq_outcomes", ["tenant_id"], unique=False)
    op.create_index("ix_acq_outcomes_campaign_id", "acq_outcomes", ["campaign_id"], unique=False)
    op.create_index(
        "ix_acq_outcomes_campaign_run_id", "acq_outcomes", ["campaign_run_id"], unique=False
    )
    op.create_index(
        "ix_acq_outcomes_tenant_campaign", "acq_outcomes", ["tenant_id", "campaign_id"], unique=False
    )
    op.create_index(
        "ix_acq_outcomes_tenant_flight",
        "acq_outcomes",
        ["tenant_id", "campaign_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_acq_outcomes_tenant_status", "acq_outcomes", ["tenant_id", "status"], unique=False
    )

    op.create_table(
        "acq_outcome_result_links",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("outcome_id", sa.String(length=36), nullable=False),
        sa.Column("attribution_id", sa.String(length=36), nullable=False),
        sa.Column("result_type", sa.String(length=64), nullable=False),
        sa.Column("result_id", sa.String(length=64), nullable=False),
        sa.Column("counted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoke_reason", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["outcome_id"], ["acq_outcomes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["attribution_id"], ["acq_result_attributions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "outcome_id",
            "result_type",
            "result_id",
            name="uq_acq_outcome_result_links_outcome_result",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "attribution_id",
            name="uq_acq_outcome_result_links_attribution",
        ),
    )
    op.create_index(
        "ix_acq_outcome_result_links_tenant_id",
        "acq_outcome_result_links",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_acq_outcome_result_links_outcome_id",
        "acq_outcome_result_links",
        ["outcome_id"],
        unique=False,
    )
    op.create_index(
        "ix_acq_outcome_result_links_attribution_id",
        "acq_outcome_result_links",
        ["attribution_id"],
        unique=False,
    )
    op.create_index(
        "ix_acq_outcome_result_links_tenant_outcome",
        "acq_outcome_result_links",
        ["tenant_id", "outcome_id"],
        unique=False,
    )
    op.create_index(
        "ix_acq_outcome_result_links_tenant_result",
        "acq_outcome_result_links",
        ["tenant_id", "result_type", "result_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_acq_outcome_result_links_tenant_result", table_name="acq_outcome_result_links"
    )
    op.drop_index(
        "ix_acq_outcome_result_links_tenant_outcome", table_name="acq_outcome_result_links"
    )
    op.drop_index(
        "ix_acq_outcome_result_links_attribution_id", table_name="acq_outcome_result_links"
    )
    op.drop_index("ix_acq_outcome_result_links_outcome_id", table_name="acq_outcome_result_links")
    op.drop_index("ix_acq_outcome_result_links_tenant_id", table_name="acq_outcome_result_links")
    op.drop_table("acq_outcome_result_links")

    op.drop_index("ix_acq_outcomes_tenant_status", table_name="acq_outcomes")
    op.drop_index("ix_acq_outcomes_tenant_flight", table_name="acq_outcomes")
    op.drop_index("ix_acq_outcomes_tenant_campaign", table_name="acq_outcomes")
    op.drop_index("ix_acq_outcomes_campaign_run_id", table_name="acq_outcomes")
    op.drop_index("ix_acq_outcomes_campaign_id", table_name="acq_outcomes")
    op.drop_index("ix_acq_outcomes_tenant_id", table_name="acq_outcomes")
    op.drop_table("acq_outcomes")
