"""Forms Sprint 6 — immutable submission persistence envelope.

Append-only content (raw + normalized). Processing status is separate.
No domain mapping. No second intake engine. No Builder.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base
from .mixins import now_utc

JSONAnyType = SQLiteJSON().with_variant(JSONB, "postgresql")

STATUS_RECEIVED = "received"
STATUS_ACCEPTED = "accepted"
STATUS_REJECTED = "rejected"
STATUS_HANDED_OFF = "handed_off"
STATUS_FAILED = "failed"


class FormSubmissionEnvelope(Base):
    """Append-only Forms submission envelope (content immutable; status mutable)."""

    __tablename__ = "form_submission_envelopes"
    __table_args__ = (
        Index("ix_form_sub_env_tenant_form", "tenant_id", "form_id"),
        Index("ix_form_sub_env_tenant_created", "tenant_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    form_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenant_lead_forms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    published_version: Mapped[int] = mapped_column(Integer, nullable=False)
    schema_contract: Mapped[str | None] = mapped_column(String(64), nullable=True)
    answer_contract: Mapped[str] = mapped_column(String(64), nullable=False, default="forms.normalized_answers.v1")
    raw_values: Mapped[dict] = mapped_column(JSONAnyType, nullable=False, default=dict)
    normalized_values: Mapped[dict] = mapped_column(JSONAnyType, nullable=False, default=dict)
    errors: Mapped[list] = mapped_column(JSONAnyType, nullable=False, default=list)
    processing_status: Mapped[str] = mapped_column(String(32), nullable=False, default=STATUS_RECEIVED)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    intake_handoff: Mapped[dict] = mapped_column(JSONAnyType, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)
    status_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)


__all__ = [
    "FormSubmissionEnvelope",
    "STATUS_RECEIVED",
    "STATUS_ACCEPTED",
    "STATUS_REJECTED",
    "STATUS_HANDED_OFF",
    "STATUS_FAILED",
]
