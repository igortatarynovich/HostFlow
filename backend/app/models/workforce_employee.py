from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from .mixins import TimestampMixin

JSONType = SQLiteJSON().with_variant(JSONB, "postgresql")


class WorkforceEmployee(Base, TimestampMixin):
    """
    Employed person in the HR workspace (separate data plane from recruitment candidates).
    `candidate_id` + `candidate_snapshot` preserve the recruitment→HR evolution without duplicating identity.
    """

    __tablename__ = "workforce_employees"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    own_company_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    candidate_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("candidates.id", ondelete="SET NULL"), nullable=True, index=True
    )
    company_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    vacancy_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("vacancies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    recruiter_user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    display_name: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="onboarding", server_default="onboarding"
    )

    hire_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    probation_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    termination_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    handoff_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    handoff_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    candidate_snapshot: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True)
