from __future__ import annotations

import pytest


@pytest.mark.anyio
async def test_notification_templates_expose_channels(client, manager_headers):
    response = await client.get(
        "/api/v1/notifications/templates",
        headers=manager_headers,
    )
    assert response.status_code == 200, response.text

    body = response.json()
    items = body.get("items") or []
    assert items, "expected at least one notification template"

    pre_24 = next(
        (item for item in items if item["slug"] == "document.expiry.pre_24"),
        None,
    )
    assert pre_24 is not None
    assert pre_24["schedule_key"] == "document_expiry:-24"
    assert pre_24["offset_hours"] == -24
    channel_names = {entry["channel"] for entry in pre_24["channels"]}
    assert channel_names == {"in_app", "email", "webhook"}

    assert set(pre_24["channel_templates"]) == {"in_app", "email", "webhook"}
    email_channel = next(entry for entry in pre_24["channels"] if entry["channel"] == "email")
    assert email_channel["template_key"] == "email.document_expiry.pre_24"
    assert email_channel["subject_key"] == "email.document_expiry.pre_24.subject"
    assert (
        pre_24["channel_templates"]["email"]["template_key"]
        == "email.document_expiry.pre_24"
    )
    assert "notifications.document_expiry.pre_24" in pre_24["localization_keys"]
    assert pre_24["metadata"]["phase"] == "pre"
