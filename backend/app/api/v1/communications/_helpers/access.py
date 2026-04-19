"""RBAC + 404-fetch primitives for the communications API.

Wraps ``assert_comm_feature_access`` together with tenant / thread loaders
and standard plan-feature lookups so per-topic route modules don't need
to repeat boilerplate (or import each other). Extracted in Phase 1
god-module split, step 3/N.
"""

from __future__ import annotations

from typing import List

import sqlalchemy as sa
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx
from backend.app.models.communication import CommunicationThread
from backend.app.models.own_company import OwnCompany
from backend.app.models.tenant import Tenant
from backend.app.services.communications_access import assert_comm_feature_access

from ..schemas import CommunicationMessageTemplateOut
from .tenant_settings import _comm_settings_root

__all__ = [
    "_get_thread_or_404",
    "_default_own_company_id_for_tenant",
    "_ensure_thread_matches_own_company_scope",
    "_get_tenant_or_404",
    "_feature_for_channel",
    "_message_templates_for_user",
    "_require_comm_feature",
    "_require_any_comm_feature",
]


async def _get_thread_or_404(db: AsyncSession, tenant_id: str, thread_id: str) -> CommunicationThread:
    thread = await db.get(CommunicationThread, thread_id)
    if thread is None or str(thread.tenant_id) != str(tenant_id):
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread


async def _default_own_company_id_for_tenant(db: AsyncSession, tenant_id: str) -> str | None:
    row = await db.execute(
        sa.select(OwnCompany.id)
        .where(OwnCompany.tenant_id == tenant_id, OwnCompany.is_archived.is_(False))
        .order_by(OwnCompany.created_at.asc())
        .limit(1)
    )
    v = row.scalar_one_or_none()
    return str(v) if v else None


def _ensure_thread_matches_own_company_scope(
    thread: CommunicationThread,
    *,
    own_company_id: str | None,
) -> None:
    if not own_company_id:
        return
    scoped = str(getattr(thread, "own_company_id", None) or "").strip()
    if not scoped:
        return
    if scoped != str(own_company_id).strip():
        raise HTTPException(status_code=404, detail="Thread not found")


async def _get_tenant_or_404(db: AsyncSession, tenant_id: str) -> Tenant:
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


def _feature_for_channel(channel: str | None) -> str:
    ch = str(channel or "").strip().lower()
    return "email" if ch == "email" else "messages"


def _message_templates_for_user(
    tenant: Tenant,
    *,
    user_id: str | None,
    target: str,
) -> List[CommunicationMessageTemplateOut]:
    comm = _comm_settings_root(tenant)
    block = comm.get("messageTemplates")
    rows = block.get("items") if isinstance(block, dict) else None
    if not isinstance(rows, list):
        return []

    normalized_target = str(target or "messages").strip().lower()
    out: List[CommunicationMessageTemplateOut] = []
    for idx, raw in enumerate(rows):
        if not isinstance(raw, dict):
            continue
        enabled = bool(raw.get("enabled", True))
        if not enabled:
            continue
        tpl_target = str(raw.get("target") or "messages").strip().lower()
        if tpl_target not in {"messages", "email", "both"}:
            tpl_target = "messages"
        if tpl_target != "both" and tpl_target != normalized_target:
            continue

        visibility = str(raw.get("visibility") or "private").strip().lower()
        if visibility not in {"private", "company"}:
            visibility = "private"
        owner_user_id = str(raw.get("ownerUserId") or raw.get("owner_user_id") or "").strip() or None
        if visibility == "private" and (not owner_user_id or not user_id or owner_user_id != user_id):
            continue

        out.append(
            CommunicationMessageTemplateOut(
                id=str(raw.get("id") or f"msg_tpl_{idx + 1}"),
                label=str(raw.get("label") or f"Template {idx + 1}"),
                body=str(raw.get("body") or ""),
                visibility=visibility,
                target=tpl_target,
                owner_user_id=owner_user_id,
                enabled=enabled,
            )
        )
    return out


async def _require_comm_feature(
    db: AsyncSession,
    *,
    tenant_id: str,
    current_user: UserCtx,
    feature: str,
) -> Tenant:
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=feature)  # type: ignore[arg-type]
    return tenant


async def _require_any_comm_feature(
    db: AsyncSession,
    *,
    tenant_id: str,
    current_user: UserCtx,
    features: List[str],
) -> Tenant:
    tenant = await _get_tenant_or_404(db, tenant_id)
    allowed = False
    for feature in features:
        try:
            assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=feature)  # type: ignore[arg-type]
            allowed = True
            break
        except HTTPException:
            continue
    if not allowed:
        raise HTTPException(status_code=403, detail="Communications access denied")
    return tenant
