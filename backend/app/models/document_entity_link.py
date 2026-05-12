"""Link one Document to an operational entity (ADR-009 Document Link MVP)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from backend.app.db.base import Base


class DocumentEntityLink(Base):
    __tablename__ = "document_entity_links"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "document_id",
            "linked_entity_type",
            "linked_entity_id",
            "relation_type",
            name="uq_document_entity_link_scope",
        ),
        {"extend_existing": True},
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    linked_entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    linked_entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    relation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    module_key: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
