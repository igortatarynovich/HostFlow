"""C2.2 PR-1: Automation Engine domain tables.

Revision ID: 202607210002_comm_automation_domain_c2_2
Revises: 202607210001_comm_template_domain_c2_1
Create Date: 2026-07-21 12:20:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


RevisionType = Union[str, Sequence[str], None]

revision: str = "202607210002_comm_automation_domain_c2_2"
down_revision: RevisionType = "202607210001_comm_template_domain_c2_1"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")

    op.create_table(
        "communication_automation_rules",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "key", name="uq_comm_auto_rules_tenant_key"),
    )
    op.create_index(
        "ix_communication_automation_rules_tenant_id",
        "communication_automation_rules",
        ["tenant_id"],
    )
    op.create_index(
        "ix_comm_auto_rules_tenant_status",
        "communication_automation_rules",
        ["tenant_id", "status"],
    )
    op.create_index(
        "ix_comm_auto_rules_tenant_enabled",
        "communication_automation_rules",
        ["tenant_id", "enabled"],
    )

    op.create_table(
        "communication_automation_rule_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("rule_id", sa.String(length=36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("conditions", json_type, nullable=False),
        sa.Column("intent_key", sa.String(length=128), nullable=False),
        sa.Column("preferred_template_key", sa.String(length=128), nullable=True),
        sa.Column("channel", sa.String(length=32), nullable=True),
        sa.Column("recipient_strategy", sa.String(length=64), nullable=False),
        sa.Column("recipient_config", json_type, nullable=False),
        sa.Column("variables_mapping", json_type, nullable=False),
        sa.Column("meta", json_type, nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["rule_id"],
            ["communication_automation_rules.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "rule_id",
            "version_number",
            name="uq_comm_auto_ver_tenant_rule_number",
        ),
    )
    op.create_index(
        "ix_communication_automation_rule_versions_tenant_id",
        "communication_automation_rule_versions",
        ["tenant_id"],
    )
    op.create_index(
        "ix_communication_automation_rule_versions_rule_id",
        "communication_automation_rule_versions",
        ["rule_id"],
    )
    op.create_index(
        "ix_comm_auto_ver_tenant_rule",
        "communication_automation_rule_versions",
        ["tenant_id", "rule_id"],
    )
    op.create_index(
        "ix_comm_auto_ver_tenant_status",
        "communication_automation_rule_versions",
        ["tenant_id", "status"],
    )
    # One draft version per rule.
    op.execute(
        """
        CREATE UNIQUE INDEX uq_comm_auto_one_draft_per_rule
        ON communication_automation_rule_versions (tenant_id, rule_id)
        WHERE status = 'draft'
        """
    )

    op.create_table(
        "communication_automation_triggers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("version_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("event_filter", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["version_id"],
            ["communication_automation_rule_versions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "version_id",
            "event_type",
            name="uq_comm_auto_trigger_version_event",
        ),
    )
    op.create_index(
        "ix_comm_auto_trigger_version",
        "communication_automation_triggers",
        ["version_id"],
    )
    op.create_index(
        "ix_comm_auto_trigger_event_type",
        "communication_automation_triggers",
        ["event_type"],
    )

    op.create_table(
        "communication_automation_decisions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("rule_id", sa.String(length=36), nullable=False),
        sa.Column("rule_version_id", sa.String(length=36), nullable=False),
        sa.Column("trigger_id", sa.String(length=36), nullable=True),
        sa.Column("source_event_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("reason_codes", json_type, nullable=False),
        sa.Column("intent_key", sa.String(length=128), nullable=True),
        sa.Column("intent_request_snapshot", json_type, nullable=True),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("meta", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_communication_automation_decisions_tenant_id",
        "communication_automation_decisions",
        ["tenant_id"],
    )
    op.create_index(
        "ix_comm_auto_dec_tenant_created",
        "communication_automation_decisions",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_comm_auto_dec_tenant_rule",
        "communication_automation_decisions",
        ["tenant_id", "rule_id"],
    )
    op.create_index(
        "ix_comm_auto_dec_tenant_event",
        "communication_automation_decisions",
        ["tenant_id", "source_event_id"],
    )
    op.create_index(
        "ix_comm_auto_dec_tenant_outcome",
        "communication_automation_decisions",
        ["tenant_id", "outcome"],
    )
    op.create_index(
        "ix_communication_automation_decisions_rule_id",
        "communication_automation_decisions",
        ["rule_id"],
    )
    op.create_index(
        "ix_communication_automation_decisions_rule_version_id",
        "communication_automation_decisions",
        ["rule_version_id"],
    )


def downgrade() -> None:
    op.drop_table("communication_automation_decisions")
    op.drop_table("communication_automation_triggers")
    op.execute("DROP INDEX IF EXISTS uq_comm_auto_one_draft_per_rule")
    op.drop_table("communication_automation_rule_versions")
    op.drop_table("communication_automation_rules")
