from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from backend.app.db.session import async_session_maker
from backend.app.models.user import User


@pytest.mark.anyio
async def test_register_requires_legal_consent(client: AsyncClient) -> None:
    email = f"signup-no-consent-{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": email,
        "password": "Host123!456",
        "workspace_name": "Consent Missing Workspace",
        "full_name": "Consent Missing",
        "plan_code": "starter",
    }

    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 422, resp.text
    assert "acceptance" in resp.text.lower()


@pytest.mark.anyio
async def test_register_persists_signup_consents_and_meta(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_send_system_email(*, to: str, subject: str, body: str) -> bool:
        return False

    monkeypatch.setattr("backend.app.auth.router.send_system_email", _fake_send_system_email)

    email = f"signup-consent-{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": email,
        "password": "Host123!456",
        "workspace_name": "Consent Verified Workspace",
        "full_name": "Consent Verified",
        "plan_code": "starter",
        "accept_terms": True,
        "accept_privacy": True,
    }

    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    assert body["tenant"]["status"] == "trial"
    assert body["tenant"]["trial_days"] == 30
    assert body.get("meta", {}).get("welcome_email_sent") is False

    async with async_session_maker() as session:
        user = await session.scalar(
            select(User).where(func.lower(User.email) == email.lower()).limit(1)
        )
        assert user is not None
        extra = user.extra or {}
        consents = extra.get("signup_consents") if isinstance(extra, dict) else None
        assert isinstance(consents, dict)
        assert consents.get("terms") is True
        assert consents.get("privacy") is True
        assert isinstance(consents.get("accepted_at"), str)
        assert consents.get("terms_version") == "2025-02-01"
        assert consents.get("privacy_version") == "2025-02-01"
