from __future__ import annotations

import base64

import pytest
import sqlalchemy as sa
from httpx import AsyncClient

from backend.app.core.security import hash_password
from backend.app.db.session import async_session_maker
from backend.app.models.user import User
from backend.tests.conftest import _init_data


AVATAR_SAMPLE = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+BFwAI/AL+P7q0WgAAAABJRU5ErkJggg=="
)


def _auth_headers(token: str, tenant_id: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Id": tenant_id,
    }


@pytest.mark.anyio
async def test_user_profile_preferences_flow(client: AsyncClient) -> None:
    data = await _init_data()

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": data["admin_email"], "password": "Host123!"},
    )
    assert login_resp.status_code == 200, login_resp.text
    login_body = login_resp.json()
    token = login_body["access_token"]

    headers = _auth_headers(token, data["tenant_id"])

    me_resp = await client.get("/api/v1/users/me", headers=headers)
    assert me_resp.status_code == 200, me_resp.text
    me_body = me_resp.json()
    assert "profile" in me_body and "preferences" in me_body and "security" in me_body

    patch_payload = {
        "profile": {
            "first_name": "Updated",
            "last_name": "Administrator",
            "country": "PL",
        },
        "preferences": {
            "ui": {
                "theme": "dark",
                "locale": "ru-RU",
                "timezone": "Europe/Warsaw",
            },
            "defaults": {
                "company_id": None,
            },
            "saved_views": {
                "candidates": [
                    {
                        "id": "test-candidates",
                        "name": "Тест candidates",
                        "filters": {"q": "demo"},
                        "is_default": True,
                    }
                ],
                "vacancies": [
                    {
                        "id": "test-vacancies",
                        "name": "Тест vacancies",
                        "filters": {"status": "open"},
                    }
                ],
            },
        },
    }

    patch_resp = await client.patch(
        "/api/v1/users/me",
        headers=headers | {"Content-Type": "application/json"},
        json=patch_payload,
    )
    assert patch_resp.status_code == 200, patch_resp.text
    patch_body = patch_resp.json()
    assert patch_body["profile"]["first_name"] == "Updated"
    assert patch_body["preferences"]["ui"]["theme"] == "dark"
    assert patch_body["preferences"]["saved_views"]["candidates"][0]["is_default"] is True

    notif_resp = await client.patch(
        "/api/v1/users/me/notifications",
        headers=headers | {"Content-Type": "application/json"},
        json={
            "mentions.direct": {"enabled": False, "mode": "daily_digest"},
        },
    )
    assert notif_resp.status_code == 200, notif_resp.text
    notif_body = notif_resp.json()
    assert notif_body["mentions.direct"]["enabled"] is False
    assert notif_body["mentions.direct"]["mode"] == "daily_digest"

    avatar_resp = await client.post(
        "/api/v1/users/me/avatar",
        headers=headers,
        files={"file": ("avatar.png", AVATAR_SAMPLE, "image/png")},
    )
    assert avatar_resp.status_code == 200, avatar_resp.text
    avatar_body = avatar_resp.json()
    assert avatar_body["avatar_url"].startswith("/uploads/avatars/")

    sessions_resp = await client.get("/api/v1/users/me/sessions", headers=headers)
    assert sessions_resp.status_code == 200, sessions_resp.text
    sessions = sessions_resp.json()
    assert isinstance(sessions, list)
    assert len(sessions) >= 1

    revoke_resp = await client.delete("/api/v1/users/me/sessions", headers=headers)
    assert revoke_resp.status_code == 200, revoke_resp.text
    revoke_body = revoke_resp.json()
    assert revoke_body.get("revoked", 0) >= 1

    password_payload = {
        "current_password": "Host123!",
        "new_password": "NewPass!234567",
    }
    pwd_resp = await client.post(
        "/api/v1/users/me/password",
        headers=headers | {"Content-Type": "application/json"},
        json=password_payload,
    )
    assert pwd_resp.status_code == 204, pwd_resp.text

    relogin_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": data["admin_email"], "password": "NewPass!234567"},
    )
    assert relogin_resp.status_code == 200, relogin_resp.text

    # revert password to original value to keep fixtures stable
    async with async_session_maker() as session:
        await session.execute(
            sa.update(User)
            .where(User.id == data["admin_id"])
            .values(password_hash=hash_password("Host123!"))
        )
        await session.commit()
