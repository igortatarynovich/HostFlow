"""Canonical Employment: one labour relationship of an Employee context.

``workforce_employments`` remains the contract card and points here.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from .mixins import TimestampMixin

JSONType = SQLiteJSON().with_variant(JSONB, "postgresql")


class Employment(Base, TimestampMixin):
    __tablename__ = "hr_employments"
    __table_args__ = (
        CheckConstraint(
            "state IN ('preparing', 'active', 'ended')",
            name="ck_hr_employments_state",
        ),
        {"extend_existing": True},
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    employee_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workforce_employees.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="preparing")
    client_company_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    started_on: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    ended_on: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    vacancy_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("vacancies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    recruiter_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    handoff_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    handoff_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    handoff_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    candidate_snapshot: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True)
