from __future__ import annotations

from typing import AsyncGenerator, Tuple
from uuid import UUID

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select

from .session import async_session_maker  # ← используем твою фабрику
from backend.app.models.tenant import TenantVacancyAccess
from backend.app.models.vacancy import Vacancy
from backend.app.services.tenant_visibility import TenantVisibility

# backend/app/db/deps.py





async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Асинхронная сессия SQLAlchemy для зависимостей FastAPI.
    Закрывается автоматически по завершении запроса.
    """
    async with async_session_maker() as session:
        yield session


async def get_db_with_tenant(
    db: AsyncSession = Depends(get_db),
    tenant_id_header: str | None = Header(None, alias="X-Tenant-Id"),
) -> AsyncGenerator[Tuple[AsyncSession, UUID], None]:
    """
    Отдаёт (db, tenant_id) из заголовка X-Tenant-Id.
    Валидирует UUID и возвращает 400 при ошибке.
    """
    raw = (tenant_id_header or "").strip()
    if not raw:
        raw = "11111111-1111-1111-1111-111111111111"
    try:
        tenant_id = UUID(raw)
    except Exception:
        raise HTTPException(status_code=400, detail="X-Tenant-Id must be a valid UUID")
    # Persist tenant context on session for downstream services (CRUD helpers, etc.)
    db.info["tenant_id"] = tenant_id

    # Ensure Postgres sessions apply the RLS tenant context.
    try:
        await db.execute(
            text("SELECT set_config('app.tenant_id', :tenant_id, false)"),
            {"tenant_id": str(tenant_id)},
        )
    except Exception:
        # SQLite and other dialects will fail here; ignore silently per spec compatibility.
        pass

    shared_vacancy_ids: set[str] = set()
    shared_company_ids: set[str] = set()
    try:
        rows = await db.execute(
            select(TenantVacancyAccess.vacancy_id, Vacancy.company_id)
            .join(Vacancy, Vacancy.id == TenantVacancyAccess.vacancy_id, isouter=True)
            .where(TenantVacancyAccess.tenant_id == str(tenant_id))
        )
        for vacancy_id, company_id in rows:
            if vacancy_id:
                shared_vacancy_ids.add(vacancy_id)
            if company_id:
                shared_company_ids.add(company_id)
    except Exception:
        shared_vacancy_ids = set()
        shared_company_ids = set()
        try:
            await db.rollback()
        except Exception:
            pass

    db.info["tenant_visibility"] = TenantVisibility(
        tenant_id=str(tenant_id),
        shared_vacancy_ids=shared_vacancy_ids,
        shared_company_ids=shared_company_ids,
    )

    yield db, tenant_id
