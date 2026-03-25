"""Risk intelligence v1 Phase B: hourly aggregates + shadow entity rows.

Revision ID: 202603221400_risk_intel_hourly_shadow
Revises: 202603221201_merge_party_pipeline_and_stages_head
Create Date: 2026-03-22
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "202603221400_risk_intel_hourly_shadow"
down_revision: Union[str, None] = "202603221201_merge_party_pipeline_and_stages_head"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgres() -> bool:
    bind = op.get_bind()
    return bind.dialect.name == "postgresql"


def upgrade() -> None:
    op.create_table(
        "risk_intel_tenant_hourly",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("bucket_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("risk_version", sa.String(length=32), nullable=False, server_default="risk_model_v1"),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("candidates_evaluated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_risk_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("high_risk_volume", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("band_low", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("band_medium", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("band_high", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("band_critical", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_response_histogram", sa.JSON(), nullable=False),
        sa.Column("effective_weights", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_risk_intel_hourly_tenant_id", "risk_intel_tenant_hourly", ["tenant_id"], unique=False)
    op.create_index("ix_risk_intel_hourly_bucket", "risk_intel_tenant_hourly", ["bucket_start"], unique=False)
    op.create_index(
        "uq_risk_intel_hourly_tenant_bucket",
        "risk_intel_tenant_hourly",
        ["tenant_id", "bucket_start"],
        unique=True,
    )

    op.create_table(
        "risk_intel_entity_shadow",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False, server_default="candidate"),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("scored_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bucket_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("risk_version", sa.String(length=32), nullable=False, server_default="risk_model_v1"),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("band", sa.String(length=16), nullable=False),
        sa.Column("stage_at_score", sa.String(length=64), nullable=True),
        sa.Column("drivers", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_risk_shadow_tenant_scored", "risk_intel_entity_shadow", ["tenant_id", "scored_at"], unique=False)
    op.create_index("ix_risk_shadow_entity", "risk_intel_entity_shadow", ["tenant_id", "entity_type", "entity_id"], unique=False)
    op.create_index("ix_risk_shadow_bucket", "risk_intel_entity_shadow", ["tenant_id", "bucket_start"], unique=False)

    if _is_postgres():
        for table in ("risk_intel_tenant_hourly", "risk_intel_entity_shadow"):
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
            policy_name = f"rls_{table}_tenant"
            op.execute(
                f"""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_policies
                        WHERE schemaname = current_schema()
                          AND tablename = '{table}'
                          AND policyname = '{policy_name}'
                    ) THEN
                        CREATE POLICY {policy_name} ON {table}
                        USING (tenant_id = current_setting('app.tenant_id'));
                    END IF;
                END $$;
                """
            )


def downgrade() -> None:
    if _is_postgres():
        for table in ("risk_intel_entity_shadow", "risk_intel_tenant_hourly"):
            op.execute(f"DROP POLICY IF EXISTS rls_{table}_tenant ON {table};")
            op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
    op.drop_index("ix_risk_shadow_bucket", table_name="risk_intel_entity_shadow")
    op.drop_index("ix_risk_shadow_entity", table_name="risk_intel_entity_shadow")
    op.drop_index("ix_risk_shadow_tenant_scored", table_name="risk_intel_entity_shadow")
    op.drop_table("risk_intel_entity_shadow")
    op.drop_index("uq_risk_intel_hourly_tenant_bucket", table_name="risk_intel_tenant_hourly")
    op.drop_index("ix_risk_intel_hourly_bucket", table_name="risk_intel_tenant_hourly")
    op.drop_index("ix_risk_intel_hourly_tenant_id", table_name="risk_intel_tenant_hourly")
    op.drop_table("risk_intel_tenant_hourly")
