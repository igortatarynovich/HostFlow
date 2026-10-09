"""Read-only Recruitment Overview: Lead, Candidate, and Application grains stay separate.

Date bounds use the same ``from`` / ``to`` strings as the rest of analytics
(``_parse_dt`` in the route). This module does not cohort everything on
``Candidate.created_at``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import and_, cast, distinct, exists, func, nullsfirst, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.models.candidate_stage_history import CandidateStageHistory
from backend.app.models.contact_attempt import ContactAttempt
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
    "current_stage_snapshot_ignores_selected_date_range",
    "current_status_reason_snapshot_ignores_selected_date_range",
    "stage_history_omits_some_stage_writes",
    "stage_history_has_no_event_time_vacancy",
    "stage_transition_company_vacancy_filter_uses_current_candidate",
    "contact_attempt_has_no_event_time_vacancy",
    "contact_attempt_company_vacancy_filter_uses_current_candidate",
    "successful_contact_is_result_answered",
)

# ContactAttempt.result values accepted by the create API are
# no_answer, answered, wrong_number, unavailable. Only ``answered`` is a
# successful contact. interested / callback_requested are not in that enum.
SUCCESSFUL_CONTACT_RESULT = "answered"
SUCCESSFUL_CONTACT_RULE = "result_equals_answered"
COMPANY_REJECTION_STAGE = "rejected"
CANDIDATE_DECLINE_STAGE = "declined"
CURRENT_CANDIDATE_PROJECTION = "current_candidate_projection"
FILTER_NOT_REQUESTED = "not_requested"


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


class CurrentStageRow(BaseModel):
    stage: str
    candidates: int


class CurrentStages(BaseModel):
    semantics: str = "current_candidate_stage_snapshot"
    date_range_applied: bool = False
    company_basis: str = "candidate.company_id"
    vacancy_basis: str = "candidate.vacancy_id"
    total_candidates: int
    by_stage: list[CurrentStageRow]


class StageEnteredRow(BaseModel):
    stage: str
    count: int


class StageTransitionRow(BaseModel):
    from_stage: Optional[str] = None
    to_stage: str
    count: int


class StageTransitions(BaseModel):
    time_basis: str = "candidate_stage_history.at"
    company_attribution: str
    vacancy_attribution: str
    total: int
    entered_by_stage: list[StageEnteredRow]
    by_transition: list[StageTransitionRow]


class StagesSection(BaseModel):
    current: CurrentStages
    transitions: StageTransitions


class ContactResultRow(BaseModel):
    result: str
    attempts: int


class ContactChannelRow(BaseModel):
    channel: str
    attempts: int


class ContactRecruiterRow(BaseModel):
    recruiter_id: Optional[str] = None
    recruiter_name: Optional[str] = None
    attempts: int


class ContactsSection(BaseModel):
    time_basis: str = "contact_attempt.attempted_at"
    successful_contact_rule: str = SUCCESSFUL_CONTACT_RULE
    company_attribution: str
    vacancy_attribution: str
    attempts_total: int
    candidates_contacted: int
    successful_attempts: int
    by_result: list[ContactResultRow]
    by_channel: list[ContactChannelRow]
    by_recruiter: list[ContactRecruiterRow]


class ReasonCodeRow(BaseModel):
    reason: str
    candidates: int
    occurrences: int


class ReasonCategory(BaseModel):
    stage: str
    candidates: int
    candidates_without_reason: int
    by_reason: list[ReasonCodeRow]


class ReasonsSection(BaseModel):
    semantics: str = "current_candidate_status_reason_snapshot"
    date_range_applied: bool = False
    company_basis: str = "candidate.company_id"
    vacancy_basis: str = "candidate.vacancy_id"
    rejected: ReasonCategory
    declined: ReasonCategory


class HistoricalGap(BaseModel):
    linked_recruitment_leads_without_application: int


class RecruitmentOverviewResponse(BaseModel):
    period: RecruitmentOverviewPeriod
    acquisition: AcquisitionSection
    recruitment: RecruitmentSection
    people: PeopleSection
    stages: StagesSection
    contacts: ContactsSection
    reasons: ReasonsSection
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


def _context_attribution(company_id: Optional[str], vacancy_id: Optional[str]) -> str:
    if company_id or vacancy_id:
        return CURRENT_CANDIDATE_PROJECTION
    return FILTER_NOT_REQUESTED


def _live_candidate_clauses(
    *,
    tenant_id: str,
    company_id: Optional[str],
    vacancy_id: Optional[str],
) -> list:
    """Current Candidate projection. The selected date range is not applied."""
    clauses: list = [
        Candidate.tenant_id == tenant_id,
        Candidate.deleted_at.is_(None),
    ]
    if company_id:
        clauses.append(Candidate.company_id == company_id)
    if vacancy_id:
        clauses.append(Candidate.vacancy_id == vacancy_id)
    return clauses


async def _current_stages(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: Optional[str],
    vacancy_id: Optional[str],
) -> CurrentStages:
    clauses = _live_candidate_clauses(
        tenant_id=tenant_id,
        company_id=company_id,
        vacancy_id=vacancy_id,
    )
    total = int(
        (await db.execute(select(func.count(Candidate.id)).where(*clauses))).scalar_one() or 0
    )
    rows = (
        await db.execute(
            select(Candidate.stage, func.count(Candidate.id))
            .where(*clauses)
            .group_by(Candidate.stage)
            .order_by(func.count(Candidate.id).desc(), nullsfirst(Candidate.stage))
        )
    ).all()
    return CurrentStages(
        total_candidates=total,
        by_stage=[
            CurrentStageRow(stage=str(stage or ""), candidates=int(count or 0))
            for stage, count in rows
        ],
    )


async def _stage_transitions(
    db: AsyncSession,
    *,
    tenant_id: str,
    date_from: Optional[datetime],
    date_to: Optional[datetime],
    company_id: Optional[str],
    vacancy_id: Optional[str],
) -> StageTransitions:
    clauses = [
        CandidateStageHistory.tenant_id == tenant_id,
        Candidate.tenant_id == tenant_id,
    ]
    if date_from is not None:
        clauses.append(CandidateStageHistory.at >= date_from)
    if date_to is not None:
        clauses.append(CandidateStageHistory.at <= date_to)
    # History has no company or vacancy. Filters use the candidate's current
    # assignment and are labeled as a projection, not event-time truth.
    if company_id:
        clauses.append(Candidate.company_id == company_id)
    if vacancy_id:
        clauses.append(Candidate.vacancy_id == vacancy_id)
    joined = (
        select(CandidateStageHistory)
        .join(
            Candidate,
            and_(
                Candidate.id == CandidateStageHistory.candidate_id,
                Candidate.tenant_id == CandidateStageHistory.tenant_id,
            ),
        )
        .where(*clauses)
    )
    total = int(
        (
            await db.execute(select(func.count()).select_from(joined.subquery()))
        ).scalar_one()
        or 0
    )
    entered = (
        await db.execute(
            select(CandidateStageHistory.to_code, func.count())
            .select_from(CandidateStageHistory)
            .join(
                Candidate,
                and_(
                    Candidate.id == CandidateStageHistory.candidate_id,
                    Candidate.tenant_id == CandidateStageHistory.tenant_id,
                ),
            )
            .where(*clauses)
            .group_by(CandidateStageHistory.to_code)
            .order_by(func.count().desc(), CandidateStageHistory.to_code)
        )
    ).all()
    pairs = (
        await db.execute(
            select(
                CandidateStageHistory.from_code,
                CandidateStageHistory.to_code,
                func.count(),
            )
            .select_from(CandidateStageHistory)
            .join(
                Candidate,
                and_(
                    Candidate.id == CandidateStageHistory.candidate_id,
                    Candidate.tenant_id == CandidateStageHistory.tenant_id,
                ),
            )
            .where(*clauses)
            .group_by(CandidateStageHistory.from_code, CandidateStageHistory.to_code)
            .order_by(func.count().desc(), CandidateStageHistory.to_code)
        )
    ).all()
    attribution = _context_attribution(company_id, vacancy_id)
    return StageTransitions(
        company_attribution=attribution,
        vacancy_attribution=attribution,
        total=total,
        entered_by_stage=[
            StageEnteredRow(stage=str(stage), count=int(count or 0)) for stage, count in entered
        ],
        by_transition=[
            StageTransitionRow(
                from_stage=str(from_code) if from_code else None,
                to_stage=str(to_code),
                count=int(count or 0),
            )
            for from_code, to_code, count in pairs
        ],
    )


async def _contacts(
    db: AsyncSession,
    *,
    tenant_id: str,
    date_from: Optional[datetime],
    date_to: Optional[datetime],
    company_id: Optional[str],
    vacancy_id: Optional[str],
) -> ContactsSection:
    clauses = [Candidate.tenant_id == tenant_id]
    if date_from is not None:
        clauses.append(ContactAttempt.attempted_at >= date_from)
    if date_to is not None:
        clauses.append(ContactAttempt.attempted_at <= date_to)
    if company_id:
        clauses.append(Candidate.company_id == company_id)
    if vacancy_id:
        clauses.append(Candidate.vacancy_id == vacancy_id)
    base = (
        select(ContactAttempt.id)
        .join(Candidate, Candidate.id == ContactAttempt.candidate_id)
        .where(*clauses)
    )
    attempts_total = int(
        (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one() or 0
    )
    candidates_contacted = int(
        (
            await db.execute(
                select(func.count(distinct(ContactAttempt.candidate_id)))
                .select_from(ContactAttempt)
                .join(Candidate, Candidate.id == ContactAttempt.candidate_id)
                .where(*clauses)
            )
        ).scalar_one()
        or 0
    )
    successful = int(
        (
            await db.execute(
                select(func.count())
                .select_from(ContactAttempt)
                .join(Candidate, Candidate.id == ContactAttempt.candidate_id)
                .where(*clauses, ContactAttempt.result == SUCCESSFUL_CONTACT_RESULT)
            )
        ).scalar_one()
        or 0
    )
    by_result = (
        await db.execute(
            select(ContactAttempt.result, func.count())
            .select_from(ContactAttempt)
            .join(Candidate, Candidate.id == ContactAttempt.candidate_id)
            .where(*clauses)
            .group_by(ContactAttempt.result)
            .order_by(func.count().desc(), ContactAttempt.result)
        )
    ).all()
    by_channel = (
        await db.execute(
            select(ContactAttempt.channel, func.count())
            .select_from(ContactAttempt)
            .join(Candidate, Candidate.id == ContactAttempt.candidate_id)
            .where(*clauses)
            .group_by(ContactAttempt.channel)
            .order_by(func.count().desc(), ContactAttempt.channel)
        )
    ).all()
    by_recruiter = (
        await db.execute(
            select(ContactAttempt.attempted_by_user_id, User.full_name, func.count())
            .select_from(ContactAttempt)
            .join(Candidate, Candidate.id == ContactAttempt.candidate_id)
            .outerjoin(User, User.id == ContactAttempt.attempted_by_user_id)
            .where(*clauses)
            .group_by(ContactAttempt.attempted_by_user_id, User.full_name)
            .order_by(func.count().desc(), nullsfirst(User.full_name))
        )
    ).all()
    attribution = _context_attribution(company_id, vacancy_id)
    return ContactsSection(
        company_attribution=attribution,
        vacancy_attribution=attribution,
        attempts_total=attempts_total,
        candidates_contacted=candidates_contacted,
        successful_attempts=successful,
        by_result=[
            ContactResultRow(result=str(result or ""), attempts=int(count or 0))
            for result, count in by_result
        ],
        by_channel=[
            ContactChannelRow(channel=str(channel or ""), attempts=int(count or 0))
            for channel, count in by_channel
        ],
        by_recruiter=[
            ContactRecruiterRow(
                recruiter_id=str(user_id) if user_id else None,
                recruiter_name=str(name) if name else None,
                attempts=int(count or 0),
            )
            for user_id, name, count in by_recruiter
        ],
    )


def _reason_category(stage: str, candidates: int, without: int, rows: list[ReasonCodeRow]) -> ReasonCategory:
    return ReasonCategory(
        stage=stage,
        candidates=candidates,
        candidates_without_reason=without,
        by_reason=rows,
    )


async def _reasons(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: Optional[str],
    vacancy_id: Optional[str],
) -> ReasonsSection:
    clauses = _live_candidate_clauses(
        tenant_id=tenant_id,
        company_id=company_id,
        vacancy_id=vacancy_id,
    )
    terminal = (COMPANY_REJECTION_STAGE, CANDIDATE_DECLINE_STAGE)
    stage_rows = (
        await db.execute(
            select(Candidate.stage, func.count(Candidate.id))
            .where(*clauses, Candidate.stage.in_(terminal))
            .group_by(Candidate.stage)
        )
    ).all()
    totals = {str(stage): int(count or 0) for stage, count in stage_rows}
    empty_length = func.coalesce(func.jsonb_array_length(cast(Candidate.status_reason, JSONB)), 0)
    empty_rows = (
        await db.execute(
            select(Candidate.stage, func.count(Candidate.id))
            .where(*clauses, Candidate.stage.in_(terminal), empty_length == 0)
            .group_by(Candidate.stage)
        )
    ).all()
    without = {str(stage): int(count or 0) for stage, count in empty_rows}
    # Set-returning function in the select list expands one candidate into one
    # row per reason code. It must not be a FROM-level cross join.
    reason_code = func.jsonb_array_elements_text(cast(Candidate.status_reason, JSONB))
    code_rows = (
        await db.execute(
            select(
                Candidate.stage,
                reason_code.label("reason_code"),
                func.count(distinct(Candidate.id)),
                func.count(),
            )
            .where(
                *clauses,
                Candidate.stage.in_(terminal),
                func.jsonb_typeof(cast(Candidate.status_reason, JSONB)) == "array",
            )
            .group_by(Candidate.stage, reason_code)
            .order_by(func.count(distinct(Candidate.id)).desc(), reason_code)
        )
    ).all()
    grouped: dict[str, list[ReasonCodeRow]] = {
        COMPANY_REJECTION_STAGE: [],
        CANDIDATE_DECLINE_STAGE: [],
    }
    for stage, code, candidates, occurrences in code_rows:
        key = str(stage)
        if key not in grouped or not code:
            continue
        grouped[key].append(
            ReasonCodeRow(
                reason=str(code),
                candidates=int(candidates or 0),
                occurrences=int(occurrences or 0),
            )
        )
    return ReasonsSection(
        rejected=_reason_category(
            COMPANY_REJECTION_STAGE,
            totals.get(COMPANY_REJECTION_STAGE, 0),
            without.get(COMPANY_REJECTION_STAGE, 0),
            grouped[COMPANY_REJECTION_STAGE],
        ),
        declined=_reason_category(
            CANDIDATE_DECLINE_STAGE,
            totals.get(CANDIDATE_DECLINE_STAGE, 0),
            without.get(CANDIDATE_DECLINE_STAGE, 0),
            grouped[CANDIDATE_DECLINE_STAGE],
        ),
    )


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
    stages = StagesSection(
        current=await _current_stages(
            db,
            tenant_id=tenant_id,
            company_id=company,
            vacancy_id=vacancy,
        ),
        transitions=await _stage_transitions(
            db,
            tenant_id=tenant_id,
            date_from=date_from,
            date_to=date_to,
            company_id=company,
            vacancy_id=vacancy,
        ),
    )
    contacts = await _contacts(
        db,
        tenant_id=tenant_id,
        date_from=date_from,
        date_to=date_to,
        company_id=company,
        vacancy_id=vacancy,
    )
    reasons = await _reasons(
        db,
        tenant_id=tenant_id,
        company_id=company,
        vacancy_id=vacancy,
    )
    return RecruitmentOverviewResponse(
        period=RecruitmentOverviewPeriod.model_validate({"from": period_from, "to": period_to}),
        acquisition=acquisition,
        recruitment=recruitment,
        people=PeopleSection(new_candidates=people_count),
        stages=stages,
        contacts=contacts,
        reasons=reasons,
        historical_gap=HistoricalGap(linked_recruitment_leads_without_application=gap),
        limitations=list(LIMITATION_CODES),
    )
