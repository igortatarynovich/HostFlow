"""Forward from `new` requires ≥1 contact attempt when client contact policy is enabled."""

import pytest


@pytest.mark.anyio
async def test_forward_blocked_new_without_attempt_when_policy_on(client, manager_headers, monkeypatch):
    create = await client.post(
        "/api/v1/candidates",
        headers=manager_headers,
        json={"first_name": "Ct", "last_name": "PolicyOn"},
    )
    assert create.status_code == 200, create.text
    cid = create.json()["id"]

    async def _policy_on(*args, **kwargs):
        return {
            "enabled": True,
            "max_attempts": 3,
            "post_action": "auto_reject",
            "stage_code": None,
            "rodo_sent": True,
            "tracking_disabled_reason": None,
        }

    async def _count_zero(*args, **kwargs):
        return 0

    monkeypatch.setattr(
        "backend.app.services.contact_attempts.get_effective_contact_policy",
        _policy_on,
    )
    monkeypatch.setattr(
        "backend.app.services.contact_attempts.count_contact_attempts",
        _count_zero,
    )

    r = await client.patch(
        f"/api/v1/candidates/{cid}",
        headers=manager_headers,
        json={"stage": "no_answer"},
    )
    assert r.status_code == 409, r.text
    detail = r.json().get("detail")
    if isinstance(detail, dict):
        assert detail.get("code") == "stage_blocked_by_contact_attempt"
    else:
        assert "contact" in str(detail).lower()


@pytest.mark.anyio
async def test_forward_allowed_new_when_attempt_counted(client, manager_headers, monkeypatch):
    create = await client.post(
        "/api/v1/candidates",
        headers=manager_headers,
        json={"first_name": "Ct", "last_name": "HasAttempt"},
    )
    assert create.status_code == 200, create.text
    cid = create.json()["id"]

    async def _policy_on(*args, **kwargs):
        return {
            "enabled": True,
            "max_attempts": 3,
            "post_action": "auto_reject",
            "stage_code": None,
            "rodo_sent": True,
            "tracking_disabled_reason": None,
        }

    async def _count_one(*args, **kwargs):
        return 1

    monkeypatch.setattr(
        "backend.app.services.contact_attempts.get_effective_contact_policy",
        _policy_on,
    )
    monkeypatch.setattr(
        "backend.app.services.contact_attempts.count_contact_attempts",
        _count_one,
    )

    r = await client.patch(
        f"/api/v1/candidates/{cid}",
        headers=manager_headers,
        json={"stage": "no_answer"},
    )
    assert r.status_code == 200, r.text
