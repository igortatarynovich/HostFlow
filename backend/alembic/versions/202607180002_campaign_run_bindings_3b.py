"""CampaignRun Form + Intake Source bindings (ADR-024 Stage 3B).

Revision ID: 202607180002_campaign_run_bindings_3b
Revises: 202607180001_campaign_foundation_3a
Create Date: 2026-07-18
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


RevisionType = Union[str, Sequence[str], None]

revision: str = "202607180002_campaign_run_bindings_3b"
down_revision: RevisionType = "202607180001_campaign_foundation_3a"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

    op.create_table(
        "acq_campaign_run_forms",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("campaign_run_id", sa.String(length=36), nullable=False),
        sa.Column("form_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False, server_default=sa.text("'primary'")),
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
        sa.ForeignKeyConstraint(["campaign_run_id"], ["acq_campaign_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["form_id"], ["tenant_lead_forms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campaign_run_id", "form_id", name="uq_acq_campaign_run_forms_run_form"),
    )
    op.create_index("ix_acq_campaign_run_forms_tenant_id", "acq_campaign_run_forms", ["tenant_id"])
    op.create_index(
        "ix_acq_campaign_run_forms_campaign_run_id",
        "acq_campaign_run_forms",
        ["campaign_run_id"],
    )
    op.create_index("ix_acq_campaign_run_forms_form_id", "acq_campaign_run_forms", ["form_id"])
    op.create_index(
        "ix_acq_campaign_run_forms_tenant_run",
        "acq_campaign_run_forms",
        ["tenant_id", "campaign_run_id"],
    )

    op.create_table(
        "acq_campaign_run_intake_sources",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("campaign_run_id", sa.String(length=36), nullable=False),
        sa.Column("intake_source_profile_id", sa.String(length=36), nullable=False),
        sa.Column(
            "provider",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'unknown'"),
        ),
        sa.Column("external_ref", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("role", sa.String(length=32), nullable=False, server_default=sa.text("'primary'")),
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
        sa.ForeignKeyConstraint(["campaign_run_id"], ["acq_campaign_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["intake_source_profile_id"],
            ["intake_source_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "campaign_run_id",
            "intake_source_profile_id",
            name="uq_acq_campaign_run_intake_sources_run_profile",
        ),
    )
    op.create_index(
        "ix_acq_campaign_run_intake_sources_tenant_id",
        "acq_campaign_run_intake_sources",
        ["tenant_id"],
    )
    op.create_index(
        "ix_acq_campaign_run_intake_sources_campaign_run_id",
        "acq_campaign_run_intake_sources",
        ["campaign_run_id"],
    )
    op.create_index(
        "ix_acq_campaign_run_intake_sources_profile_id",
        "acq_campaign_run_intake_sources",
        ["intake_source_profile_id"],
    )
    op.create_index(
        "ix_acq_campaign_run_intake_sources_tenant_run",
        "acq_campaign_run_intake_sources",
        ["tenant_id", "campaign_run_id"],
    )


def downgrade() -> None:
    op.drop_table("acq_campaign_run_intake_sources")
    op.drop_table("acq_campaign_run_forms")
