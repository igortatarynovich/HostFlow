"""ADR-024 Stage 3D PR-1 — Result attribution table.

Revision ID: 202607180004_acq_3d
Revises: 202607180003_acq_3b_fix
Create Date: 2026-07-18

NOTE: revision id kept ≤32 chars for alembic_version.version_num VARCHAR(32).
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


RevisionType = Union[str, Sequence[str], None]

revision: str = "202607180004_acq_3d"
down_revision: RevisionType = "202607180003_acq_3b_fix"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    op.create_table(
        "acq_result_attributions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("campaign_id", sa.String(length=36), nullable=False),
        sa.Column("campaign_run_id", sa.String(length=36), nullable=False),
        sa.Column("result_type", sa.String(length=64), nullable=False),
        sa.Column("result_id", sa.String(length=64), nullable=False),
        sa.Column("submission_id", sa.String(length=36), nullable=False),
        sa.Column("lead_id", sa.String(length=36), nullable=False),
        sa.Column("route_intent", sa.String(length=64), nullable=True),
        sa.Column("endpoint_form_id", sa.String(length=36), nullable=True),
        sa.Column("endpoint_intake_source_profile_id", sa.String(length=36), nullable=True),
        sa.Column("routing_source", sa.String(length=64), nullable=True),
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
        sa.UniqueConstraint(
            "tenant_id",
            "result_type",
            "result_id",
            name="uq_acq_result_attributions_tenant_result",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "submission_id",
            name="uq_acq_result_attributions_tenant_submission",
        ),
    )
    op.create_index(
        "ix_acq_result_attributions_tenant_id",
        "acq_result_attributions",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_acq_result_attributions_campaign_id",
        "acq_result_attributions",
        ["campaign_id"],
        unique=False,
    )
    op.create_index(
        "ix_acq_result_attributions_campaign_run_id",
        "acq_result_attributions",
        ["campaign_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_acq_result_attributions_tenant_campaign",
        "acq_result_attributions",
        ["tenant_id", "campaign_id"],
        unique=False,
    )
    op.create_index(
        "ix_acq_result_attributions_tenant_flight",
        "acq_result_attributions",
        ["tenant_id", "campaign_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_acq_result_attributions_tenant_lead",
        "acq_result_attributions",
        ["tenant_id", "lead_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_acq_result_attributions_tenant_lead", table_name="acq_result_attributions")
    op.drop_index("ix_acq_result_attributions_tenant_flight", table_name="acq_result_attributions")
    op.drop_index("ix_acq_result_attributions_tenant_campaign", table_name="acq_result_attributions")
    op.drop_index("ix_acq_result_attributions_campaign_run_id", table_name="acq_result_attributions")
    op.drop_index("ix_acq_result_attributions_campaign_id", table_name="acq_result_attributions")
    op.drop_index("ix_acq_result_attributions_tenant_id", table_name="acq_result_attributions")
    op.drop_table("acq_result_attributions")
