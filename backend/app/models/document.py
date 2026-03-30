from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import Date, DateTime, Enum, Integer, String, Text, text
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import Mapped, mapped_column, synonym
from sqlalchemy.sql import func

from backend.app.db.base import Base
from backend.app.db.tsvector_compat import TsVector
from .enums import (
    DocumentKind,
    DocumentProcessType,
    DocumentRequestedFrom,
    DocumentStatus,
)


class Document(Base):
    """
    Canonical document model.
    Stores candidate-bound documents with full lifecycle tracking and metadata.
    """

    __tablename__ = "documents"
    __table_args__ = {"extend_existing": True}

    # Primary / tenant
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    own_company_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    # Candidate / company ownership
    candidate_id: Mapped[str] = mapped_column(
        String(36),
        index=True,
        nullable=False,
    )
    company_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, index=True
    )

    # Categorisation
    kind: Mapped[DocumentKind] = mapped_column(
        Enum(DocumentKind, name="document_kind_enum"),
        nullable=False,
        default=DocumentKind.driver,
        server_default=DocumentKind.driver.value,
    )

    # Type / naming
    doc_type: Mapped[str] = mapped_column(String(100), nullable=False)
    custom_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Status flow
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status_enum_v2"),
        nullable=False,
        default=DocumentStatus.missing,
        server_default=DocumentStatus.missing.value,
    )
    requested_from: Mapped[DocumentRequestedFrom] = mapped_column(
        Enum(DocumentRequestedFrom, name="document_requested_from_enum"),
        nullable=False,
        default=DocumentRequestedFrom.driver,
        server_default=DocumentRequestedFrom.driver.value,
    )
    process_type: Mapped[DocumentProcessType] = mapped_column(
        Enum(DocumentProcessType, name="document_process_type_enum"),
        nullable=False,
        default=DocumentProcessType.none,
        server_default=DocumentProcessType.none.value,
    )

    # Dates
    issue_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expire_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    ordered_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    valid_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    user_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Misc
    reminder_days_before: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30, server_default=text("30")
    )
    owner_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, index=True
    )
    _JSONDict = MutableDict.as_mutable(SQLiteJSON().with_variant(JSONB, "postgresql"))
    _JSONList = MutableList.as_mutable(SQLiteJSON().with_variant(JSONB, "postgresql"))

    workflow: Mapped[Optional[dict[str, Any]]] = mapped_column(
        _JSONDict, nullable=True
    )
    files: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(
        _JSONList, nullable=True, default=list
    )
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(_JSONDict, nullable=True)

    # Legacy fields retained for backward compatibility
    owner_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, server_default=text("'candidate'")
    )
    number: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    filename: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )

    # Timestamps / soft delete
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    hostflow_document_search_tsv: Mapped[Optional[Any]] = mapped_column(TsVector, nullable=True)

    # --- backwards compatibility helpers ---
    key = synonym("doc_type")
    type = synonym("doc_type")
    issued_at = synonym("issue_date")
    expires_at = synonym("expire_date")
    extra = synonym("meta")
    meta_json = synonym("meta")
