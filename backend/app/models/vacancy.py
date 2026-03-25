from __future__ import annotations


from typing import Optional, TYPE_CHECKING, List
from uuid import uuid4
from enum import Enum

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base

from .mixins import TimestampMixin

if TYPE_CHECKING:
    from .company import Company
    from .vacancy_recruiter import VacancyRecruiter



class EmploymentType(str, Enum):
    full_time = "full_time"
    part_time = "part_time"
    b2b = "b2b"


class Vacancy(Base, TimestampMixin):
    __tablename__ = "vacancies"

    # identifiers
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    # scope: which own-company within the tenant owns this vacancy
    own_company_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("own_companies.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    # relations
    company_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("companies.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # manager (UUID str of user)
    manager: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)

    # details
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    employment_type: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=EmploymentType.full_time.value,
        server_default=text("'full_time'"),
    )

    # salary/meta (kept for compatibility)
    salary_from: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    salary_to: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="open")

    # Planned number of positions to fill (recruitment container target); optional.
    headcount_target: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # free-form JSON stored as string for now
    extra: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Привязка к профилю кандидата
    candidate_profile_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("candidate_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Профиль кандидата для этой вакансии",
    )
    funnel_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("funnels.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Шаблон документов для авто-применения при назначении кандидата на вакансию
    required_documents_template_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("document_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="При назначении кандидата на вакансию применяется этот шаблон документов",
    )

    # state flags (optional but helpful)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("1")
    )
    is_archived: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0")
    )

    # ORM relationship to Company
    company: Mapped["Company"] = relationship(
        "Company",
        back_populates="vacancies",
        foreign_keys=[company_id],
        lazy="selectin",
    )
    recruiter_links: Mapped[List["VacancyRecruiter"]] = relationship(
        "VacancyRecruiter",
        back_populates="vacancy",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
