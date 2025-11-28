from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.audit import log_activity


async def log_public_event(
    db: AsyncSession,
    *,
    tenant_id: str,
    action: str,
    target_id: Optional[str],
    payload: Optional[dict[str, Any]] = None,
    ip: Optional[str] = None,
    ua: Optional[str] = None,
) -> None:
    await log_activity(
        db,
        tenant_id=tenant_id,
        action=action,
        actor_id=None,
        target_type="public_intake",
        target_id=target_id,
        payload=payload or {},
        ip=ip,
        ua=ua,
    )
