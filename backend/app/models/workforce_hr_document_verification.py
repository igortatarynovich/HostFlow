"""Per-document HR review verification state (PR3 — lightweight, not verified-fields SoT)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from .mixins import TimestampMixin

JSONType = SQLiteJSON().with_variant(JSONB, "postgresql")

VERIFICATION_PENDING = "pending"
VERIFICATION_OPENED = "opened"
VERIFICATION_VERIFIED = "verified"
VERIFICATION_REJECTED = "rejected"
VERIFICATION_NEEDS_CORRECTION = "needs_correction"
VERIFICATION_NOT_REQUIRED = "not_required"

VERIFICATION_TERMINAL_OK = frozenset({VERIFICATION_VERIFIED, VERIFICATION_NOT_REQUIRED})


class WorkforceHrDocumentVerification(Base, TimestampMixin):
    __tablename__ = "workforce_hr_document_verifications"
    __table_args__ = (
        UniqueConstraint("tenant_id", "hr_review_id", "document_key", name="uq_hr_doc_verify_review_key"),
        {"extend_existing": True},
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    hr_review_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workforce_hr_reviews.id", ondelete="CASCADE"), index=True, nullable=False
    )
    employee_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("workforce_employees.id", ondelete="CASCADE"), nullable=True, index=True
    )
    handoff_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("candidate_handoffs.id", ondelete="SET NULL"), nullable=True, index=True
    )

    document_key: Mapped[str] = mapped_column(String(128), nullable=False)
    document_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    document_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    checklist_item_code: Mapped[str] = mapped_column(String(64), nullable=False, default="documents_uploaded")
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    verification_status: Mapped[str] = mapped_column(String(32), nullable=False, default=VERIFICATION_PENDING)
    verified_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    opened_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    correction_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_fields_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True)
