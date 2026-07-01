"""Document Expiry Notifications P2 — notification event registry."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.document_expiry_notifications.constants import (
    DEFAULT_EXPIRING_SOON_DAYS,
    EVENT_STATUS_OPEN,
    SOURCE_LAYER,
    VALID_EVENT_STATUSES,
    UpsertAction,
)
from backend.app.document_expiry_notifications.evaluator import evaluate_document_expiry_events
from backend.app.models.notification_event import NotificationEvent


def _coerce_evaluated_at(value: Any) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, str) and value.strip():
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    return datetime.now(timezone.utc)


def notification_event_to_dict(row: NotificationEvent) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "tenant_id": str(row.tenant_id),
        "event_key": str(row.event_key),
        "evaluation_version": str(row.evaluation_version),
        "event_code": str(row.event_code),
        "source_layer": str(row.source_layer),
        "owner_type": str(row.owner_type),
        "owner_id": str(row.owner_id),
        "document_id": row.document_id,
        "document_type_code": row.document_type_code,
        "severity": str(row.severity),
        "document_runtime": dict(row.document_runtime or {}),
        "metadata": dict(row.metadata_json or {}),
        "evaluated_at": row.evaluated_at.isoformat() if row.evaluated_at else None,
        "status": str(row.status),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _metadata_from_event(event: dict[str, Any]) -> dict[str, Any] | None:
    window_days = event.get("expiring_soon_window_days")
    if window_days is None:
        return None
    return {"expiring_soon_window_days": int(window_days)}


def _apply_event_payload(entity: NotificationEvent, event: dict[str, Any]) -> None:
    entity.evaluation_version = str(event.get("evaluation_version") or entity.evaluation_version)
    entity.event_code = str(event.get("event_code") or entity.event_code)
    entity.source_layer = str(event.get("source_layer") or SOURCE_LAYER)
    entity.owner_type = str(event.get("owner_type") or entity.owner_type)
    entity.owner_id = str(event.get("owner_id") or entity.owner_id)
    entity.document_id = event.get("document_id")
    entity.document_type_code = event.get("document_type_code")
    entity.severity = str(event.get("severity") or entity.severity)
    entity.document_runtime = dict(event.get("document_runtime") or {})
    entity.metadata_json = _metadata_from_event(event)
    entity.evaluated_at = _coerce_evaluated_at(event.get("evaluated_at"))


async def upsert_notification_event(
    db: AsyncSession,
    event: dict[str, Any],
    *,
    tenant_id: str | None = None,
) -> NotificationEvent:
    """Insert or refresh one evaluated notification event (idempotent on event_key)."""
    entity, _action = await upsert_notification_event_with_action(db, event, tenant_id=tenant_id)
    return entity


async def upsert_notification_event_with_action(
    db: AsyncSession,
    event: dict[str, Any],
    *,
    tenant_id: str | None = None,
) -> tuple[NotificationEvent, UpsertAction]:
    """Insert or refresh one event and report whether it was created, updated, or skipped."""
    scoped_tenant_id = str(tenant_id or event.get("tenant_id") or "").strip()
    event_key = str(event.get("event_key") or "").strip()
    if not scoped_tenant_id or not event_key:
        raise ValueError("tenant_id and event_key are required for notification event upsert")

    existing = (
        await db.execute(
            select(NotificationEvent).where(
                NotificationEvent.tenant_id == scoped_tenant_id,
                NotificationEvent.event_key == event_key,
            )
        )
    ).scalar_one_or_none()

    if existing is None:
        entity = NotificationEvent(
            id=str(uuid4()),
            tenant_id=scoped_tenant_id,
            event_key=event_key,
            status=EVENT_STATUS_OPEN,
        )
        db.add(entity)
        _apply_event_payload(entity, event)
        return entity, "created"

    entity = existing
    preserved_status = str(entity.status or EVENT_STATUS_OPEN)
    _apply_event_payload(entity, event)
    if preserved_status != EVENT_STATUS_OPEN:
        entity.status = preserved_status
        return entity, "skipped"
    return entity, "updated"


async def upsert_notification_events(
    db: AsyncSession,
    events: Iterable[dict[str, Any]],
    *,
    tenant_id: str | None = None,
) -> list[NotificationEvent]:
    rows: list[NotificationEvent] = []
    for event in events or []:
        if not isinstance(event, dict):
            continue
        entity, _action = await upsert_notification_event_with_action(db, event, tenant_id=tenant_id)
        rows.append(entity)
    return rows


def empty_sync_summary(*, tenant_id: str) -> dict[str, Any]:
    return {
        "tenant_id": str(tenant_id),
        "evaluated_owners": 0,
        "evaluated_documents": 0,
        "events_evaluated": 0,
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "event_codes": {},
    }


async def sync_document_expiry_events_with_summary(
    db: AsyncSession,
    runtime_snapshots: list[dict[str, Any]],
    *,
    tenant_id: str,
    expiring_soon_days: int = DEFAULT_EXPIRING_SOON_DAYS,
) -> dict[str, Any]:
    """Evaluate P1 expiry events, persist idempotently, and return observability summary."""
    scoped_tenant_id = str(tenant_id or "").strip()
    summary = empty_sync_summary(tenant_id=scoped_tenant_id)
    normalized_snapshots: list[dict[str, Any]] = []
    for snapshot in runtime_snapshots or []:
        if not isinstance(snapshot, dict):
            continue
        row = dict(snapshot)
        row.setdefault("tenant_id", scoped_tenant_id)
        normalized_snapshots.append(row)

    summary["evaluated_documents"] = len(normalized_snapshots)
    evaluated = evaluate_document_expiry_events(
        normalized_snapshots,
        expiring_soon_days=expiring_soon_days,
    )
    summary["events_evaluated"] = len(evaluated)

    for event in evaluated:
        _entity, action = await upsert_notification_event_with_action(
            db,
            event,
            tenant_id=scoped_tenant_id,
        )
        summary[action] = int(summary.get(action) or 0) + 1
        code = str(event.get("event_code") or "").strip()
        if code:
            codes = summary.setdefault("event_codes", {})
            codes[code] = int(codes.get(code) or 0) + 1

    return summary


async def sync_document_expiry_events(
    db: AsyncSession,
    runtime_snapshots: list[dict[str, Any]],
    *,
    tenant_id: str,
    expiring_soon_days: int = DEFAULT_EXPIRING_SOON_DAYS,
) -> list[NotificationEvent]:
    """Evaluate P1 expiry events and persist them idempotently."""
    scoped_tenant_id = str(tenant_id or "").strip()
    normalized_snapshots: list[dict[str, Any]] = []
    for snapshot in runtime_snapshots or []:
        if not isinstance(snapshot, dict):
            continue
        row = dict(snapshot)
        row.setdefault("tenant_id", scoped_tenant_id)
        normalized_snapshots.append(row)

    evaluated = evaluate_document_expiry_events(
        normalized_snapshots,
        expiring_soon_days=expiring_soon_days,
    )
    return await upsert_notification_events(db, evaluated, tenant_id=scoped_tenant_id)


async def list_notification_events(
    db: AsyncSession,
    tenant_id: str,
    *,
    status: str = EVENT_STATUS_OPEN,
    source_layer: str | None = SOURCE_LAYER,
    event_code: str | None = None,
) -> list[NotificationEvent]:
    stmt = select(NotificationEvent).where(NotificationEvent.tenant_id == str(tenant_id).strip())
    if status:
        stmt = stmt.where(NotificationEvent.status == str(status).strip())
    if source_layer:
        stmt = stmt.where(NotificationEvent.source_layer == str(source_layer).strip())
    if event_code:
        stmt = stmt.where(NotificationEvent.event_code == str(event_code).strip())
    stmt = stmt.order_by(NotificationEvent.evaluated_at.desc(), NotificationEvent.event_key.asc())
    return list((await db.execute(stmt)).scalars().all())


async def get_notification_event(
    db: AsyncSession,
    tenant_id: str,
    event_id: str,
) -> NotificationEvent | None:
    return (
        await db.execute(
            select(NotificationEvent).where(
                NotificationEvent.id == str(event_id).strip(),
                NotificationEvent.tenant_id == str(tenant_id).strip(),
            )
        )
    ).scalar_one_or_none()


async def update_notification_event_status(
    db: AsyncSession,
    tenant_id: str,
    event_id: str,
    *,
    status: str,
) -> NotificationEvent | None:
    normalized_status = str(status or "").strip().lower()
    if normalized_status not in VALID_EVENT_STATUSES:
        raise ValueError(f"Unsupported notification event status: {status}")

    row = (
        await db.execute(
            select(NotificationEvent).where(
                NotificationEvent.id == str(event_id).strip(),
                NotificationEvent.tenant_id == str(tenant_id).strip(),
            )
        )
    ).scalar_one_or_none()
    if row is None:
        return None

    row.status = normalized_status
    return row


async def count_notification_events(
    db: AsyncSession,
    tenant_id: str,
    *,
    event_key: str | None = None,
) -> int:
    stmt = (
        select(func.count())
        .select_from(NotificationEvent)
        .where(NotificationEvent.tenant_id == str(tenant_id).strip())
    )
    if event_key:
        stmt = stmt.where(NotificationEvent.event_key == str(event_key).strip())
    return int(await db.scalar(stmt) or 0)
