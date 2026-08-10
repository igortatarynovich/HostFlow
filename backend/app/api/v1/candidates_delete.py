from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.auth.trust_role_deps import require_trust_admin, require_trust_read, require_trust_write
from backend.app.auth.trust_roles import is_recruiter_preset_actor, is_team_lead_org_actor
from backend.app.auth.deps import Role, UserCtx, get_current_user
from backend.app.db.deps import get_db_with_tenant
from backend.app.schemas.candidate_delete_request import (
    CandidateDeleteDecision,
    CandidateDeleteRequestCreate,
    CandidateDeleteRequestOut,
)
from backend.app.services import candidate_deletion as deletion_service
from backend.app.api.v1.candidates.acl import ensure_candidate_access

router = APIRouter(prefix="/api/v1", tags=["candidate-delete"], redirect_slashes=False)


@router.post(
    "/candidates/{candidate_id}/delete-request",
    response_model=CandidateDeleteRequestOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_trust_write())],
)
async def request_delete(
    candidate_id: str,
    payload: CandidateDeleteRequestCreate,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    if is_recruiter_preset_actor(ctx.role, getattr(ctx, "preset_id", None)):
        await ensure_candidate_access(db, tenant_id, candidate_id, ctx)
    try:
        request = await deletion_service.create_delete_request(
            db,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            requested_by=ctx.sub,
            reason=payload.reason,
        )
        await db.commit()
    except deletion_service.CandidateDeleteError as exc:
        await db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return CandidateDeleteRequestOut.model_validate(request)


@router.get(
    "/delete-requests",
    response_model=list[CandidateDeleteRequestOut],
    dependencies=[Depends(require_trust_write())],
)
async def list_requests(
    status: str | None = Query(default=None),
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    supervisor_filter = ctx.sub if is_team_lead_org_actor(ctx.role, getattr(ctx, "preset_id", None)) else None
    requests = await deletion_service.list_requests(
        db,
        tenant_id=tenant_id,
        status=status,
        supervisor_id=supervisor_filter,
    )
    return [CandidateDeleteRequestOut.model_validate(req) for req in requests]


async def _resolve(
    approve: bool,
    request_id: str,
    payload: CandidateDeleteDecision,
    ctx: UserCtx,
    db_tenant,
):
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    try:
        request = await deletion_service.resolve_request(
            db,
            tenant_id=tenant_id,
            request_id=request_id,
            actor_id=ctx.sub,
            approve=approve,
            comment=payload.comment,
        )
        await db.commit()
    except deletion_service.CandidateDeleteError as exc:
        await db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return CandidateDeleteRequestOut.model_validate(request)


@router.post(
    "/delete-requests/{request_id}/approve",
    response_model=CandidateDeleteRequestOut,
    dependencies=[Depends(require_trust_write())],
)
async def approve_request(
    request_id: str,
    payload: CandidateDeleteDecision,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    return await _resolve(True, request_id, payload, ctx, db_tenant)


@router.post(
    "/delete-requests/{request_id}/reject",
    response_model=CandidateDeleteRequestOut,
    dependencies=[Depends(require_trust_write())],
)
async def reject_request(
    request_id: str,
    payload: CandidateDeleteDecision,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    return await _resolve(False, request_id, payload, ctx, db_tenant)
