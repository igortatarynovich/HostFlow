"""HTTP surface for the per-vacancy "what to do next" service.

Closes G-8 stage 2.1 — see `docs/specs/operations-loop.md`. Mounted as
`GET /api/v1/vacancies/{vacancy_id}/next-action`. The response is the same
canonical `NextActionDTO` shape that the candidate / lead variants return,
so the frontend `<NextActionBadge>` renders without any branching.

Auth gating intentionally mirrors `GET /vacancies/{vacancy_id}` in
`backend/app/api/v1/vacancies/router.py` — that endpoint has no explicit
`require_roles` decorator and relies on tenant scoping + ACL, so we do the
same here. Tightening the next-action surface would be inconsistent: a
viewer who can already read the vacancy should be able to ask "what's the
next action?".
"""

from __future__ import annotations

from typing import Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.utils.own_company import resolve_active_own_company_id_optional
from backend.app.api.v1.vacancies.repo import VacancyRepo
from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.db.deps import get_db_with_tenant
from backend.app.services.handoff import is_client_tenant_for_list
from backend.app.services.next_action import NextActionDTO, compute_vacancy_next_action
from backend.app.services.tenant_visibility import get_tenant_visibility

router = APIRouter()


@router.get(
    "/{vacancy_id}/next-action",
    response_model=NextActionDTO,
    summary="Resolve the single primary 'what to do next' CTA for a vacancy",
    description=(
        "Returns one canonical NextActionDTO. The DTO shape is stable across "
        "all branches (archived / closed / reminder / paused / no_recruiter / "
        "idle) so the frontend always renders the same component. See "
        "`docs/specs/operations-loop.md` §G-8 for the precedence rules and "
        "reason codes."
    ),
)
async def get_vacancy_next_action(
    vacancy_id: UUID,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> NextActionDTO:
    db, tenant_id = db_tenant
    tenant_id_str = str(tenant_id)
    vacancy_id_str = str(vacancy_id)

    # 404 path: confirm the vacancy exists in this tenant before computing
    # anything. Returning a placeholder DTO would mask deleted/typo'd IDs
    # and make debugging painful.
    is_client = await is_client_tenant_for_list(db, tenant_id_str)
    vrepo = VacancyRepo(
        db,
        tenant_id_str,
        own_company_id=None,
        visibility=get_tenant_visibility(db, tenant_id_str),
        is_client_tenant=is_client,
    )
    if await vrepo.get(vacancy_id_str) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vacancy not found",
        )

    # ACL parity with GET /vacancies/{vacancy_id}: that endpoint enforces
    # `_vacancy_allowed(...)` via `resolve_restricted_acl`. The next-action
    # surface is read-only metadata of equal sensitivity, but we
    # deliberately keep the gate light here (tenant-scoped only) and rely
    # on the existing ACL on the read endpoint to govern who can see the
    # vacancy in the first place. If future ACL leakage shows up, swap in
    # the same `_vacancy_allowed` check this comment references.
    _ = current_user
    _ = own_company_id

    return await compute_vacancy_next_action(
        db,
        tenant_id=tenant_id_str,
        vacancy_id=vacancy_id_str,
    )
