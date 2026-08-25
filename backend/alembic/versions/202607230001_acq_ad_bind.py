"""Stage Acquisition — FlightAdBinding (Meta Ad ID → Flight).

Revision ID: 202607230001_acq_ad_bind
Revises: 202607220002_acq_3e_imm
Create Date: 2026-07-23

NOTE: revision id kept ≤32 chars for alembic_version.version_num VARCHAR(32).
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


RevisionType = Union[str, Sequence[str], None]

revision: str = "202607230001_acq_ad_bind"
down_revision: RevisionType = "202607220002_acq_3e_imm"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    op.create_table(
        "acq_flight_ad_bindings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False, server_default="meta"),
        sa.Column("provider_ad_id", sa.String(length=64), nullable=False),
        sa.Column("campaign_id", sa.String(length=36), nullable=False),
        sa.Column("campaign_run_id", sa.String(length=36), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
    )
    op.create_index(
        "ix_acq_flight_ad_bindings_tenant_id",
        "acq_flight_ad_bindings",
        ["tenant_id"],
    )
    op.create_index(
        "ix_acq_flight_ad_bindings_tenant_flight",
        "acq_flight_ad_bindings",
        ["tenant_id", "campaign_run_id"],
    )
    op.create_index(
        "ix_acq_flight_ad_bindings_tenant_campaign",
        "acq_flight_ad_bindings",
        ["tenant_id", "campaign_id"],
    )
    op.create_index(
        "ix_acq_flight_ad_bindings_lookup",
        "acq_flight_ad_bindings",
        ["tenant_id", "provider", "provider_ad_id"],
    )
    # At most one active Ad → Flight route per tenant/provider/ad.
    op.execute(
        """
        CREATE UNIQUE INDEX uq_acq_flight_ad_bindings_active_ad
        ON acq_flight_ad_bindings (tenant_id, provider, provider_ad_id)
        WHERE is_active IS TRUE
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_acq_flight_ad_bindings_active_ad")
    op.drop_index("ix_acq_flight_ad_bindings_lookup", table_name="acq_flight_ad_bindings")
    op.drop_index("ix_acq_flight_ad_bindings_tenant_campaign", table_name="acq_flight_ad_bindings")
    op.drop_index("ix_acq_flight_ad_bindings_tenant_flight", table_name="acq_flight_ad_bindings")
    op.drop_index("ix_acq_flight_ad_bindings_tenant_id", table_name="acq_flight_ad_bindings")
    op.drop_table("acq_flight_ad_bindings")
