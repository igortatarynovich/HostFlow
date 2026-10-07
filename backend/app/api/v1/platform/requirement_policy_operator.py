"""Requirement Policy Operator API (RPM-2).

GET/PUT /platform/requirement-policy-operator
Documents-first require/remove → R5 tenant_delta → same evaluate D4 uses.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.auth.trust_role_deps import require_trust_admin, require_trust_read
from backend.app.db.deps import get_db_with_tenant
from backend.app.reference.document_policy_tenant_overlay_repository import (
    OverlayRevisionConflict,
    load_tenant_overlay,
    save_tenant_overlay,
)
from backend.app.reference.requirement_policy_operator import (
    CONTRACT_ID,
    EMPTY_REVISION,
    OperatorOverlayError,
    build_operator_view,
    compile_operator_overlay_delta,
    validate_reason,
)

router = APIRouter(
    prefix="/platform/requirement-policy-operator",
    tags=["requirement-policy-operator"],
    redirect_slashes=False,
)


class OperatorPutIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    require: list[str] = Field(default_factory=list)
    remove: list[str] = Field(default_factory=list)
    reason: str = Field(..., min_length=3, max_length=2000)
    expected_revision: int = Field(..., ge=0)
    preview_context: Optional[dict[str, Any]] = None


class OperatorViewOut(BaseModel):
    contract_id: str
    write_authority: str
    base: dict[str, Any]
    override: dict[str, Any]
    reason: str
    revision: int
    result: dict[str, Any]
    preview_context: dict[str, Any]
    pack_defaults: dict[str, Any]


def _ensure_tenant(ctx: UserCtx, tenant_id: str) -> None:
    token_tenant = (ctx.tenant_id or "").strip()
    if token_tenant and token_tenant != tenant_id:
        raise HTTPException(status_code=403, detail="Forbidden for tenant")


def _snapshot_to_view(
    *,
    snap_revision: int,
    snap_delta: dict[str, Any],
    snap_reason: str,
    preview_context: Optional[dict[str, Any]],
) -> dict[str, Any]:
    return build_operator_view(
        delta=snap_delta,
        reason=snap_reason,
        revision=snap_revision,
        preview_context=preview_context,
    )


@router.get(
    "",
    response_model=OperatorViewOut,
    dependencies=[Depends(require_trust_read())],
)
async def get_requirement_policy_operator(
    residency_status: Optional[str] = Query(default=None),
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple[AsyncSession, Any] = Depends(get_db_with_tenant),
) -> dict[str, Any]:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    preview: dict[str, Any] = {}
    if residency_status:
        preview["residency_status"] = residency_status.strip()
    snap = await load_tenant_overlay(db, tenant_id=tenant_id)
    if snap is None:
        return _snapshot_to_view(
            snap_revision=EMPTY_REVISION,
            snap_delta={},
            snap_reason="",
            preview_context=preview,
        )
    return _snapshot_to_view(
        snap_revision=snap.revision,
        snap_delta=snap.delta,
        snap_reason=snap.reason,
        preview_context=preview,
    )


@router.put(
    "",
    response_model=OperatorViewOut,
    dependencies=[Depends(require_trust_admin())],
)
async def put_requirement_policy_operator(
    body: OperatorPutIn,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple[AsyncSession, Any] = Depends(get_db_with_tenant),
) -> dict[str, Any]:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    _ensure_tenant(ctx, tenant_id)
    try:
        reason = validate_reason(body.reason)
        delta = compile_operator_overlay_delta(
            require=body.require, remove=body.remove
        )
    except OperatorOverlayError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    actor_id = str(ctx.id) if getattr(ctx, "id", None) else None
    try:
        snap = await save_tenant_overlay(
            db,
            tenant_id=tenant_id,
            delta=delta,
            reason=reason,
            expected_revision=int(body.expected_revision),
            actor_id=actor_id,
        )
        await db.commit()
    except OverlayRevisionConflict as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail={
                "error": "overlay_revision_conflict",
                "current_revision": exc.current_revision,
                "contract_id": CONTRACT_ID,
            },
        ) from exc
    except Exception:
        await db.rollback()
        raise

    return _snapshot_to_view(
        snap_revision=snap.revision,
        snap_delta=snap.delta,
        snap_reason=snap.reason,
        preview_context=body.preview_context,
    )
