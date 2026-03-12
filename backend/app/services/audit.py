from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.audit import ActivityLog
from backend.app.core.audit_events import AuditEntityType, AuditEventType


async def log_activity(
    db: AsyncSession,
    *,
    tenant_id: str,
    action: str,
    actor_id: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    payload: Optional[dict[str, Any]] = None,
    ip: Optional[str] = None,
    ua: Optional[str] = None,
) -> None:
    stmt = (
        insert(ActivityLog)
        .values(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            payload=payload or {},
            ip=ip,
            ua=ua,
        )
    )
    await db.execute(stmt)
    await db.flush()


async def log_audit_event(
    db: AsyncSession,
    *,
    tenant_id: str,
    event_type: AuditEventType | str,
    entity_type: AuditEntityType | str,
    entity_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    payload: Optional[dict[str, Any]] = None,
    ip: Optional[str] = None,
    ua: Optional[str] = None,
) -> None:
    """Log a structured audit event (upgrade spec: RODO, handoff, contact attempts)."""
    await log_activity(
        db,
        tenant_id=tenant_id,
        action=str(event_type),
        actor_id=actor_id,
        target_type=str(entity_type),
        target_id=entity_id,
        payload=payload or {},
        ip=ip,
        ua=ua,
    )
