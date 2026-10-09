"""Shared logic for hiring pipeline gates (mounted under settings/team and tenants/me)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
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
    policy_revision: Optional[int] = None


class HiringPipelineGatesPatch(BaseModel):
    expected_policy_revision: Optional[int] = None
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
    from backend.app.models.process_engine import PeProcessProfile
    from backend.app.process_engine.constants import RECRUITMENT_MODULE
    from backend.app.process_engine.manifests.recruitment import DEFAULT_PROFILE_CODE

    revision = await db.scalar(
        select(PeProcessProfile.policy_revision).where(
            PeProcessProfile.tenant_id == tenant_id,
            PeProcessProfile.module == RECRUITMENT_MODULE,
            PeProcessProfile.code == DEFAULT_PROFILE_CODE,
        )
    )
    return HiringPipelineGatesPublicOut.model_validate(
        {**serialize_gates_public(gates), "policy_revision": revision}
    )


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
    patch_raw = payload.model_dump(exclude_unset=True, exclude={"expected_policy_revision"})
    sanitized = sanitize_hiring_gates_patch(patch_raw)
    if not sanitized:
        gates = hiring_gates_from_tenant_settings(tenant.settings if isinstance(tenant.settings, dict) else None)
        return HiringPipelineGatesPublicOut.model_validate(serialize_gates_public(gates))
    settings_payload = dict(tenant.settings or {})
    new_settings = patch_hiring_gates_settings_dict(settings_payload, sanitized)
    from backend.app.models.mixins import now_utc
    from backend.app.models.process_engine import PeProcessProfile
    from backend.app.process_engine.constants import RECRUITMENT_MODULE
    from backend.app.process_engine.manifests.recruitment import (
        DEFAULT_PROFILE_CODE,
        RECRUITMENT_PIPELINE_GATES_RULE_CODE,
    )
    from backend.app.process_engine.policy_safety import (
        ProcessPolicyRevisionConflictError,
        ProcessPolicySafetyError,
        correct_hiring_pipeline_gates_policy,
    )

    profile = await db.scalar(
        select(PeProcessProfile).where(
            PeProcessProfile.tenant_id == tenant_id,
            PeProcessProfile.module == RECRUITMENT_MODULE,
            PeProcessProfile.code == DEFAULT_PROFILE_CODE,
        )
    )
    if profile is None:
        # Compatibility for tenants created before Process Engine bootstrap. The
        # bootstrap participates in this request transaction and does not commit.
        from backend.app.process_engine.seed import ensure_recruitment_process_engine_defaults

        await ensure_recruitment_process_engine_defaults(db, tenant_id)
        profile = await db.scalar(
            select(PeProcessProfile).where(
                PeProcessProfile.tenant_id == tenant_id,
                PeProcessProfile.module == RECRUITMENT_MODULE,
                PeProcessProfile.code == DEFAULT_PROFILE_CODE,
            )
        )
    if profile is None:
        raise HTTPException(status_code=409, detail="Default Process Profile is not initialized")

    # Backward-compatible transition: old clients may omit the token. We capture the
    # current revision before taking the service lock, so a concurrent correction still
    # produces a stale-revision conflict. GET exposes the revision for explicit clients.
    expected_revision = (
        int(payload.expected_policy_revision)
        if payload.expected_policy_revision is not None
        else int(profile.policy_revision or 1)
    )
    tenant.settings = new_settings
    tenant.updated_at = now_utc()
    gates = hiring_gates_from_tenant_settings(new_settings)
    actor_id = str(ctx.sub or "").strip()
    try:
        await correct_hiring_pipeline_gates_policy(
            db,
            tenant_id=tenant_id,
            process_profile_id=str(profile.id),
            expected_policy_revision=expected_revision,
            gates=gates,
            reason="Hiring Pipeline Gates updated through tenant settings",
            actor_id=actor_id,
            source="settings.hiring_pipeline_gates",
            rule_code=RECRUITMENT_PIPELINE_GATES_RULE_CODE,
        )
        await db.commit()
    except ProcessPolicyRevisionConflictError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail={
                "message": str(exc),
                "expected_policy_revision": exc.expected_revision,
                "current_policy_revision": exc.current_revision,
            },
        ) from exc
    except ProcessPolicySafetyError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return HiringPipelineGatesPublicOut.model_validate(
        {**serialize_gates_public(gates), "policy_revision": int(profile.policy_revision)}
    )
