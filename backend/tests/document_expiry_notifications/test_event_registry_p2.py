"""Document Expiry Notifications P2 — event registry persistence tests."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text

from backend.app.document_expiry_notifications.constants import (
    EVENT_DOCUMENT_EXPIRED,
    EVENT_DOCUMENT_EXPIRING_SOON,
    EVENT_STATUS_IGNORED,
    EVENT_STATUS_OPEN,
    EVENT_STATUS_RESOLVED,
    SOURCE_LAYER,
)
from backend.app.document_expiry_notifications.event_registry import (
    count_notification_events,
    list_notification_events,
    sync_document_expiry_events,
    update_notification_event_status,
)
from backend.app.document_runtime.delivery_contract import enrich_documents_via_contract
from backend.app.models.notification_event import NotificationEvent


pytestmark = pytest.mark.anyio


def _runtime_snapshot(
    *,
    status: str = "approved",
    expires_on: str | None,
    document_id: str,
    doc_type: str = "passport",
    tenant_id: str = "p2-test-tenant",
    owner_id: str = "cand-p2-1",
) -> dict:
    row = {
        "document_id": document_id,
        "type": doc_type,
        "status": status,
        "has_files": True,
        "expires_on": expires_on,
        "tenant_id": tenant_id,
        "owner_type": "candidate",
        "owner_id": owner_id,
    }
    return enrich_documents_via_contract([row])[0]


async def _require_notification_events_table(db) -> None:
    try:
        await db.execute(text("SELECT 1 FROM notification_events LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"notification_events table not available: {exc}")


async def test_p2_expired_and_expiring_events_persist(db) -> None:
    await _require_notification_events_table(db)
    tenant_id = "p2-persist-tenant"
    past = (date.today() - timedelta(days=2)).isoformat()
    soon = (date.today() + timedelta(days=5)).isoformat()
    snapshots = [
        _runtime_snapshot(expires_on=past, document_id="doc-expired", tenant_id=tenant_id),
        _runtime_snapshot(expires_on=soon, document_id="doc-soon", tenant_id=tenant_id, doc_type="code95"),
    ]

    rows = await sync_document_expiry_events(db, snapshots, tenant_id=tenant_id)
    await db.commit()
    assert len(rows) == 2
    codes = {row.event_code for row in rows}
    assert codes == {EVENT_DOCUMENT_EXPIRED, EVENT_DOCUMENT_EXPIRING_SOON}
    assert all(row.source_layer == SOURCE_LAYER for row in rows)
    assert all(row.status == EVENT_STATUS_OPEN for row in rows)


async def test_p2_idempotent_replay_no_duplicate(db) -> None:
    await _require_notification_events_table(db)
    tenant_id = "p2-idempotent-tenant"
    past = (date.today() - timedelta(days=1)).isoformat()
    snapshot = _runtime_snapshot(expires_on=past, document_id="doc-dup", tenant_id=tenant_id)

    await sync_document_expiry_events(db, [snapshot], tenant_id=tenant_id)
    await db.commit()
    first_count = await count_notification_events(db, tenant_id)

    await sync_document_expiry_events(db, [snapshot], tenant_id=tenant_id)
    await db.commit()
    second_count = await count_notification_events(db, tenant_id)

    assert first_count == 1
    assert second_count == 1

    stored = (
        await db.execute(
            select(NotificationEvent).where(NotificationEvent.tenant_id == tenant_id)
        )
    ).scalars().all()
    assert len(stored) == 1
    assert stored[0].event_code == EVENT_DOCUMENT_EXPIRED


async def test_p2_event_key_unique_per_tenant(db) -> None:
    await _require_notification_events_table(db)
    tenant_id = "p2-unique-tenant"
    past = (date.today() - timedelta(days=1)).isoformat()
    snapshot = _runtime_snapshot(expires_on=past, document_id="doc-unique", tenant_id=tenant_id)

    rows = await sync_document_expiry_events(db, [snapshot, snapshot], tenant_id=tenant_id)
    await db.commit()
    assert len(rows) == 1
    assert rows[0].event_key


async def test_p2_list_open_events(db) -> None:
    await _require_notification_events_table(db)
    tenant_id = "p2-open-tenant"
    past = (date.today() - timedelta(days=3)).isoformat()
    snapshot = _runtime_snapshot(expires_on=past, document_id="doc-open", tenant_id=tenant_id)

    await sync_document_expiry_events(db, [snapshot], tenant_id=tenant_id)
    await db.commit()

    open_rows = await list_notification_events(db, tenant_id, status=EVENT_STATUS_OPEN)
    assert len(open_rows) == 1
    assert open_rows[0].status == EVENT_STATUS_OPEN


async def test_p2_mark_event_resolved_or_ignored(db) -> None:
    await _require_notification_events_table(db)
    tenant_id = "p2-status-tenant"
    past = (date.today() - timedelta(days=4)).isoformat()
    snapshot = _runtime_snapshot(expires_on=past, document_id="doc-status", tenant_id=tenant_id)

    persisted = await sync_document_expiry_events(db, [snapshot], tenant_id=tenant_id)
    await db.commit()
    event_id = persisted[0].id

    resolved = await update_notification_event_status(
        db,
        tenant_id,
        event_id,
        status=EVENT_STATUS_RESOLVED,
    )
    await db.commit()
    assert resolved is not None
    assert resolved.status == EVENT_STATUS_RESOLVED

    open_rows = await list_notification_events(db, tenant_id, status=EVENT_STATUS_OPEN)
    assert open_rows == []

    ignored = await update_notification_event_status(
        db,
        tenant_id,
        event_id,
        status=EVENT_STATUS_IGNORED,
    )
    await db.commit()
    assert ignored is not None
    assert ignored.status == EVENT_STATUS_IGNORED


async def test_p2_replay_preserves_resolved_status(db) -> None:
    await _require_notification_events_table(db)
    tenant_id = "p2-replay-resolved-tenant"
    past = (date.today() - timedelta(days=1)).isoformat()
    snapshot = _runtime_snapshot(expires_on=past, document_id="doc-resolved", tenant_id=tenant_id)

    persisted = await sync_document_expiry_events(db, [snapshot], tenant_id=tenant_id)
    await db.commit()
    await update_notification_event_status(
        db,
        tenant_id,
        persisted[0].id,
        status=EVENT_STATUS_RESOLVED,
    )
    await db.commit()

    await sync_document_expiry_events(db, [snapshot], tenant_id=tenant_id)
    await db.commit()

    row = (
        await db.execute(
            select(NotificationEvent).where(NotificationEvent.id == persisted[0].id)
        )
    ).scalar_one()
    assert row.status == EVENT_STATUS_RESOLVED
    assert await count_notification_events(db, tenant_id) == 1


@pytest.mark.asyncio
async def test_p2_api_list_open_events(
    client: AsyncClient,
    manager_headers,
    tenant_id: str,
    db,
) -> None:
    await _require_notification_events_table(db)
    past = (date.today() - timedelta(days=2)).isoformat()
    snapshot = _runtime_snapshot(expires_on=past, document_id="doc-api", tenant_id=tenant_id)
    await sync_document_expiry_events(db, [snapshot], tenant_id=tenant_id)
    await db.commit()

    resp = await client.get(
        "/api/v1/platform/notification-events",
        params={"status": "open"},
        headers=manager_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body, list)
    assert any(row["event_code"] == EVENT_DOCUMENT_EXPIRED for row in body)
    assert all(row["source_layer"] == SOURCE_LAYER for row in body)


@pytest.mark.asyncio
async def test_p2_api_patch_event_status(
    client: AsyncClient,
    manager_headers,
    tenant_id: str,
    db,
) -> None:
    await _require_notification_events_table(db)
    past = (date.today() - timedelta(days=2)).isoformat()
    snapshot = _runtime_snapshot(expires_on=past, document_id="doc-api-patch", tenant_id=tenant_id)
    persisted = await sync_document_expiry_events(db, [snapshot], tenant_id=tenant_id)
    await db.commit()

    resp = await client.patch(
        f"/api/v1/platform/notification-events/{persisted[0].id}/status",
        headers=manager_headers,
        json={"status": "ignored"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == EVENT_STATUS_IGNORED

    open_resp = await client.get(
        "/api/v1/platform/notification-events",
        params={"status": "open"},
        headers=manager_headers,
    )
    assert open_resp.status_code == 200
    assert all(row["id"] != persisted[0].id for row in open_resp.json())
