"""Who may read GET /handoffs/{id}/snapshot."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, UserCtx
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
    if role == Role.superadmin.value:
        return

    agency_tid = str(handoff.agency_tenant_id)
    dest = (getattr(handoff, "destination", None) or "client_portal").strip().lower()

    client_roles = {Role.client_processor.value, Role.client_manager.value}
    agency_staff_roles = {
        Role.administrator.value,
        Role.supervisor.value,
        Role.recruiter.value,
        Role.compliance_officer.value,
    }

    if role in client_roles and dest == "internal_hr":
        raise HTTPException(status_code=403, detail="Not allowed to read internal HR handoff snapshot")

    if role == Role.hr_officer.value:
        if workspace_tenant_id != agency_tid:
            raise HTTPException(status_code=403, detail="Not allowed to read this handoff snapshot")
        if dest != "internal_hr":
            raise HTTPException(status_code=403, detail="Not allowed to read this handoff snapshot")
        return

    if role in client_roles:
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

    if role in agency_staff_roles:
        if workspace_tenant_id != agency_tid:
            raise HTTPException(status_code=403, detail="Not allowed to read this handoff snapshot")
        return

    raise HTTPException(status_code=403, detail="Not allowed to read this handoff snapshot")
