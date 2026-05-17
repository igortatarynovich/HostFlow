from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.audit import ActivityLog
from backend.app.core.audit_events import AuditEntityType, AuditEventType


# ``ActivityLog.target_id`` is ``String(36)`` (UUID-shaped). Some legitimate
# entity ids exceed that — e.g. reminders for documents fingerprinting use
# composite ids like ``"<uuid>:fingerprints"`` (49 chars). Widening the
# column is Phase 4 territory (migration); until then we keep the column
# safe and preserve the full value inside ``payload.target_id_full`` so
# audit trails remain queryable.
_AUDIT_TARGET_ID_LIMIT = 36


def _audit_enum_value(value: Enum | str) -> str:
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def _split_target_id(value: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    if value is None:
        return None, None
    s = str(value)
    if len(s) <= _AUDIT_TARGET_ID_LIMIT:
        return s, None
    return None, s


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
    safe_target_id, overflow_target_id = _split_target_id(target_id)
    safe_payload: dict[str, Any] = dict(payload or {})
    if overflow_target_id is not None:
        safe_payload.setdefault("target_id_full", overflow_target_id)
    stmt = (
        insert(ActivityLog)
        .values(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=safe_target_id,
            payload=safe_payload,
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
        action=_audit_enum_value(event_type),
        actor_id=actor_id,
        target_type=_audit_enum_value(entity_type),
        target_id=entity_id,
        payload=payload or {},
        ip=ip,
        ua=ua,
    )
