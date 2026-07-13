"""ADR-019 domain event outbox + evaluation results (PR 3A-1).

Revision ID: 202607131402
Revises: 202606300004
Create Date: 2026-07-13 15:20:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


RevisionType = Union[str, Sequence[str], None]

revision: str = "202607131402"
down_revision: RevisionType = "202606300004"
branch_labels: RevisionType = None
depends_on: RevisionType = None

JSONType = postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "domain_event_outbox",
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("event_version", sa.String(length=16), nullable=False),
        sa.Column("aggregate_type", sa.String(length=64), nullable=False),
        sa.Column("aggregate_id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=True),
        sa.Column("payload", JSONType, nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.String(length=36), nullable=False),
        sa.Column("causation_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index(
        "ix_domain_event_outbox_status_available",
        "domain_event_outbox",
        ["status", "available_at"],
    )
    op.create_index(
        "ix_domain_event_outbox_tenant_type",
        "domain_event_outbox",
        ["tenant_id", "event_type"],
    )
    op.create_index(
        "ix_domain_event_outbox_aggregate",
        "domain_event_outbox",
        ["aggregate_type", "aggregate_id"],
    )
    op.create_index(
        op.f("ix_domain_event_outbox_aggregate_id"),
        "domain_event_outbox",
        ["aggregate_id"],
    )
    op.create_index(
        op.f("ix_domain_event_outbox_company_id"),
        "domain_event_outbox",
        ["company_id"],
    )
    op.create_index(
        op.f("ix_domain_event_outbox_status"),
        "domain_event_outbox",
        ["status"],
    )
    op.create_index(
        op.f("ix_domain_event_outbox_tenant_id"),
        "domain_event_outbox",
        ["tenant_id"],
    )

    op.create_table(
        "domain_event_consumer_receipts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("consumer_name", sa.String(length=128), nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_domain_event_consumer_receipt",
        "domain_event_consumer_receipts",
        ["consumer_name", "event_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_domain_event_consumer_receipts_event_id"),
        "domain_event_consumer_receipts",
        ["event_id"],
    )
    op.create_index(
        op.f("ix_domain_event_consumer_receipts_tenant_id"),
        "domain_event_consumer_receipts",
        ["tenant_id"],
    )

    op.create_table(
        "requirement_evaluation_results",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=True),
        sa.Column("policy_ref", sa.String(length=128), nullable=False),
        sa.Column("policy_version", sa.String(length=64), nullable=False),
        sa.Column("target_stage", sa.String(length=64), nullable=False),
        sa.Column("entity_revision", sa.String(length=128), nullable=False),
        sa.Column("can_transition", sa.Boolean(), nullable=False),
        sa.Column("blocker_codes", JSONType, nullable=False),
        sa.Column("result_snapshot", JSONType, nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_req_eval_results_entity",
        "requirement_evaluation_results",
        ["entity_type", "entity_id", "evaluated_at"],
    )
    op.create_index(
        "ix_req_eval_results_tenant_entity",
        "requirement_evaluation_results",
        ["tenant_id", "entity_type", "entity_id"],
    )
    op.create_index(
        op.f("ix_requirement_evaluation_results_company_id"),
        "requirement_evaluation_results",
        ["company_id"],
    )
    op.create_index(
        op.f("ix_requirement_evaluation_results_entity_id"),
        "requirement_evaluation_results",
        ["entity_id"],
    )
    op.create_index(
        op.f("ix_requirement_evaluation_results_tenant_id"),
        "requirement_evaluation_results",
        ["tenant_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_requirement_evaluation_results_tenant_id"),
        table_name="requirement_evaluation_results",
    )
    op.drop_index(
        op.f("ix_requirement_evaluation_results_entity_id"),
        table_name="requirement_evaluation_results",
    )
    op.drop_index(
        op.f("ix_requirement_evaluation_results_company_id"),
        table_name="requirement_evaluation_results",
    )
    op.drop_index("ix_req_eval_results_tenant_entity", table_name="requirement_evaluation_results")
    op.drop_index("ix_req_eval_results_entity", table_name="requirement_evaluation_results")
    op.drop_table("requirement_evaluation_results")

    op.drop_index(
        op.f("ix_domain_event_consumer_receipts_tenant_id"),
        table_name="domain_event_consumer_receipts",
    )
    op.drop_index(
        op.f("ix_domain_event_consumer_receipts_event_id"),
        table_name="domain_event_consumer_receipts",
    )
    op.drop_index("uq_domain_event_consumer_receipt", table_name="domain_event_consumer_receipts")
    op.drop_table("domain_event_consumer_receipts")

    op.drop_index(op.f("ix_domain_event_outbox_tenant_id"), table_name="domain_event_outbox")
    op.drop_index(op.f("ix_domain_event_outbox_status"), table_name="domain_event_outbox")
    op.drop_index(op.f("ix_domain_event_outbox_company_id"), table_name="domain_event_outbox")
    op.drop_index(op.f("ix_domain_event_outbox_aggregate_id"), table_name="domain_event_outbox")
    op.drop_index("ix_domain_event_outbox_aggregate", table_name="domain_event_outbox")
    op.drop_index("ix_domain_event_outbox_tenant_type", table_name="domain_event_outbox")
    op.drop_index("ix_domain_event_outbox_status_available", table_name="domain_event_outbox")
    op.drop_table("domain_event_outbox")
