"""Stage 6B: shared cookie session, logout, refresh, CSRF."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from backend.app.auth.session_cookies import CSRF_HEADER, session_cookie_names
from backend.tests.conftest import _init_data


def _cookie_map(resp) -> dict[str, str]:
    # httpx 0.27+: resp.cookies is a Cookies jar
    return {k: v for k, v in resp.cookies.items()}


@pytest.mark.anyio
async def test_login_sets_shared_session_cookies(client: AsyncClient) -> None:
    data = await _init_data()
    names = session_cookie_names()
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": data["admin_email"], "password": "Host123!"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("access_token")
    cookies = _cookie_map(resp)
    assert names["access"] in cookies
    assert names["refresh"] in cookies
    assert names["csrf"] in cookies
    assert cookies[names["access"]] == body["access_token"]


@pytest.mark.anyio
async def test_whoami_verify_accepts_access_cookie_without_bearer(client: AsyncClient) -> None:
    data = await _init_data()
    names = session_cookie_names()
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": data["admin_email"], "password": "Host123!"},
    )
    assert login.status_code == 200, login.text
    access = login.cookies.get(names["access"])
    assert access

    # New request with cookie only (no Authorization).
    who = await client.get(
        "/api/v1/auth/whoami-verify",
        cookies={names["access"]: access},
    )
    assert who.status_code == 200, who.text
    assert who.json().get("email")


@pytest.mark.anyio
async def test_logout_clears_cookies_and_rejects_refresh(client: AsyncClient) -> None:
    data = await _init_data()
    names = session_cookie_names()
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": data["admin_email"], "password": "Host123!"},
    )
    assert login.status_code == 200, login.text
    cookies = {
        names["access"]: login.cookies.get(names["access"]),
        names["refresh"]: login.cookies.get(names["refresh"]),
        names["csrf"]: login.cookies.get(names["csrf"]),
    }
    assert all(cookies.values())

    out = await client.post("/api/v1/auth/logout", cookies=cookies)
    assert out.status_code == 200, out.text

    # Refresh must fail after logout (token revoked + cookies cleared by Set-Cookie).
    refresh = await client.post(
        "/api/v1/auth/refresh",
        cookies={names["refresh"]: cookies[names["refresh"]], names["csrf"]: cookies[names["csrf"]]},
        headers={CSRF_HEADER: cookies[names["csrf"]]},
    )
    assert refresh.status_code == 401


@pytest.mark.anyio
async def test_refresh_rotates_access_cookie(client: AsyncClient) -> None:
    data = await _init_data()
    names = session_cookie_names()
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": data["admin_email"], "password": "Host123!"},
    )
    assert login.status_code == 200, login.text
    csrf = login.cookies.get(names["csrf"])
    refresh_cookie = login.cookies.get(names["refresh"])
    old_access = login.cookies.get(names["access"])
    assert csrf and refresh_cookie and old_access

    refreshed = await client.post(
        "/api/v1/auth/refresh",
        cookies={
            names["refresh"]: refresh_cookie,
            names["csrf"]: csrf,
            names["access"]: old_access,
        },
        headers={CSRF_HEADER: csrf},
    )
    assert refreshed.status_code == 200, refreshed.text
    new_access = refreshed.cookies.get(names["access"]) or refreshed.json().get("access_token")
    new_refresh = refreshed.cookies.get(names["refresh"])
    assert new_access
    assert new_refresh
    assert new_refresh != refresh_cookie
    assert new_access != old_access


@pytest.mark.anyio
async def test_session_sync_reuses_login_refresh_cookie(client: AsyncClient) -> None:
    """Sync must not revoke the refresh family login just minted.

    Concurrent POST /login + POST /session/sync used to rotate hf_refresh out
    from under the browser, bouncing a valid password back to /login.
    """
    data = await _init_data()
    names = session_cookie_names()
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": data["admin_email"], "password": "Host123!"},
    )
    assert login.status_code == 200, login.text
    login_refresh = login.cookies.get(names["refresh"])
    login_access = login.cookies.get(names["access"]) or login.json().get("access_token")
    csrf = login.cookies.get(names["csrf"])
    assert login_refresh and login_access and csrf

    synced = await client.post(
        "/api/v1/auth/session/sync",
        cookies={
            names["access"]: login_access,
            names["refresh"]: login_refresh,
            names["csrf"]: csrf,
        },
        headers={"Authorization": f"Bearer {login_access}"},
    )
    assert synced.status_code == 200, synced.text
    assert synced.cookies.get(names["refresh"]) == login_refresh

    again = await client.post(
        "/api/v1/auth/session/sync",
        cookies={
            names["access"]: synced.cookies.get(names["access"]) or login_access,
            names["refresh"]: login_refresh,
            names["csrf"]: synced.cookies.get(names["csrf"]) or csrf,
        },
        headers={"Authorization": f"Bearer {login_access}"},
    )
    assert again.status_code == 200, again.text
    assert again.cookies.get(names["refresh"]) == login_refresh

    refreshed = await client.post(
        "/api/v1/auth/refresh",
        cookies={
            names["refresh"]: login_refresh,
            names["csrf"]: csrf,
            names["access"]: login_access,
        },
        headers={CSRF_HEADER: csrf},
    )
    assert refreshed.status_code == 200, refreshed.text


@pytest.mark.anyio
async def test_csrf_blocks_mutating_cookie_session_without_header(client: AsyncClient) -> None:
    data = await _init_data()
    names = session_cookie_names()
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": data["admin_email"], "password": "Host123!"},
    )
    assert login.status_code == 200, login.text
    cookies = {
        names["access"]: login.cookies.get(names["access"]),
        names["refresh"]: login.cookies.get(names["refresh"]),
        names["csrf"]: login.cookies.get(names["csrf"]),
    }

    # Preference PATCH is a mutating authenticated route.
    blocked = await client.patch(
        "/api/v1/users/me",
        json={"preferences": {"ui": {"theme": "light"}}},
        cookies=cookies,
        # deliberately omit CSRF header
    )
    assert blocked.status_code == 403, blocked.text

    ok = await client.patch(
        "/api/v1/users/me",
        json={"preferences": {"ui": {"theme": "light"}}},
        cookies=cookies,
        headers={CSRF_HEADER: cookies[names["csrf"]]},
    )
    # 200 or 422 depending on schema; must not be CSRF 403
    assert ok.status_code != 403, ok.text


@pytest.mark.anyio
async def test_bearer_without_csrf_cookie_still_works_for_api_clients(client: AsyncClient) -> None:
    data = await _init_data()
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": data["admin_email"], "password": "Host123!"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    # Pure Bearer call without sending session cookies.
    who = await client.get(
        "/api/v1/auth/whoami-verify",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert who.status_code == 200, who.text
