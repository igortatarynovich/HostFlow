from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base
from .mixins import now_utc


class TenantLeadForm(Base):
    """Tenant-scoped lead form slot (§2.16): counts toward active lead-forms cap."""

    __tablename__ = "tenant_lead_forms"
    __table_args__ = (
        Index("ix_tenant_lead_forms_tenant_active", "tenant_id", "is_active"),
        UniqueConstraint("tenant_id", "public_slug", name="uq_tenant_lead_forms_tenant_public_slug"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    public_slug: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)


__all__ = ["TenantLeadForm"]
