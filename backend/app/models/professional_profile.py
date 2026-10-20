"""Schema for professional-profile facts that are not employment rows.

Catalog and mapping rows are platform reference data. Constraint, preference,
and availability rows belong to one candidate. Nothing here stores calculated
experience.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base
from .mixins import TimestampMixin

PLATFORM_SCOPE = ""


class ProfessionalCatalogCode(Base, TimestampMixin):
    __tablename__ = "professional_catalog_codes"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "vocabulary",
            "code",
            name="uq_professional_catalog_codes_scope",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, default=PLATFORM_SCOPE, index=True)
    vocabulary: Mapped[str] = mapped_column(String(64), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)


class ProfessionalCodeMapping(Base, TimestampMixin):
    __tablename__ = "professional_code_mappings"
    __table_args__ = (
        UniqueConstraint(
            "source_vocabulary",
            "source_code",
            "target_vocabulary",
            name="uq_professional_code_mappings_source",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    source_vocabulary: Mapped[str] = mapped_column(String(64), nullable=False)
    source_code: Mapped[str] = mapped_column(String(64), nullable=False)
    target_vocabulary: Mapped[str] = mapped_column(String(64), nullable=False)
    target_code: Mapped[str] = mapped_column(String(64), nullable=False)


class CandidateProfessionalConstraint(Base, TimestampMixin):
    __tablename__ = "candidate_professional_constraints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(32), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    effect: Mapped[str] = mapped_column(String(16), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class CandidateDeclaredFact(Base, TimestampMixin):
    """Declared professional answer from intake. Not an employment and not a calculated tenure."""

    __tablename__ = "candidate_declared_facts"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "candidate_id",
            "subject",
            "code",
            name="uq_candidate_declared_facts_scope",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(32), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    years: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    presence: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    provenance: Mapped[str] = mapped_column(String(32), nullable=False, default="candidate_intake")


class CandidateAvailability(Base, TimestampMixin):
    __tablename__ = "candidate_availability"
    __table_args__ = (
        UniqueConstraint("tenant_id", "candidate_id", name="uq_candidate_availability_candidate"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    available_from: Mapped[date | None] = mapped_column(Date, nullable=True)


class CandidatePreferenceChoice(Base, TimestampMixin):
    __tablename__ = "candidate_preference_choices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(32), nullable=False)
    kind: Mapped[str | None] = mapped_column(String(16), nullable=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)


class CandidateCompensationExpectation(Base, TimestampMixin):
    __tablename__ = "candidate_compensation_expectations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "candidate_id", name="uq_candidate_compensation_candidate"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    period: Mapped[str | None] = mapped_column(String(32), nullable=True)


__all__ = [
    "CandidateAvailability",
    "CandidateDeclaredFact",
    "CandidateCompensationExpectation",
    "CandidatePreferenceChoice",
    "CandidateProfessionalConstraint",
    "PLATFORM_SCOPE",
    "ProfessionalCatalogCode",
    "ProfessionalCodeMapping",
]
