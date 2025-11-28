from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.auth.deps import Role, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.services.reminders import run_expiry_notifications

router = APIRouter(prefix="/documents", tags=["reminders"])


@router.post(
    "/run-expiry-notifications",
    dependencies=[Depends(require_roles(Role.manager, Role.admin))],
)
async def run_expiry(db_tenant=Depends(get_db_with_tenant)):
    db, tenant_id = db_tenant
    seen, sent = await run_expiry_notifications(db, str(tenant_id))
    return {"ok": True, "seen": seen, "sent": sent}
