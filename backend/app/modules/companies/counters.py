from uuid import UUID

from backend.app.models import Candidate, Vacancy
from backend.app.services.handoff import is_client_tenant_for_list
from backend.app.services.tenant_visibility import get_tenant_visibility
from backend.app.api.v1.candidates.repo import _candidate_scope_clause as repo_scope_clause
from backend.app.modules.companies.crud import _tenant_id_from_session
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession


async def get_company_counters(db: AsyncSession, company_id: UUID) -> dict:
    """
    Возвращает агрегированные счётчики по компании:
      - vacancies_total: общее число вакансий компании (неважно, активна или нет)
      - vacancies_active: активные и неархивные вакансии
      - candidates_total: кандидаты, привязанные к вакансиям этой компании

    Для клиентских тенантов (Citronex и др.) candidates_total дополнительно
    ограничивается тем же скоупом, что используется в списке и аналитике
    (handoff + связанные компании/вакансии), чтобы цифры совпадали.
    """
    tenant_id = _tenant_id_from_session(db)
    visibility = get_tenant_visibility(db, tenant_id)
    is_client = await is_client_tenant_for_list(db, tenant_id)

    # Всего вакансий по компании (поведение как раньше; RLS ограничит по tenant_id).
    # Для клиентского тенанта скорректируем ниже через candidates-со scope.
    vacancies_total_q = (
        select(func.count())
        .select_from(Vacancy)
        .where(Vacancy.company_id == company_id)
    )
    vacancies_total = (await db.execute(vacancies_total_q)).scalar_one()

    # Активные вакансии: если в модели есть поля is_active / is_archived — учитываем их, иначе берём все
    col_is_active = getattr(Vacancy, "is_active", None)
    col_is_archived = getattr(Vacancy, "is_archived", None)
    vacancies_active_stmt = (
        select(func.count())
        .select_from(Vacancy)
        .where(Vacancy.company_id == company_id)
    )
    if col_is_active is not None:
        vacancies_active_stmt = vacancies_active_stmt.where(col_is_active.is_(True))
    if col_is_archived is not None:
        vacancies_active_stmt = vacancies_active_stmt.where(col_is_archived.is_(False))
    vacancies_active = (await db.execute(vacancies_active_stmt)).scalar_one()

    # Кандидаты, привязанные к вакансиям этой компании, с учётом скоупа для клиента
    scope_clause = repo_scope_clause(tenant_id, visibility, is_client_tenant=is_client)

    candidates_total_q = (
        select(func.count())
        .select_from(Candidate)
        .join(Vacancy, Vacancy.id == Candidate.vacancy_id)
        .where(
            and_(
                Vacancy.company_id == company_id,
                Candidate.deleted_at.is_(None),
                scope_clause,
            )
        )
    )
    candidates_total = (await db.execute(candidates_total_q)).scalar_one()

    # Для клиентских тенантов считаем вакансии так же через candidates+scope,
    # чтобы counters совпадали с аналитикой и списком (а не упирались в отдельный RLS по Vacancy).
    if is_client:
        vacancies_for_client_q = (
            select(func.count(func.distinct(Vacancy.id)))
            .select_from(Candidate)
            .join(Vacancy, Vacancy.id == Candidate.vacancy_id)
            .where(
                and_(
                    Vacancy.company_id == company_id,
                    Candidate.deleted_at.is_(None),
                    scope_clause,
                )
            )
        )
        vacancies_for_client = (await db.execute(vacancies_for_client_q)).scalar_one()
        # Для клиента "всего" и "активные" считаем одинаково по доступным вакансиям.
        vacancies_total = vacancies_for_client
        vacancies_active = vacancies_for_client

    return {
        "vacancies_total": int(vacancies_total or 0),
        "vacancies_active": int(vacancies_active or 0),
        "candidates_total": int(candidates_total or 0),
    }


async def company_recruitment_metrics_for_list(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_ids: list[str],
) -> dict[str, dict[str, int]]:
    """
    Per-company recruitment signals for the clients list (parity with get_company_counters scope).
    Keys: recruitment_vacancies_active, recruitment_candidates_total.
    """
    ids = [str(x) for x in company_ids if x]
    if not ids:
        return {}

    is_client = await is_client_tenant_for_list(db, tenant_id)
    visibility = get_tenant_visibility(db, tenant_id)
    scope = repo_scope_clause(tenant_id, visibility, is_client_tenant=is_client)

    base: dict[str, dict[str, int]] = {
        cid: {"recruitment_vacancies_active": 0, "recruitment_candidates_total": 0} for cid in ids
    }

    # Candidates in funnel (per employer company via vacancy)
    cand_stmt = (
        select(Vacancy.company_id, func.count(Candidate.id))
        .select_from(Candidate)
        .join(Vacancy, Vacancy.id == Candidate.vacancy_id)
        .where(
            Vacancy.company_id.in_(ids),
            Candidate.deleted_at.is_(None),
            scope,
        )
        .group_by(Vacancy.company_id)
    )
    cand_rows = (await db.execute(cand_stmt)).all()
    for cid, cnt in cand_rows:
        if not cid:
            continue
        sid = str(cid)
        if sid in base:
            base[sid]["recruitment_candidates_total"] = int(cnt or 0)

    if is_client:
        vac_stmt = (
            select(Vacancy.company_id, func.count(func.distinct(Vacancy.id)))
            .select_from(Candidate)
            .join(Vacancy, Vacancy.id == Candidate.vacancy_id)
            .where(
                Vacancy.company_id.in_(ids),
                Candidate.deleted_at.is_(None),
                scope,
            )
            .group_by(Vacancy.company_id)
        )
        vac_rows = (await db.execute(vac_stmt)).all()
        for cid, cnt in vac_rows:
            if not cid:
                continue
            sid = str(cid)
            if sid in base:
                n = int(cnt or 0)
                base[sid]["recruitment_vacancies_active"] = n
    else:
        col_is_active = getattr(Vacancy, "is_active", None)
        col_is_archived = getattr(Vacancy, "is_archived", None)
        vac_stmt = (
            select(Vacancy.company_id, func.count())
            .select_from(Vacancy)
            .where(
                Vacancy.tenant_id == tenant_id,
                Vacancy.company_id.in_(ids),
            )
        )
        if col_is_active is not None:
            vac_stmt = vac_stmt.where(col_is_active.is_(True))
        if col_is_archived is not None:
            vac_stmt = vac_stmt.where(col_is_archived.is_(False))
        vac_stmt = vac_stmt.group_by(Vacancy.company_id)
        vac_rows = (await db.execute(vac_stmt)).all()
        for cid, cnt in vac_rows:
            if not cid:
                continue
            sid = str(cid)
            if sid in base:
                base[sid]["recruitment_vacancies_active"] = int(cnt or 0)

    return base
