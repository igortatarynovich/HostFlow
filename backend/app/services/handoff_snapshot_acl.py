"""Who may read GET /handoffs/{id}/snapshot."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, UserCtx
from backend.app.auth.trust_roles import (
    TrustRole,
    is_hr_workspace_actor,
    is_portal_actor,
    normalize_trust_role,
)
from backend.app.models.access import UserCompanyAccess
from backend.app.models.candidate_handoff import CandidateHandoff


async def assert_handoff_snapshot_readable(
    db: AsyncSession,
    *,
    handoff: CandidateHandoff,
    viewer: UserCtx,
    workspace_tenant_id: str,
) -> None:
    """Raise HTTPException if viewer cannot read this handoff snapshot."""
    role = (viewer.role or "").strip().lower()
    trust = normalize_trust_role(role)
    access_context = getattr(viewer, "access_context", None)
    if trust == TrustRole.superadmin.value:
        return

    agency_tid = str(handoff.agency_tenant_id)
    dest = (getattr(handoff, "destination", None) or "client_portal").strip().lower()

    portal = is_portal_actor(role, access_context)
    agency_staff = trust in {
        TrustRole.administrator.value,
        TrustRole.employee.value,
    } and not is_hr_workspace_actor(role) and not portal

    if portal and dest == "internal_hr":
        raise HTTPException(status_code=403, detail="Not allowed to read internal HR handoff snapshot")

    if is_hr_workspace_actor(role):
        if workspace_tenant_id != agency_tid:
            raise HTTPException(status_code=403, detail="Not allowed to read this handoff snapshot")
        if dest != "internal_hr":
            raise HTTPException(status_code=403, detail="Not allowed to read this handoff snapshot")
        return

    if portal:
        uid = str(viewer.sub)
        if handoff.client_company_id:
            row = await db.execute(
                select(UserCompanyAccess.id).where(
                    UserCompanyAccess.user_id == uid,
                    UserCompanyAccess.tenant_id == agency_tid,
                    UserCompanyAccess.company_id == str(handoff.client_company_id),
                ).limit(1)
            )
            if row.scalar_one_or_none() is not None and dest != "internal_hr":
                return
        if handoff.client_tenant_id:
            chk = await db.execute(
                text(
                    "SELECT 1 FROM user_memberships WHERE user_id = :u AND tenant_id = :t LIMIT 1"
                ),
                {"u": uid, "t": str(handoff.client_tenant_id)},
            )
            if chk.first() is not None and dest != "internal_hr":
                return
        raise HTTPException(status_code=403, detail="Not allowed to read this handoff snapshot")

    if agency_staff or trust in {
        TrustRole.administrator.value,
        TrustRole.employee.value,
        TrustRole.superadmin.value,
    } or role in {
        Role.employee.value,
        Role.administrator.value,
        Role.superadmin.value,
    }:
        if workspace_tenant_id != agency_tid:
            raise HTTPException(status_code=403, detail="Not allowed to read this handoff snapshot")
        return

    raise HTTPException(status_code=403, detail="Not allowed to read this handoff snapshot")
