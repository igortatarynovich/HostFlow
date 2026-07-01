from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import Boolean, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from .mixins import TimestampMixin

JSONType = SQLiteJSON().with_variant(JSONB, "postgresql")


class MergeDocumentTemplate(Base, TimestampMixin):
    """
    Text (or HTML) template with ``{{dotted.path}}`` placeholders, scoped by tenant
    and optionally by own company. Differs from DocumentTemplate (hiring checklist).
    """

    __tablename__ = "merge_document_templates"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    own_company_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("own_companies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    output_mime: Mapped[str] = mapped_column(
        String(128), nullable=False, default="text/plain", server_default="text/plain"
    )
    variable_bindings: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True)
    output_filename_pattern: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    doc_type: Mapped[str] = mapped_column(
        String(128), nullable=False, default="additional_document", server_default="additional_document"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
