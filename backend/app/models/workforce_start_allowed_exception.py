"""Typed start_allowed exception resolutions (PEM-1 allowlist only)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from .mixins import TimestampMixin

JSONType = SQLiteJSON().with_variant(JSONB, "postgresql")


class WorkforceStartAllowedException(Base, TimestampMixin):
    """Audited allowlisted exception for employment_start_allowed.v1."""

    __tablename__ = "workforce_start_allowed_exceptions"
    __table_args__ = ({"extend_existing": True},)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workforce_employees.id", ondelete="CASCADE"), index=True, nullable=False
    )
    handoff_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    requirement_code: Mapped[str] = mapped_column(String(128), nullable=False)
    exception_code: Mapped[str] = mapped_column(String(128), nullable=False)
    facts_json: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False, default=dict)
    evidence_refs_json: Mapped[Optional[list[Any]]] = mapped_column(JSONType, nullable=True)

    actor_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    revoke_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
