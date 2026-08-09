"""Shared logic for hiring pipeline gates (mounted under settings/team and tenants/me)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, UserCtx
from backend.app.api.v1.tenants import service as tenant_service
from backend.app.services.document_catalog import normalize_doc_type
from backend.app.services.hiring_pipeline_gates import (
    hiring_gates_from_tenant_settings,
    patch_settings_dict as patch_hiring_gates_settings_dict,
    serialize_gates_public,
)


def _ensure_tenant(ctx: UserCtx, tenant_id: str) -> None:
    if (ctx.role or "").strip().lower() == Role.superadmin.value:
        return
    token_tenant = (ctx.tenant_id or "").strip()
    if token_tenant and token_tenant != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden for tenant")


class HiringPipelineGatesPublicOut(BaseModel):
    version: int
    stages_without_doc_pipeline_block: List[str]
    stages_verify_uploads_block_forward: List[str]
    stages_require_vacancy_for_forward: List[str]
    contact_attempt_gate_stages: List[str]
    stages_doc_block_soft_only: List[str]
    non_overridable_doc_types_extra: List[str]
    effective_non_overridable_doc_types: List[str]


class HiringPipelineGatesPatch(BaseModel):
    stages_without_doc_pipeline_block: Optional[List[str]] = None
    stages_verify_uploads_block_forward: Optional[List[str]] = None
    stages_require_vacancy_for_forward: Optional[List[str]] = None
    contact_attempt_gate_stages: Optional[List[str]] = None
    stages_doc_block_soft_only: Optional[List[str]] = None
    non_overridable_doc_types_extra: Optional[List[str]] = None


def sanitize_hiring_gates_patch(raw: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in raw.items():
        if v is None:
            out[k] = None
            continue
        if not isinstance(v, list):
            continue
        if k == "non_overridable_doc_types_extra":
            seen: set[str] = set()
            acc: List[str] = []
            for item in v:
                c = normalize_doc_type(str(item))
                if c and c not in seen:
                    seen.add(c)
                    acc.append(c)
            out[k] = acc
        else:
            acc2: List[str] = []
            for item in v:
                s = str(item).strip().lower()
                if s and len(s) <= 64:
                    acc2.append(s)
            out[k] = acc2
    return out


from backend.app.auth.trust_role_deps import TRUST_READ_ROLES
HIRING_GATES_READ_ROLES = TRUST_READ_ROLES


async def get_hiring_pipeline_gates_core(
    ctx: UserCtx,
    db_tenant: Tuple[AsyncSession, UUID],
) -> HiringPipelineGatesPublicOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    tenant = await tenant_service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    gates = hiring_gates_from_tenant_settings(tenant.settings if isinstance(tenant.settings, dict) else None)
    return HiringPipelineGatesPublicOut.model_validate(serialize_gates_public(gates))


async def patch_hiring_pipeline_gates_core(
    payload: HiringPipelineGatesPatch,
    ctx: UserCtx,
    db_tenant: Tuple[AsyncSession, UUID],
) -> HiringPipelineGatesPublicOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    tenant = await tenant_service.get_tenant(db, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    patch_raw = payload.model_dump(exclude_unset=True)
    sanitized = sanitize_hiring_gates_patch(patch_raw)
    if not sanitized:
        gates = hiring_gates_from_tenant_settings(tenant.settings if isinstance(tenant.settings, dict) else None)
        return HiringPipelineGatesPublicOut.model_validate(serialize_gates_public(gates))
    settings_payload = dict(tenant.settings or {})
    new_settings = patch_hiring_gates_settings_dict(settings_payload, sanitized)
    tenant = await tenant_service.update_tenant(db, tenant, {"settings": new_settings})
    gates = hiring_gates_from_tenant_settings(tenant.settings if isinstance(tenant.settings, dict) else None)
    from backend.app.process_engine.transition_rules_adapter import (
        sync_hiring_gates_to_default_profile_from_tenant_settings,
    )

    await sync_hiring_gates_to_default_profile_from_tenant_settings(
        db, tenant_id=tenant_id, gates=gates
    )
    await db.commit()
    return HiringPipelineGatesPublicOut.model_validate(serialize_gates_public(gates))
