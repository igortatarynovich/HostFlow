"""Tenant-scoped R5 document-policy overlay (RPM-2).

One current overlay per tenant. Delta must pass validate_tenant_overlay_delta.
Not P3B TenantRequirementOverride. Not document_policies. Not ruleset JSON.
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from backend.app.models.mixins import TimestampMixin

JSONType = SQLiteJSON().with_variant(JSONB, "postgresql")


class DocumentPolicyTenantOverlay(TimestampMixin, Base):
    """Persisted R5 tenant_delta for requirement-policy operator writes."""

    __tablename__ = "document_policy_tenant_overlays"

    tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        primary_key=True,
    )
    revision: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1"), default=1
    )
    delta: Mapped[dict[str, Any]] = mapped_column(
        JSONType, nullable=False, default=dict, server_default=text("'{}'")
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    updated_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
