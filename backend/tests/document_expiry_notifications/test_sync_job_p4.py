"""Document Expiry Notifications P4 — scheduled sync job tests."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text

from backend.app.document_expiry_notifications.constants import (
    EVENT_DOCUMENT_EXPIRED,
    EVENT_DOCUMENT_EXPIRING_SOON,
    EVENT_STATUS_OPEN,
    EVENT_STATUS_RESOLVED,
)
from backend.app.document_expiry_notifications.event_registry import (
    count_notification_events,
    sync_document_expiry_events_with_summary,
    update_notification_event_status,
)
from backend.app.document_expiry_notifications import sync_job as expiry_sync_job
from backend.app.document_runtime.delivery_contract import enrich_documents_via_contract
from backend.app.models.candidate import Candidate
from backend.app.models.notification_event import NotificationEvent


pytestmark = pytest.mark.anyio


def _runtime_snapshot(
    *,
    status: str = "approved",
    expires_on: str | None,
    document_id: str,
    doc_type: str = "passport",
    tenant_id: str = "p4-test-tenant",
    owner_id: str = "cand-p4-1",
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


async def test_p4_summary_creates_expired_and_expiring_events(db) -> None:
    await _require_notification_events_table(db)
    tenant_id = "p4-summary-create"
    past = (date.today() - timedelta(days=2)).isoformat()
    soon = (date.today() + timedelta(days=4)).isoformat()
    snapshots = [
        _runtime_snapshot(expires_on=past, document_id="doc-exp", tenant_id=tenant_id),
        _runtime_snapshot(expires_on=soon, document_id="doc-soon", tenant_id=tenant_id, doc_type="code95"),
    ]

    summary = await sync_document_expiry_events_with_summary(db, snapshots, tenant_id=tenant_id)
    await db.commit()

    assert summary["events_evaluated"] == 2
    assert summary["created"] == 2
    assert summary["updated"] == 0
    assert summary["event_codes"][EVENT_DOCUMENT_EXPIRED] == 1
    assert summary["event_codes"][EVENT_DOCUMENT_EXPIRING_SOON] == 1


async def test_p4_replay_summary_reports_updated_not_created(db) -> None:
    await _require_notification_events_table(db)
    tenant_id = "p4-summary-replay"
    past = (date.today() - timedelta(days=1)).isoformat()
    snapshot = _runtime_snapshot(expires_on=past, document_id="doc-replay", tenant_id=tenant_id)

    first = await sync_document_expiry_events_with_summary(db, [snapshot], tenant_id=tenant_id)
    await db.commit()
    second = await sync_document_expiry_events_with_summary(db, [snapshot], tenant_id=tenant_id)
    await db.commit()

    assert first["created"] == 1
    assert second["created"] == 0
    assert second["updated"] == 1
    assert await count_notification_events(db, tenant_id) == 1


async def test_p4_resolved_event_stays_skipped_on_replay(db) -> None:
    await _require_notification_events_table(db)
    tenant_id = "p4-summary-resolved"
    past = (date.today() - timedelta(days=1)).isoformat()
    snapshot = _runtime_snapshot(expires_on=past, document_id="doc-resolved", tenant_id=tenant_id)

    initial = await sync_document_expiry_events_with_summary(db, [snapshot], tenant_id=tenant_id)
    await db.commit()
    row = (
        await db.execute(select(NotificationEvent).where(NotificationEvent.tenant_id == tenant_id))
    ).scalar_one()
    await update_notification_event_status(db, tenant_id, row.id, status=EVENT_STATUS_RESOLVED)
    await db.commit()

    replay = await sync_document_expiry_events_with_summary(db, [snapshot], tenant_id=tenant_id)
    await db.commit()

    assert initial["created"] == 1
    assert replay["skipped"] == 1
    assert replay["created"] == 0
    refreshed = (
        await db.execute(select(NotificationEvent).where(NotificationEvent.id == row.id))
    ).scalar_one()
    assert refreshed.status == EVENT_STATUS_RESOLVED


async def test_p4_sync_job_uses_delivery_contract_snapshots(db, monkeypatch: pytest.MonkeyPatch) -> None:
    await _require_notification_events_table(db)
    tenant_id = "p4-job-tenant"
    candidate_id = str(uuid.uuid4())
    db.add(
        Candidate(
            id=candidate_id,
            tenant_id=tenant_id,
            first_name="Sync",
            last_name="Candidate",
        )
    )
    await db.commit()

    past = (date.today() - timedelta(days=1)).isoformat()
    snapshots = [_runtime_snapshot(expires_on=past, document_id="doc-job", tenant_id=tenant_id, owner_id=candidate_id)]

    async def _fake_collect(
        _db,
        *,
        tenant_id: str,
        candidate_id: str,
        own_company_id: str | None = None,
    ) -> list[dict]:
        return snapshots

    monkeypatch.setattr(expiry_sync_job, "collect_candidate_runtime_snapshots", _fake_collect)

    summary = await expiry_sync_job.sync_document_expiry_notification_events(
        db,
        tenant_id=tenant_id,
        candidate_ids=[candidate_id],
    )
    await db.commit()

    assert summary["evaluated_owners"] == 1
    assert summary["created"] == 1
    assert summary["events_evaluated"] == 1
    open_rows = (
        await db.execute(
            select(NotificationEvent).where(
                NotificationEvent.tenant_id == tenant_id,
                NotificationEvent.status == EVENT_STATUS_OPEN,
            )
        )
    ).scalars().all()
    assert len(open_rows) == 1


@pytest.mark.asyncio
async def test_p4_api_sync_endpoint(
    client: AsyncClient,
    manager_headers,
    tenant_id: str,
    db,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _require_notification_events_table(db)
    candidate_id = str(uuid.uuid4())
    db.add(
        Candidate(
            id=candidate_id,
            tenant_id=tenant_id,
            first_name="Api",
            last_name="Sync",
        )
    )
    await db.commit()

    past = (date.today() - timedelta(days=1)).isoformat()
    snapshots = [
        _runtime_snapshot(expires_on=past, document_id="doc-api", tenant_id=tenant_id, owner_id=candidate_id)
    ]

    async def _fake_collect(
        _db,
        *,
        tenant_id: str,
        candidate_id: str,
        own_company_id: str | None = None,
    ) -> list[dict]:
        return snapshots

    monkeypatch.setattr(expiry_sync_job, "collect_candidate_runtime_snapshots", _fake_collect)

    resp = await client.post(
        "/api/v1/platform/notification-events/sync",
        headers=manager_headers,
        json={"candidate_ids": [candidate_id]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["created"] >= 1
    assert body["events_evaluated"] >= 1
    assert EVENT_DOCUMENT_EXPIRED in body["event_codes"]
