"""Social / ZUS insurance materialisation profile (legal layer; distinct from payroll ZUS registration row)."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from .mixins import TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.workforce_employee import WorkforceEmployee


class WorkforceInsuranceProfile(Base, TimestampMixin):
    __tablename__ = "workforce_insurance_profiles"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workforce_employees.id", ondelete="CASCADE"), index=True, nullable=False
    )

    zus_title_code: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    social_insurance: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    health_insurance: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    sickness_insurance: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    accident_insurance: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    zus_registration_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    registered_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    deregistered_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", server_default="draft")

    employee: Mapped["WorkforceEmployee"] = relationship(
        "WorkforceEmployee",
        foreign_keys=[employee_id],
        back_populates="insurance_profile",
    )
