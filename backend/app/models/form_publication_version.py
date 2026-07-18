"""Forms Sprint 3 — append-only publication version ledger.

One immutable row per commit_publish. TenantLeadForm.published_* remain current pointers.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base
from .mixins import now_utc

JSONAnyType = SQLiteJSON().with_variant(JSONB, "postgresql")


class FormPublicationVersion(Base):
    """Append-only HostFlow Form publication version (audit + submission pin target)."""

    __tablename__ = "form_publication_versions"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "form_id",
            "version",
            name="uq_form_pub_versions_tenant_form_ver",
        ),
        Index("ix_form_pub_versions_tenant_form", "tenant_id", "form_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    form_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenant_lead_forms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSONAnyType, nullable=False, default=dict)
    consent_pin: Mapped[dict] = mapped_column(JSONAnyType, nullable=False, default=dict)
    submission_pin_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=now_utc)


__all__ = ["FormPublicationVersion"]
