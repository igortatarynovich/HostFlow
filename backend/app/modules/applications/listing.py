"""Recruitment inbox listing helpers — SQL tab filters and aggregate counts."""

from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import Lead, Vacancy

from .mappers import TERMINAL_RECRUITMENT_STATUSES

_TERMINAL = tuple(str(s).lower() for s in TERMINAL_RECRUITMENT_STATUSES)
_RECRUITMENT_TABS = frozenset({"all", "new", "in_progress", "waiting", "completed"})


def normalize_recruitment_inbox_tab(tab: str | None) -> str:
    key = str(tab or "all").strip().lower()
    return key if key in _RECRUITMENT_TABS else "all"


def normalize_recruitment_inbox_scope(scope: str | None) -> str:
    return "open" if str(scope or "").strip().lower() == "open" else "all"


def _not_client_lead_clause() -> Any:
    """Recruitment inbox must not include Sales/client transport Leads (slice 4)."""
    return func.lower(func.coalesce(Lead.lead_type, "")) != "client"


def _status_lower() -> Any:
    return func.coalesce(func.lower(Lead.status), "")


def _open_recruitment_clause() -> Any:
    return and_(
        Lead.candidate_id.is_(None),
        _status_lower().notin_(_TERMINAL),
    )


def _new_recruitment_clause() -> Any:
    return and_(
        _open_recruitment_clause(),
        or_(Lead.status.is_(None), Lead.status == "", _status_lower() == "new"),
    )


def _in_progress_recruitment_clause() -> Any:
    return and_(
        _open_recruitment_clause(),
        Lead.status.isnot(None),
        Lead.status != "",
        _status_lower() != "new",
    )


def _completed_recruitment_clause() -> Any:
    return or_(Lead.candidate_id.isnot(None), _status_lower().in_(_TERMINAL))


def recruitment_inbox_sql_filters(
    *,
    tab: str | None,
    scope: str,
    vacancy_id: str | None = None,
) -> List[Any]:
    """Build SQLAlchemy filters for recruitment inbox tabs."""
    tab_key = normalize_recruitment_inbox_tab(tab)
    scope_key = normalize_recruitment_inbox_scope(scope)
    filters: List[Any] = [_not_client_lead_clause()]
    vac = str(vacancy_id or "").strip()
    if vac:
        filters.append(Lead.vacancy_id == vac)
    if scope_key == "open":
        filters.append(_open_recruitment_clause())
        return filters
    if tab_key == "new":
        filters.append(_new_recruitment_clause())
    elif tab_key == "in_progress":
        filters.append(_in_progress_recruitment_clause())
    elif tab_key == "completed":
        filters.append(_completed_recruitment_clause())
    return filters


async def count_recruitment_inbox(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str | None,
    tab: str | None,
    scope: str,
    vacancy_id: str | None = None,
) -> int:
    filters: List[Any] = [Lead.tenant_id == tenant_id]
    if own_company_id:
        filters.append(Lead.own_company_id == own_company_id)
    filters.extend(recruitment_inbox_sql_filters(tab=tab, scope=scope, vacancy_id=vacancy_id))
    row = await db.execute(select(func.count()).select_from(Lead).where(*filters))
    return int(row.scalar_one() or 0)


async def recruitment_inbox_tab_counts(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str | None,
    vacancy_id: str | None = None,
) -> Dict[str, int]:
    """Aggregate counts for inbox tab badges (same own-company scope)."""
    base: List[Any] = [Lead.tenant_id == tenant_id, _not_client_lead_clause()]
    if own_company_id:
        base.append(Lead.own_company_id == own_company_id)
    vac = str(vacancy_id or "").strip()
    if vac:
        base.append(Lead.vacancy_id == vac)
    row = await db.execute(
        select(
            func.count().label("all_count"),
            func.coalesce(func.sum(case((_new_recruitment_clause(), 1), else_=0)), 0).label("new_count"),
            func.coalesce(func.sum(case((_in_progress_recruitment_clause(), 1), else_=0)), 0).label(
                "in_progress_count"
            ),
            func.coalesce(func.sum(case((_completed_recruitment_clause(), 1), else_=0)), 0).label(
                "completed_count"
            ),
        )
        .select_from(Lead)
        .where(*base)
    )
    data = row.one()
    return {
        "all": int(data.all_count or 0),
        "new": int(data.new_count or 0),
        "in_progress": int(data.in_progress_count or 0),
        "waiting": 0,
        "completed": int(data.completed_count or 0),
    }


async def list_recruitment_inbox_leads(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str | None,
    tab: str | None,
    scope: str,
    vacancy_id: str | None = None,
    limit: int = 200,
    offset: int = 0,
    order_updated_at: bool = False,
) -> List[Lead]:
    """Load recruitment inbox rows (Lead-backed applications) with vacancy title."""
    filters: List[Any] = [Lead.tenant_id == tenant_id]
    if own_company_id:
        filters.append(Lead.own_company_id == own_company_id)
    filters.extend(recruitment_inbox_sql_filters(tab=tab, scope=scope, vacancy_id=vacancy_id))

    vacancy_scope_join = and_(
        Vacancy.id == Lead.vacancy_id,
        or_(Vacancy.own_company_id.is_(None), Vacancy.own_company_id == Lead.own_company_id),
    )
    order_col = Lead.updated_at if order_updated_at else Lead.created_at
    stmt = (
        select(Lead, Vacancy.title.label("vacancy_title"))
        .select_from(Lead)
        .join(Vacancy, vacancy_scope_join, isouter=True)
        .where(*filters)
        .order_by(order_col.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await db.execute(stmt)).all()
    leads: List[Lead] = []
    for lead, vacancy_title in rows:
        if vacancy_title:
            setattr(lead, "vacancy_title", vacancy_title)
        leads.append(lead)
    return leads
