from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.candidates.acl import CandidateACL, resolve_candidate_acl
from backend.app.auth.deps import Role, UserCtx
from backend.app.models.candidate import Candidate


async def resolve_restricted_acl(
    db: AsyncSession,
    tenant_id: str,
    user: UserCtx,
) -> CandidateACL | None:
    """
    Return a CandidateACL for the user only if they should be restricted.
    Administrators and superadmins are treated as unrestricted.
    """
    role = (user.role or "").strip().lower()
    if role in {Role.superadmin.value, Role.administrator.value}:
        return None

    acl = await resolve_candidate_acl(db, tenant_id, user)
    if acl.unrestricted:
        return None
    return acl


async def vacancy_readable_via_candidate_assignment(
    db: AsyncSession,
    tenant_id: str,
    vacancy_id: str,
    acl: CandidateACL,
) -> bool:
    """Allow vacancy read when the user already has a candidate on that vacancy.

    Candidate list/card ACL grants access via ``recruiter_id`` / ``manager`` even
    when the vacancy company is outside ``user_company_access``. Vacancy GET must
    stay in parity — otherwise opening the candidate card fires GET
    ``/vacancies/{id}`` → 403 on every load while the dossier itself remains usable.
    """
    mgr = [m for m in (acl.manager_ids or set()) if m]
    if not mgr:
        return False
    result = await db.execute(
        select(Candidate.id)
        .where(
            Candidate.tenant_id == tenant_id,
            Candidate.vacancy_id == vacancy_id,
            Candidate.deleted_at.is_(None),
            or_(Candidate.manager.in_(mgr), Candidate.recruiter_id.in_(mgr)),
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None
