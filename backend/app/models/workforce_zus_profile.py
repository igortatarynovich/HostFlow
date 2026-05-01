from __future__ import annotations

from datetime import date
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from .mixins import TimestampMixin

JSONType = SQLiteJSON().with_variant(JSONB, "postgresql")


class WorkforceZusProfile(Base, TimestampMixin):
    """ZUS registration tracking (forms, coverage flags, responsible party) — not a payroll calculator."""

    __tablename__ = "workforce_zus_profiles"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workforce_employees.id", ondelete="CASCADE"), index=True, nullable=False
    )
    registration_status: Mapped[str] = mapped_column(String(64), nullable=False, default="not_submitted")
    submitted_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    employment_basis: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    responsible_party: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    insurance_coverage: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True)
    forms: Mapped[Optional[list[Any]]] = mapped_column(JSONType, nullable=True)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True)
