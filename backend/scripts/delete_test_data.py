#!/usr/bin/env python3
"""
Скрипт для удаления тестовых данных из базы данных.

Удаляет компании, вакансии и кандидатов, которые содержат в названии
ключевые слова: test, тест, demo, демо (без учета регистра).
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, delete, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker
from app.models import Company, Vacancy, Candidate


async def delete_test_data():
    """Удаляет тестовые данные из базы."""
    # Получаем сессию БД
    async with async_session_maker() as db:
        test_patterns = ["test", "тест", "demo", "демо"]
        
        # Находим тестовые компании
        company_conditions = [func.lower(Company.name).like(f"%{pattern}%") for pattern in test_patterns]
        company_stmt = select(Company.id, Company.name).where(or_(*company_conditions))
        companies_result = await db.execute(company_stmt)
        test_companies = companies_result.all()
        
        company_ids = [c[0] for c in test_companies]
        print(f"Найдено тестовых компаний: {len(company_ids)}")
        for cid, name in test_companies:
            print(f"  - {cid}: {name}")
        
        # Находим тестовые вакансии
        vacancy_conditions = [func.lower(Vacancy.title).like(f"%{pattern}%") for pattern in test_patterns]
        vacancy_stmt = select(Vacancy.id, Vacancy.title).where(or_(*vacancy_conditions))
        vacancies_result = await db.execute(vacancy_stmt)
        test_vacancies = vacancies_result.all()
        
        vacancy_ids = [v[0] for v in test_vacancies]
        print(f"\nНайдено тестовых вакансий: {len(vacancy_ids)}")
        for vid, title in test_vacancies:
            print(f"  - {vid}: {title}")
        
        # Находим кандидатов, связанных с тестовыми компаниями/вакансиями
        candidate_conditions = []
        if company_ids:
            candidate_conditions.append(Candidate.company_id.in_(company_ids))
        if vacancy_ids:
            candidate_conditions.append(Candidate.vacancy_id.in_(vacancy_ids))
        
        candidate_count = 0
        if candidate_conditions:
            candidate_count_stmt = select(func.count(Candidate.id)).where(or_(*candidate_conditions))
            candidate_count = (await db.execute(candidate_count_stmt)).scalar_one() or 0
            print(f"\nНайдено кандидатов, связанных с тестовыми данными: {candidate_count}")
        
        # Подтверждение удаления
        total_to_delete = len(company_ids) + len(vacancy_ids) + candidate_count
        if total_to_delete == 0:
            print("\nТестовых данных для удаления не найдено.")
            return
        
        print(f"\nВсего записей для удаления: {total_to_delete}")
        print("Удаление:")
        
        # Удаляем кандидатов (сначала, чтобы не нарушить внешние ключи)
        if candidate_conditions:
            delete_candidates_stmt = delete(Candidate).where(or_(*candidate_conditions))
            result = await db.execute(delete_candidates_stmt)
            deleted_candidates = result.rowcount
            print(f"  Удалено кандидатов: {deleted_candidates}")
            await db.commit()
        
        # Удаляем вакансии
        if vacancy_ids:
            delete_vacancies_stmt = delete(Vacancy).where(Vacancy.id.in_(vacancy_ids))
            result = await db.execute(delete_vacancies_stmt)
            deleted_vacancies = result.rowcount
            print(f"  Удалено вакансий: {deleted_vacancies}")
            await db.commit()
        
        # Удаляем компании
        if company_ids:
            delete_companies_stmt = delete(Company).where(Company.id.in_(company_ids))
            result = await db.execute(delete_companies_stmt)
            deleted_companies = result.rowcount
            print(f"  Удалено компаний: {deleted_companies}")
            await db.commit()
        
        print("\nГотово! Тестовые данные удалены.")


if __name__ == "__main__":
    asyncio.run(delete_test_data())
