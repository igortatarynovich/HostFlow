from uuid import UUID

from backend.app.models import Candidate, Vacancy
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def get_company_counters(db: AsyncSession, company_id: UUID) -> dict:
    """
    Возвращает агрегированные счётчики по компании:
      - vacancies_total: общее число вакансий компании (неважно, активна или нет)
      - vacancies_active: активные и неархивные вакансии
      - candidates_total: кандидаты, привязанные к вакансиям этой компании

    Примечание:
      Поле/логика "candidates_in_progress" зависят от каноники стадий кандидата в проекте.
      Чтобы не гадать, пока возвращаем только три стабильных метрики.
    """
    # Всего вакансий по компании
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

    # Кандидаты, привязанные к вакансиям этой компании
    candidates_total_q = (
        select(func.count())
        .select_from(Candidate)
        .join(Vacancy, Vacancy.id == Candidate.vacancy_id)
        .where(Vacancy.company_id == company_id)
    )
    candidates_total = (await db.execute(candidates_total_q)).scalar_one()

    return {
        "vacancies_total": int(vacancies_total or 0),
        "vacancies_active": int(vacancies_active or 0),
        "candidates_total": int(candidates_total or 0),
    }
