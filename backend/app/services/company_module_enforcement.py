"""Enforce company-level module access on API operations (ADR-003 P1b)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, exists, false as sql_false, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.models.company import Company
from backend.app.models.tenant import Tenant, TenantLink
from backend.app.models.vacancy import Vacancy
from backend.app.services.company_module_access import company_allows_module


async def _load_tenant(db: AsyncSession, tenant_id: str) -> Tenant:
    r = await db.execute(select(Tenant).where(Tenant.id == tenant_id).limit(1))
    t = r.scalar_one_or_none()
    if t is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return t


async def _load_company(db: AsyncSession, tenant_id: str, company_id: str) -> Optional[Company]:
    r = await db.execute(
        select(Company).where(Company.id == company_id, Company.tenant_id == tenant_id).limit(1)
    )
    return r.scalar_one_or_none()


async def assert_recruitment_for_company_scope(
    db: AsyncSession,
    tenant_id: str,
    company_id: Optional[str],
) -> None:
    """
    Recruitment is allowed if the tenant has the product enabled and (when company_id is set)
    that company does not opt out via ``enabled_modules``.
    """
    tenant = await _load_tenant(db, tenant_id)
    company: Optional[Company] = None
    if company_id:
        company = await _load_company(db, tenant_id, str(company_id).strip())
        if company is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    if not company_allows_module(tenant, company, "recruitment"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Recruitment module is disabled for this company"
                if company_id
                else "Recruitment module is not enabled for this workspace"
            ),
        )


async def assert_recruitment_for_candidate(
    db: AsyncSession,
    tenant_id: str,
    candidate: Candidate,
) -> None:
    """Resolve owning company from candidate (direct or via vacancy) and enforce recruitment access."""
    cid = candidate.company_id
    if cid:
        await assert_recruitment_for_company_scope(db, tenant_id, str(cid))
        return
    vid = candidate.vacancy_id
    if vid:
        r = await db.execute(
            select(Vacancy.company_id).where(Vacancy.id == vid, Vacancy.tenant_id == tenant_id).limit(1)
        )
        vc = r.scalar_one_or_none()
        if vc:
            await assert_recruitment_for_company_scope(db, tenant_id, str(vc))
            return
    await assert_recruitment_for_company_scope(db, tenant_id, None)


async def assert_recruitment_for_candidate_reassignment_payload(
    db: AsyncSession,
    tenant_id: str,
    data: Dict[str, Any],
) -> None:
    """
    When PATCH changes ``company_id`` or ``vacancy_id``, enforce recruitment for the
    target company (vacancy wins over company payload, same as create flow).
    """
    if "vacancy_id" not in data and "company_id" not in data:
        return
    target_cid: Optional[str] = None
    vid = data.get("vacancy_id")
    if vid:
        r = await db.execute(
            select(Vacancy.company_id).where(
                Vacancy.id == str(vid),
                Vacancy.tenant_id == tenant_id,
            ).limit(1)
        )
        row = r.scalar_one_or_none()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vacancy not found")
        target_cid = str(row) if row else None
    elif "company_id" in data:
        c_raw = data.get("company_id")
        target_cid = str(c_raw) if c_raw else None
    await assert_recruitment_for_company_scope(db, tenant_id, target_cid)


async def recruitment_candidate_list_sql_clause(
    db: AsyncSession,
    scope_tenant_id: str,
    *,
    is_client_tenant: bool,
) -> Any:
    """
    SQL predicate aligned with company-level ``recruitment`` access (ADR-003 P1b).

    Uses tenant ids: workspace scope + (for agency) active linked client tenants, then
    evaluates ``company_allows_module`` in Python and emits OR of company / vacancy / orphan rows.
    """
    tenant_scope = await db.get(Tenant, scope_tenant_id)
    if tenant_scope is None or not company_allows_module(tenant_scope, None, "recruitment"):
        return sql_false()

    tenant_ids: set[str] = {scope_tenant_id}
    if not is_client_tenant:
        r = await db.execute(
            select(TenantLink.client_tenant_id).where(
                TenantLink.agency_tenant_id == scope_tenant_id,
                TenantLink.client_tenant_id.isnot(None),
                TenantLink.status == "active",
            )
        )
        for (tid,) in r.all():
            if tid:
                tenant_ids.add(str(tid))

    t_rows = await db.execute(select(Tenant).where(Tenant.id.in_(list(tenant_ids))))
    tenants_map: dict[str, Tenant] = {str(t.id): t for t in t_rows.scalars()}

    c_rows = await db.execute(
        select(Company).where(
            Company.tenant_id.in_(list(tenant_ids)),
            Company.is_archived.is_(False),
        )
    )
    companies = list(c_rows.scalars())

    allowed_company_ids: set[str] = set()
    for comp in companies:
        t = tenants_map.get(str(comp.tenant_id))
        if t and company_allows_module(t, comp, "recruitment"):
            allowed_company_ids.add(str(comp.id))

    parts: list[Any] = []
    if allowed_company_ids:
        aid = tuple(allowed_company_ids)
        parts.append(Candidate.company_id.in_(aid))
        parts.append(
            exists(select(1).select_from(Vacancy).where(
                Vacancy.id == Candidate.vacancy_id,
                Vacancy.company_id.in_(aid),
            )).correlate(Candidate)
        )

    orphan_parts: list[Any] = []
    for tid in tenant_ids:
        t = tenants_map.get(tid)
        if t and company_allows_module(t, None, "recruitment"):
            orphan_parts.append(
                and_(
                    Candidate.tenant_id == tid,
                    Candidate.company_id.is_(None),
                    Candidate.vacancy_id.is_(None),
                )
            )
    if orphan_parts:
        parts.append(or_(*orphan_parts))

    if not parts:
        return sql_false()
    return or_(*parts)
