from __future__ import annotations

import os
from typing import AsyncGenerator, Tuple
from uuid import UUID

from contextlib import asynccontextmanager

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select

from .session import async_session_maker  # ← используем твою фабрику
from backend.app.auth.deps import UserCtx, get_current_user_optional
from backend.app.models.tenant import Tenant, TenantLink, TenantType, TenantVacancyAccess
from backend.app.models.vacancy import Vacancy
from backend.app.services.tenant_visibility import TenantVisibility

# backend/app/db/deps.py

# Legacy fallback when X-Tenant-Id is omitted (CRM / older embeds). Public intake must not rely on this alone.
PUBLIC_LEGACY_DEFAULT_TENANT_UUID = UUID("11111111-1111-1111-1111-111111111111")


async def bind_tenant_context_to_session(db: AsyncSession, tenant_id: UUID) -> None:
    """Set db.info, Postgres RLS app.tenant_id, tenant_visibility, and mark rls_tenant_bound.

    Postgres: set_config must succeed and current_setting must match (no silent failure).
    During binding, ``_binding_tenant_context`` allows guarded session to run SQL before
    ``rls_tenant_bound`` is set.
    """
    db.info["_binding_tenant_context"] = True
    try:
        db.info["tenant_id"] = tenant_id
        bind = db.get_bind()
        dialect = getattr(getattr(bind, "dialect", None), "name", None)

        if dialect == "postgresql":
            await db.execute(
                text("SELECT set_config('app.tenant_id', :tenant_id, false)"),
                {"tenant_id": str(tenant_id)},
            )
            row = await db.execute(text("SELECT current_setting('app.tenant_id', true) AS v"))
            current = row.scalar_one()
            if (current or "").strip() != str(tenant_id):
                raise RuntimeError(f"RLS tenant bind mismatch: expected {tenant_id} got {current!r}")
        else:
            # SQLite / other drivers: best-effort (tests, local); RLS not enforced the same way.
            try:
                await db.execute(
                    text("SELECT set_config('app.tenant_id', :tenant_id, false)"),
                    {"tenant_id": str(tenant_id)},
                )
            except Exception:
                if os.environ.get("ALLOW_SQLITE_FOR_TESTS", "").strip().lower() not in ("1", "true", "yes"):
                    raise

        db.info["tenant_visibility"] = await compute_tenant_visibility_for_tenant(db, tenant_id)
        db.info["rls_tenant_bound"] = True
    finally:
        db.info["_binding_tenant_context"] = False


@asynccontextmanager
async def tenant_enforced_session(
    tenant_id: UUID,
    *,
    actor_id: str = "system:tenant_job",
    correlation_id: str | None = None,
):
    """Background / worker helper: session with enforcement + RLS tenant bound.

    Usage::

        async with tenant_enforced_session(tid, actor_id=\"system:my-job\") as db:
            ...
    """
    from backend.app.security.runtime_context import security_job_context

    async with security_job_context(actor_id=actor_id, correlation_id=correlation_id):
        async with async_session_maker() as session:
            session.info["tenant_rls_enforcement"] = True
            await bind_tenant_context_to_session(session, tenant_id)
            yield session


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
    elevated_reason: str | None = Header(None, alias="X-HostFlow-Elevated-Reason"),
    elevated_scope: str | None = Header(None, alias="X-HostFlow-Elevated-Scope"),
    user: UserCtx | None = Depends(get_current_user_optional),
) -> AsyncGenerator[Tuple[AsyncSession, UUID], None]:
    """
    Отдаёт (db, tenant_id) из заголовка X-Tenant-Id.
    Валидирует UUID и возвращает 400 при ошибке.
    """
    from backend.app.security.api_tenant_context import (
        SecurityAccessKind,
        classify_api_tenant_access,
        require_elevated_reason_or_raise,
    )
    from backend.app.security.canonical_emit import emit_security_event_v1
    from backend.app.security.event_taxonomy import (
        EVENT_AUTH_IMPERSONATION_DB_BIND,
        EVENT_SUPERADMIN_ELEVATED_DB_BIND,
    )

    if user is not None and getattr(user, "sub", None):
        from backend.app.security.runtime_context import set_security_actor_id

        set_security_actor_id(str(user.sub))

    raw = (tenant_id_header or "").strip()
    if not raw:
        raw = str(PUBLIC_LEGACY_DEFAULT_TENANT_UUID)
    try:
        tenant_id = UUID(raw)
    except Exception:
        raise HTTPException(status_code=400, detail="X-Tenant-Id must be a valid UUID")

    header_str = str(tenant_id)
    access_kind, default_scope = classify_api_tenant_access(
        user,
        header_tenant_id=header_str,
        elevated_reason=elevated_reason,
        elevated_scope=elevated_scope,
    )

    eff_reason: str | None = None
    eff_scope: str | None = None

    if access_kind == SecurityAccessKind.superadmin_elevated:
        eff_reason = require_elevated_reason_or_raise(
            reason=elevated_reason,
            detail="X-HostFlow-Elevated-Reason is required for superadmin cross-tenant DB access",
        )
        eff_scope = default_scope
        emit_security_event_v1(
            event_type=EVENT_SUPERADMIN_ELEVATED_DB_BIND,
            result="success",
            severity="info",
            source="http:get_db_with_tenant",
            tenant_id=header_str,
            access_kind=access_kind.value,
            entity_type="tenant",
            entity_id=header_str,
            extra={
                "access_kind": access_kind.value,
                "jwt_tenant_id": (user.tenant_id or "").strip() if user else None,
                "elevated_reason": eff_reason,
                "elevated_scope": eff_scope,
            },
            extra_allowlist=frozenset(
                {"access_kind", "jwt_tenant_id", "elevated_reason", "elevated_scope"}
            ),
        )
    elif access_kind == SecurityAccessKind.support_impersonation:
        eff_reason = require_elevated_reason_or_raise(
            reason=elevated_reason,
            detail="X-HostFlow-Elevated-Reason is required for support impersonation DB access",
        )
        eff_scope = default_scope
        emit_security_event_v1(
            event_type=EVENT_AUTH_IMPERSONATION_DB_BIND,
            result="success",
            severity="info",
            source="http:get_db_with_tenant",
            tenant_id=header_str,
            access_kind=access_kind.value,
            entity_type="tenant",
            entity_id=header_str,
            extra={
                "access_kind": access_kind.value,
                "jwt_tenant_id": (user.tenant_id or "").strip() if user else None,
                "elevated_reason": eff_reason,
                "elevated_scope": eff_scope,
            },
            extra_allowlist=frozenset(
                {"access_kind", "jwt_tenant_id", "elevated_reason", "elevated_scope"}
            ),
        )
    elif user is not None and getattr(user, "sub", None):
        # P0 fail-closed: X-Tenant-Id must match JWT tenant or user_memberships.
        # Classifier leaves mismatches as tenant_bound; never bind RLS to a foreign
        # tenant without proving membership (security-ssot §3).
        from backend.app.auth.tenant_scope import ensure_user_can_access_tenant

        await ensure_user_can_access_tenant(db, user, header_str)

    db.info["security_access_kind"] = access_kind.value
    db.info["security_elevated_reason"] = eff_reason
    db.info["security_elevated_scope"] = eff_scope

    db.info["tenant_rls_enforcement"] = True
    await bind_tenant_context_to_session(db, tenant_id)

    yield db, tenant_id
