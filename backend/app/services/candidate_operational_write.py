"""Recruitment vs HR operational ownership on candidate-owned write paths.

After internal HR accept materializes ``WorkforceEmployee``, recruiters must not mutate
documents / tasks / permits / notes on the candidate dossier (403 ``candidate_readonly``).
Privileged roles (administrator / supervisor / superadmin) and HR on the internal lane keep write access.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.candidate_workforce_lock import is_candidate_locked_by_workforce
from backend.app.services.handoff import is_client_tenant
from backend.app.services.recruitment_handoff_write_guard import (
    RECRUITMENT_LOCK_OVERRIDE_ROLES,
    agency_candidate_has_internal_hr_handoff_lane,
    is_recruitment_recruiter_write_locked_by_handoff,
)
_RECRUITMENT_OPERATIONAL_RECRUITER_ROLES = frozenset({"recruiter", "supervisor", "viewer"})


async def build_candidate_operational_permissions(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    client_tenant: bool,
) -> dict[str, Any]:
    """UI contract: ``operational_owner`` + ``readonly_reason`` on GET /candidates/{id}."""
    if client_tenant:
        return {}
    tid = str(tenant_id or "").strip()
    cid = str(candidate_id or "").strip()
    if not tid or not cid:
        return {"operational_owner": "recruitment", "readonly_reason": None}

    if await is_candidate_locked_by_workforce(db, tenant_id=tid, candidate_id=cid):
        return {
            "operational_owner": "hr",
            "readonly_reason": "workforce_hr_ownership",
        }

    locked, lock_reason = await is_recruitment_recruiter_write_locked_by_handoff(
        db, agency_tenant_id=tid, candidate_id=cid
    )
    if locked:
        return {
            "operational_owner": "hr",
            "readonly_reason": lock_reason or "active_handoff",
        }

    return {"operational_owner": "recruitment", "readonly_reason": None}


async def ensure_candidate_operational_write_allowed(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    role: str,
) -> None:
    """Raise 403 ``candidate_readonly`` when recruitment cannot mutate operational candidate data."""
    tid = str(tenant_id or "").strip()
    cid = str(candidate_id or "").strip()
    if not tid or not cid:
        raise HTTPException(status_code=403, detail="candidate_readonly")

    if await is_client_tenant(db, tid):
        return

    role_l = str(role or "").strip().lower()

    if role_l in RECRUITMENT_LOCK_OVERRIDE_ROLES:
        return

    if role_l == "hr_officer" and await agency_candidate_has_internal_hr_handoff_lane(
        db, agency_tenant_id=tid, candidate_id=cid
    ):
        return

    if await is_candidate_locked_by_workforce(db, tenant_id=tid, candidate_id=cid):
        raise HTTPException(status_code=403, detail="candidate_readonly")

    locked, _ = await is_recruitment_recruiter_write_locked_by_handoff(
        db, agency_tenant_id=tid, candidate_id=cid
    )
    if locked and role_l in _RECRUITMENT_OPERATIONAL_RECRUITER_ROLES:
        raise HTTPException(status_code=403, detail="candidate_readonly")


__all__ = [
    "build_candidate_operational_permissions",
    "ensure_candidate_operational_write_allowed",
]
