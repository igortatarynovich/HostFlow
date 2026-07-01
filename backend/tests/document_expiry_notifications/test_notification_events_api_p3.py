"""P3 API filter tests for notification events."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from httpx import AsyncClient

from backend.app.document_expiry_notifications.constants import (
    EVENT_DOCUMENT_EXPIRED,
    EVENT_DOCUMENT_EXPIRING_SOON,
    EVENT_STATUS_RESOLVED,
)
from backend.app.document_expiry_notifications.event_registry import sync_document_expiry_events
from backend.app.document_runtime.delivery_contract import enrich_documents_via_contract


pytestmark = pytest.mark.anyio


def _snapshot(*, expires_on: str, document_id: str, tenant_id: str) -> dict:
    return enrich_documents_via_contract(
        [
            {
                "document_id": document_id,
                "type": "passport",
                "status": "approved",
                "has_files": True,
                "expires_on": expires_on,
                "tenant_id": tenant_id,
                "owner_type": "candidate",
                "owner_id": "cand-filter",
            }
        ]
    )[0]


@pytest.mark.asyncio
async def test_p3_api_filter_event_type(
    client: AsyncClient,
    manager_headers,
    tenant_id: str,
    db,
) -> None:
    past = (date.today() - timedelta(days=1)).isoformat()
    soon = (date.today() + timedelta(days=3)).isoformat()
    await sync_document_expiry_events(
        db,
        [_snapshot(expires_on=past, document_id="d-exp", tenant_id=tenant_id), _snapshot(expires_on=soon, document_id="d-soon", tenant_id=tenant_id)],
        tenant_id=tenant_id,
    )
    await db.commit()

    expired_resp = await client.get(
        "/api/v1/platform/notification-events",
        params={"status": "open", "event_type": EVENT_DOCUMENT_EXPIRED},
        headers=manager_headers,
    )
    assert expired_resp.status_code == 200, expired_resp.text
    expired_rows = expired_resp.json()
    assert expired_rows
    assert all(row["event_code"] == EVENT_DOCUMENT_EXPIRED for row in expired_rows)
    assert any(row["document_id"] == "d-exp" for row in expired_rows)

    soon_resp = await client.get(
        "/api/v1/platform/notification-events",
        params={"status": "open", "event_type": EVENT_DOCUMENT_EXPIRING_SOON},
        headers=manager_headers,
    )
    assert soon_resp.status_code == 200
    assert all(row["event_code"] == EVENT_DOCUMENT_EXPIRING_SOON for row in soon_resp.json())


@pytest.mark.asyncio
async def test_p3_api_get_event_detail(
    client: AsyncClient,
    manager_headers,
    tenant_id: str,
    db,
) -> None:
    past = (date.today() - timedelta(days=2)).isoformat()
    rows = await sync_document_expiry_events(
        db,
        [_snapshot(expires_on=past, document_id="d-detail", tenant_id=tenant_id)],
        tenant_id=tenant_id,
    )
    await db.commit()

    resp = await client.get(
        f"/api/v1/platform/notification-events/{rows[0].id}",
        headers=manager_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == rows[0].id
    assert body["event_code"] == EVENT_DOCUMENT_EXPIRED


@pytest.mark.asyncio
async def test_p3_api_resolved_events_not_in_open_list(
    client: AsyncClient,
    manager_headers,
    tenant_id: str,
    db,
) -> None:
    past = (date.today() - timedelta(days=2)).isoformat()
    rows = await sync_document_expiry_events(
        db,
        [_snapshot(expires_on=past, document_id="d-resolved", tenant_id=tenant_id)],
        tenant_id=tenant_id,
    )
    await db.commit()

    patch_resp = await client.patch(
        f"/api/v1/platform/notification-events/{rows[0].id}/status",
        headers=manager_headers,
        json={"status": EVENT_STATUS_RESOLVED},
    )
    assert patch_resp.status_code == 200

    open_resp = await client.get(
        "/api/v1/platform/notification-events",
        params={"status": "open"},
        headers=manager_headers,
    )
    assert open_resp.status_code == 200
    assert all(row["id"] != rows[0].id for row in open_resp.json())
