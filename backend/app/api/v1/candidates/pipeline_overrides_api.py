from __future__ import annotations

from typing import Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.candidates.acl import ensure_candidate_access
from backend.app.api.v1.candidates.pipeline_overrides_service import (
    approve_override,
    create_override_request,
    list_overrides,
    reject_override,
    revoke_override,
)
from backend.app.auth.deps import Role, get_current_user, require_roles, UserCtx
from backend.app.auth.hiring_workspace_roles import (
    HIRING_CANDIDATE_MUTATE_ROLES,
    HIRING_CANDIDATE_VIEW_ROLES,
)
from backend.app.core.audit_events import AuditEntityType, AuditEventType
from backend.app.db.deps import get_db_with_tenant
from backend.app.services.audit import log_audit_event
from backend.app.services.tenant_visibility import get_tenant_visibility
from backend.app.services.handoff import is_client_tenant_for_list

router = APIRouter()

_ALLOW_MANAGER_ROLES = HIRING_CANDIDATE_MUTATE_ROLES
_CANDIDATE_VIEW_ROLES = HIRING_CANDIDATE_VIEW_ROLES

APPROVE_OVERRIDE_ROLES = (Role.manager, Role.administrator, Role.superadmin)


class PipelineOverrideCreateIn(BaseModel):
    doc_type_code: Optional[str] = Field(default=None, max_length=128)
    requirement_code: Optional[str] = Field(default=None, max_length=128)
    reason: str = Field(min_length=8, max_length=4000)
    requested_scope: str = Field(default="pipeline", description="pipeline | both")

    @model_validator(mode="after")
    def exactly_one_target(self) -> "PipelineOverrideCreateIn":
        has_doc = bool(str(self.doc_type_code or "").strip())
        has_req = bool(str(self.requirement_code or "").strip())
        if has_doc == has_req:
            raise ValueError("exactly_one_override_target")
        return self


class PipelineOverrideApproveIn(BaseModel):
    granted_scope: str = Field(description="pipeline | both")
    review_note: Optional[str] = Field(default=None, max_length=4000)


class PipelineOverrideReviewNoteIn(BaseModel):
    review_note: Optional[str] = Field(default=None, max_length=4000)


def _map_value_error(exc: Exception) -> HTTPException:
    code = str(exc).strip()
    mapping = {
        "invalid_doc_type": (400, "invalid_doc_type"),
        "doc_type_not_overridable": (400, "doc_type_not_overridable"),
        "requirement_not_overridable": (400, "requirement_not_overridable"),
        "missing_override_target": (400, "missing_override_target"),
        "ambiguous_override_target": (400, "ambiguous_override_target"),
        "exactly_one_override_target": (400, "exactly_one_override_target"),
        "invalid_requested_scope": (400, "invalid_requested_scope"),
        "invalid_granted_scope": (400, "invalid_granted_scope"),
        "reason_too_short": (400, "reason_too_short"),
        "reason_too_long": (400, "reason_too_long"),
        "pending_exists": (409, "pending_override_exists"),
        "not_found": (404, "override_not_found"),
        "not_pending": (409, "override_not_pending"),
        "not_approved": (409, "override_not_approved"),
    }
    if code in mapping:
        st, detail = mapping[code]
        return HTTPException(status_code=st, detail=detail)
    return HTTPException(status_code=400, detail=code or "bad_request")


@router.get(
    "/{candidate_id}/pipeline-overrides",
    dependencies=[Depends(require_roles(*_CANDIDATE_VIEW_ROLES))],
)
async def get_pipeline_overrides(
    candidate_id: UUID,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    visibility = get_tenant_visibility(db, tenant_id_str)
    await ensure_candidate_access(db, tenant_id_str, str(candidate_id), current_user)

    role = (current_user.role or "").lower()
    if role in (Role.client_manager.value, Role.client_processor.value):
        return {"items": []}

    client_tenant = await is_client_tenant_for_list(db, tenant_id_str)
    from backend.app.api.v1.candidates import repo as cand_repo

    row = await cand_repo.get_candidate_with_labels(
        db,
        tenant_id=tenant_id_str,
        candidate_id=str(candidate_id),
        visibility=visibility,
        is_client_tenant=client_tenant,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    items = await list_overrides(db, tenant_id=tenant_id_str, candidate_id=str(candidate_id))
    return {"items": items}


@router.post(
    "/{candidate_id}/pipeline-overrides",
    dependencies=[Depends(require_roles(*_ALLOW_MANAGER_ROLES))],
    status_code=status.HTTP_201_CREATED,
)
async def post_pipeline_override(
    candidate_id: UUID,
    body: PipelineOverrideCreateIn,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    visibility = get_tenant_visibility(db, tenant_id_str)
    await ensure_candidate_access(db, tenant_id_str, str(candidate_id), current_user)

    role = (current_user.role or "").lower()
    if role in (Role.client_manager.value, Role.client_processor.value):
        raise HTTPException(status_code=403, detail="Forbidden")

    client_tenant = await is_client_tenant_for_list(db, tenant_id_str)
    from backend.app.api.v1.candidates import repo as cand_repo

    row = await cand_repo.get_candidate_with_labels(
        db,
        tenant_id=tenant_id_str,
        candidate_id=str(candidate_id),
        visibility=visibility,
        is_client_tenant=client_tenant,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    try:
        created = await create_override_request(
            db,
            tenant_id=tenant_id_str,
            candidate_id=str(candidate_id),
            actor_id=current_user.sub,
            doc_type_code=body.doc_type_code,
            requirement_code=body.requirement_code,
            reason=body.reason,
            requested_scope=body.requested_scope,
        )
    except ValueError as e:
        raise _map_value_error(e) from e

    await log_audit_event(
        db,
        tenant_id=tenant_id_str,
        event_type=AuditEventType.pipeline_override_requested,
        entity_type=AuditEntityType.candidate,
        entity_id=str(candidate_id),
        actor_id=current_user.sub,
        payload={
            "override_id": created["id"],
            "doc_type_code": created.get("doc_type_code"),
            "requirement_code": created.get("requirement_code"),
            "requested_scope": created["requested_scope"],
            "reason": created["reason"],
            "requested_by_user_id": created.get("requested_by_user_id"),
        },
    )
    await db.commit()
    return created


@router.post(
    "/{candidate_id}/pipeline-overrides/{override_id}/approve",
    dependencies=[Depends(require_roles(*APPROVE_OVERRIDE_ROLES))],
)
async def post_pipeline_override_approve(
    candidate_id: UUID,
    override_id: UUID,
    body: PipelineOverrideApproveIn,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    visibility = get_tenant_visibility(db, tenant_id_str)
    await ensure_candidate_access(db, tenant_id_str, str(candidate_id), current_user)

    role = (current_user.role or "").lower()
    if role in (Role.client_manager.value, Role.client_processor.value):
        raise HTTPException(status_code=403, detail="Forbidden")

    client_tenant = await is_client_tenant_for_list(db, tenant_id_str)
    from backend.app.api.v1.candidates import repo as cand_repo

    row = await cand_repo.get_candidate_with_labels(
        db,
        tenant_id=tenant_id_str,
        candidate_id=str(candidate_id),
        visibility=visibility,
        is_client_tenant=client_tenant,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    try:
        updated = await approve_override(
            db,
            tenant_id=tenant_id_str,
            candidate_id=str(candidate_id),
            override_id=str(override_id),
            actor_id=current_user.sub,
            granted_scope=body.granted_scope,
            review_note=body.review_note,
        )
    except ValueError as e:
        raise _map_value_error(e) from e

    await log_audit_event(
        db,
        tenant_id=tenant_id_str,
        event_type=AuditEventType.pipeline_override_approved,
        entity_type=AuditEntityType.candidate,
        entity_id=str(candidate_id),
        actor_id=current_user.sub,
        payload={
            "override_id": updated["id"],
            "doc_type_code": updated.get("doc_type_code"),
            "requirement_code": updated.get("requirement_code"),
            "granted_scope": updated["granted_scope"],
            "review_note": updated.get("review_note"),
            "reviewed_by_user_id": updated.get("reviewed_by_user_id"),
            "reviewed_at": updated.get("reviewed_at"),
        },
    )
    await db.commit()
    return updated


@router.post(
    "/{candidate_id}/pipeline-overrides/{override_id}/reject",
    dependencies=[Depends(require_roles(*APPROVE_OVERRIDE_ROLES))],
)
async def post_pipeline_override_reject(
    candidate_id: UUID,
    override_id: UUID,
    body: PipelineOverrideReviewNoteIn,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    visibility = get_tenant_visibility(db, tenant_id_str)
    await ensure_candidate_access(db, tenant_id_str, str(candidate_id), current_user)

    role = (current_user.role or "").lower()
    if role in (Role.client_manager.value, Role.client_processor.value):
        raise HTTPException(status_code=403, detail="Forbidden")

    client_tenant = await is_client_tenant_for_list(db, tenant_id_str)
    from backend.app.api.v1.candidates import repo as cand_repo

    row = await cand_repo.get_candidate_with_labels(
        db,
        tenant_id=tenant_id_str,
        candidate_id=str(candidate_id),
        visibility=visibility,
        is_client_tenant=client_tenant,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    try:
        updated = await reject_override(
            db,
            tenant_id=tenant_id_str,
            candidate_id=str(candidate_id),
            override_id=str(override_id),
            actor_id=current_user.sub,
            review_note=body.review_note,
        )
    except ValueError as e:
        raise _map_value_error(e) from e

    await log_audit_event(
        db,
        tenant_id=tenant_id_str,
        event_type=AuditEventType.pipeline_override_rejected,
        entity_type=AuditEntityType.candidate,
        entity_id=str(candidate_id),
        actor_id=current_user.sub,
        payload={
            "override_id": updated["id"],
            "doc_type_code": updated.get("doc_type_code"),
            "requirement_code": updated.get("requirement_code"),
            "review_note": updated.get("review_note"),
            "reviewed_by_user_id": updated.get("reviewed_by_user_id"),
            "reviewed_at": updated.get("reviewed_at"),
        },
    )
    await db.commit()
    return updated


@router.post(
    "/{candidate_id}/pipeline-overrides/{override_id}/revoke",
    dependencies=[Depends(require_roles(*APPROVE_OVERRIDE_ROLES))],
)
async def post_pipeline_override_revoke(
    candidate_id: UUID,
    override_id: UUID,
    body: PipelineOverrideReviewNoteIn,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
):
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    visibility = get_tenant_visibility(db, tenant_id_str)
    await ensure_candidate_access(db, tenant_id_str, str(candidate_id), current_user)

    role = (current_user.role or "").lower()
    if role in (Role.client_manager.value, Role.client_processor.value):
        raise HTTPException(status_code=403, detail="Forbidden")

    client_tenant = await is_client_tenant_for_list(db, tenant_id_str)
    from backend.app.api.v1.candidates import repo as cand_repo

    row = await cand_repo.get_candidate_with_labels(
        db,
        tenant_id=tenant_id_str,
        candidate_id=str(candidate_id),
        visibility=visibility,
        is_client_tenant=client_tenant,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    try:
        updated = await revoke_override(
            db,
            tenant_id=tenant_id_str,
            candidate_id=str(candidate_id),
            override_id=str(override_id),
            actor_id=current_user.sub,
            review_note=body.review_note,
        )
    except ValueError as e:
        raise _map_value_error(e) from e

    await log_audit_event(
        db,
        tenant_id=tenant_id_str,
        event_type=AuditEventType.pipeline_override_revoked,
        entity_type=AuditEntityType.candidate,
        entity_id=str(candidate_id),
        actor_id=current_user.sub,
        payload={
            "override_id": updated["id"],
            "doc_type_code": updated.get("doc_type_code"),
            "requirement_code": updated.get("requirement_code"),
            "review_note": updated.get("review_note"),
            "reviewed_by_user_id": updated.get("reviewed_by_user_id"),
            "reviewed_at": updated.get("reviewed_at"),
        },
    )
    await db.commit()
    return updated
