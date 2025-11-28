
from uuid import UUID

from backend.app.models.vacancy import Vacancy
from backend.app.modules.vacancies import crud, schemas
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession


async def get_vacancy_or_404(db: AsyncSession, vacancy_id: UUID) -> Vacancy:
    vacancy = await crud.get_vacancy(db, vacancy_id)
    if vacancy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vacancy not found"
        )
    return vacancy


async def list_vacancies_service(
    db: AsyncSession,
    company_id: UUID | None,
    status: str | None,
    include_archived: bool,
) -> list[Vacancy]:
    return list(
        await crud.list_vacancies(
            db,
            company_id,
            status=status,
            include_archived=include_archived,
        )
    )


async def create_vacancy_service(
    db: AsyncSession, data: schemas.VacancyCreate
) -> Vacancy:
    return await crud.create_vacancy(db, data)


async def update_vacancy_service(
    db: AsyncSession, vacancy_id: UUID, data: schemas.VacancyUpdate
) -> Vacancy:
    vacancy = await crud.update_vacancy(db, vacancy_id, data)
    if vacancy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vacancy not found"
        )
    return vacancy


async def archive_vacancy_service(db: AsyncSession, vacancy_id: UUID) -> None:
    archived = await crud.archive_vacancy(db, vacancy_id)
    if not archived:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vacancy not found"
        )


async def unarchive_vacancy_service(db: AsyncSession, vacancy_id: UUID) -> None:
    unarchived = await crud.unarchive_vacancy(db, vacancy_id)
    if not unarchived:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vacancy not found"
        )
