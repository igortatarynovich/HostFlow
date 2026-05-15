"""Work eligibility (legal stay / work permit) — gates ZUS registration for transport HR."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any, Optional
from uuid import uuid4

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from .mixins import TimestampMixin

JSONType = SQLiteJSON().with_variant(JSONB, "postgresql")

if TYPE_CHECKING:
    from backend.app.models.workforce_employee import WorkforceEmployee


class WorkforceWorkEligibilityProfile(Base, TimestampMixin):
    __tablename__ = "workforce_work_eligibility_profiles"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    employee_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workforce_employees.id", ondelete="CASCADE"), index=True, nullable=False
    )

    citizenship: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    residence_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    legal_stay_document_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    legal_stay_valid_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    requires_work_permit: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    work_permit_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    work_permit_submission_method: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    work_permit_application_status: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    work_permit_submitted_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    work_permit_received_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    work_permit_valid_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    red_paper_required: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    red_paper_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    eligibility_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="not_evaluated", server_default="not_evaluated", index=True
    )
    position_category: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    work_country: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    employer_country: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    contract_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    meta: Mapped[Optional[Any]] = mapped_column(JSONType, nullable=True)

    employee: Mapped["WorkforceEmployee"] = relationship(
        "WorkforceEmployee",
        back_populates="work_eligibility_profile",
        foreign_keys=[employee_id],
    )


class WorkPermitSubmissionChannel(Base, TimestampMixin):
    """Reference rows: where / how to submit work permit applications (no tenant RLS)."""

    __tablename__ = "work_permit_submission_channels"
    __table_args__ = {"extend_existing": True}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    country: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    voivodeship: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    permit_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    submission_method: Mapped[str] = mapped_column(String(64), nullable=False)
    portal_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    office_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    required_forms: Mapped[Optional[Any]] = mapped_column(JSONType, nullable=True)
    expected_processing_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
