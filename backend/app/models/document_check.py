from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, Index, JSON, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class DocumentCheck(Base):
    """
    Stores reviewer decisions for documents (approve / reject) with optional reasoning.
    """

    __tablename__ = "document_checks"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('approved','rejected')",
            name="ck_document_checks_decision",
        ),
        Index("ix_document_checks_tenant_doc", "tenant_id", "document_id"),
        Index("ix_document_checks_doc", "document_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    document_id: Mapped[str] = mapped_column(String(36), nullable=False)
    reviewer_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    payload: Mapped[Optional[dict[str, object]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_now_utc,
        server_default=text("CURRENT_TIMESTAMP"),
    )


__all__ = ["DocumentCheck"]
