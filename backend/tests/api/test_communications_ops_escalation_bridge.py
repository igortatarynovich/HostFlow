"""Manual Inbox ops escalation → Tasks + notifications + audit (UOS bridge)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_patch_thread_escalated_emits_notification_and_reminder(
    client: AsyncClient,
    manager_headers: dict[str, str],
) -> None:
    me = await client.get("/api/v1/users/me", headers=manager_headers)
    assert me.status_code == 200, me.text
    profile = (me.json() or {}).get("profile") or {}
    manager_id = str(profile.get("user_id") or "").strip()
    assert manager_id

    created = await client.post(
        "/api/v1/communications/threads",
        headers=manager_headers,
        json={
            "channel": "messages",
            "subject": "Escalation bridge test",
            "channel_thread_ref": "test-esc-bridge-1",
            "participants_json": {"senders": [], "recipients": []},
        },
    )
    assert created.status_code == 201, created.text
    thread_id = str((created.json() or {}).get("id") or "")
    assert thread_id

    patch = await client.patch(
        f"/api/v1/communications/threads/{thread_id}",
        headers=manager_headers,
        json={
            "thread_meta": {
                "ops": {
                    "mode": "escalated",
                    "escalation": {
                        "reason": "Need supervisor review on terms.",
                        "target": {"user_id": manager_id},
                    },
                },
            },
        },
    )
    assert patch.status_code == 200, patch.text

    notifs = await client.get(
        "/api/v1/notifications",
        headers=manager_headers,
        params={"include_read": True, "limit": 50},
    )
    assert notifs.status_code == 200, notifs.text
    items = (notifs.json() or {}).get("items") or []
    hit = [x for x in items if str(x.get("event_type") or "") == "communications_thread_escalated"]
    assert hit, "expected communications_thread_escalated notification"
    assert str((hit[0].get("entity_id") or "")) == thread_id

    reminders = await client.get(
        "/api/v1/reminders",
        headers=manager_headers,
        params={"assignee_scope": "mine", "limit": 80},
    )
    assert reminders.status_code == 200, reminders.text
    ritems = (reminders.json() or {}).get("items") or []
    rhit = [
        x
        for x in ritems
        if str(x.get("type") or "") == "communications_thread_escalated"
        and str(x.get("entity_id") or "") == thread_id
    ]
    assert rhit, "expected communications_thread_escalated reminder"

    again = await client.patch(
        f"/api/v1/communications/threads/{thread_id}",
        headers=manager_headers,
        json={"thread_meta": {"sla_policy": {"muted": False}}},
    )
    assert again.status_code == 200, again.text

    notifs2 = await client.get(
        "/api/v1/notifications",
        headers=manager_headers,
        params={"include_read": True, "limit": 200},
    )
    assert notifs2.status_code == 200, notifs2.text
    items2 = (notifs2.json() or {}).get("items") or []
    escal_for_thread = [
        x
        for x in items2
        if str(x.get("event_type") or "") == "communications_thread_escalated"
        and str(x.get("entity_id") or "") == thread_id
    ]
    assert len(escal_for_thread) == 1, "re-patch while still escalated must not duplicate bridge"

