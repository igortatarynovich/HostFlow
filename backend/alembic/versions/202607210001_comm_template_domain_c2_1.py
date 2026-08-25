"""C2.1 PR-1: Template Platform domain tables.

Revision ID: 202607210001_comm_template_domain_c2_1
Revises: 202607200008_comm_delivery_diagnostics_tables_repair
Create Date: 2026-07-21 11:10:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


RevisionType = Union[str, Sequence[str], None]

revision: str = "202607210001_comm_template_domain_c2_1"
down_revision: RevisionType = "202607200008_comm_delivery_diagnostics_tables_repair"
branch_labels: RevisionType = None
depends_on: RevisionType = None


def upgrade() -> None:
    json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")

    op.create_table(
        "communication_templates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "key", name="uq_comm_templates_tenant_key"),
    )
    op.create_index("ix_communication_templates_tenant_id", "communication_templates", ["tenant_id"])
    op.create_index(
        "ix_comm_templates_tenant_status",
        "communication_templates",
        ["tenant_id", "status"],
    )

    op.create_table(
        "communication_template_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("template_id", sa.String(length=36), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("locale", sa.String(length=16), nullable=False),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("body_html", sa.Text(), nullable=True),
        sa.Column("meta", json_type, nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["communication_templates.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "template_id",
            "version_number",
            name="uq_comm_tpl_ver_tenant_template_number",
        ),
    )
    op.create_index(
        "ix_communication_template_versions_tenant_id",
        "communication_template_versions",
        ["tenant_id"],
    )
    op.create_index(
        "ix_communication_template_versions_template_id",
        "communication_template_versions",
        ["template_id"],
    )
    op.create_index(
        "ix_comm_tpl_ver_tenant_template",
        "communication_template_versions",
        ["tenant_id", "template_id"],
    )
    op.create_index(
        "ix_comm_tpl_ver_tenant_status",
        "communication_template_versions",
        ["tenant_id", "status"],
    )
    # One draft version per template.
    op.execute(
        """
        CREATE UNIQUE INDEX uq_comm_tpl_one_draft_per_template
        ON communication_template_versions (tenant_id, template_id)
        WHERE status = 'draft'
        """
    )

    op.create_table(
        "communication_template_variables",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("version_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("var_type", sa.String(length=32), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("default_value", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["version_id"],
            ["communication_template_versions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version_id", "name", name="uq_comm_tpl_var_version_name"),
    )
    op.create_index("ix_comm_tpl_var_version", "communication_template_variables", ["version_id"])

    op.create_table(
        "communication_template_channel_bindings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("version_id", sa.String(length=36), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["version_id"],
            ["communication_template_versions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "version_id",
            "channel",
            name="uq_comm_tpl_channel_version_channel",
        ),
    )
    op.create_index(
        "ix_comm_tpl_channel_version",
        "communication_template_channel_bindings",
        ["version_id"],
    )

    op.create_table(
        "communication_template_intent_bindings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("version_id", sa.String(length=36), nullable=False),
        sa.Column("intent_key", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["version_id"],
            ["communication_template_versions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "version_id",
            "intent_key",
            name="uq_comm_tpl_intent_version_intent",
        ),
    )
    op.create_index(
        "ix_comm_tpl_intent_version",
        "communication_template_intent_bindings",
        ["version_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_comm_tpl_intent_version", table_name="communication_template_intent_bindings")
    op.drop_table("communication_template_intent_bindings")
    op.drop_index("ix_comm_tpl_channel_version", table_name="communication_template_channel_bindings")
    op.drop_table("communication_template_channel_bindings")
    op.drop_index("ix_comm_tpl_var_version", table_name="communication_template_variables")
    op.drop_table("communication_template_variables")
    op.execute("DROP INDEX IF EXISTS uq_comm_tpl_one_draft_per_template")
    op.drop_index("ix_comm_tpl_ver_tenant_status", table_name="communication_template_versions")
    op.drop_index("ix_comm_tpl_ver_tenant_template", table_name="communication_template_versions")
    op.drop_index(
        "ix_communication_template_versions_template_id",
        table_name="communication_template_versions",
    )
    op.drop_index(
        "ix_communication_template_versions_tenant_id",
        table_name="communication_template_versions",
    )
    op.drop_table("communication_template_versions")
    op.drop_index("ix_comm_templates_tenant_status", table_name="communication_templates")
    op.drop_index("ix_communication_templates_tenant_id", table_name="communication_templates")
    op.drop_table("communication_templates")
