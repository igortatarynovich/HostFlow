"""Read-only professional profile for one candidate.

Does not replace Candidate Card, matching, readiness, handoff, or HR reads.
"""

from __future__ import annotations

from typing import Any, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.candidates.acl import ensure_candidate_access
from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.auth.trust_role_deps import require_trust_read
from backend.app.db.deps import get_db_with_tenant
from backend.app.services.professional_profile import (
    ProfessionalProfileNotFound,
    load_professional_profile,
)

router = APIRouter()


@router.get(
    "/{candidate_id}/professional-profile",
    dependencies=[Depends(require_trust_read())],
    summary="Read-only professional profile projection",
)
async def get_professional_profile(
    candidate_id: UUID,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> dict[str, Any]:
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    candidate_id_str = str(candidate_id)
    await ensure_candidate_access(db, tenant_id_str, candidate_id_str, current_user)
    try:
        return await load_professional_profile(
            db,
            tenant_id=tenant_id_str,
            candidate_id=candidate_id_str,
        )
    except ProfessionalProfileNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found") from exc
