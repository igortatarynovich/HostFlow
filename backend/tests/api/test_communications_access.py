from __future__ import annotations

import copy
from uuid import uuid4

import pytest
from httpx import AsyncClient

from backend.app.db.session import async_session_maker
from backend.app.models.tenant_lead_form import TenantLeadForm


async def _get_comm_settings(client: AsyncClient, headers: dict[str, str]) -> dict:
    resp = await client.get("/api/v1/settings/communications", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _patch_comm_settings(client: AsyncClient, headers: dict[str, str], payload: dict) -> dict:
    resp = await client.patch("/api/v1/settings/communications", headers=headers, json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _update_comm_settings(client: AsyncClient, headers: dict[str, str], mutator) -> dict:
    settings = await _get_comm_settings(client, headers)
    next_settings = copy.deepcopy(settings)
    mutator(next_settings)
    return await _patch_comm_settings(client, headers, next_settings)


async def _me_user_id(client: AsyncClient, headers: dict[str, str]) -> str:
    resp = await client.get("/api/v1/users/me", headers=headers)
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    profile = payload.get("profile") or {}
    user_id = str(profile.get("user_id") or "").strip()
    assert user_id
    return user_id


async def _create_email_account(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    label: str = "OAuth mailbox",
    provider: str = "gmail",
) -> dict:
    resp = await client.post(
        "/api/v1/communications/accounts",
        headers=headers,
        json={
            "channel": "email",
            "account_label": label,
            "inbox_address": "oauth@example.test",
            "settings_json": {
                "provider": provider,
                "oauth": {
                    "provider": provider,
                    "client_id": "test-client-id",
                    "redirect_uri": "https://app.hostflow.test/oauth/callback",
                },
            },
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.anyio
async def test_settings_get_requires_communications_admin_access(
    client: AsyncClient,
    recruiter_headers: dict[str, str],
    supervisor_headers: dict[str, str],
) -> None:
    forbidden = await client.get("/api/v1/settings/communications", headers=recruiter_headers)
    assert forbidden.status_code == 403

    allowed = await client.get("/api/v1/settings/communications", headers=supervisor_headers)
    assert allowed.status_code == 200


@pytest.mark.anyio
async def test_email_entitlement_blocks_email_channel_endpoints(
    client: AsyncClient,
    manager_headers: dict[str, str],
) -> None:
    await _update_comm_settings(
        client,
        manager_headers,
        lambda s: s["entitlements"]["modules"]["email"].update({"enabled": False}),
    )

    r = await client.get("/api/v1/communications/threads", headers=manager_headers, params={"channel": "email", "limit": 20})
    assert r.status_code == 403

    r = await client.get("/api/v1/communications/accounts", headers=manager_headers, params={"channel": "email"})
    assert r.status_code == 403


@pytest.mark.anyio
async def test_messages_role_access_and_user_override_allow(
    client: AsyncClient,
    manager_headers: dict[str, str],
    recruiter_headers: dict[str, str],
) -> None:
    await _update_comm_settings(
        client,
        manager_headers,
        lambda s: s["entitlements"]["modules"]["messages"].update({"enabled": True}),
    )
    await _update_comm_settings(
        client,
        manager_headers,
        lambda s: s["access"]["roles"].update({"messages": ["administrator"]}),
    )

    denied = await client.get("/api/v1/communications/threads", headers=recruiter_headers, params={"channel": "telegram", "limit": 20})
    assert denied.status_code == 403

    recruiter_id = await _me_user_id(client, recruiter_headers)
    await _update_comm_settings(
        client,
        manager_headers,
        lambda s: s["access"]["usersOverrides"].update({recruiter_id: {"messages": True}}),
    )

    allowed = await client.get("/api/v1/communications/threads", headers=recruiter_headers, params={"channel": "telegram", "limit": 20})
    assert allowed.status_code == 200


@pytest.mark.anyio
async def test_threads_without_channel_require_any_messages_or_email_enabled(
    client: AsyncClient,
    manager_headers: dict[str, str],
) -> None:
    await _update_comm_settings(
        client,
        manager_headers,
        lambda s: (
            s["entitlements"]["modules"]["messages"].update({"enabled": False}),
            s["entitlements"]["modules"]["email"].update({"enabled": False}),
        ),
    )

    r = await client.get("/api/v1/communications/threads", headers=manager_headers, params={"limit": 20})
    assert r.status_code == 403


@pytest.mark.anyio
async def test_communications_list_endpoints_accept_high_limit_values(
    client: AsyncClient,
    manager_headers: dict[str, str],
) -> None:
    await _update_comm_settings(
        client,
        manager_headers,
        lambda s: (
            s["entitlements"]["modules"]["messages"].update({"enabled": True}),
            s["entitlements"]["modules"]["email"].update({"enabled": True}),
            s["entitlements"]["modules"]["availability"].update({"enabled": True}),
            s["entitlements"]["modules"]["timeOff"].update({"enabled": True}),
        ),
    )

    threads = await client.get("/api/v1/communications/threads", headers=manager_headers, params={"limit": 300})
    assert threads.status_code == 200, threads.text

    time_off = await client.get(
        "/api/v1/communications/time-off/requests",
        headers=manager_headers,
        params={"limit": 500, "status_filter": ["approved"]},
    )
    assert time_off.status_code == 200, time_off.text


# NOTE: ``test_planner_access_by_role_and_override`` was deleted in
# Phase 2.1 (ADR-012, 2026-05-09). It exercised
# ``settings.access.roles.planner`` against the legacy
# ``/api/v1/communications/planner/events`` endpoint which was removed
# (planner-events were absorbed into ``/api/v1/activities``). The new
# activities endpoint does not enforce the ``planner`` role gate the
# same way, so the test could not be faithfully rewritten — see
# ``docs/specs/architecture/phase-2-1-planner-tasks-into-activities.md``.


@pytest.mark.anyio
async def test_email_oauth_flow_and_sync_cursor_endpoints(
    client: AsyncClient,
    manager_headers: dict[str, str],
) -> None:
    await _update_comm_settings(
        client,
        manager_headers,
        lambda s: s["entitlements"]["modules"]["email"].update({"enabled": True}),
    )
    account = await _create_email_account(client, manager_headers, label="OAuth flow mailbox", provider="gmail")
    account_id = str(account["id"])

    start = await client.post(
        f"/api/v1/communications/accounts/{account_id}/oauth/start",
        headers=manager_headers,
        json={},
    )
    assert start.status_code == 200, start.text
    start_payload = start.json()
    state = str(start_payload.get("state") or "")
    assert len(state) >= 8
    assert "auth_url" in start_payload

    complete = await client.post(
        f"/api/v1/communications/accounts/{account_id}/oauth/complete",
        headers=manager_headers,
        json={
            "state": state,
            "code": "dummy-code",
            "simulate_exchange": True,
        },
    )
    assert complete.status_code == 200, complete.text
    complete_payload = complete.json()
    assert complete_payload.get("ok") is True
    assert complete_payload.get("action") == "oauth_complete"

    refresh = await client.post(
        f"/api/v1/communications/accounts/{account_id}/oauth/refresh",
        headers=manager_headers,
        json={"simulate_refresh": True},
    )
    assert refresh.status_code == 200, refresh.text
    refresh_payload = refresh.json()
    assert refresh_payload.get("ok") is True
    assert refresh_payload.get("action") == "oauth_refresh"

    patch_cursor = await client.patch(
        f"/api/v1/communications/accounts/{account_id}/sync-cursor",
        headers=manager_headers,
        json={
            "cursor_key": "inbox_cursor",
            "cursor_value": "cursor-123",
            "meta": {"source": "pytest"},
        },
    )
    assert patch_cursor.status_code == 200, patch_cursor.text
    patch_payload = patch_cursor.json()
    assert patch_payload.get("cursor_key") == "inbox_cursor"
    assert patch_payload.get("cursor_value") == "cursor-123"
    assert (patch_payload.get("meta") or {}).get("source") == "pytest"

    get_cursor = await client.get(
        f"/api/v1/communications/accounts/{account_id}/sync-cursor",
        headers=manager_headers,
        params={"cursor_key": "inbox_cursor"},
    )
    assert get_cursor.status_code == 200, get_cursor.text
    get_payload = get_cursor.json()
    assert get_payload.get("cursor_value") == "cursor-123"
    assert (get_payload.get("meta") or {}).get("source") == "pytest"


@pytest.mark.anyio
async def test_email_oauth_real_exchange_and_refresh_path_uses_provider_adapter(
    client: AsyncClient,
    manager_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _update_comm_settings(
        client,
        manager_headers,
        lambda s: s["entitlements"]["modules"]["email"].update({"enabled": True}),
    )
    account = await _create_email_account(client, manager_headers, label="OAuth real mailbox", provider="gmail")
    account_id = str(account["id"])

    async def _fake_exchange(**kwargs):
        class _R:
            access_token = "real-access-token"
            refresh_token = "real-refresh-token"
            token_type = "Bearer"
            expires_in = 1800
            scope = "openid email profile"
            id_token = "real-id-token"
            provider_payload = {"provider": "exchange"}

        assert kwargs.get("provider") == "gmail"
        assert kwargs.get("code") == "real-code"
        return _R()

    async def _fake_refresh(**kwargs):
        class _R:
            access_token = "refreshed-access-token"
            refresh_token = "refreshed-refresh-token"
            token_type = "Bearer"
            expires_in = 2400
            scope = "openid email profile"
            id_token = "refreshed-id-token"
            provider_payload = {"provider": "refresh"}

        assert kwargs.get("provider") == "gmail"
        assert kwargs.get("refresh_token")
        return _R()

    monkeypatch.setattr("backend.app.api.v1.communications.exchange_oauth_code_for_tokens", _fake_exchange)
    monkeypatch.setattr("backend.app.api.v1.communications.refresh_oauth_access_token", _fake_refresh)

    start = await client.post(
        f"/api/v1/communications/accounts/{account_id}/oauth/start",
        headers=manager_headers,
        json={},
    )
    assert start.status_code == 200, start.text
    state = str(start.json().get("state") or "")
    assert state

    complete = await client.post(
        f"/api/v1/communications/accounts/{account_id}/oauth/complete",
        headers=manager_headers,
        json={
            "state": state,
            "code": "real-code",
            "simulate_exchange": False,
        },
    )
    assert complete.status_code == 200, complete.text
    complete_payload = complete.json()
    account_after_complete = complete_payload.get("account") or {}
    oauth_after_complete = (account_after_complete.get("settings_json") or {}).get("oauth") or {}
    assert oauth_after_complete.get("has_access_token") is True
    assert oauth_after_complete.get("has_refresh_token") is True

    refresh = await client.post(
        f"/api/v1/communications/accounts/{account_id}/oauth/refresh",
        headers=manager_headers,
        json={},
    )
    assert refresh.status_code == 200, refresh.text
    refresh_payload = refresh.json()
    assert refresh_payload.get("action") == "oauth_refresh"
    account_after_refresh = refresh_payload.get("account") or {}
    oauth_after_refresh = (account_after_refresh.get("settings_json") or {}).get("oauth") or {}
    assert oauth_after_refresh.get("has_access_token") is True


@pytest.mark.anyio
async def test_patch_communication_account_updates_oauth_settings_and_masks_secret(
    client: AsyncClient,
    manager_headers: dict[str, str],
) -> None:
    await _update_comm_settings(
        client,
        manager_headers,
        lambda s: s["entitlements"]["modules"]["email"].update({"enabled": True}),
    )
    account = await _create_email_account(client, manager_headers, label="Patch OAuth mailbox", provider="gmail")
    account_id = str(account["id"])

    patch = await client.patch(
        f"/api/v1/communications/accounts/{account_id}",
        headers=manager_headers,
        json={
            "settings_json": {
                "oauth": {
                    "client_id": "patched-client-id",
                    "client_secret": "patched-secret",
                    "redirect_uri": "https://app.hostflow.test/oauth/new-callback",
                    "scopes": ["openid", "email"],
                }
            }
        },
    )
    assert patch.status_code == 200, patch.text
    payload = patch.json()
    oauth = (payload.get("settings_json") or {}).get("oauth") or {}
    assert oauth.get("client_id") == "patched-client-id"
    assert oauth.get("redirect_uri") == "https://app.hostflow.test/oauth/new-callback"
    assert oauth.get("has_client_secret") is True
    assert "client_secret" not in oauth


@pytest.mark.anyio
async def test_email_poll_worker_gmail_oauth_ingests_and_updates_cursor(
    client: AsyncClient,
    manager_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _update_comm_settings(
        client,
        manager_headers,
        lambda s: s["entitlements"]["modules"]["email"].update({"enabled": True}),
    )
    account = await _create_email_account(client, manager_headers, label="Gmail poll mailbox", provider="gmail")
    account_id = str(account["id"])

    patch = await client.patch(
        f"/api/v1/communications/accounts/{account_id}",
        headers=manager_headers,
        json={
            "settings_json": {
                "oauth": {
                    "access_token": "token-abc",
                    "client_id": "client-id",
                    "redirect_uri": "https://app.hostflow.test/oauth/callback",
                }
            }
        },
    )
    assert patch.status_code == 200, patch.text

    async def _fake_poll(**kwargs):
        class _R:
            ok = True
            provider = "gmail"
            returned = 1
            next_cursor = "next-page-token"
            raw = {"mocked": True}
            items = [
                {
                    "provider_thread_ref": f"thread-{account_id}",
                    "external_message_ref": f"msg-{account_id}",
                    "subject": "Hello from Gmail",
                    "from_address": "sender@example.test",
                    "to_address": "oauth@example.test",
                    "cc": [],
                    "text": "Body from Gmail",
                    "html": None,
                    "received_at": "2026-01-01T10:00:00+00:00",
                    "headers": {"message_id": "msg-1"},
                    "payload": {"source": "pytest"},
                }
            ]

        assert kwargs.get("provider") == "gmail"
        assert kwargs.get("access_token")
        return _R()

    monkeypatch.setattr("backend.app.api.v1.communications.poll_oauth_mailbox_messages", _fake_poll)

    poll = await client.post(
        "/api/v1/communications/email/worker/poll",
        headers=manager_headers,
        json={"only_account_id": account_id, "limit_per_account": 10},
    )
    assert poll.status_code == 200, poll.text
    poll_payload = poll.json()
    assert poll_payload.get("ingested_messages") == 1
    assert poll_payload.get("created_threads") == 1
    assert poll_payload.get("unsupported_accounts") == 0

    cursor = await client.get(
        f"/api/v1/communications/accounts/{account_id}/sync-cursor",
        headers=manager_headers,
        params={"cursor_key": "inbox_cursor"},
    )
    assert cursor.status_code == 200, cursor.text
    cursor_payload = cursor.json()
    assert cursor_payload.get("cursor_value") == "next-page-token"


@pytest.mark.anyio
async def test_outbound_thread_message_allowed_without_mandatory_link(
    client: AsyncClient,
    manager_headers: dict[str, str],
) -> None:
    await _update_comm_settings(
        client,
        manager_headers,
        lambda s: s["entitlements"]["modules"]["email"].update({"enabled": True}),
    )
    account = await _create_email_account(client, manager_headers, label="Unlinked outbound ok", provider="gmail")
    account_id = str(account["id"])

    created_thread = await client.post(
        "/api/v1/communications/threads",
        headers=manager_headers,
        json={
            "channel": "email",
            "subject": "Unlinked outbound",
            "channel_account_id": account_id,
            "participants_json": {"recipients": ["receiver@example.test"]},
        },
    )
    assert created_thread.status_code == 201, created_thread.text
    thread_id = str(created_thread.json().get("id") or "")

    first = await client.post(
        f"/api/v1/communications/threads/{thread_id}/messages",
        headers=manager_headers,
        json={
            "direction": "outbound",
            "message_type": "text",
            "recipient_address": "receiver@example.test",
            "subject": "Hi",
            "body_text": "Body",
            "delivery_status": "queued",
        },
    )
    assert first.status_code == 201, first.text

    patch = await client.patch(
        f"/api/v1/communications/threads/{thread_id}",
        headers=manager_headers,
        json={"thread_meta": {"uos": {"linked_service_order_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"}}},
    )
    assert patch.status_code == 200, patch.text

    second = await client.post(
        f"/api/v1/communications/threads/{thread_id}/messages",
        headers=manager_headers,
        json={
            "direction": "outbound",
            "message_type": "text",
            "recipient_address": "receiver@example.test",
            "subject": "Hi 2",
            "body_text": "Body 2",
            "delivery_status": "queued",
        },
    )
    assert second.status_code == 201, second.text
    # C0.1: UOS service order is known origin → G13 auto-ensured on outbound.
    detail = await client.get(
        f"/api/v1/communications/threads/{thread_id}",
        headers=manager_headers,
    )
    assert detail.status_code == 200, detail.text
    links = detail.json().get("thread", {}).get("entity_links") or []
    assert any(l.get("entity_type") == "service_order" for l in links)


@pytest.mark.anyio
async def test_email_dispatch_worker_gmail_oauth_uses_provider_send_adapter(
    client: AsyncClient,
    manager_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _update_comm_settings(
        client,
        manager_headers,
        lambda s: s["entitlements"]["modules"]["email"].update({"enabled": True}),
    )
    account = await _create_email_account(client, manager_headers, label="Gmail dispatch mailbox", provider="gmail")
    account_id = str(account["id"])
    patch = await client.patch(
        f"/api/v1/communications/accounts/{account_id}",
        headers=manager_headers,
        json={
            "settings_json": {
                "oauth": {
                    "access_token": "token-send-abc",
                    "client_id": "client-id",
                    "redirect_uri": "https://app.hostflow.test/oauth/callback",
                }
            }
        },
    )
    assert patch.status_code == 200, patch.text

    _link_stub = "11111111-1111-1111-1111-111111111111"
    created_thread = await client.post(
        "/api/v1/communications/threads",
        headers=manager_headers,
        json={
            "channel": "email",
            "subject": "Dispatch test",
            "channel_account_id": account_id,
            "linked_company_id": _link_stub,
            "participants_json": {"recipients": ["receiver@example.test"]},
        },
    )
    assert created_thread.status_code == 201, created_thread.text
    thread_id = str(created_thread.json().get("id") or "")
    assert thread_id

    created_msg = await client.post(
        f"/api/v1/communications/threads/{thread_id}/messages",
        headers=manager_headers,
        json={
            "direction": "outbound",
            "message_type": "text",
            "recipient_address": "receiver@example.test",
            "subject": "Hello outbound",
            "body_text": "Outbound body",
            "delivery_status": "queued",
        },
    )
    assert created_msg.status_code == 201, created_msg.text

    async def _fake_send(**kwargs):
        assert kwargs.get("provider") == "gmail"
        assert kwargs.get("to") == "receiver@example.test"
        return {"provider": "gmail", "message_ref": "gmail-message-1", "thread_ref": "gmail-thread-1", "payload": {"mocked": True}}

    monkeypatch.setattr("backend.app.api.v1.communications.send_oauth_email_message", _fake_send)

    dispatched = await client.post(
        "/api/v1/communications/email/worker/dispatch",
        headers=manager_headers,
        json={"limit": 20, "mark_delivered": True},
    )
    assert dispatched.status_code == 200, dispatched.text
    payload = dispatched.json()
    assert payload.get("processed") == 1
    assert payload.get("dispatched") == 1
    assert payload.get("failed") == 0
    first = (payload.get("items") or [])[0]
    assert first.get("dispatched") is True
    msg = first.get("message") or {}
    assert msg.get("delivery_status") in {"sent", "delivered"}
    assert str(msg.get("external_message_ref") or "").startswith("gmail-message-1")


@pytest.mark.anyio
async def test_email_dispatch_worker_schedules_retry_on_oauth_send_failure(
    client: AsyncClient,
    manager_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _update_comm_settings(
        client,
        manager_headers,
        lambda s: s["entitlements"]["modules"]["email"].update({"enabled": True}),
    )
    account = await _create_email_account(client, manager_headers, label="Gmail retry mailbox", provider="gmail")
    account_id = str(account["id"])
    patch = await client.patch(
        f"/api/v1/communications/accounts/{account_id}",
        headers=manager_headers,
        json={
            "settings_json": {
                "oauth": {
                    "access_token": "token-send-abc",
                    "client_id": "client-id",
                    "redirect_uri": "https://app.hostflow.test/oauth/callback",
                }
            }
        },
    )
    assert patch.status_code == 200, patch.text

    _link_stub = "11111111-1111-1111-1111-111111111111"
    created_thread = await client.post(
        "/api/v1/communications/threads",
        headers=manager_headers,
        json={
            "channel": "email",
            "subject": "Retry dispatch test",
            "channel_account_id": account_id,
            "linked_company_id": _link_stub,
            "participants_json": {"recipients": ["receiver@example.test"]},
        },
    )
    assert created_thread.status_code == 201, created_thread.text
    thread_id = str(created_thread.json().get("id") or "")

    created_msg = await client.post(
        f"/api/v1/communications/threads/{thread_id}/messages",
        headers=manager_headers,
        json={
            "direction": "outbound",
            "message_type": "text",
            "recipient_address": "receiver@example.test",
            "subject": "Hello outbound",
            "body_text": "Outbound body",
            "delivery_status": "queued",
        },
    )
    assert created_msg.status_code == 201, created_msg.text

    async def _fake_send(**kwargs):
        raise RuntimeError("provider down")

    monkeypatch.setattr("backend.app.api.v1.communications.send_oauth_email_message", _fake_send)

    dispatched = await client.post(
        "/api/v1/communications/email/worker/dispatch",
        headers=manager_headers,
        json={"limit": 20, "mark_delivered": True},
    )
    assert dispatched.status_code == 200, dispatched.text
    payload = dispatched.json()
    assert payload.get("processed") == 1
    assert payload.get("dispatched") == 0
    assert payload.get("failed") == 1
    first = (payload.get("items") or [])[0]
    msg = first.get("message") or {}
    assert msg.get("delivery_status") == "queued"
    dispatch_meta = (msg.get("payload") or {}).get("dispatch") or {}
    assert dispatch_meta.get("status") == "retry_scheduled"
    assert int(dispatch_meta.get("attempt_count") or 0) == 1
    assert dispatch_meta.get("next_retry_at")


@pytest.mark.anyio
async def test_email_dispatch_worker_marks_failed_after_retry_exhaustion(
    client: AsyncClient,
    manager_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _update_comm_settings(
        client,
        manager_headers,
        lambda s: s["entitlements"]["modules"]["email"].update({"enabled": True}),
    )
    account = await _create_email_account(client, manager_headers, label="Gmail exhausted retry mailbox", provider="gmail")
    account_id = str(account["id"])
    patch = await client.patch(
        f"/api/v1/communications/accounts/{account_id}",
        headers=manager_headers,
        json={
            "settings_json": {
                "oauth": {
                    "access_token": "token-send-abc",
                    "client_id": "client-id",
                    "redirect_uri": "https://app.hostflow.test/oauth/callback",
                }
            }
        },
    )
    assert patch.status_code == 200, patch.text

    _link_stub = "11111111-1111-1111-1111-111111111111"
    created_thread = await client.post(
        "/api/v1/communications/threads",
        headers=manager_headers,
        json={
            "channel": "email",
            "subject": "Retry exhaustion dispatch test",
            "channel_account_id": account_id,
            "linked_company_id": _link_stub,
            "participants_json": {"recipients": ["receiver@example.test"]},
        },
    )
    assert created_thread.status_code == 201, created_thread.text
    thread_id = str(created_thread.json().get("id") or "")

    created_msg = await client.post(
        f"/api/v1/communications/threads/{thread_id}/messages",
        headers=manager_headers,
        json={
            "direction": "outbound",
            "message_type": "text",
            "recipient_address": "receiver@example.test",
            "subject": "Hello outbound",
            "body_text": "Outbound body",
            "delivery_status": "queued",
            "payload": {"dispatch": {"attempt_count": 4}},
        },
    )
    assert created_msg.status_code == 201, created_msg.text

    async def _fake_send(**kwargs):
        raise RuntimeError("provider down")

    monkeypatch.setattr("backend.app.api.v1.communications.send_oauth_email_message", _fake_send)

    dispatched = await client.post(
        "/api/v1/communications/email/worker/dispatch",
        headers=manager_headers,
        json={"limit": 20, "mark_delivered": True},
    )
    assert dispatched.status_code == 200, dispatched.text
    payload = dispatched.json()
    assert payload.get("processed") == 1
    assert payload.get("dispatched") == 0
    assert payload.get("failed") == 1
    first = (payload.get("items") or [])[0]
    msg = first.get("message") or {}
    assert msg.get("delivery_status") == "failed"
    dispatch_meta = (msg.get("payload") or {}).get("dispatch") or {}
    assert dispatch_meta.get("status") == "failed"
    assert int(dispatch_meta.get("attempt_count") or 0) == 5


@pytest.mark.anyio
async def test_generic_ingest_updates_linked_candidate_on_existing_telegram_thread(
    client: AsyncClient,
    manager_headers: dict[str, str],
    tenant_id: str,
) -> None:
    await _update_comm_settings(
        client,
        manager_headers,
        lambda s: s["entitlements"]["modules"]["messages"].update({"enabled": True}),
    )

    intake_slug = f"comm-tg-{uuid4().hex[:10]}"
    async with async_session_maker() as session:
        session.add(
            TenantLeadForm(
                id=str(uuid4()),
                tenant_id=tenant_id,
                title="Communications intake form",
                public_slug=intake_slug,
                is_active=True,
            )
        )
        await session.commit()

    create_intake = await client.post(
        "/api/v1/public/intake",
        headers=manager_headers,
        json={
            "contacts": {
                "phone_country_code": "+48",
                "phone": f"500{uuid4().hex[:9]}",
                "email": f"tg-link-{uuid4().hex[:8]}@example.com",
            },
            "source": "test",
            "lead_form_slug": intake_slug,
        },
    )
    assert create_intake.status_code == 200, create_intake.text
    candidate_id = str(create_intake.json().get("candidate_id") or "")
    assert candidate_id

    chat_ref = f"tg-chat-regression-{uuid4().hex}"
    created_thread = await client.post(
        "/api/v1/communications/threads",
        headers=manager_headers,
        json={
            "channel": "telegram",
            "subject": "Link regression thread",
            "channel_thread_ref": chat_ref,
            "participants_json": {
                "senders": [chat_ref],
                "recipients": [chat_ref],
            },
        },
    )
    assert created_thread.status_code == 201, created_thread.text
    thread = created_thread.json()
    thread_id = str(thread.get("id") or "")
    assert thread_id
    assert not thread.get("linked_candidate_id")

    ingested = await client.post(
        "/api/v1/communications/ingest/telegram",
        headers=manager_headers,
        json={
            "provider": "telegram_bot",
            "provider_thread_ref": chat_ref,
            "provider_chat_ref": chat_ref,
            "external_message_ref": f"telegram:test:link-regression-{uuid4().hex}",
            "sender_address": chat_ref,
            "recipient_address": chat_ref,
            "text": "hello from linked candidate",
            "linked_candidate_id": candidate_id,
            "auto_assign": False,
        },
    )
    assert ingested.status_code == 201, ingested.text
    ingest_payload = ingested.json()
    assert ingest_payload.get("created_thread") is False
    ingest_thread = ingest_payload.get("thread") or {}
    assert str(ingest_thread.get("id") or "") == thread_id
    assert str(ingest_thread.get("linked_candidate_id") or "") == candidate_id

    reloaded = await client.get(
        f"/api/v1/communications/threads/{thread_id}",
        headers=manager_headers,
    )
    assert reloaded.status_code == 200, reloaded.text
    reloaded_thread = (reloaded.json().get("thread") or {})
    assert str(reloaded_thread.get("linked_candidate_id") or "") == candidate_id
