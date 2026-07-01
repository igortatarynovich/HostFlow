from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from backend.app.db.base import Base
from backend.app.core.settings import settings
from backend.app.models.calendar_integration import (
    CalendarConnection,
    CalendarSyncJob,
    CalendarItem,
    CalendarItemLink,
    CalendarChannel,
    CalendarSyncCursor,
    IntegrationActionLog,
)
from backend.app.services.communications_oauth import OAuthTokenPayload
from backend.app.core.arq_worker import job_calendar_sync_ingest
from backend.app.services.calendar_provider_sync import CalendarProviderSyncResult


pytestmark = pytest.mark.anyio


async def _ensure_calendar_tables(db) -> None:
    async with db.bind.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn,
                tables=[
                    CalendarConnection.__table__,
                    CalendarChannel.__table__,
                    CalendarItem.__table__,
                    CalendarItemLink.__table__,
                    CalendarSyncCursor.__table__,
                    CalendarSyncJob.__table__,
                    IntegrationActionLog.__table__,
                ],
            )
        )


async def test_calendar_connection_oauth_complete_and_refresh(client, manager_headers, monkeypatch, db):
    await _ensure_calendar_tables(db)
    async def _fake_exchange(**kwargs):
        assert kwargs["provider"] == "gmail"
        return OAuthTokenPayload(
            access_token="acc_1",
            refresh_token="ref_1",
            token_type="Bearer",
            expires_in=3600,
            scope="calendar",
            id_token="id_1",
            provider_payload={"ok": True},
        )

    async def _fake_refresh(**kwargs):
        assert kwargs["provider"] == "gmail"
        assert kwargs["refresh_token"] == "ref_1"
        return OAuthTokenPayload(
            access_token="acc_2",
            refresh_token="ref_2",
            token_type="Bearer",
            expires_in=1800,
            scope="calendar.read",
            id_token=None,
            provider_payload={"ok": True},
        )

    monkeypatch.setattr("backend.app.api.v1.calendar.exchange_oauth_code_for_tokens", _fake_exchange)
    monkeypatch.setattr("backend.app.api.v1.calendar.refresh_oauth_access_token", _fake_refresh)

    create_resp = await client.post(
        "/api/v1/calendar/integrations/connections/oauth/complete",
        headers=manager_headers,
        json={
            "provider": "google",
            "code": "test-code",
            "client_id": "client-id",
            "client_secret": "client-secret",
            "redirect_uri": "https://example.test/oauth/callback",
            "account_ref": "user@example.test",
            "scopes": ["calendar", "calendar.events"],
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()
    assert created["provider"] == "google"
    assert created["token_meta"]["access_token"] == "acc_1"

    refresh_resp = await client.post(
        f"/api/v1/calendar/integrations/connections/{created['id']}/refresh",
        headers=manager_headers,
        json={
            "client_id": "client-id",
            "client_secret": "client-secret",
            "scope": "calendar.read",
        },
    )
    assert refresh_resp.status_code == 200, refresh_resp.text
    refreshed = refresh_resp.json()
    assert refreshed["token_meta"]["access_token"] == "acc_2"
    assert refreshed["token_meta"]["refresh_token"] == "ref_2"


async def test_calendar_webhook_slack_signature_required(client, tenant_id, monkeypatch, db):
    await _ensure_calendar_tables(db)
    monkeypatch.setattr(settings, "slack_signing_secret", "test-secret", raising=False)
    payload = {"event_id": "evt-1", "tenant_id": tenant_id, "event": {"id": "ev-1"}}
    now_ts = str(int(datetime.now(timezone.utc).timestamp()))
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    digest = hmac.new(b"test-secret", f"v0:{now_ts}:".encode("utf-8") + raw, hashlib.sha256).hexdigest()
    signature = f"v0={digest}"

    bad_resp = await client.post(
        "/api/v1/calendar/integrations/slack/events",
        headers={
            "X-Tenant-Id": tenant_id,
            "X-Slack-Signature": "v0=bad",
            "X-Slack-Request-Timestamp": now_ts,
            "Content-Type": "application/json",
        },
        content=raw,
    )
    assert bad_resp.status_code == 401, bad_resp.text

    good_resp = await client.post(
        "/api/v1/calendar/integrations/slack/events",
        headers={
            "X-Tenant-Id": tenant_id,
            "X-Slack-Signature": signature,
            "X-Slack-Request-Timestamp": now_ts,
            "Content-Type": "application/json",
        },
        content=raw,
    )
    assert good_resp.status_code == 202, good_resp.text
    assert good_resp.json()["accepted"] is True


async def test_calendar_webhook_creates_sync_job_and_connection_crud(client, manager_headers, db, tenant_id):
    await _ensure_calendar_tables(db)
    create_resp = await client.post(
        "/api/v1/calendar/integrations/connections",
        headers=manager_headers,
        json={
            "provider": "microsoft",
            "account_ref": "ms-user@example.test",
            "status": "active",
            "scopes": ["Calendars.ReadWrite"],
            "refresh_token": "refresh-raw",
            "access_token": "access-raw",
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    connection_id = create_resp.json()["id"]

    list_resp = await client.get("/api/v1/calendar/integrations/connections", headers=manager_headers)
    assert list_resp.status_code == 200, list_resp.text
    ids = [x["id"] for x in list_resp.json()["items"]]
    assert connection_id in ids

    wh_resp = await client.post(
        "/api/v1/calendar/integrations/microsoft/calendar/webhook",
        headers={"X-Tenant-Id": tenant_id},
        json={
            "event_id": "evt-ms-1",
            "tenant_id": tenant_id,
            "resourceData": {
                "id": "provider-event-1",
                "subject": "Test Sync Event",
                "startDateTime": "2026-04-21T10:00:00Z",
                "endDateTime": "2026-04-21T11:00:00Z",
                "timeZone": "UTC",
            },
        },
    )
    assert wh_resp.status_code == 202, wh_resp.text

    rows = (await db.execute(select(CalendarSyncJob).where(CalendarSyncJob.tenant_id == tenant_id))).scalars().all()
    assert any(r.source_kind == "microsoft_webhook" for r in rows)

    delete_resp = await client.delete(
        f"/api/v1/calendar/integrations/connections/{connection_id}",
        headers=manager_headers,
    )
    assert delete_resp.status_code == 204, delete_resp.text

    row = await db.get(CalendarConnection, connection_id)
    assert row is None


async def test_calendar_cursor_and_reconcile_queue(client, manager_headers, db):
    await _ensure_calendar_tables(db)
    create_resp = await client.post(
        "/api/v1/calendar/integrations/connections",
        headers=manager_headers,
        json={
            "provider": "google",
            "account_ref": "cursor-user@example.test",
            "status": "active",
            "scopes": ["calendar.read"],
            "refresh_token": "refresh-token",
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    connection_id = create_resp.json()["id"]

    cursor_patch = await client.patch(
        f"/api/v1/calendar/integrations/connections/{connection_id}/cursor",
        headers=manager_headers,
        json={
            "calendar_ref": "primary",
            "cursor": "sync-token-1",
            "cursor_meta": {"window": "7d"},
        },
    )
    assert cursor_patch.status_code == 200, cursor_patch.text
    assert cursor_patch.json()["cursor"] == "sync-token-1"

    cursor_get = await client.get(
        f"/api/v1/calendar/integrations/connections/{connection_id}/cursor",
        headers=manager_headers,
    )
    assert cursor_get.status_code == 200, cursor_get.text
    assert len(cursor_get.json()["items"]) == 1

    reconcile_resp = await client.post(
        "/api/v1/calendar/integrations/reconcile",
        headers=manager_headers,
        json={"connection_id": connection_id},
    )
    assert reconcile_resp.status_code == 200, reconcile_resp.text
    assert reconcile_resp.json()["queued"] == 1


async def test_calendar_worker_skips_conflicting_action(db, tenant_id):
    await _ensure_calendar_tables(db)
    item = CalendarItem(
        tenant_id=tenant_id,
        owner_id=None,
        assignee_id=None,
        kind="event",
        status="scheduled",
        title="Conflict Event",
        description=None,
        timezone="UTC",
        starts_at=datetime(2026, 4, 21, 10, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 4, 21, 11, 0, tzinfo=timezone.utc),
        all_day=False,
        linked_entity_type=None,
        linked_entity_id=None,
        source="microsoft",
        payload={},
    )
    db.add(item)
    await db.flush()
    item_id = str(item.id)
    db.add(
        CalendarItemLink(
            tenant_id=tenant_id,
            calendar_item_id=item.id,
            connection_id=None,
            provider="microsoft",
            provider_calendar_id="primary",
            provider_event_id="provider-event-42",
            provider_version="v2",
            sync_state="synced",
            payload={},
        )
    )
    job = CalendarSyncJob(
        tenant_id=tenant_id,
        source_kind="slack_event",
        operation="ingest",
        status="queued",
        dedupe_key="conflict-job",
        payload={
            "calendar_item_id": item.id,
            "action": "reschedule",
            "expected_provider_version": "v1",
            "starts_at": "2026-04-21T15:00:00Z",
        },
    )
    db.add(job)
    await db.commit()

    result = await job_calendar_sync_ingest({}, sync_job_id=job.id)
    assert result["mode"] == "action_conflict_skipped"

    db.expire_all()
    refreshed = await db.get(CalendarItem, item_id)
    assert refreshed is not None
    assert refreshed.starts_at == datetime(2026, 4, 21, 10, 0, tzinfo=timezone.utc)
    payload = dict(refreshed.payload or {})
    assert payload.get("last_action") == "conflict_skipped"


async def test_calendar_worker_reconcile_pulls_provider_events(db, tenant_id, monkeypatch):
    await _ensure_calendar_tables(db)
    connection = CalendarConnection(
        tenant_id=tenant_id,
        user_id=None,
        provider="google",
        account_ref="provider-user@example.test",
        status="active",
        scopes_json=["calendar.read"],
        token_meta_json={"access_token": "token-1"},
        last_error=None,
    )
    db.add(connection)
    await db.flush()
    connection_id = str(connection.id)

    async def _fake_google_fetch(**kwargs):
        assert kwargs["access_token"] == "token-1"
        return CalendarProviderSyncResult(
            events=[
                {
                    "id": "google-event-1",
                    "summary": "Fetched Event",
                    "start": {"dateTime": "2026-04-22T09:00:00Z"},
                    "end": {"dateTime": "2026-04-22T10:00:00Z"},
                    "timeZone": "UTC",
                    "etag": "etag-v1",
                }
            ],
            next_cursor="sync-token-next",
            cursor_meta={"calendar_ref": "primary"},
        )

    monkeypatch.setattr("backend.app.services.calendar_provider_sync.fetch_google_events", _fake_google_fetch)

    reconcile_job = CalendarSyncJob(
        tenant_id=tenant_id,
        source_kind="google_reconcile",
        operation="reconcile",
        status="queued",
        dedupe_key="reconcile-google-1",
        payload={
            "connection_id": connection_id,
            "provider": "google",
            "cursor": None,
            "cursor_meta": {"calendar_ref": "primary"},
        },
    )
    db.add(reconcile_job)
    await db.commit()

    result = await job_calendar_sync_ingest({}, sync_job_id=reconcile_job.id)
    assert result["ok"] is True

    item_rows = (await db.execute(select(CalendarItem).where(CalendarItem.tenant_id == tenant_id))).scalars().all()
    assert any(i.title == "Fetched Event" for i in item_rows)
    cursor_rows = (
        await db.execute(
            select(CalendarSyncCursor).where(CalendarSyncCursor.connection_id == connection_id)
        )
    ).scalars().all()
    assert len(cursor_rows) >= 1
    assert any(c.cursor == "sync-token-next" for c in cursor_rows)


async def test_calendar_subscription_renew_queue_and_worker(client, manager_headers, db, tenant_id):
    await _ensure_calendar_tables(db)
    create_resp = await client.post(
        "/api/v1/calendar/integrations/connections",
        headers=manager_headers,
        json={
            "provider": "microsoft",
            "account_ref": "renew-user@example.test",
            "status": "active",
            "scopes": ["Calendars.ReadWrite"],
            "refresh_token": "refresh-token",
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    connection_id = create_resp.json()["id"]

    renew_resp = await client.post(
        "/api/v1/calendar/integrations/subscriptions/renew",
        headers=manager_headers,
        json={"connection_id": connection_id},
    )
    assert renew_resp.status_code == 200, renew_resp.text
    assert renew_resp.json()["queued"] == 1

    renew_job = (
        await db.execute(
            select(CalendarSyncJob)
            .where(CalendarSyncJob.operation == "renew_subscription")
            .order_by(CalendarSyncJob.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    assert renew_job is not None
    await job_calendar_sync_ingest({}, sync_job_id=renew_job.id)

    channels = (
        await db.execute(
            select(CalendarChannel).where(CalendarChannel.connection_id == connection_id)
        )
    ).scalars().all()
    assert len(channels) >= 1
    assert channels[0].health_state == "healthy"
