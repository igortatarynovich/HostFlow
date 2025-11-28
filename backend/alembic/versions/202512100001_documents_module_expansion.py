"""Expand documents module: versioning, checks, rulesets, compliance, and reporting scaffolding."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202512100001_documents_module_expansion"
down_revision: Union[str, Sequence[str], None] = "202512090002_vacancies_status_text"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _insp():
    return sa.inspect(op.get_bind())


def _has_table(name: str) -> bool:
    try:
        return name in _insp().get_table_names()
    except Exception:
        return False


def _has_column(table: str, column: str) -> bool:
    try:
        return any(col["name"] == column for col in _insp().get_columns(table))
    except Exception:
        return False


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    # Ensure documents.version exists and defaults to 1
    if _has_table("documents"):
        if not _has_column("documents", "version"):
            op.add_column(
                "documents",
                sa.Column(
                    "version",
                    sa.Integer(),
                    nullable=False,
                    server_default=sa.text("1"),
                ),
            )
        if dialect != "sqlite":
            # Normalize NULLs just in case and enforce default
            op.execute(sa.text("UPDATE documents SET version = 1 WHERE version IS NULL"))
            op.alter_column(
                "documents",
                "version",
                existing_type=sa.Integer(),
                nullable=False,
                server_default=sa.text("1"),
            )

    # document_checks
    if not _has_table("document_checks"):
        op.create_table(
            "document_checks",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column("tenant_id", sa.String(length=36), nullable=False, index=True),
            sa.Column("document_id", sa.String(length=36), nullable=False),
            sa.Column("reviewer_id", sa.String(length=36), nullable=True),
            sa.Column("decision", sa.String(length=32), nullable=False),
            sa.Column("reason_code", sa.String(length=64), nullable=True),
            sa.Column("comment", sa.Text(), nullable=True),
            sa.Column("payload", sa.JSON(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.CheckConstraint(
                "decision IN ('approved','rejected')",
                name="ck_document_checks_decision",
            ),
        )
        op.create_index(
            "ix_document_checks_tenant_doc",
            "document_checks",
            ["tenant_id", "document_id"],
        )
        op.create_index(
            "ix_document_checks_doc",
            "document_checks",
            ["document_id"],
        )

    # document_ruleset_versions
    if not _has_table("document_ruleset_versions"):
        op.create_table(
            "document_ruleset_versions",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column("tenant_id", sa.String(length=36), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("json_data", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("comment", sa.Text(), nullable=True),
            sa.Column("created_by", sa.String(length=36), nullable=True),
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default="1" if dialect == "sqlite" else sa.text("TRUE"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.UniqueConstraint(
                "tenant_id", "version", name="uq_document_ruleset_versions_tenant_version"
            ),
        )
        op.create_index(
            "ix_document_ruleset_versions_tenant",
            "document_ruleset_versions",
            ["tenant_id"],
        )

    # document_ruleset_usage
    if not _has_table("document_ruleset_usage"):
        op.create_table(
            "document_ruleset_usage",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column("tenant_id", sa.String(length=36), nullable=False),
            sa.Column(
                "ruleset_version_id",
                sa.String(length=36),
                sa.ForeignKey(
                    "document_ruleset_versions.id", ondelete="CASCADE"
                ),
                nullable=False,
            ),
            sa.Column("used_in", sa.String(length=64), nullable=False),
            sa.Column("reference_id", sa.String(length=64), nullable=True),
            sa.Column(
                "used_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )
        op.create_index(
            "ix_document_ruleset_usage_version",
            "document_ruleset_usage",
            ["ruleset_version_id"],
        )
        op.create_index(
            "ix_document_ruleset_usage_tenant",
            "document_ruleset_usage",
            ["tenant_id"],
        )

    # document_ruleset_diffs
    if not _has_table("document_ruleset_diffs"):
        op.create_table(
            "document_ruleset_diffs",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column(
                "ruleset_id_from",
                sa.String(length=36),
                sa.ForeignKey("document_ruleset_versions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "ruleset_id_to",
                sa.String(length=36),
                sa.ForeignKey("document_ruleset_versions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("diff_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )
        op.create_index(
            "ix_document_ruleset_diffs_from",
            "document_ruleset_diffs",
            ["ruleset_id_from"],
        )
        op.create_index(
            "ix_document_ruleset_diffs_to",
            "document_ruleset_diffs",
            ["ruleset_id_to"],
        )

    # documents_compliance_log
    if not _has_table("documents_compliance_log"):
        op.create_table(
            "documents_compliance_log",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column("tenant_id", sa.String(length=36), nullable=False),
            sa.Column("candidate_id", sa.String(length=36), nullable=True),
            sa.Column("company_id", sa.String(length=36), nullable=True),
            sa.Column("ruleset_version_id", sa.String(length=36), nullable=True),
            sa.Column("compliance_score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("missing_types", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("snapshot_date", sa.Date(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )
        op.create_index(
            "ix_documents_compliance_log_tenant_date",
            "documents_compliance_log",
            ["tenant_id", "snapshot_date"],
        )
        op.create_index(
            "ix_documents_compliance_log_candidate",
            "documents_compliance_log",
            ["candidate_id"],
        )
        op.create_index(
            "ix_documents_compliance_log_company",
            "documents_compliance_log",
            ["company_id"],
        )

    # document_metrics_daily
    if not _has_table("document_metrics_daily"):
        op.create_table(
            "document_metrics_daily",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column("tenant_id", sa.String(length=36), nullable=False),
            sa.Column("date", sa.Date(), nullable=False),
            sa.Column("candidate_id", sa.String(length=36), nullable=True),
            sa.Column("company_id", sa.String(length=36), nullable=True),
            sa.Column("total_docs", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("valid_docs", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("expired_docs", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("avg_review_time", sa.Float(), nullable=True),
            sa.Column("reviewer_id", sa.String(length=36), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )
        op.create_index(
            "ix_document_metrics_daily_tenant_date",
            "document_metrics_daily",
            ["tenant_id", "date"],
        )
        op.create_index(
            "ix_document_metrics_daily_candidate",
            "document_metrics_daily",
            ["candidate_id"],
        )

    # report_summaries
    if not _has_table("report_summaries"):
        op.create_table(
            "report_summaries",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column("tenant_id", sa.String(length=36), nullable=False),
            sa.Column("report_type", sa.String(length=64), nullable=False),
            sa.Column("period_start", sa.Date(), nullable=False),
            sa.Column("period_end", sa.Date(), nullable=False),
            sa.Column("total_candidates", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("avg_compliance", sa.Float(), nullable=True),
            sa.Column("avg_sla", sa.Float(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )
        op.create_index(
            "ix_report_summaries_tenant_type",
            "report_summaries",
            ["tenant_id", "report_type"],
        )

    # report_exports
    if not _has_table("report_exports"):
        op.create_table(
            "report_exports",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column("tenant_id", sa.String(length=36), nullable=False),
            sa.Column("file_id", sa.String(length=64), nullable=False),
            sa.Column("report_type", sa.String(length=64), nullable=False),
            sa.Column("created_by", sa.String(length=36), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )
        op.create_index(
            "ix_report_exports_tenant_type",
            "report_exports",
            ["tenant_id", "report_type"],
        )

    # bulk_operations
    if not _has_table("bulk_operations"):
        op.create_table(
            "bulk_operations",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column("tenant_id", sa.String(length=36), nullable=False),
            sa.Column("operation_type", sa.String(length=64), nullable=False),
            sa.Column("target_type", sa.String(length=64), nullable=False),
            sa.Column("filters", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("items_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_by", sa.String(length=36), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("result_summary", sa.JSON(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index(
            "ix_bulk_operations_tenant_type",
            "bulk_operations",
            ["tenant_id", "operation_type"],
        )

    # bulk_operation_items
    if not _has_table("bulk_operation_items"):
        op.create_table(
            "bulk_operation_items",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column(
                "bulk_operation_id",
                sa.String(length=36),
                sa.ForeignKey("bulk_operations.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("target_id", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )
        op.create_index(
            "ix_bulk_operation_items_operation",
            "bulk_operation_items",
            ["bulk_operation_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    # Drop tables in reverse order to satisfy FK constraints
    for table in (
        "bulk_operation_items",
        "bulk_operations",
        "report_exports",
        "report_summaries",
        "document_metrics_daily",
        "documents_compliance_log",
        "document_ruleset_diffs",
        "document_ruleset_usage",
        "document_ruleset_versions",
        "document_checks",
    ):
        if _has_table(table):
            op.drop_table(table)

    # Drop documents.version column if present
    if _has_table("documents") and _has_column("documents", "version"):
        if dialect == "sqlite":
            with op.batch_alter_table("documents", recreate="always") as batch:
                batch.drop_column("version")
        else:
            op.drop_column("documents", "version")
