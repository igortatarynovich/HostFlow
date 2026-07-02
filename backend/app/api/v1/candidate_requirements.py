"""Candidate Requirements API — confirm requirements via Candidate Evidence."""

from __future__ import annotations

import uuid
from typing import Any, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.candidates.acl import ensure_candidate_access
from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.candidate import Candidate
from backend.app.services.candidate_evidence_service import (
    approve_evidence,
    build_requirements_checklist,
    link_document_to_evidence,
    reject_evidence,
    replace_evidence,
    select_evidence_variant,
    serialize_candidate_evidence,
)
from backend.app.services.requirements_workspace_service import build_requirements_workspace
from backend.app.services.recruitment_handoff_write_guard import (
    RECRUITMENT_LOCK_OVERRIDE_ROLES,
    is_recruitment_recruiter_write_locked_by_handoff,
)

router = APIRouter(prefix="/candidates", tags=["candidate-requirements"], redirect_slashes=False)

WRITE_ROLES = (Role.manager, Role.admin, Role.recruiter, Role.supervisor)
RESTRICTED_ROLES = {
    Role.recruiter.value,
    Role.supervisor.value,
    Role.manager.value,
}


class SelectEvidenceRequest(BaseModel):
    evidence_variant_code: str = Field(..., min_length=1)


class LinkDocumentRequest(BaseModel):
    document_id: str = Field(..., min_length=1)
    role: Optional[str] = None


class RejectEvidenceRequest(BaseModel):
    reason: Optional[str] = None


async def _ensure_candidate_write(
    db: AsyncSession,
    tenant_id: str,
    candidate_id: str,
    user: UserCtx,
) -> Candidate:
    if user.role in RESTRICTED_ROLES:
        await ensure_candidate_access(db, tenant_id, candidate_id, user)

    candidate = await db.get(Candidate, candidate_id)
    if not candidate or str(candidate.tenant_id) != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    role = str(getattr(user, "role", "") or "")
    locked, lock_reason = await is_recruitment_recruiter_write_locked_by_handoff(
        db,
        agency_tenant_id=tenant_id,
        candidate_id=candidate_id,
    )
    if locked and role not in RECRUITMENT_LOCK_OVERRIDE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Recruitment locked ({lock_reason or 'handoff'}): requirement evidence cannot be changed",
        )
    return candidate


@router.get(
    "/{candidate_id}/requirements/checklist",
    dependencies=[Depends(require_roles(*WRITE_ROLES, Role.viewer, Role.compliance_officer))],
)
async def get_requirements_checklist(
    candidate_id: uuid.UUID,
    db_tenant: Tuple[AsyncSession, uuid.UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> dict[str, Any]:
    db, tenant_id = db_tenant
    tenant_str = str(tenant_id)
    if current_user.role in RESTRICTED_ROLES:
        await ensure_candidate_access(db, tenant_str, str(candidate_id), current_user)

    candidate = await db.get(Candidate, str(candidate_id))
    if not candidate or str(candidate.tenant_id) != tenant_str:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    return await build_requirements_checklist(db, tenant_id=tenant_str, candidate=candidate)


@router.get(
    "/{candidate_id}/requirements/workspace",
    dependencies=[Depends(require_roles(*WRITE_ROLES, Role.viewer, Role.compliance_officer))],
)
async def get_requirements_workspace(
    candidate_id: uuid.UUID,
    db_tenant: Tuple[AsyncSession, uuid.UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> dict[str, Any]:
    db, tenant_id = db_tenant
    tenant_str = str(tenant_id)
    if current_user.role in RESTRICTED_ROLES:
        await ensure_candidate_access(db, tenant_str, str(candidate_id), current_user)

    candidate = await db.get(Candidate, str(candidate_id))
    if not candidate or str(candidate.tenant_id) != tenant_str:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    return await build_requirements_workspace(
        db,
        tenant_id=tenant_str,
        candidate=candidate,
        user_role=str(getattr(current_user, "role", "") or ""),
    )


@router.post(
    "/{candidate_id}/requirements/{requirement_code}/select-evidence",
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def post_select_evidence(
    candidate_id: uuid.UUID,
    requirement_code: str,
    payload: SelectEvidenceRequest,
    db_tenant: Tuple[AsyncSession, uuid.UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> dict[str, Any]:
    db, tenant_id = db_tenant
    tenant_str = str(tenant_id)
    await _ensure_candidate_write(db, tenant_str, str(candidate_id), current_user)

    row = await select_evidence_variant(
        db,
        tenant_id=tenant_str,
        candidate_id=str(candidate_id),
        requirement_code=requirement_code,
        evidence_variant_code=payload.evidence_variant_code,
        user_id=str(current_user.sub),
    )
    payload_out = serialize_candidate_evidence(row)
    await db.commit()
    return payload_out


@router.post(
    "/{candidate_id}/requirements/evidence/{evidence_id}/documents",
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def post_link_document(
    candidate_id: uuid.UUID,
    evidence_id: uuid.UUID,
    payload: LinkDocumentRequest,
    db_tenant: Tuple[AsyncSession, uuid.UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> dict[str, Any]:
    db, tenant_id = db_tenant
    tenant_str = str(tenant_id)
    await _ensure_candidate_write(db, tenant_str, str(candidate_id), current_user)

    await link_document_to_evidence(
        db,
        tenant_id=tenant_str,
        evidence_id=str(evidence_id),
        document_id=payload.document_id,
        user_id=str(current_user.sub),
        role=payload.role,
    )
    await db.commit()
    return {"linked": True, "document_id": payload.document_id, "evidence_id": str(evidence_id)}


@router.post(
    "/{candidate_id}/requirements/evidence/{evidence_id}/approve",
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def post_approve_evidence(
    candidate_id: uuid.UUID,
    evidence_id: uuid.UUID,
    db_tenant: Tuple[AsyncSession, uuid.UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> dict[str, Any]:
    db, tenant_id = db_tenant
    tenant_str = str(tenant_id)
    await _ensure_candidate_write(db, tenant_str, str(candidate_id), current_user)

    row = await approve_evidence(
        db,
        tenant_id=tenant_str,
        evidence_id=str(evidence_id),
        user_id=str(current_user.sub),
    )
    payload_out = serialize_candidate_evidence(row)
    await db.commit()
    return payload_out


@router.post(
    "/{candidate_id}/requirements/evidence/{evidence_id}/reject",
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def post_reject_evidence(
    candidate_id: uuid.UUID,
    evidence_id: uuid.UUID,
    payload: RejectEvidenceRequest,
    db_tenant: Tuple[AsyncSession, uuid.UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> dict[str, Any]:
    db, tenant_id = db_tenant
    tenant_str = str(tenant_id)
    await _ensure_candidate_write(db, tenant_str, str(candidate_id), current_user)

    row = await reject_evidence(
        db,
        tenant_id=tenant_str,
        evidence_id=str(evidence_id),
        user_id=str(current_user.sub),
        reason=payload.reason,
    )
    payload_out = serialize_candidate_evidence(row)
    await db.commit()
    return payload_out


@router.post(
    "/{candidate_id}/requirements/{requirement_code}/replace-evidence",
    dependencies=[Depends(require_roles(*WRITE_ROLES))],
)
async def post_replace_evidence(
    candidate_id: uuid.UUID,
    requirement_code: str,
    payload: SelectEvidenceRequest,
    db_tenant: Tuple[AsyncSession, uuid.UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> dict[str, Any]:
    db, tenant_id = db_tenant
    tenant_str = str(tenant_id)
    await _ensure_candidate_write(db, tenant_str, str(candidate_id), current_user)

    row = await replace_evidence(
        db,
        tenant_id=tenant_str,
        candidate_id=str(candidate_id),
        requirement_code=requirement_code,
        evidence_variant_code=payload.evidence_variant_code,
        user_id=str(current_user.sub),
    )
    payload_out = serialize_candidate_evidence(row)
    await db.commit()
    return payload_out
