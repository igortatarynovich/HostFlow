"""Admin API for draft intake reminders (cron job)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from backend.app.auth.trust_role_deps import require_trust_admin, require_trust_read, require_trust_write
from backend.app.auth.deps import Role, get_current_user
from backend.app.db.deps import get_db_with_tenant
from backend.app.services.draft_reminders import send_draft_reminders


class DraftRemindersOut(BaseModel):
    sent: int


router = APIRouter(
    prefix="/admin/draft-reminders",
    tags=["admin-draft-reminders"],
)


@router.post(
    "",
    response_model=DraftRemindersOut,
    dependencies=[Depends(require_trust_admin())],
)
async def run_draft_reminders(
    tenant_id: Optional[str] = Query(None, description="Optional tenant filter (superadmin only)"),
    ctx=Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
) -> DraftRemindersOut:
    """
    Send reminder emails to candidates with draft intake (not submitted).
    Intended to be called by cron (e.g. daily).
    """
    db, tid = db_tenant
    tid_filter = tenant_id if tenant_id else str(tid)
    sent = await send_draft_reminders(db, tenant_id=tid_filter)
    return DraftRemindersOut(sent=sent)
