"""ADR-024 Stage 3D PR-3 — Flight spend source + qualification contract.

Revision ID: 202607180006_acq_3d_k
Revises: 202607180005_acq_3d_o
Create Date: 2026-07-18

NOTE: revision id kept ≤32 chars for alembic_version.version_num VARCHAR(32).
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


RevisionType = Union[str, Sequence[str], None]

revision: str = "202607180006_acq_3d_k"
down_revision: RevisionType = "202607180005_acq_3d_o"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    op.create_table(
        "acq_flight_spend_entries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("campaign_id", sa.String(length=36), nullable=False),
        sa.Column("campaign_run_id", sa.String(length=36), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
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
    op.create_index(
        "ix_acq_flight_spend_entries_tenant_id", "acq_flight_spend_entries", ["tenant_id"]
    )
    op.create_index(
        "ix_acq_flight_spend_entries_campaign_id", "acq_flight_spend_entries", ["campaign_id"]
    )
    op.create_index(
        "ix_acq_flight_spend_entries_campaign_run_id",
        "acq_flight_spend_entries",
        ["campaign_run_id"],
    )
    op.create_index(
        "ix_acq_flight_spend_entries_tenant_flight",
        "acq_flight_spend_entries",
        ["tenant_id", "campaign_run_id"],
    )
    op.create_index(
        "ix_acq_flight_spend_entries_tenant_campaign",
        "acq_flight_spend_entries",
        ["tenant_id", "campaign_id"],
    )

    op.create_table(
        "acq_result_qualifications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("attribution_id", sa.String(length=36), nullable=False),
        sa.Column("qualified_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["attribution_id"], ["acq_result_attributions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "attribution_id",
            name="uq_acq_result_qualifications_attribution",
        ),
    )
    op.create_index(
        "ix_acq_result_qualifications_tenant_id", "acq_result_qualifications", ["tenant_id"]
    )
    op.create_index(
        "ix_acq_result_qualifications_attribution_id",
        "acq_result_qualifications",
        ["attribution_id"],
    )
    op.create_index(
        "ix_acq_result_qualifications_tenant_attr",
        "acq_result_qualifications",
        ["tenant_id", "attribution_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_acq_result_qualifications_tenant_attr", table_name="acq_result_qualifications"
    )
    op.drop_index(
        "ix_acq_result_qualifications_attribution_id", table_name="acq_result_qualifications"
    )
    op.drop_index("ix_acq_result_qualifications_tenant_id", table_name="acq_result_qualifications")
    op.drop_table("acq_result_qualifications")

    op.drop_index(
        "ix_acq_flight_spend_entries_tenant_campaign", table_name="acq_flight_spend_entries"
    )
    op.drop_index(
        "ix_acq_flight_spend_entries_tenant_flight", table_name="acq_flight_spend_entries"
    )
    op.drop_index(
        "ix_acq_flight_spend_entries_campaign_run_id", table_name="acq_flight_spend_entries"
    )
    op.drop_index(
        "ix_acq_flight_spend_entries_campaign_id", table_name="acq_flight_spend_entries"
    )
    op.drop_index("ix_acq_flight_spend_entries_tenant_id", table_name="acq_flight_spend_entries")
    op.drop_table("acq_flight_spend_entries")
