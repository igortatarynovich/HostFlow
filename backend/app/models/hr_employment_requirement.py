"""Pre-employment requirement instance for one Employment.

Applicability and resolution are separate columns. The row is
``pre_employment_requirements.v1``. It is not a candidate evaluation
status and it is not an onboarding task.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from .mixins import TimestampMixin

APPLICABILITY_APPLICABLE = "applicable"
APPLICABILITY_NOT_APPLICABLE = "not_applicable"

RESOLUTION_UNRESOLVED = "unresolved"
RESOLUTION_SATISFIED = "satisfied"
RESOLUTION_WAIVED = "waived"
RESOLUTION_BLOCKING = "blocking"


class HrEmploymentRequirement(Base, TimestampMixin):
    __tablename__ = "hr_employment_requirements"
    __table_args__ = (
        UniqueConstraint(
            "employment_id",
            "definition_key",
            name="uq_hr_employment_requirements_employment_definition",
        ),
        CheckConstraint(
            "applicability IN ('applicable', 'not_applicable')",
            name="ck_hr_employment_requirements_applicability",
        ),
        CheckConstraint(
            "(applicability = 'not_applicable' AND resolution IS NULL) "
            "OR (applicability = 'applicable' AND resolution IN "
            "('unresolved', 'satisfied', 'waived', 'blocking'))",
            name="ck_hr_employment_requirements_resolution",
        ),
        CheckConstraint(
            "(resolution = 'satisfied' AND ("
            "satisfaction_evidence_id IS NOT NULL OR satisfaction_document_id IS NOT NULL)) "
            "OR ((resolution IS NULL OR resolution <> 'satisfied') AND "
            "satisfaction_evidence_id IS NULL AND satisfaction_document_id IS NULL)",
            name="ck_hr_employment_requirements_satisfaction",
        ),
        CheckConstraint(
            "(resolution = 'waived' AND waiver_actor_id IS NOT NULL AND waiver_at IS NOT NULL "
            "AND waiver_reason IS NOT NULL AND length(waiver_reason) > 0) "
            "OR ((resolution IS NULL OR resolution <> 'waived') AND waiver_actor_id IS NULL "
            "AND waiver_at IS NULL AND waiver_reason IS NULL)",
            name="ck_hr_employment_requirements_waiver",
        ),
        CheckConstraint(
            "(resolution = 'blocking' AND blocking_reason IS NOT NULL AND length(blocking_reason) > 0) "
            "OR ((resolution IS NULL OR resolution <> 'blocking') AND blocking_reason IS NULL)",
            name="ck_hr_employment_requirements_blocking",
        ),
        {"extend_existing": True},
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False
    )
    employment_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("hr_employments.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    definition_key: Mapped[str] = mapped_column(String(191), nullable=False)
    policy_id: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    applicability: Mapped[str] = mapped_column(String(16), nullable=False)
    applicability_basis: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution: Mapped[str | None] = mapped_column(String(16), nullable=True)
    satisfaction_evidence_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("candidate_evidence.id", ondelete="RESTRICT"),
        nullable=True,
    )
    satisfaction_document_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="RESTRICT"),
        nullable=True,
    )
    waiver_actor_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    waiver_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    waiver_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    blocking_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
