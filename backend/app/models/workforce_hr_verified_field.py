"""HR verified fields — employment case SoT for downstream contract / ZUS / payroll (PR4)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from .mixins import TimestampMixin

JSONType = SQLiteJSON().with_variant(JSONB, "postgresql")

FIELD_STATUS_PENDING = "pending"
FIELD_STATUS_VERIFIED = "verified"
FIELD_STATUS_CONFLICT = "conflict"
FIELD_STATUS_OVERRIDDEN = "overridden"

FIELD_STATUS_APPROVE_OK = frozenset({FIELD_STATUS_VERIFIED, FIELD_STATUS_OVERRIDDEN})


class WorkforceHrVerifiedField(Base, TimestampMixin):
    __tablename__ = "workforce_hr_verified_fields"
    __table_args__ = (
        UniqueConstraint("tenant_id", "hr_review_id", "field_code", name="uq_hr_verified_field_review_code"),
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

    document_verification_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("workforce_hr_document_verifications.id", ondelete="SET NULL"), nullable=True, index=True
    )

    field_code: Mapped[str] = mapped_column(String(64), nullable=False)
    field_label: Mapped[str] = mapped_column(String(256), nullable=False)
    downstream_use_json: Mapped[Optional[list[str]]] = mapped_column(JSONType, nullable=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default=FIELD_STATUS_PENDING)
    verified_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_document_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    source_document_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    profile_values_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True)

    verified_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    override_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    conflict_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
