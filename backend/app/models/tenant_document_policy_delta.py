"""Persisted R5 tenant overlay delta (RPM-2).

JSONB is the R5 delta contract only. reason and actor are sibling metadata.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base
from .mixins import TimestampMixin

JSONType = SQLiteJSON().with_variant(JSONB, "postgresql")


class TenantDocumentPolicyDelta(TimestampMixin, Base):
    """One current R5 tenant_delta per tenant."""

    __tablename__ = "tenant_document_policy_deltas"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    tenant_delta: Mapped[dict[str, Any]] = mapped_column(
        JSONType, nullable=False, default=dict
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    updated_by_user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )


__all__ = ["TenantDocumentPolicyDelta"]
