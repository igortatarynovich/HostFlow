"""Role-based /meta/stages visibility when agency has handoff enabled + PATCH stage enforcement."""

from __future__ import annotations

from typing import Any, Callable

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx
from backend.app.auth.trust_roles import (
    TrustRole,
    is_hr_workspace_actor,
    is_portal_actor,
    normalize_trust_role,
)
from backend.app.constants.stages import (
    CLIENT_HANDOFF_VISIBLE_STAGE_CODES,
    INTERNAL_HR_HANDOFF_VISIBLE_STAGE_CODES,
    LABELS,
    RECRUITMENT_HANDOFF_HIDDEN_STAGE_CODES,
    STAGES_BY_GROUP,
)
from backend.app.models.user import Role as UserRole
from backend.app.services.handoff import is_client_tenant
from backend.app.services.tenant_links import list_links_for_agency

# Роли «рекрутинг» — воронка до передачи (+ исключения из констант скрытия).
RECRUITMENT_PIPELINE_STAGE_FILTER_ROLES: frozenset[str] = frozenset(
    {"employee", "recruiter", "supervisor", "viewer"}  # trust + legacy
)

def _is_recruitment_pipeline_actor(role: str, access_context: str | None = None) -> bool:
    r = (role or "").strip().lower()
    if r in RECRUITMENT_PIPELINE_STAGE_FILTER_ROLES:
        return True
    trust = normalize_trust_role(r)
    if trust == TrustRole.employee.value and not is_hr_workspace_actor(r):
        return True
    if trust == TrustRole.viewer.value and not is_portal_actor(r, access_context):
        return True
    return False

STAGE_VISIBILITY_RECRUITMENT = "recruitment_handoff"
STAGE_VISIBILITY_INTERNAL_HR = "internal_hr_handoff"
STAGE_VISIBILITY_CLIENT_HANDOFF = "client_handoff"


def _code_ok_for_recruitment(code: str) -> bool:
    return code not in RECRUITMENT_HANDOFF_HIDDEN_STAGE_CODES


def _make_allowed_predicate(allowed_known: frozenset[str]) -> Callable[[str], bool]:
    def _pred(code: str) -> bool:
        c = str(code or "").strip()
        if not c:
            return False
        if c not in LABELS:
            return True
        return c in allowed_known

    return _pred


def _dedupe_preserve(seq: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in seq:
        c = str(x or "").strip()
        if not c or c in seen:
            continue
        seen.add(c)
        out.append(c)
    return out


def merge_internal_hr_lane_into_funnel_order(payload: dict[str, Any]) -> dict[str, Any]:
    """Tenant default funnel may list only permit/trip stages; HR handoff lane still needs system codes."""
    out = dict(payload)
    order = [str(c) for c in (out.get("order") or [])]
    codes = [str(c) for c in (out.get("codes") or [])]
    preferred = ["processing_by_hr", "hired"] + [
        c
        for c in (STAGES_BY_GROUP.get("client_process") or [])
        if c in INTERNAL_HR_HANDOFF_VISIBLE_STAGE_CODES
    ]
    seen_o = set(order)
    prefix = [c for c in preferred if c not in seen_o]
    if not prefix:
        return out
    out["order"] = _dedupe_preserve(prefix + order)
    out["codes"] = _dedupe_preserve(prefix + codes)
    return out


def handoff_lane_active_for_company(links: list[Any], *, company_id: str | None) -> bool:
    """True when the recruiter/HR lane split applies for this operating company.

    Company-scoped: another client's handoff must not lock POLTRAKT-style
    employment funnels that have handoff off. Without a company id the lane
    split does not apply — mixed-tenant /meta/stages must not hide employment
    stages for clients that have handoff off.
    """
    if not links:
        return False

    def _company_ids(link: Any) -> set[str]:
        ids: set[str] = set()
        for attr in ("client_company_id", "handoff_include_company_id"):
            raw = str(getattr(link, attr, None) or "").strip()
            if raw:
                ids.add(raw)
        return ids

    cid = str(company_id or "").strip()
    if not cid:
        return False
    scoped = [link for link in links if cid in _company_ids(link)]
    if not scoped:
        return False
    return any(bool(link.get_handoff_enabled()) for link in scoped)


def filter_meta_stages_payload(
    payload: dict[str, Any],
    *,
    code_allowed: Callable[[str], bool],
    visibility_mode: str,
) -> dict[str, Any]:
    """Copy payload; keep labels/reason_choices; narrow structural fields by *code_allowed*."""
    out = dict(payload)

    groups_in = payload.get("groups") or {}
    new_groups: dict[str, list[str]] = {}
    if isinstance(groups_in, dict):
        for col, codes in groups_in.items():
            key = str(col or "").strip()
            if not key:
                continue
            raw = codes if isinstance(codes, list) else []
            filtered = [str(c) for c in raw if code_allowed(str(c).strip())]
            if filtered:
                new_groups[key] = filtered
    out["groups"] = new_groups

    order = [str(c) for c in (payload.get("order") or []) if code_allowed(str(c).strip())]
    out["order"] = order
    out["codes"] = [str(c) for c in (payload.get("codes") or []) if code_allowed(str(c).strip())]

    co_in = payload.get("column_of") or {}
    out["column_of"] = {
        str(k): v for k, v in co_in.items() if isinstance(k, (str, int)) and code_allowed(str(k).strip())
    }

    meta_in = payload.get("meta") or {}
    out["meta"] = {str(k): v for k, v in meta_in.items() if code_allowed(str(k).strip())}

    cs = payload.get("custom_stages") or []
    if isinstance(cs, list):
        kept = []
        for x in cs:
            if not isinstance(x, dict):
                continue
            c = x.get("code")
            if code_allowed(str(c or "").strip()):
                kept.append(x)
        out["custom_stages"] = kept

    dc = out.get("default")
    if dc is not None and not code_allowed(str(dc).strip()):
        out["default"] = order[0] if order else "new"

    out["stage_visibility_mode"] = visibility_mode
    out["recruiter_handoff_stage_filter"] = True  # backward compat for tests / UI
    return out


async def apply_handoff_stage_meta_for_user(
    db: AsyncSession,
    tenant_id: str,
    user: UserCtx,
    payload: dict[str, Any],
    *,
    company_id: str | None = None,
) -> dict[str, Any]:
    """Apply recruitment / HR / client-processor narrowing for agency tenants with handoff links."""
    tid = (tenant_id or "").strip()
    if not tid or (user.tenant_id or "").strip() != tid:
        return payload
    if await is_client_tenant(db, tid):
        return payload

    links = await list_links_for_agency(db, tid)
    if not handoff_lane_active_for_company(links, company_id=company_id):
        return payload

    role = (user.role or "").strip().lower()

    if role in (UserRole.administrator.value, UserRole.superadmin.value):
        return payload

    if _is_recruitment_pipeline_actor(role, getattr(user, "access_context", None)):
        return filter_meta_stages_payload(
            payload,
            code_allowed=_code_ok_for_recruitment,
            visibility_mode=STAGE_VISIBILITY_RECRUITMENT,
        )

    if is_hr_workspace_actor(role):
        merged = merge_internal_hr_lane_into_funnel_order(payload)
        return filter_meta_stages_payload(
            merged,
            code_allowed=_make_allowed_predicate(INTERNAL_HR_HANDOFF_VISIBLE_STAGE_CODES),
            visibility_mode=STAGE_VISIBILITY_INTERNAL_HR,
        )

    if is_portal_actor(role, getattr(user, "access_context", None)):
        return filter_meta_stages_payload(
            payload,
            code_allowed=_make_allowed_predicate(CLIENT_HANDOFF_VISIBLE_STAGE_CODES),
            visibility_mode=STAGE_VISIBILITY_CLIENT_HANDOFF,
        )

    return payload


async def enforce_agency_handoff_stage_change_allowed(
    db: AsyncSession,
    *,
    tenant_id: str,
    user: UserCtx,
    new_stage_code: str,
    company_id: str | None = None,
) -> None:
    """403 if agency user tries to set a stage outside their lane while handoff is enabled.

    Recruitment (recruiter/supervisor/viewer): may set ``ready_for_hr`` (финал Recruitment);
    blocked codes — ``RECRUITMENT_HANDOFF_HIDDEN_STAGE_CODES`` (e.g. ``hired``, ``employed``, post-handoff lane).
    Lane split is per operating company: employment funnels without handoff stay writable.
    """
    tid = (tenant_id or "").strip()
    if not tid or (user.tenant_id or "").strip() != tid:
        return
    if await is_client_tenant(db, tid):
        return

    links = await list_links_for_agency(db, tid)
    if not handoff_lane_active_for_company(links, company_id=company_id):
        return

    role = (user.role or "").strip().lower()
    code = str(new_stage_code or "").strip()
    if not code:
        return

    if role in (UserRole.administrator.value, UserRole.superadmin.value):
        return

    if _is_recruitment_pipeline_actor(role, getattr(user, "access_context", None)):
        if code in RECRUITMENT_HANDOFF_HIDDEN_STAGE_CODES:
            raise HTTPException(
                status_code=403,
                detail="Stage change not allowed for recruitment role after handoff is enabled",
            )
        return

    if is_hr_workspace_actor(role):
        pred = _make_allowed_predicate(INTERNAL_HR_HANDOFF_VISIBLE_STAGE_CODES)
        if not pred(code):
            raise HTTPException(
                status_code=403,
                detail="Stage change not allowed for HR role (outside post-handoff lane)",
            )
        return

    if is_portal_actor(role, getattr(user, "access_context", None)):
        pred = _make_allowed_predicate(CLIENT_HANDOFF_VISIBLE_STAGE_CODES)
        if not pred(code):
            raise HTTPException(
                status_code=403,
                detail="Stage change not allowed for client processor role (outside client handoff lane)",
            )
        return


# Backward-compatible name for imports
async def apply_recruitment_handoff_stage_meta_if_needed(
    db: AsyncSession,
    tenant_id: str,
    user: UserCtx,
    payload: dict[str, Any],
    *,
    company_id: str | None = None,
) -> dict[str, Any]:
    return await apply_handoff_stage_meta_for_user(
        db, tenant_id, user, payload, company_id=company_id
    )
