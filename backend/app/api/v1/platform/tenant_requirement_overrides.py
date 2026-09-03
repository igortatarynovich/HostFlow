"""Tenant requirement override admin API (P3B)."""

from __future__ import annotations

from backend.app.auth.trust_role_deps import require_trust_admin, require_trust_read, require_trust_write

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.db.deps import get_db_with_tenant
from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.entity_profile.manifests.recruitment import recruitment_candidate_driver_ce_profile
from backend.app.models.tenant_requirement_override import TenantRequirementOverride
from backend.app.requirement_rules.constants import (
    OVERRIDE_STATUS_ACTIVE,
    OVERRIDE_STATUS_REVOKED,
    RULE_TYPE_DOCUMENT_REQUIRED,
    VALID_CONTEXTS,
)
from backend.app.requirement_rules.registry import build_field_required_rules
from backend.app.requirement_rules.tenant_override_source import (
    TenantOverridePolicyError,
    validate_tenant_override_policy,
)
from backend.app.reference.requirement_policy_parallel_authority_retirement import (
    raise_p3b_document_required_retired,
)
from backend.app.auth.trust_role_deps import TRUST_ADMIN_ROLES

ADMIN_ROLES = TRUST_ADMIN_ROLES

router = APIRouter(
    prefix="/platform/requirement-overrides",
    tags=["requirement-overrides"],
    redirect_slashes=False,
)

class TenantRequirementOverrideIn(BaseModel):
    entity_profile_code: Optional[str] = Field(default=None, max_length=128)
    context: Optional[Literal["intake", "card_save", "transition", "handoff", "readiness"]] = None
    stage_code: Optional[str] = Field(default=None, max_length=128)
    override_kind: Literal["relax", "add", "severity"]
    rule_type: Literal["field_required", "document_required"]
    target_code: str = Field(..., min_length=1, max_length=191)
    level: Optional[Literal["blocking", "warning"]] = None
    reason: str = Field(..., min_length=3, max_length=2000)

class TenantRequirementOverrideOut(BaseModel):
    id: str
    tenant_id: str
    entity_profile_code: Optional[str] = None
    context: Optional[str] = None
    stage_code: Optional[str] = None
    override_kind: str
    rule_type: str
    target_code: str
    level: Optional[str] = None
    status: str
    reason: str

def _canonical_field_targets() -> set[str]:
    manifest = recruitment_candidate_driver_ce_profile()
    profile_view = {
        "profile_code": manifest["profile_code"],
        "fields": manifest["fields"],
    }
    targets: set[str] = set()
    for ctx in VALID_CONTEXTS:
        for row in build_field_required_rules(profile_view, context=ctx):
            code = str(row.get("qualified_code") or "").strip()
            if code:
                targets.add(code)
    return targets

def _row_to_out(row: TenantRequirementOverride) -> TenantRequirementOverrideOut:
    return TenantRequirementOverrideOut(
        id=str(row.id),
        tenant_id=str(row.tenant_id),
        entity_profile_code=row.entity_profile_code,
        context=row.context,
        stage_code=row.stage_code,
        override_kind=str(row.override_kind),
        rule_type=str(row.rule_type),
        target_code=str(row.target_code),
        level=row.level,
        status=str(row.status),
        reason=str(row.reason),
    )

@router.get(
    "",
    response_model=list[TenantRequirementOverrideOut],
    dependencies=[Depends(require_trust_admin())],
)
async def list_tenant_requirement_overrides(
    db_tenant: tuple = Depends(get_db_with_tenant),
) -> list[TenantRequirementOverrideOut]:
    db, tenant_id = db_tenant
    rows = (
        await db.execute(
            select(TenantRequirementOverride)
            .where(TenantRequirementOverride.tenant_id == str(tenant_id))
            .order_by(TenantRequirementOverride.created_at.desc())
        )
    ).scalars().all()
    return [_row_to_out(row) for row in rows]

@router.post(
    "",
    response_model=TenantRequirementOverrideOut,
    dependencies=[Depends(require_trust_admin())],
)
async def create_tenant_requirement_override(
    body: TenantRequirementOverrideIn,
    ctx_user: UserCtx = Depends(get_current_user),
    db_tenant: tuple = Depends(get_db_with_tenant),
) -> TenantRequirementOverrideOut:
    db, tenant_id = db_tenant
    if body.rule_type == RULE_TYPE_DOCUMENT_REQUIRED:
        raise_p3b_document_required_retired()
    payload = body.model_dump()
    try:
        validate_tenant_override_policy(
            payload,
            canonical_field_targets=_canonical_field_targets(),
        )
    except TenantOverridePolicyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    row = TenantRequirementOverride(
        tenant_id=str(tenant_id).strip(),
        entity_profile_code=body.entity_profile_code or DRIVER_CE_PROFILE_CODE,
        context=body.context,
        stage_code=body.stage_code,
        override_kind=body.override_kind,
        rule_type=body.rule_type,
        target_code=str(body.target_code).strip(),
        level=body.level,
        status=OVERRIDE_STATUS_ACTIVE,
        reason=str(body.reason).strip(),
        approved_by_user_id=str(ctx_user.id) if getattr(ctx_user, "id", None) else None,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _row_to_out(row)

@router.patch(
    "/{override_id}/revoke",
    response_model=TenantRequirementOverrideOut,
    dependencies=[Depends(require_trust_admin())],
)
async def revoke_tenant_requirement_override(
    override_id: str,
    db_tenant: tuple = Depends(get_db_with_tenant),
) -> TenantRequirementOverrideOut:
    db, tenant_id = db_tenant
    row = (
        await db.execute(
            select(TenantRequirementOverride).where(
                TenantRequirementOverride.id == str(override_id).strip(),
                TenantRequirementOverride.tenant_id == str(tenant_id).strip(),
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Tenant requirement override not found")
    row.status = OVERRIDE_STATUS_REVOKED
    await db.commit()
    await db.refresh(row)
    return _row_to_out(row)
