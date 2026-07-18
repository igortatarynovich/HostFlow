"""Campaign foundation (ADR-024 Stage 3A).

Revision ID: 202607180001_campaign_foundation_3a
Revises: 202607160002_comm_message_context
Create Date: 2026-07-18
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


RevisionType = Union[str, Sequence[str], None]

revision: str = "202607180001_campaign_foundation_3a"
down_revision: RevisionType = "202607160002_comm_message_context"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    op.create_table(
        "acq_campaigns",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("own_company_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'draft'")),
        sa.Column("goal_type", sa.String(length=64), nullable=False),
        sa.Column("primary_kpi", sa.String(length=64), nullable=False),
        sa.Column("current_flight_id", sa.String(length=36), nullable=True),
        sa.Column("created_by_user_id", sa.String(length=36), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_acq_campaigns_tenant_id", "acq_campaigns", ["tenant_id"], unique=False)
    op.create_index("ix_acq_campaigns_own_company_id", "acq_campaigns", ["own_company_id"], unique=False)
    op.create_index(
        "ix_acq_campaigns_tenant_company",
        "acq_campaigns",
        ["tenant_id", "own_company_id"],
        unique=False,
    )
    op.create_index(
        "ix_acq_campaigns_tenant_status",
        "acq_campaigns",
        ["tenant_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_acq_campaigns_current_flight_id",
        "acq_campaigns",
        ["current_flight_id"],
        unique=False,
    )

    op.create_table(
        "acq_campaign_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("campaign_id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False, server_default=sa.text("'flight_1'")),
        sa.Column("name", sa.String(length=255), nullable=False, server_default=sa.text("'Flight 1'")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'planned'")),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campaign_id", "code", name="uq_acq_campaign_runs_campaign_code"),
    )
    op.create_index("ix_acq_campaign_runs_tenant_id", "acq_campaign_runs", ["tenant_id"], unique=False)
    op.create_index("ix_acq_campaign_runs_campaign_id", "acq_campaign_runs", ["campaign_id"], unique=False)
    op.create_index(
        "ix_acq_campaign_runs_tenant_campaign",
        "acq_campaign_runs",
        ["tenant_id", "campaign_id"],
        unique=False,
    )

    op.create_table(
        "acq_campaign_targets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("campaign_id", sa.String(length=36), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=False),
        sa.Column("target_module", sa.String(length=32), nullable=False),
        sa.Column("route_intent", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False, server_default=sa.text("'primary'")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "campaign_id",
            "target_type",
            "target_id",
            "role",
            name="uq_acq_campaign_targets_campaign_type_id_role",
        ),
    )
    op.create_index("ix_acq_campaign_targets_tenant_id", "acq_campaign_targets", ["tenant_id"], unique=False)
    op.create_index(
        "ix_acq_campaign_targets_campaign_id",
        "acq_campaign_targets",
        ["campaign_id"],
        unique=False,
    )
    op.create_index(
        "ix_acq_campaign_targets_tenant_campaign",
        "acq_campaign_targets",
        ["tenant_id", "campaign_id"],
        unique=False,
    )
    op.create_index(
        "ix_acq_campaign_targets_type_id",
        "acq_campaign_targets",
        ["target_type", "target_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("acq_campaign_targets")
    op.drop_table("acq_campaign_runs")
    op.drop_table("acq_campaigns")
