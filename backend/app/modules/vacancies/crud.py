from typing import Optional, Tuple, Union, Any, List
from uuid import UUID

from backend.app.models.vacancy import Vacancy
from backend.app.modules.vacancies import schemas
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession



# Позволяем принимать как чистую AsyncSession, так и (AsyncSession, tenant_id)
def _normalize_db_ctx(db_or_ctx: Union[AsyncSession, Tuple[AsyncSession, Any]]) -> tuple[AsyncSession, Optional[str]]:
    if isinstance(db_or_ctx, tuple) and len(db_or_ctx) == 2:
        db, tenant_id = db_or_ctx
    else:
        db, tenant_id = db_or_ctx, None
    # normalize tenant_id to string if provided
    if tenant_id is not None:
        tenant_id = str(tenant_id)
    return db, tenant_id


async def get_vacancy(db: Union[AsyncSession, Tuple[AsyncSession, Any]], vacancy_id: UUID) -> Optional[Vacancy]:
    db, tenant_id = _normalize_db_ctx(db)
    stmt = select(Vacancy).where(Vacancy.id == str(vacancy_id))
    if tenant_id is not None and hasattr(Vacancy, "tenant_id"):
        stmt = stmt.where(Vacancy.tenant_id == str(tenant_id))
    result = await db.execute(stmt)
    return result.scalars().first()


async def list_vacancies(
    db: Union[AsyncSession, Tuple[AsyncSession, Any]],
    company_id: Optional[UUID] = None,
    *,
    status: Optional[str] = None,
    include_archived: bool = False,
) -> List[Vacancy]:
    db, tenant_id = _normalize_db_ctx(db)
    query = select(Vacancy)
    if company_id:
        query = query.where(Vacancy.company_id == str(company_id))
    if tenant_id is not None and hasattr(Vacancy, "tenant_id"):
        query = query.where(Vacancy.tenant_id == str(tenant_id))
    status_filter = (status or "").strip()
    normalized_status = status_filter.lower() or None
    archived_requested = normalized_status == "archived"
    if archived_requested:
        include_archived = True
    if not include_archived:
        col_is_archived = getattr(Vacancy, "is_archived", None)
        if col_is_archived is not None:
            query = query.where(col_is_archived.is_(False))
    else:
        col_is_archived = getattr(Vacancy, "is_archived", None)
        if archived_requested and col_is_archived is not None:
            query = query.where(col_is_archived.is_(True))
    if normalized_status and not archived_requested:
        col_status = getattr(Vacancy, "status", None)
        if col_status is not None:
            query = query.where(col_status == status_filter)
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_vacancy(db: Union[AsyncSession, Tuple[AsyncSession, Any]], data: schemas.VacancyCreate) -> Vacancy:
    db, tenant_id = _normalize_db_ctx(db)
    payload = data.model_dump()
    # Normalize UUID-like fields to strings for SQLite (stores as VARCHAR)
    if isinstance(payload.get("id"), UUID):
        payload["id"] = str(payload["id"])
    if isinstance(payload.get("company_id"), UUID):
        payload["company_id"] = str(payload["company_id"])
    if tenant_id is not None and hasattr(Vacancy, "tenant_id"):
        if not payload.get("tenant_id"):
            payload["tenant_id"] = str(tenant_id)
        elif isinstance(payload.get("tenant_id"), UUID):
            payload["tenant_id"] = str(payload["tenant_id"])
    vacancy = Vacancy(**payload)
    db.add(vacancy)
    await db.commit()
    await db.refresh(vacancy)
    return vacancy


async def update_vacancy(
    db: Union[AsyncSession, Tuple[AsyncSession, Any]],
    vacancy_id: UUID,
    data: schemas.VacancyUpdate,
) -> Optional[Vacancy]:
    db, tenant_id = _normalize_db_ctx(db)
    update_data = data.model_dump(exclude_unset=True)
    update_data.pop("id", None)  # never allow id change; just drop if present

    if not update_data:
        return await get_vacancy((db, tenant_id) if tenant_id is not None else db, vacancy_id)

    existing = await get_vacancy(
        (db, tenant_id) if tenant_id is not None else db,
        vacancy_id,
    )
    if existing is None:
        return None

    if "company_id" in update_data:
        raw_company_id = update_data["company_id"]
        if isinstance(raw_company_id, UUID):
            update_data["company_id"] = str(raw_company_id)
        elif raw_company_id is None:
            update_data["company_id"] = None

    dirty = False
    for key, value in update_data.items():
        if not hasattr(existing, key):
            continue
        current = getattr(existing, key)
        if current != value:
            setattr(existing, key, value)
            dirty = True

    if not dirty:
        await db.refresh(existing)
        return existing

    await db.flush()

    await db.commit()
    await db.refresh(existing)
    return existing


async def archive_vacancy(db: Union[AsyncSession, Tuple[AsyncSession, Any]], vacancy_id: UUID) -> bool:
    db, tenant_id = _normalize_db_ctx(db)
    col_is_archived = getattr(Vacancy, "is_archived", None)
    if col_is_archived is None:
        # Модель не поддерживает soft-delete — действие не применимо
        return False
    stmt = (
        update(Vacancy)
        .where(Vacancy.id == str(vacancy_id))
        .values(is_archived=True)
        .execution_options(synchronize_session="fetch")
    )
    if tenant_id is not None and hasattr(Vacancy, "tenant_id"):
        stmt = stmt.where(Vacancy.tenant_id == str(tenant_id))
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount > 0


async def unarchive_vacancy(db: Union[AsyncSession, Tuple[AsyncSession, Any]], vacancy_id: UUID) -> bool:
    db, tenant_id = _normalize_db_ctx(db)
    col_is_archived = getattr(Vacancy, "is_archived", None)
    if col_is_archived is None:
        # Модель не поддерживает soft-delete — действие не применимо
        return False
    stmt = (
        update(Vacancy)
        .where(Vacancy.id == str(vacancy_id))
        .values(is_archived=False)
        .execution_options(synchronize_session="fetch")
    )
    if tenant_id is not None and hasattr(Vacancy, "tenant_id"):
        stmt = stmt.where(Vacancy.tenant_id == str(tenant_id))
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount > 0
