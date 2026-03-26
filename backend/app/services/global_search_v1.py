"""
Global search v1: server-side merge + heuristic ranking for CRM core entities.

Leads are matched via normalized/payload JSON text, ids, stage/source/status, and
linked company name (same tenant / own_company scope as list endpoints).

Documents, communications, reminders, invoices, and service orders stay on the
client (see hostflow-frontend/src/api/search.ts) until a wider backend search exists.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import Text, cast, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.candidates import repo as cand_repo
from backend.app.api.v1.candidates.acl import resolve_candidate_acl
from backend.app.api.v1.utils.access import resolve_restricted_acl
from backend.app.auth.deps import Role, UserCtx
from backend.app.modules.companies.service import list_companies_service
from backend.app.api.v1.vacancies.repo import VacancyRepo
from backend.app.api.v1.vacancies.service import VacancyService
from backend.app.constants.spa_paths import spa_candidate, spa_client, spa_lead, spa_vacancy
from backend.app.db.deps import compute_tenant_visibility_for_tenant
from backend.app.models import Company, Lead
from backend.app.services.handoff import is_client_tenant_for_list
from backend.app.services.tenant_visibility import get_tenant_visibility

logger = logging.getLogger(__name__)


@dataclass
class _SavedTenantCtx:
    tenant_id: Any
    tenant_visibility: Any


async def _push_scope_tenant_context(db: AsyncSession, scope_tenant: str) -> _SavedTenantCtx:
    """Align session.info + RLS + TenantVisibility with scope_tenant (see candidates scope_tenant_id)."""
    saved = _SavedTenantCtx(
        tenant_id=db.info.get("tenant_id"),
        tenant_visibility=db.info.get("tenant_visibility"),
    )
    tid = UUID(scope_tenant)
    db.info["tenant_id"] = tid
    try:
        await db.execute(
            text("SELECT set_config('app.tenant_id', :tid, true)"),
            {"tid": scope_tenant},
        )
    except Exception:
        pass
    db.info["tenant_visibility"] = await compute_tenant_visibility_for_tenant(db, tid)
    return saved


async def _pop_scope_tenant_context(db: AsyncSession, saved: _SavedTenantCtx) -> None:
    db.info["tenant_id"] = saved.tenant_id
    db.info["tenant_visibility"] = saved.tenant_visibility
    try:
        if saved.tenant_id is not None:
            await db.execute(
                text("SELECT set_config('app.tenant_id', :tid, true)"),
                {"tid": str(saved.tenant_id)},
            )
    except Exception:
        pass

MAX_CONSECUTIVE_SAME_TYPE = 2


def _normalize_for_match(s: str) -> str:
    return " ".join(s.strip().lower().split())


def _match_quality_score(q_norm: str, title: str, subtitle: str | None) -> int:
    if not q_norm:
        return 0
    t = _normalize_for_match(title)
    sub = _normalize_for_match(subtitle) if subtitle else ""
    hay = f"{t} {sub}".strip() if sub else t
    if t == q_norm:
        return 100
    if hay == q_norm:
        return 95
    if t.startswith(q_norm):
        return 85
    if hay.startswith(q_norm):
        return 80
    idx = hay.find(q_norm)
    if idx >= 0:
        at_word = idx == 0 or hay[idx - 1] == " "
        return 55 if at_word else 35
    return 0


def merge_and_rank_items(
    items: list[dict[str, Any]],
    raw_query: str,
    *,
    max_out: int = 24,
) -> list[dict[str, Any]]:
    """Interleave by match quality (ported from frontend mergeSearchResultsHeuristic)."""
    if len(items) <= 1:
        return items[:max_out]
    q_norm = _normalize_for_match(raw_query)
    scored = [(it, _match_quality_score(q_norm, str(it.get("title") or ""), it.get("subtitle"))) for it in items]
    scored.sort(
        key=lambda x: (-x[1], str(x[0].get("title") or "").casefold()),
    )
    pool = [x[0] for x in scored]
    out: list[dict[str, Any]] = []
    last_type: str | None = None
    streak = 0
    while len(out) < max_out and pool:
        idx = next(
            (i for i, item in enumerate(pool) if not (item.get("type") == last_type and streak >= MAX_CONSECUTIVE_SAME_TYPE)),
            0,
        )
        next_item = pool.pop(idx)
        out.append(next_item)
        nt = str(next_item.get("type") or "")
        if nt == last_type:
            streak += 1
        else:
            last_type = nt
            streak = 1
    return out


def _candidate_row_to_model(row: Any) -> Any:
    return row[0] if isinstance(row, (list, tuple)) and row else row


def _candidate_to_mask_dict(c: Any) -> dict[str, Any]:
    extra = getattr(c, "extra", None)
    if not isinstance(extra, dict):
        extra = {}
    return {
        "id": str(c.id),
        "tenant_id": str(getattr(c, "tenant_id", "") or "") or None,
        "short_id": getattr(c, "short_id", None),
        "first_name": getattr(c, "first_name", None),
        "last_name": getattr(c, "last_name", None),
        "email": getattr(c, "email", None),
        "phone": getattr(c, "phone", None),
        "phone_country_code": getattr(c, "phone_country_code", None),
        "stage": getattr(c, "stage", None),
        "extra": extra,
    }


async def _search_candidates_slice(
    db: AsyncSession,
    *,
    scope_tenant: str,
    current_user: UserCtx,
    own_company_id: str | None,
    q: str,
    limit: int,
) -> list[dict[str, Any]]:
    from backend.app.api.v1.candidates.router import ACL_RESTRICTED_ROLES, _apply_client_view_mask

    try:
        await db.execute(
            text("SELECT set_config('app.tenant_id', :tid, true)"),
            {"tid": scope_tenant},
        )
    except Exception:
        pass

    visibility = get_tenant_visibility(db, scope_tenant)
    filters: dict[str, object] = {}
    client_tenant = await is_client_tenant_for_list(db, scope_tenant)
    if own_company_id and not client_tenant:
        filters["own_company_id"] = own_company_id
    filters["is_client_tenant"] = client_tenant

    user_role_lower = (current_user.role or "").lower()
    is_platform_superadmin = user_role_lower == Role.superadmin.value and not client_tenant
    apply_client_view = client_tenant and not is_platform_superadmin

    qs = q.strip()
    if not qs:
        return []
    filters["q"] = qs

    if current_user.role in ACL_RESTRICTED_ROLES:
        acl = await resolve_candidate_acl(db, scope_tenant, current_user)
        if not client_tenant and acl.is_empty():
            return []
        if not client_tenant:
            filters["allowed_company_ids"] = list(acl.company_ids)
            filters["allowed_vacancy_ids"] = list(acl.vacancy_ids)
            filters["allowed_manager_ids"] = list(acl.manager_ids)

    raw_rows: list[Any]
    if client_tenant:
        cands = await cand_repo.list_candidates(
            db,
            scope_tenant,
            filters,
            "created_at",
            True,
            limit,
            0,
            visibility,
        )
        raw_rows = list(cands)
    else:
        rows = await cand_repo.fetch_candidates_with_labels(
            db,
            tenant_id=scope_tenant,
            filters=filters,
            limit=limit,
            offset=0,
            order_by="created_at",
            desc=True,
            visibility=visibility,
        )
        raw_rows = list(rows)

    out: list[dict[str, Any]] = []
    for row in raw_rows:
        c = _candidate_row_to_model(row)
        if c is None:
            continue
        item = _candidate_to_mask_dict(c)
        cid = str(item["id"])
        if apply_client_view:
            item = await _apply_client_view_mask(db, item, cid, scope_tenant)
        fn = str(item.get("first_name") or "").strip()
        ln = str(item.get("last_name") or "").strip()
        title = f"{fn} {ln}".strip() or (str(item.get("email") or "").strip()) or (str(item.get("short_id") or "").strip()) or "Candidate"
        email = item.get("email")
        stage = item.get("stage")
        subtitle = str(stage) if stage else (str(email) if email else None)
        out.append(
            {
                "type": "candidate",
                "id": cid,
                "title": title,
                "subtitle": subtitle,
                "link": spa_candidate(cid),
            }
        )
    return out


async def _search_companies_slice(
    db: AsyncSession,
    *,
    tenant_id: str,
    current_user: UserCtx,
    q: str,
    limit: int,
) -> list[dict[str, Any]]:
    try:
        acl = await resolve_restricted_acl(db, tenant_id, current_user)
        allowed_company_ids = None if acl is None else set(acl.company_ids)
        companies = await list_companies_service(
            db=db,
            q=q.strip() or None,
            include_archived=False,
            allowed_company_ids=allowed_company_ids,
        )
        sliced = companies[:limit]
        results: list[dict[str, Any]] = []
        for c in sliced:
            cid = str(c.id)
            name = (getattr(c, "name", None) or getattr(c, "legal_name", None) or "Company") or "Company"
            city = getattr(c, "city", None)
            cc = getattr(c, "country_code", None)
            subtitle = " · ".join(x for x in [str(city) if city else None, str(cc) if cc else None] if x) or None
            results.append(
                {
                    "type": "company",
                    "id": cid,
                    "title": str(name),
                    "subtitle": subtitle,
                    "link": spa_client(cid),
                }
            )
        return results
    except Exception:
        logger.exception("global_search companies slice failed")
        return []


def _user_can_global_search_leads(user: UserCtx) -> bool:
    """Align with GET /leads list roles (no client handoff roles)."""
    r = (user.role or "").strip().lower()
    return r not in (Role.client_manager.value, Role.client_processor.value)


async def _search_leads_slice(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str | None,
    current_user: UserCtx,
    q: str,
    limit: int,
) -> list[dict[str, Any]]:
    if not _user_can_global_search_leads(current_user):
        return []
    qs = q.strip().lower()
    if len(qs) < 2:
        return []
    like = f"%{qs}%"
    try:
        text_norm = cast(Lead.normalized, Text)
        text_payload = cast(Lead.payload, Text)
        company_l = func.lower(func.coalesce(Company.name, ""))
        search_clause = or_(
            func.lower(text_norm).like(like),
            func.lower(text_payload).like(like),
            func.lower(Lead.id).like(like),
            func.lower(Lead.source).like(like),
            func.lower(func.coalesce(Lead.stage, "")).like(like),
            func.lower(func.coalesce(Lead.status, "")).like(like),
            func.lower(func.coalesce(Lead.lead_type, "")).like(like),
            company_l.like(like),
        )
        filters: list[Any] = [Lead.tenant_id == tenant_id, search_clause]
        if own_company_id:
            filters.append(Lead.own_company_id == own_company_id)
        stmt = (
            select(Lead)
            .outerjoin(Company, Company.id == Lead.company_id)
            .where(*filters)
            .order_by(Lead.created_at.desc())
            .limit(limit)
        )
        rows = (await db.execute(stmt)).scalars().all()
    except Exception:
        logger.exception("global_search leads slice failed")
        return []

    out: list[dict[str, Any]] = []
    for lead in rows:
        lid = str(lead.id)
        norm = lead.normalized if isinstance(lead.normalized, dict) else {}
        fn = str(norm.get("first_name") or norm.get("name") or "").strip()
        ln = str(norm.get("last_name") or "").strip()
        title = (
            f"{fn} {ln}".strip()
            or str(norm.get("email") or "").strip()
            or str(norm.get("phone") or "").strip()
            or f"Lead {lid[:8]}…"
        )
        parts = [lead.stage, lead.source, lead.status]
        subtitle = " · ".join(str(p) for p in parts if p) or None
        out.append(
            {
                "type": "lead",
                "id": lid,
                "title": title,
                "subtitle": subtitle,
                "link": spa_lead(lid),
            }
        )
    return out


async def _search_vacancies_slice(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    current_user: UserCtx,
    own_company_id: str | None,
    q: str,
    limit: int,
) -> list[dict[str, Any]]:
    try:
        tid = str(tenant_id)
        visibility = get_tenant_visibility(db, tid)
        svc = VacancyService(VacancyRepo(db, tid, own_company_id=own_company_id, visibility=visibility))
        acl = await resolve_restricted_acl(db, tid, current_user)
        rows = await svc.list(
            company_id=None,
            status=None,
            search=q.strip() or None,
            candidate_profile_id=None,
            limit=limit,
            offset=0,
            order_by="created_at",
            descending=True,
            acl=acl,
            include_archived=False,
        )
        results: list[dict[str, Any]] = []
        for v in rows:
            vid = str(v.id)
            parts = [v.company_name, v.status]
            subtitle = " · ".join(str(p) for p in parts if p) or None
            results.append(
                {
                    "type": "vacancy",
                    "id": vid,
                    "title": str(v.title or "Vacancy"),
                    "subtitle": subtitle,
                    "link": spa_vacancy(vid),
                }
            )
        return results
    except Exception:
        logger.exception("global_search vacancies slice failed")
        return []


async def run_global_search_v1(
    db: AsyncSession,
    *,
    header_tenant_id: UUID,
    scope_tenant_id: UUID | None,
    current_user: UserCtx,
    own_company_id: str | None,
    q: str,
    limit_per_type: int,
    max_results: int,
) -> dict[str, Any]:
    scope_tenant = str(scope_tenant_id).strip() if scope_tenant_id else str(header_tenant_id).strip()
    header_str = str(header_tenant_id).strip()
    scope_override = scope_tenant != header_str

    saved: _SavedTenantCtx | None = None
    if scope_override:
        saved = await _push_scope_tenant_context(db, scope_tenant)

    try:
        # One session: run sequentially (avoid concurrent set_config / session mutation).
        candidates = await _search_candidates_slice(
            db,
            scope_tenant=scope_tenant,
            current_user=current_user,
            own_company_id=own_company_id,
            q=q,
            limit=limit_per_type,
        )
        companies = await _search_companies_slice(
            db,
            tenant_id=scope_tenant,
            current_user=current_user,
            q=q,
            limit=limit_per_type,
        )
        vacancies = await _search_vacancies_slice(
            db,
            tenant_id=UUID(scope_tenant),
            current_user=current_user,
            own_company_id=own_company_id,
            q=q,
            limit=limit_per_type,
        )
        leads = await _search_leads_slice(
            db,
            tenant_id=scope_tenant,
            own_company_id=own_company_id,
            current_user=current_user,
            q=q,
            limit=limit_per_type,
        )
    finally:
        if saved is not None:
            await _pop_scope_tenant_context(db, saved)

    merged = [*candidates, *companies, *vacancies, *leads]
    ranked = merge_and_rank_items(merged, q.strip(), max_out=max_results)
    return {"q": q.strip(), "items": ranked}
