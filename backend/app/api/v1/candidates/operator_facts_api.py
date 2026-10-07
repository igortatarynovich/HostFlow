"""Operator Facts Surface for one candidate and one Employment."""

from __future__ import annotations

from typing import Any, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.candidates.acl import ensure_candidate_access
from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.auth.trust_role_deps import require_trust_read, require_trust_write
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.candidate import Candidate
from backend.app.services.operator_facts_persistence import (
    operator_facts_view_for_candidate,
    preparing_employment_for_candidate,
    save_operator_facts,
)
from backend.app.services.operator_facts_surface import OperatorFactsRejected

router = APIRouter()


async def _candidate(
    db: AsyncSession,
    tenant_id: str,
    candidate_id: str,
) -> Candidate:
    row = await db.scalar(
        select(Candidate).where(
            Candidate.id == candidate_id,
            Candidate.tenant_id == tenant_id,
            Candidate.deleted_at.is_(None),
        )
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return row


@router.get(
    "/{candidate_id}/operator-facts",
    dependencies=[Depends(require_trust_read())],
    summary="Operator facts for this candidate and Employment",
)
async def get_operator_facts(
    candidate_id: UUID,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> dict[str, Any]:
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    candidate_id_str = str(candidate_id)
    await ensure_candidate_access(db, tenant_id_str, candidate_id_str, current_user)
    candidate = await _candidate(db, tenant_id_str, candidate_id_str)
    employment = await preparing_employment_for_candidate(
        db, tenant_id=tenant_id_str, candidate_id=candidate_id_str
    )
    return operator_facts_view_for_candidate(
        candidate,
        employment_id=str(employment.id) if employment is not None else None,
    )


@router.put(
    "/{candidate_id}/operator-facts",
    dependencies=[Depends(require_trust_write())],
    summary="Record operator facts and refresh the legal chain",
)
async def put_operator_facts(
    candidate_id: UUID,
    patch: dict[str, Any],
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> dict[str, Any]:
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    candidate_id_str = str(candidate_id)
    await ensure_candidate_access(db, tenant_id_str, candidate_id_str, current_user)
    candidate = await _candidate(db, tenant_id_str, candidate_id_str)
    actor = str(current_user.sub or "").strip()
    if not actor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="actor is required")
    try:
        return await save_operator_facts(
            db,
            tenant_id=tenant_id_str,
            candidate=candidate,
            patch=patch,
            actor_user_id=actor,
        )
    except OperatorFactsRejected as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
