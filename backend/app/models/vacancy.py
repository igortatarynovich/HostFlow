from __future__ import annotations


import logging
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


logger = logging.getLogger(__name__)


class EmploymentType(str, Enum):
    full_time = "full_time"
    part_time = "part_time"
    b2b = "b2b"


class VacancyStatus(str, Enum):
    """Canonical vacancy lifecycle states.

    See `docs/specs/vacancy-statuses.md` for full semantics:

    - `open`        — accepting candidates (default for new rows).
    - `on_hold`     — temporarily paused; not closed, but not actively
                      sourced. (`paused` is a legacy alias normalized to
                      this value at the API layer.)
    - `closed`      — pipeline finished without a hire (client cancelled,
                      priorities shifted).
    - `filled`      — closed via successful hire(s). Reserved for the
                      future auto-flip on `Candidate.employed`; today set
                      manually only.
    - `cancelled`   — vacancy was cancelled (created by mistake, or
                      cancelled by the client before work started).

    DB column `vacancies.status` remains free-string TEXT (see migration
    `202512090002_vacancies_status_text.py`) — validation lives in the
    Pydantic layer via `normalize_vacancy_status`.

    `is_archived` is an orthogonal boolean (soft-delete from default
    lists) and can co-exist with any non-`open` status.
    """

    open = "open"
    on_hold = "on_hold"
    closed = "closed"
    filled = "filled"
    cancelled = "cancelled"


# Legacy aliases — accepted as INPUT, normalized to canonical on write.
# Kept here so writers, readers and analytics share one source of truth.
_VACANCY_STATUS_ALIASES: dict[str, str] = {
    "paused": VacancyStatus.on_hold.value,
}

# Statuses that historically existed but are no longer canonical. They are
# preserved here so the normalizer can emit a single warning the first time
# they are encountered (helps spot dirty rows during the Phase 2.6.D
# migration window). After the alembic backfill they should disappear.
_VACANCY_STATUS_LEGACY_PASSTHROUGH: frozenset[str] = frozenset({
    # `archived` historically doubled as a status — `VacancyService.patch`
    # converts it to `is_archived=True`. We accept it as INPUT but the
    # alembic migration in Stage B rewrites stored rows to `closed` +
    # `is_archived=true`.
    "archived",
})


def normalize_vacancy_status(raw: object | None) -> str:
    """Normalize an arbitrary input value to a canonical `VacancyStatus`.

    Rules (deterministic, idempotent):

    1. `None`/empty/whitespace            → `"open"` (default for new rows).
    2. Already canonical                   → returned as-is (lowercased).
    3. Known alias (`paused`)              → mapped to canonical.
    4. Legacy passthrough (`archived`)     → returned unchanged so the
       service layer can keep its existing translation to `is_archived`.
       Will be cleaned up by the Stage B alembic migration.
    5. Unknown value                       → clamped to `"open"` and a
       single warning is logged (so dirty data is observable in tests
       and prod, but does not 422 a request).

    The function is **never** rejecting — it always returns a string.
    Strict transition validation is a separate concern (Stage D in
    `docs/specs/vacancy-statuses.md`) and lives in `vacancies/rules.py`.
    """

    if raw is None:
        return VacancyStatus.open.value
    # `str(SomeEnum.member)` historically returned `"SomeEnum.member"`
    # rather than the underlying value. Normalize defensively before the
    # lowercase/strip step so callers can pass an enum member, a `str`,
    # or any custom subclass without surprises.
    if isinstance(raw, VacancyStatus):
        return raw.value
    text_val = str(raw).strip().lower()
    if not text_val:
        return VacancyStatus.open.value
    if text_val in {member.value for member in VacancyStatus}:
        return text_val
    aliased = _VACANCY_STATUS_ALIASES.get(text_val)
    if aliased is not None:
        return aliased
    if text_val in _VACANCY_STATUS_LEGACY_PASSTHROUGH:
        return text_val
    logger.warning(
        "vacancy.status.unknown_value_clamped_to_open",
        extra={"raw_value": text_val},
    )
    return VacancyStatus.open.value


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
    # When ``order_line_id`` is set, MUST mirror SalesOrderLine.quantity_needed (ADR-032).
    headcount_target: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Sales Order Line (1:1). Null = freeform vacancy.
    order_line_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("sales_order_lines.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True,
        comment="ADR-032: Vacancy executes exactly one Order Line when set",
    )

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
    pe_process_profile_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("pe_process_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Process Engine profile — canonical process source for this vacancy (P3)",
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
