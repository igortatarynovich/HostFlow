"""Materialised compliance snapshot per employee (deterministic store; complements derived queues)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from .mixins import TimestampMixin

JSONType = SQLiteJSON().with_variant(JSONB, "postgresql")

if TYPE_CHECKING:
    from backend.app.models.workforce_employee import WorkforceEmployee


class WorkforceComplianceState(Base, TimestampMixin):
    __tablename__ = "workforce_compliance_states"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workforce_employees.id", ondelete="CASCADE"), index=True, nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="not_evaluated", server_default="not_evaluated"
    )
    missing_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    expired_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    expiring_soon_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    high_risk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    cannot_work: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    last_evaluated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reasons: Mapped[Optional[Any]] = mapped_column(JSONType, nullable=True)

    employee: Mapped[WorkforceEmployee] = relationship(
        "WorkforceEmployee",
        foreign_keys=[employee_id],
        back_populates="compliance_state",
    )
