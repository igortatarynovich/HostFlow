from __future__ import annotations

from typing import AsyncGenerator, Tuple
from uuid import UUID

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select

from .session import async_session_maker  # ← используем твою фабрику
from backend.app.models.tenant import Tenant, TenantLink, TenantType, TenantVacancyAccess
from backend.app.models.vacancy import Vacancy
from backend.app.services.tenant_visibility import TenantVisibility

# backend/app/db/deps.py


async def compute_tenant_visibility_for_tenant(db: AsyncSession, tenant_id: UUID) -> TenantVisibility:
    """
    Shared vacancy/company visibility for a tenant (same rules as get_db_with_tenant).
    Does not mutate db.info — caller assigns the result.
    """
    tid = str(tenant_id)
    shared_vacancy_ids: set[str] = set()
    shared_company_ids: set[str] = set()
    try:
        rows = await db.execute(
            select(TenantVacancyAccess.vacancy_id, Vacancy.company_id)
            .join(Vacancy, Vacancy.id == TenantVacancyAccess.vacancy_id, isouter=True)
            .where(TenantVacancyAccess.tenant_id == tid)
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

    try:
        tenant_row = await db.execute(select(Tenant.type).where(Tenant.id == tid).limit(1))
        ttype = tenant_row.scalar_one_or_none()
        if ttype == TenantType.company:
            link_rows = await db.execute(
                select(TenantLink.handoff_include_company_id)
                .where(
                    TenantLink.client_tenant_id == tid,
                    TenantLink.handoff_include_company_id.isnot(None),
                    TenantLink.status == "active",
                )
            )
            for (company_id,) in link_rows.all():
                if company_id:
                    shared_company_ids.add(str(company_id))
            if shared_company_ids:
                vac_rows = await db.execute(select(Vacancy.id).where(Vacancy.company_id.in_(shared_company_ids)))
                for (vid,) in vac_rows.all():
                    if vid:
                        shared_vacancy_ids.add(str(vid))
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass

    return TenantVisibility(
        tenant_id=tid,
        shared_vacancy_ids=shared_vacancy_ids,
        shared_company_ids=shared_company_ids,
    )



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

    db.info["tenant_visibility"] = await compute_tenant_visibility_for_tenant(db, tenant_id)

    yield db, tenant_id
