from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional
from uuid import uuid4

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base
from .mixins import TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.workforce_compliance_state import WorkforceComplianceState
    from backend.app.models.workforce_hr_document_context import WorkforceHrDocumentContext
    from backend.app.models.workforce_insurance_profile import WorkforceInsuranceProfile
    from backend.app.models.workforce_tax_profile import WorkforceTaxProfile
    from backend.app.models.workforce_work_eligibility_profile import WorkforceWorkEligibilityProfile
    from backend.app.models.workforce_zus_workspace_task import WorkforceZusWorkspaceTask

JSONType = SQLiteJSON().with_variant(JSONB, "postgresql")


class WorkforceEmployee(Base, TimestampMixin):
    """HR context for a person. Relationship facts live on Employment."""

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

    display_name: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="onboarding", server_default="onboarding"
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True)

    tax_profile: Mapped[Optional["WorkforceTaxProfile"]] = relationship(
        "WorkforceTaxProfile",
        back_populates="employee",
        uselist=False,
    )
    insurance_profile: Mapped[Optional["WorkforceInsuranceProfile"]] = relationship(
        "WorkforceInsuranceProfile",
        back_populates="employee",
        uselist=False,
    )
    compliance_state: Mapped[Optional["WorkforceComplianceState"]] = relationship(
        "WorkforceComplianceState",
        back_populates="employee",
        uselist=False,
    )
    hr_document_contexts: Mapped[list["WorkforceHrDocumentContext"]] = relationship(
        "WorkforceHrDocumentContext",
        back_populates="employee",
        cascade="all, delete-orphan",
    )
    zus_workspace_tasks: Mapped[list["WorkforceZusWorkspaceTask"]] = relationship(
        "WorkforceZusWorkspaceTask",
        back_populates="employee",
        cascade="all, delete-orphan",
        foreign_keys="WorkforceZusWorkspaceTask.employee_id",
    )
    work_eligibility_profile: Mapped[Optional["WorkforceWorkEligibilityProfile"]] = relationship(
        "WorkforceWorkEligibilityProfile",
        back_populates="employee",
        uselist=False,
        foreign_keys="WorkforceWorkEligibilityProfile.employee_id",
    )
