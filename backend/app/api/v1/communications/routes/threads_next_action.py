"""HTTP surface for the per-thread "what to do next" service.

Closes G-8 stage 2.3 — see `docs/specs/operations-loop.md`. Mounted as
`GET /api/v1/communications/threads/{thread_id}/next-action` (the
communications router uses prefix `/communications`, see
`backend/app/api/v1/communications/__init__.py`). The response is the
same canonical `NextActionDTO` shape that the candidate / lead /
vacancy / document variants return, so the frontend `<NextActionBadge>`
renders without any branching.

Auth gating mirrors `GET /communications/threads/{thread_id}` in
`routes/threads.py:get_thread`:

  * tenant + thread existence (404 if missing);
  * own-company scope (`_ensure_thread_matches_own_company_scope`);
  * channel-specific feature access via `assert_comm_feature_access`.

We intentionally do NOT add an extra `require_roles` gate — anyone who
can already read the thread should be able to ask "what's the next
action?". The dependency wall is exactly the same as the read endpoint.
"""

from __future__ import annotations

from typing import Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.utils.own_company import resolve_active_own_company_id_optional
from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.db.deps import get_db_with_tenant
from backend.app.services.communications_access import assert_comm_feature_access
from backend.app.services.next_action import NextActionDTO, compute_thread_next_action

from .._helpers.access import (
    _ensure_thread_matches_own_company_scope,
    _feature_for_channel,
    _get_tenant_or_404,
    _get_thread_or_404,
)


router = APIRouter(tags=["communications"])


@router.get(
    "/threads/{thread_id}/next-action",
    response_model=NextActionDTO,
    summary="Resolve the single primary 'what to do next' CTA for a communication thread",
    description=(
        "Returns one canonical NextActionDTO. The DTO shape is stable across "
        "all branches (archived / deleted / closed / sla_overdue / reminder / "
        "unread / awaiting_reply / sla_due_soon / snoozed / idle) so the "
        "frontend always renders the same component. See "
        "`docs/specs/operations-loop.md` §G-8 for the precedence rules and "
        "reason codes."
    ),
)
async def get_thread_next_action(
    thread_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
    own_company_id: Optional[str] = Depends(resolve_active_own_company_id_optional),
) -> NextActionDTO:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)

    # Mirror `get_thread` exactly — every gate the read endpoint enforces
    # we re-enforce here. If `_get_thread_or_404` raises, we propagate.
    tenant = await _get_tenant_or_404(db, tenant_id)
    thread = await _get_thread_or_404(db, tenant_id, thread_id)
    _ensure_thread_matches_own_company_scope(thread, own_company_id=own_company_id)
    assert_comm_feature_access(
        tenant=tenant,
        current_user=current_user,
        tenant_id=tenant_id,
        feature=_feature_for_channel(thread.channel),  # type: ignore[arg-type]
    )

    return await compute_thread_next_action(
        db,
        tenant_id=tenant_id,
        thread_id=thread_id,
    )
