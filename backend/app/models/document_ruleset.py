from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
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


class DocumentRulesetVersion(Base):
    """
    Stores immutable JSON snapshots of rulesets with per-tenant versioning.
    """

    __tablename__ = "document_ruleset_versions"
    __table_args__ = (
        Index("ix_document_ruleset_versions_tenant", "tenant_id"),
        Index(
            "uq_document_ruleset_global_version",
            "tenant_id",
            "version",
            unique=True,
            sqlite_where=text("own_company_id IS NULL"),
            postgresql_where=text("own_company_id IS NULL"),
        ),
        Index(
            "uq_document_ruleset_scoped_version",
            "tenant_id",
            "own_company_id",
            "version",
            unique=True,
            sqlite_where=text("own_company_id IS NOT NULL"),
            postgresql_where=text("own_company_id IS NOT NULL"),
        ),
        Index("ix_document_ruleset_versions_own_company_id", "own_company_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    own_company_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("own_companies.id", ondelete="SET NULL"),
        nullable=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    json_data: Mapped[dict[str, object]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("1"),
    )
    signature: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default="",
        server_default=text("''"),
    )
    origin_version_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("document_ruleset_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    rollback_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now_utc,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class DocumentRulesetUsage(Base):
    """
    Tracks where a particular ruleset version was used (compliance/report/checklist/etc).
    """

    __tablename__ = "document_ruleset_usage"
    __table_args__ = (
        Index("ix_document_ruleset_usage_version", "ruleset_version_id"),
        Index("ix_document_ruleset_usage_tenant", "tenant_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    ruleset_version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("document_ruleset_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    used_in: Mapped[str] = mapped_column(String(64), nullable=False)
    reference_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now_utc,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    meta: Mapped[dict[str, object]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )


class DocumentRulesetDiff(Base):
    """
    Optional storage of JSON diffs between consecutive ruleset versions.
    """

    __tablename__ = "document_ruleset_diffs"
    __table_args__ = (
        Index("ix_document_ruleset_diffs_from", "ruleset_id_from"),
        Index("ix_document_ruleset_diffs_to", "ruleset_id_to"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    ruleset_id_from: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("document_ruleset_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    ruleset_id_to: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("document_ruleset_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    diff_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    computed_with: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now_utc,
        server_default=text("CURRENT_TIMESTAMP"),
    )


__all__ = [
    "DocumentRulesetVersion",
    "DocumentRulesetUsage",
    "DocumentRulesetDiff",
]
