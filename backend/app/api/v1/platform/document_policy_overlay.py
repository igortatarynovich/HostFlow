"""RPM-2 operator overlay — persist the existing R5 tenant_delta.

GET returns merge_resolved_policy output as ``resolved_policy``. It does not
evaluate a hypothetical candidate. reason is sibling metadata, not part of the delta.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.auth.trust_role_deps import require_trust_admin
from backend.app.db.deps import get_db_with_tenant
from backend.app.reference.document_policy_overlay_store import (
    load_overlay_row,
    overlay_delta_payload,
    pack_version,
    resolved_policy_from_delta,
    save_persisted_tenant_delta,
)

router = APIRouter(
    prefix="/platform/document-policy-overlay",
    tags=["document-policy-overlay"],
    redirect_slashes=False,
)


class DocumentPolicyOverlayIn(BaseModel):
    tenant_delta: dict[str, Any] = Field(default_factory=dict)
    reason: str = Field(..., min_length=3, max_length=2000)


class DocumentPolicyOverlayOut(BaseModel):
    pack_version: str
    tenant_delta: dict[str, Any]
    reason: Optional[str] = None
    resolved_policy: dict[str, Any]
    updated_at: Optional[datetime] = None
    updated_by_user_id: Optional[str] = None


def _empty_out() -> DocumentPolicyOverlayOut:
    return DocumentPolicyOverlayOut(
        pack_version=pack_version(),
        tenant_delta={},
        reason=None,
        resolved_policy=resolved_policy_from_delta(None),
        updated_at=None,
        updated_by_user_id=None,
    )


def _row_out(row) -> DocumentPolicyOverlayOut:
    delta = overlay_delta_payload(row.tenant_delta or {})
    return DocumentPolicyOverlayOut(
        pack_version=pack_version(),
        tenant_delta=delta,
        reason=str(row.reason) if row.reason else None,
        resolved_policy=resolved_policy_from_delta(delta),
        updated_at=row.updated_at,
        updated_by_user_id=row.updated_by_user_id,
    )


@router.get(
    "",
    response_model=DocumentPolicyOverlayOut,
    dependencies=[Depends(require_trust_admin())],
)
async def get_document_policy_overlay(
    db_tenant: tuple = Depends(get_db_with_tenant),
) -> DocumentPolicyOverlayOut:
    db, tenant_id = db_tenant
    row = await load_overlay_row(db, str(tenant_id))
    if row is None:
        return _empty_out()
    return _row_out(row)


@router.put(
    "",
    response_model=DocumentPolicyOverlayOut,
    dependencies=[Depends(require_trust_admin())],
)
async def put_document_policy_overlay(
    body: DocumentPolicyOverlayIn,
    ctx_user: UserCtx = Depends(get_current_user),
    db_tenant: tuple = Depends(get_db_with_tenant),
) -> DocumentPolicyOverlayOut:
    db, tenant_id = db_tenant
    try:
        row = await save_persisted_tenant_delta(
            db,
            tenant_id=str(tenant_id),
            tenant_delta=body.tenant_delta,
            reason=body.reason,
            updated_by_user_id=str(ctx_user.id) if getattr(ctx_user, "id", None) else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _row_out(row)
