"""Tenant-scoped requirement overrides for Requirement Rules Engine (P3B)."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from backend.app.models.mixins import TimestampMixin


class TenantRequirementOverride(TimestampMixin, Base):
    """Audited tenant relax/add/severity override — not a custom rule engine."""

    __tablename__ = "tenant_requirement_overrides"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    entity_profile_code: Mapped[Optional[str]] = mapped_column(String(128), index=True, nullable=True)
    context: Mapped[Optional[str]] = mapped_column(String(32), index=True, nullable=True)
    stage_code: Mapped[Optional[str]] = mapped_column(String(128), index=True, nullable=True)
    # relax | add | severity
    override_kind: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    # field_required | document_required
    rule_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_code: Mapped[str] = mapped_column(String(191), nullable=False, index=True)
    # blocking | warning (for add / severity)
    level: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    # active | revoked
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=text("'active'"), index=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    approved_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
