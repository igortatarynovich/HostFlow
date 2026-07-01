from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import Mapped, mapped_column, synonym

from .enums import (
    DocumentKind,
    DocumentProcessType,
    DocumentRequestedFrom,
    DocumentDuplicatePolicy,
    DocumentStatusModel,
)
from backend.app.db.base import Base  # единый Base


class DocumentType(Base):
    """
    Типы документов (паспорт, виза, права и т.п.).
    Уникальность кода в пределах tenant_id.
    """

    __tablename__ = "document_types"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_document_types_tenant_code"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    kind: Mapped[DocumentKind] = mapped_column(
        Enum(DocumentKind, name="document_kind_enum"),
        nullable=False,
        default=DocumentKind.driver,
        server_default=DocumentKind.driver.value,
    )
    requested_from: Mapped[DocumentRequestedFrom] = mapped_column(
        Enum(DocumentRequestedFrom, name="document_requested_from_enum"),
        nullable=False,
        default=DocumentRequestedFrom.driver,
        server_default=DocumentRequestedFrom.driver.value,
    )
    process_type: Mapped[Optional[DocumentProcessType]] = mapped_column(
        Enum(DocumentProcessType, name="document_process_type_enum"),
        nullable=True,
        default=DocumentProcessType.none,
        server_default=DocumentProcessType.none.value,
    )
    default_expire_in_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    _JSONList = MutableList.as_mutable(SQLiteJSON().with_variant(JSONB, "postgresql"))
    _JSONDict = MutableDict.as_mutable(SQLiteJSON().with_variant(JSONB, "postgresql"))

    aliases: Mapped[list[str]] = mapped_column(
        _JSONList, nullable=False, default=list
    )
    required_meta: Mapped[list[str]] = mapped_column(
        _JSONList, nullable=False, default=list
    )
    title: Mapped[dict[str, str]] = mapped_column(
        _JSONDict,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )
    metadata_schema: Mapped[dict[str, Any]] = mapped_column(
        _JSONDict, nullable=False, default=dict, server_default=text("'{}'")
    )
    required_files: Mapped[dict[str, Any]] = mapped_column(
        _JSONDict, nullable=False, default=dict, server_default=text("'{}'")
    )
    expiry_rule: Mapped[dict[str, Any]] = mapped_column(
        _JSONDict, nullable=False, default=dict, server_default=text("'{}'")
    )
    owner_summary_weight: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default=text("0")
    )
    i18n_key: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    requires_custom_name: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=func.false()
    )
    duplicate_policy: Mapped[DocumentDuplicatePolicy] = mapped_column(
        Enum(
            DocumentDuplicatePolicy,
            name="document_duplicate_policy_enum",
            native_enum=False,
        ),
        nullable=False,
        default=DocumentDuplicatePolicy.one_per_candidate,
        server_default=DocumentDuplicatePolicy.one_per_candidate.value,
    )
    orderable: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=func.false()
    )

    # Backwards compatibility alias (legacy column name)
    valid_days = synonym("default_expire_in_days")

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=func.true()
    )

    # Модель статусов документа (определяет набор допустимых статусов)
    status_model: Mapped[Optional[DocumentStatusModel]] = mapped_column(
        Enum(DocumentStatusModel, name="document_status_model_enum", native_enum=False),
        nullable=True,
        default=DocumentStatusModel.EVIDENCE,
        server_default=DocumentStatusModel.EVIDENCE.value,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<DocumentType {self.tenant_id}:{self.code}>"
