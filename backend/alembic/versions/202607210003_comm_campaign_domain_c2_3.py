"""C2.3 PR-1: Campaign Orchestrator domain tables.

Revision ID: 202607210003_comm_campaign_domain_c2_3
Revises: 202607210002_comm_automation_domain_c2_2
Create Date: 2026-07-21 13:10:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


RevisionType = Union[str, Sequence[str], None]

revision: str = "202607210003_comm_campaign_domain_c2_3"
down_revision: RevisionType = "202607210002_comm_automation_domain_c2_2"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")

    op.create_table(
        "communication_campaigns",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "key", name="uq_comm_campaigns_tenant_key"),
    )
    op.create_index(
        "ix_communication_campaigns_tenant_id",
        "communication_campaigns",
        ["tenant_id"],
    )
    op.create_index(
        "ix_comm_campaigns_tenant_status",
        "communication_campaigns",
        ["tenant_id", "status"],
    )

    op.create_table(
        "communication_campaign_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("campaign_id", sa.String(length=36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("intent_key", sa.String(length=128), nullable=False),
        sa.Column("preferred_template_key", sa.String(length=128), nullable=True),
        sa.Column("channel", sa.String(length=32), nullable=True),
        sa.Column("plan", json_type, nullable=False),
        sa.Column("meta", json_type, nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["communication_campaigns.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "campaign_id",
            "version_number",
            name="uq_comm_camp_ver_tenant_campaign_number",
        ),
    )
    op.create_index(
        "ix_communication_campaign_versions_tenant_id",
        "communication_campaign_versions",
        ["tenant_id"],
    )
    op.create_index(
        "ix_communication_campaign_versions_campaign_id",
        "communication_campaign_versions",
        ["campaign_id"],
    )
    op.create_index(
        "ix_comm_camp_ver_tenant_campaign",
        "communication_campaign_versions",
        ["tenant_id", "campaign_id"],
    )
    op.create_index(
        "ix_comm_camp_ver_tenant_status",
        "communication_campaign_versions",
        ["tenant_id", "status"],
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_comm_camp_one_draft_per_campaign
        ON communication_campaign_versions (tenant_id, campaign_id)
        WHERE status = 'draft'
        """
    )

    op.create_table(
        "communication_campaign_audience_definitions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("version_id", sa.String(length=36), nullable=False),
        sa.Column("definition_type", sa.String(length=64), nullable=False),
        sa.Column("definition", json_type, nullable=False),
        sa.Column("meta", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["version_id"],
            ["communication_campaign_versions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version_id", name="uq_comm_camp_audience_def_version"),
    )
    op.create_index(
        "ix_comm_camp_audience_def_version",
        "communication_campaign_audience_definitions",
        ["version_id"],
    )

    op.create_table(
        "communication_campaign_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("campaign_id", sa.String(length=36), nullable=False),
        sa.Column("campaign_version_id", sa.String(length=36), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("audience_snapshot", json_type, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meta", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["communication_campaigns.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["campaign_version_id"],
            ["communication_campaign_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "idempotency_key",
            name="uq_comm_camp_runs_tenant_idempotency",
        ),
    )
    op.create_index(
        "ix_communication_campaign_runs_tenant_id",
        "communication_campaign_runs",
        ["tenant_id"],
    )
    op.create_index(
        "ix_communication_campaign_runs_campaign_id",
        "communication_campaign_runs",
        ["campaign_id"],
    )
    op.create_index(
        "ix_communication_campaign_runs_campaign_version_id",
        "communication_campaign_runs",
        ["campaign_version_id"],
    )
    op.create_index(
        "ix_comm_camp_runs_tenant_campaign",
        "communication_campaign_runs",
        ["tenant_id", "campaign_id"],
    )
    op.create_index(
        "ix_comm_camp_runs_tenant_version",
        "communication_campaign_runs",
        ["tenant_id", "campaign_version_id"],
    )
    op.create_index(
        "ix_comm_camp_runs_tenant_status",
        "communication_campaign_runs",
        ["tenant_id", "status"],
    )

    op.create_table(
        "communication_campaign_recipients",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("address", sa.String(length=320), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("snapshot", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["communication_campaign_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "run_id",
            "entity_type",
            "entity_id",
            "address",
            name="uq_comm_camp_recip_run_entity_address",
        ),
    )
    op.create_index(
        "ix_comm_camp_recip_run",
        "communication_campaign_recipients",
        ["run_id"],
    )

    op.create_table(
        "communication_campaign_run_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("recipient_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason_codes", json_type, nullable=False),
        sa.Column("reason_message", sa.Text(), nullable=True),
        sa.Column("intent_key", sa.String(length=128), nullable=True),
        sa.Column("source_event_id", sa.String(length=128), nullable=True),
        sa.Column("meta", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["communication_campaign_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recipient_id"],
            ["communication_campaign_recipients.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "run_id",
            "recipient_id",
            name="uq_comm_camp_item_run_recipient",
        ),
    )
    op.create_index(
        "ix_communication_campaign_run_items_run_id",
        "communication_campaign_run_items",
        ["run_id"],
    )
    op.create_index(
        "ix_communication_campaign_run_items_recipient_id",
        "communication_campaign_run_items",
        ["recipient_id"],
    )
    op.create_index(
        "ix_comm_camp_item_run_status",
        "communication_campaign_run_items",
        ["run_id", "status"],
    )


def downgrade() -> None:
    op.drop_table("communication_campaign_run_items")
    op.drop_table("communication_campaign_recipients")
    op.drop_table("communication_campaign_runs")
    op.drop_table("communication_campaign_audience_definitions")
    op.execute("DROP INDEX IF EXISTS uq_comm_camp_one_draft_per_campaign")
    op.drop_table("communication_campaign_versions")
    op.drop_table("communication_campaigns")
