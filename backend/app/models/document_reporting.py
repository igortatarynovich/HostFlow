from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class DocumentComplianceLog(Base):
    """
    Snapshot of compliance state for a candidate/company pair at a specific date.
    """

    __tablename__ = "documents_compliance_log"
    __table_args__ = (
        Index("ix_documents_compliance_log_tenant_date", "tenant_id", "snapshot_date"),
        Index("ix_documents_compliance_log_candidate", "candidate_id"),
        Index("ix_documents_compliance_log_company", "company_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    candidate_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    company_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    ruleset_version_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    compliance_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    missing_types: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now_utc,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class DocumentMetricsDaily(Base):
    """
    Aggregated per-day metrics covering document readiness and review SLA.
    """

    __tablename__ = "document_metrics_daily"
    __table_args__ = (
        Index("ix_document_metrics_daily_tenant_date", "tenant_id", "date"),
        Index("ix_document_metrics_daily_candidate", "candidate_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    candidate_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    company_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    total_docs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_docs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expired_docs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_review_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    reviewer_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now_utc,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class ReportSummary(Base):
    """
    Cached high-level report aggregates per period.
    """

    __tablename__ = "report_summaries"
    __table_args__ = (
        Index("ix_report_summaries_tenant_type", "tenant_id", "report_type"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    report_type: Mapped[str] = mapped_column(String(64), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    total_candidates: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_compliance: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_sla: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now_utc,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class ReportExport(Base):
    """
    Stores generated exports (CSV/PDF) metadata.
    """

    __tablename__ = "report_exports"
    __table_args__ = (
        Index("ix_report_exports_tenant_type", "tenant_id", "report_type"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    file_id: Mapped[str] = mapped_column(String(64), nullable=False)
    report_type: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now_utc,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class BulkOperation(Base):
    """
    Represents a bulk action (approve docs, send notifications, etc).
    """

    __tablename__ = "bulk_operations"
    __table_args__ = (
        Index("ix_bulk_operations_tenant_type", "tenant_id", "operation_type"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    operation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    filters: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    items_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    result_summary: Mapped[Optional[dict[str, object]]] = mapped_column(
        JSON, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now_utc,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class BulkOperationItem(Base):
    """
    Individual item result inside a bulk operation.
    """

    __tablename__ = "bulk_operation_items"
    __table_args__ = (
        Index("ix_bulk_operation_items_operation", "bulk_operation_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    bulk_operation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("bulk_operations.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now_utc,
        server_default=text("CURRENT_TIMESTAMP"),
    )


__all__ = [
    "DocumentComplianceLog",
    "DocumentMetricsDaily",
    "ReportSummary",
    "ReportExport",
    "BulkOperation",
    "BulkOperationItem",
]
