"""Read-only Recruitment Overview: Lead, Candidate, and Application grains stay separate.

Date bounds use the same ``from`` / ``to`` strings as the rest of analytics
(``_parse_dt`` in the route). This module does not cohort everything on
``Candidate.created_at``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import and_, distinct, exists, func, nullsfirst, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.models.lead import Lead
from backend.app.models.recruitment_application import RecruitmentApplication
from backend.app.models.user import User
from backend.app.models.vacancy import Vacancy
from backend.app.modules.intake_routing.meta_bridge import LEAD_TARGET_CANDIDATE
from backend.app.services.recruitment_application_lifecycle import normalize_application_status

NEW_RETURNING_RULE = "candidate_created_at_strictly_before_lead_created_at_is_returning"

# Finalized attachment statuses are not required: any linked recruitment lead
# without an application row is reported. ``duplicate_review`` is excluded
# because the creation contract forbids an application until a decision.
_GAP_EXCLUDED_LEAD_STATUS = "duplicate_review"

LIMITATION_CODES: tuple[str, ...] = (
    "application_status_is_current_snapshot_of_started_cohort",
    "no_per_application_stage_funnel",
    "candidate_stage_remains_person_projection",
    "company_filter_excludes_pool_applications_without_vacancy",
    "acquisition_new_returning_compares_candidate_created_at_to_lead_created_at",
    "linked_recruitment_leads_without_application_is_not_reconstructed_intent",
    "unresolved_candidate_link_is_not_new_or_returning",
)


class RecruitmentOverviewPeriod(BaseModel):
    from_: Optional[str] = Field(None, alias="from")
    to: Optional[str] = None

    model_config = {"populate_by_name": True}


class AcquisitionSourceRow(BaseModel):
    source: str
    leads: int
    unique_candidates_linked: int
    leads_with_application: int


class AcquisitionVacancyRow(BaseModel):
    vacancy_id: Optional[str] = None
    vacancy_name: Optional[str] = None
    leads: int
    unique_candidates_linked: int
    leads_with_application: int


class AcquisitionSection(BaseModel):
    time_basis: str = "lead.created_at"
    new_returning_rule: str = NEW_RETURNING_RULE
    leads_received: int
    unique_candidates_linked: int
    new_candidates: int
    returning_candidates: int
    leads_with_application: int
    leads_duplicated: int
    leads_in_duplicate_review: int
    by_source: list[AcquisitionSourceRow]
    by_vacancy: list[AcquisitionVacancyRow]


class ApplicationStatusRow(BaseModel):
    status: str
    count: int


class RecruitmentVacancyRow(BaseModel):
    vacancy_id: Optional[str] = None
    vacancy_name: Optional[str] = None
    applications: int


class RecruitmentRecruiterRow(BaseModel):
    recruiter_id: Optional[str] = None
    recruiter_name: Optional[str] = None
    applications: int


class RecruitmentSection(BaseModel):
    time_basis: str = "recruitment_application.applied_at"
    applications_started: int
    by_current_status: list[ApplicationStatusRow]
    by_vacancy: list[RecruitmentVacancyRow]
    by_recruiter: list[RecruitmentRecruiterRow]


class PeopleSection(BaseModel):
    time_basis: str = "candidate.created_at"
    new_candidates: int


class HistoricalGap(BaseModel):
    linked_recruitment_leads_without_application: int


class RecruitmentOverviewResponse(BaseModel):
    period: RecruitmentOverviewPeriod
    acquisition: AcquisitionSection
    recruitment: RecruitmentSection
    people: PeopleSection
    historical_gap: HistoricalGap
    limitations: list[str]


def _as_naive_utc(value: Optional[datetime]) -> Optional[datetime]:
    """``candidates.created_at`` is timestamp without time zone, stored as UTC."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _candidate_created_utc():
    # Interpret the naive column as UTC so it can be compared with timestamptz.
    return func.timezone("UTC", Candidate.created_at)


def _lead_filters(
    *,
    tenant_id: str,
    date_from: Optional[datetime],
    date_to: Optional[datetime],
    company_id: Optional[str],
    vacancy_id: Optional[str],
) -> list:
    clauses = [
        Lead.tenant_id == tenant_id,
        Lead.lead_target_type == LEAD_TARGET_CANDIDATE,
    ]
    if date_from is not None:
        clauses.append(Lead.created_at >= date_from)
    if date_to is not None:
        clauses.append(Lead.created_at <= date_to)
    if company_id:
        clauses.append(Lead.company_id == company_id)
    if vacancy_id:
        clauses.append(Lead.vacancy_id == vacancy_id)
    return clauses


def _application_exists(tenant_id: str):
    return exists(
        select(RecruitmentApplication.id).where(
            RecruitmentApplication.tenant_id == tenant_id,
            RecruitmentApplication.lead_id == Lead.id,
        )
    )


def _application_filters(
    *,
    tenant_id: str,
    date_from: Optional[datetime],
    date_to: Optional[datetime],
    vacancy_id: Optional[str],
) -> list:
    clauses = [RecruitmentApplication.tenant_id == tenant_id]
    if date_from is not None:
        clauses.append(RecruitmentApplication.applied_at >= date_from)
    if date_to is not None:
        clauses.append(RecruitmentApplication.applied_at <= date_to)
    if vacancy_id:
        clauses.append(RecruitmentApplication.vacancy_id == vacancy_id)
    return clauses


async def _acquisition(
    db: AsyncSession,
    *,
    tenant_id: str,
    date_from: Optional[datetime],
    date_to: Optional[datetime],
    company_id: Optional[str],
    vacancy_id: Optional[str],
) -> AcquisitionSection:
    lead_where = _lead_filters(
        tenant_id=tenant_id,
        date_from=date_from,
        date_to=date_to,
        company_id=company_id,
        vacancy_id=vacancy_id,
    )
    has_app = _application_exists(tenant_id)
    linked = and_(Lead.candidate_id.is_not(None), Candidate.id.is_not(None))
    candidate_at = _candidate_created_utc()
    totals = (
        await db.execute(
            select(
                func.count(Lead.id),
                func.count(distinct(Lead.candidate_id)),
                func.count(Lead.id).filter(and_(linked, candidate_at >= Lead.created_at)),
                func.count(Lead.id).filter(and_(linked, candidate_at < Lead.created_at)),
                func.count(distinct(Lead.id)).filter(has_app),
                func.count(Lead.id).filter(Lead.status == "duplicated"),
                func.count(Lead.id).filter(Lead.status == "duplicate_review"),
            )
            .select_from(Lead)
            .outerjoin(
                Candidate,
                and_(Candidate.id == Lead.candidate_id, Candidate.tenant_id == Lead.tenant_id),
            )
            .where(*lead_where)
        )
    ).one()

    source_rows = (
        await db.execute(
            select(
                Lead.source,
                func.count(Lead.id),
                func.count(distinct(Lead.candidate_id)),
                func.count(distinct(Lead.id)).filter(has_app),
            )
            .where(*lead_where)
            .group_by(Lead.source)
            .order_by(func.count(Lead.id).desc(), Lead.source.asc())
        )
    ).all()

    vacancy_rows = (
        await db.execute(
            select(
                Lead.vacancy_id,
                Vacancy.title,
                func.count(Lead.id),
                func.count(distinct(Lead.candidate_id)),
                func.count(distinct(Lead.id)).filter(has_app),
            )
            .select_from(Lead)
            .outerjoin(
                Vacancy,
                and_(Vacancy.id == Lead.vacancy_id, Vacancy.tenant_id == Lead.tenant_id),
            )
            .where(*lead_where)
            .group_by(Lead.vacancy_id, Vacancy.title)
            .order_by(func.count(Lead.id).desc(), nullsfirst(Lead.vacancy_id.asc()))
        )
    ).all()

    return AcquisitionSection(
        leads_received=int(totals[0] or 0),
        unique_candidates_linked=int(totals[1] or 0),
        new_candidates=int(totals[2] or 0),
        returning_candidates=int(totals[3] or 0),
        leads_with_application=int(totals[4] or 0),
        leads_duplicated=int(totals[5] or 0),
        leads_in_duplicate_review=int(totals[6] or 0),
        by_source=[
            AcquisitionSourceRow(
                source=str(source or ""),
                leads=int(leads or 0),
                unique_candidates_linked=int(unique or 0),
                leads_with_application=int(with_app or 0),
            )
            for source, leads, unique, with_app in source_rows
        ],
        by_vacancy=[
            AcquisitionVacancyRow(
                vacancy_id=str(vid) if vid else None,
                vacancy_name=str(title) if title else None,
                leads=int(leads or 0),
                unique_candidates_linked=int(unique or 0),
                leads_with_application=int(with_app or 0),
            )
            for vid, title, leads, unique, with_app in vacancy_rows
        ],
    )


async def _recruitment(
    db: AsyncSession,
    *,
    tenant_id: str,
    date_from: Optional[datetime],
    date_to: Optional[datetime],
    company_id: Optional[str],
    vacancy_id: Optional[str],
) -> RecruitmentSection:
    filters = _application_filters(
        tenant_id=tenant_id,
        date_from=date_from,
        date_to=date_to,
        vacancy_id=vacancy_id,
    )

    def _base(columns):
        stmt = select(*columns).select_from(RecruitmentApplication)
        if company_id:
            stmt = stmt.join(
                Vacancy,
                and_(
                    Vacancy.id == RecruitmentApplication.vacancy_id,
                    Vacancy.tenant_id == RecruitmentApplication.tenant_id,
                ),
            ).where(Vacancy.company_id == company_id)
        return stmt.where(*filters)

    status_rows = (
        await db.execute(
            _base((RecruitmentApplication.status, func.count(RecruitmentApplication.id)))
            .group_by(RecruitmentApplication.status)
            .order_by(func.count(RecruitmentApplication.id).desc(), RecruitmentApplication.status.asc())
        )
    ).all()
    merged: dict[str, int] = {}
    for raw_status, count in status_rows:
        key = normalize_application_status(str(raw_status or ""))
        merged[key] = merged.get(key, 0) + int(count or 0)
    by_status = [
        ApplicationStatusRow(status=status, count=count)
        for status, count in sorted(merged.items(), key=lambda item: (-item[1], item[0]))
    ]

    if company_id:
        vacancy_stmt = (
            select(
                RecruitmentApplication.vacancy_id,
                Vacancy.title,
                func.count(RecruitmentApplication.id),
            )
            .select_from(RecruitmentApplication)
            .join(
                Vacancy,
                and_(
                    Vacancy.id == RecruitmentApplication.vacancy_id,
                    Vacancy.tenant_id == RecruitmentApplication.tenant_id,
                ),
            )
            .where(*filters, Vacancy.company_id == company_id)
            .group_by(RecruitmentApplication.vacancy_id, Vacancy.title)
            .order_by(
                func.count(RecruitmentApplication.id).desc(),
                nullsfirst(RecruitmentApplication.vacancy_id.asc()),
            )
        )
        vacancy_rows = (await db.execute(vacancy_stmt)).all()
        by_vacancy = [
            RecruitmentVacancyRow(
                vacancy_id=str(vid) if vid else None,
                vacancy_name=str(title) if title else None,
                applications=int(count or 0),
            )
            for vid, title, count in vacancy_rows
        ]
    else:
        vacancy_rows = (
            await db.execute(
                select(
                    RecruitmentApplication.vacancy_id,
                    Vacancy.title,
                    func.count(RecruitmentApplication.id),
                )
                .select_from(RecruitmentApplication)
                .outerjoin(
                    Vacancy,
                    and_(
                        Vacancy.id == RecruitmentApplication.vacancy_id,
                        Vacancy.tenant_id == RecruitmentApplication.tenant_id,
                    ),
                )
                .where(*filters)
                .group_by(RecruitmentApplication.vacancy_id, Vacancy.title)
                .order_by(
                    func.count(RecruitmentApplication.id).desc(),
                    nullsfirst(RecruitmentApplication.vacancy_id.asc()),
                )
            )
        ).all()
        by_vacancy = [
            RecruitmentVacancyRow(
                vacancy_id=str(vid) if vid else None,
                vacancy_name=str(title) if title else None,
                applications=int(count or 0),
            )
            for vid, title, count in vacancy_rows
        ]

    recruiter_rows = (
        await db.execute(
            _base((RecruitmentApplication.recruiter_id, User.full_name, func.count(RecruitmentApplication.id)))
            .outerjoin(User, User.id == RecruitmentApplication.recruiter_id)
            .group_by(RecruitmentApplication.recruiter_id, User.full_name)
            .order_by(
                func.count(RecruitmentApplication.id).desc(),
                nullsfirst(RecruitmentApplication.recruiter_id.asc()),
            )
        )
    ).all()

    return RecruitmentSection(
        applications_started=sum(row.count for row in by_status),
        by_current_status=by_status,
        by_vacancy=by_vacancy,
        by_recruiter=[
            RecruitmentRecruiterRow(
                recruiter_id=str(rid) if rid else None,
                recruiter_name=str(name) if name else None,
                applications=int(count or 0),
            )
            for rid, name, count in recruiter_rows
        ],
    )


async def _people_new_candidates(
    db: AsyncSession,
    *,
    tenant_id: str,
    date_from: Optional[datetime],
    date_to: Optional[datetime],
    company_id: Optional[str],
    vacancy_id: Optional[str],
) -> int:
    clauses = [
        Candidate.tenant_id == tenant_id,
        Candidate.deleted_at.is_(None),
    ]
    naive_from = _as_naive_utc(date_from)
    naive_to = _as_naive_utc(date_to)
    if naive_from is not None:
        clauses.append(Candidate.created_at >= naive_from)
    if naive_to is not None:
        clauses.append(Candidate.created_at <= naive_to)
    if company_id:
        clauses.append(Candidate.company_id == company_id)
    if vacancy_id:
        inbound = exists(
            select(Lead.id).where(
                Lead.tenant_id == tenant_id,
                Lead.lead_target_type == LEAD_TARGET_CANDIDATE,
                Lead.candidate_id == Candidate.id,
                Lead.vacancy_id == vacancy_id,
            )
        )
        participation = exists(
            select(RecruitmentApplication.id).where(
                RecruitmentApplication.tenant_id == tenant_id,
                RecruitmentApplication.candidate_id == Candidate.id,
                RecruitmentApplication.vacancy_id == vacancy_id,
            )
        )
        clauses.append(inbound | participation)
    count = (
        await db.execute(select(func.count(Candidate.id)).where(*clauses))
    ).scalar_one()
    return int(count or 0)


async def _historical_gap(
    db: AsyncSession,
    *,
    tenant_id: str,
    date_from: Optional[datetime],
    date_to: Optional[datetime],
    company_id: Optional[str],
    vacancy_id: Optional[str],
) -> int:
    clauses = _lead_filters(
        tenant_id=tenant_id,
        date_from=date_from,
        date_to=date_to,
        company_id=company_id,
        vacancy_id=vacancy_id,
    )
    clauses.append(Lead.candidate_id.is_not(None))
    clauses.append(Lead.status != _GAP_EXCLUDED_LEAD_STATUS)
    clauses.append(~_application_exists(tenant_id))
    count = (await db.execute(select(func.count(Lead.id)).where(*clauses))).scalar_one()
    return int(count or 0)


async def build_recruitment_overview(
    db: AsyncSession,
    *,
    tenant_id: str,
    period_from: Optional[str],
    period_to: Optional[str],
    date_from: Optional[datetime],
    date_to: Optional[datetime],
    company_id: Optional[str] = None,
    vacancy_id: Optional[str] = None,
) -> RecruitmentOverviewResponse:
    company = str(company_id).strip() if company_id else None
    vacancy = str(vacancy_id).strip() if vacancy_id else None
    acquisition = await _acquisition(
        db,
        tenant_id=tenant_id,
        date_from=date_from,
        date_to=date_to,
        company_id=company,
        vacancy_id=vacancy,
    )
    recruitment = await _recruitment(
        db,
        tenant_id=tenant_id,
        date_from=date_from,
        date_to=date_to,
        company_id=company,
        vacancy_id=vacancy,
    )
    people_count = await _people_new_candidates(
        db,
        tenant_id=tenant_id,
        date_from=date_from,
        date_to=date_to,
        company_id=company,
        vacancy_id=vacancy,
    )
    gap = await _historical_gap(
        db,
        tenant_id=tenant_id,
        date_from=date_from,
        date_to=date_to,
        company_id=company,
        vacancy_id=vacancy,
    )
    return RecruitmentOverviewResponse(
        period=RecruitmentOverviewPeriod.model_validate({"from": period_from, "to": period_to}),
        acquisition=acquisition,
        recruitment=recruitment,
        people=PeopleSection(new_candidates=people_count),
        historical_gap=HistoricalGap(linked_recruitment_leads_without_application=gap),
        limitations=list(LIMITATION_CODES),
    )
