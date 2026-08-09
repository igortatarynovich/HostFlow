from typing import List
from uuid import UUID

from backend.app.auth.trust_role_deps import require_trust_admin, require_trust_read, require_trust_write
from backend.app.auth.deps import Role as AuthRole
from backend.app.db.deps import get_db_with_tenant
from backend.app.modules.vacancies import schemas
from backend.app.modules.vacancies.service import (
    archive_vacancy_service,
    unarchive_vacancy_service,
    create_vacancy_service,
    get_vacancy_or_404,
    list_vacancies_service,
    update_vacancy_service,
)
from fastapi import APIRouter, Depends, Query, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/vacancies",
    tags=["vacancies"],
)


@router.get(
    "/",
    response_model=List[schemas.VacancyOut],
    dependencies=[Depends(require_trust_read())],
)
async def list_vacancies(
    company_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    include_archived: bool = Query(default=False),
    db: AsyncSession = Depends(get_db_with_tenant),
):
    status_filter = (status or "").strip() or None
    effective_include_archived = include_archived or (
        status_filter is not None and status_filter.lower() == "archived"
    )
    return await list_vacancies_service(
        db=db,
        company_id=company_id,
        status=status_filter,
        include_archived=effective_include_archived,
    )


@router.post(
    "/",
    response_model=schemas.VacancyOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_trust_write())],
)
async def create_vacancy(
    vacancy_in: schemas.VacancyCreate,
    db: AsyncSession = Depends(get_db_with_tenant),
):
    return await create_vacancy_service(db=db, data=vacancy_in)


@router.get(
    "/{vacancy_id}",
    response_model=schemas.VacancyOut,
    dependencies=[Depends(require_trust_read())],
)
async def get_vacancy(
    vacancy_id: UUID,
    db: AsyncSession = Depends(get_db_with_tenant),
):
    return await get_vacancy_or_404(db=db, vacancy_id=vacancy_id)


@router.put(
    "/{vacancy_id}",
    response_model=schemas.VacancyOut,
    dependencies=[Depends(require_trust_write())],
)
async def update_vacancy(
    vacancy_id: UUID,
    vacancy_in: schemas.VacancyUpdate,
    db: AsyncSession = Depends(get_db_with_tenant),
):
    return await update_vacancy_service(db=db, vacancy_id=vacancy_id, data=vacancy_in)


# PATCH endpoint for partial update
@router.patch(
    "/{vacancy_id}",
    response_model=schemas.VacancyOut,
    dependencies=[Depends(require_trust_write())],
)
async def patch_vacancy(
    vacancy_id: UUID,
    vacancy_in: schemas.VacancyUpdate,
    db: AsyncSession = Depends(get_db_with_tenant),
):
    return await update_vacancy_service(db=db, vacancy_id=vacancy_id, data=vacancy_in)


@router.delete(
    "/{vacancy_id}",
    status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None,
    dependencies=[Depends(require_trust_admin())],
)
async def archive_vacancy(
    vacancy_id: UUID,
    db: AsyncSession = Depends(get_db_with_tenant),
):
    await archive_vacancy_service(db=db, vacancy_id=vacancy_id)


# Alias POST endpoint for archiving a vacancy

@router.post(
    "/{vacancy_id}/archive",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_trust_admin())],
)
async def archive_vacancy_alias(
    vacancy_id: UUID,
    db: AsyncSession = Depends(get_db_with_tenant),
):
    await archive_vacancy_service(db=db, vacancy_id=vacancy_id)
    return {"ok": True}

# Alias POST endpoint for unarchiving a vacancy
@router.post(
    "/{vacancy_id}/unarchive",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_trust_admin())],
)
async def unarchive_vacancy_alias(
    vacancy_id: UUID,
    db: AsyncSession = Depends(get_db_with_tenant),
):
    await unarchive_vacancy_service(db=db, vacancy_id=vacancy_id)
    return {"ok": True}
