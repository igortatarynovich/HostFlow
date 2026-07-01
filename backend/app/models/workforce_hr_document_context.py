"""Links documents to workforce employees with HR / e-teczka semantics."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from .mixins import TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.document import Document
    from backend.app.models.workforce_employee import WorkforceEmployee


class WorkforceHrDocumentContext(Base, TimestampMixin):
    __tablename__ = "workforce_hr_document_contexts"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workforce_employees.id", ondelete="CASCADE"), index=True, nullable=False
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False
    )

    context_type: Mapped[str] = mapped_column(String(64), nullable=False)
    legal_category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    document_group: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    verification_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    employee: Mapped["WorkforceEmployee"] = relationship(
        "WorkforceEmployee",
        foreign_keys=[employee_id],
        back_populates="hr_document_contexts",
    )
    document: Mapped["Document"] = relationship("Document", foreign_keys=[document_id])
