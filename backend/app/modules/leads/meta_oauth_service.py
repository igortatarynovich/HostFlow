"""Facebook Login OAuth for Meta Leads: code exchange, long-lived user token, page list."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any, List
from urllib.parse import urlencode

import httpx

from backend.app.constants.spa_paths import SETTINGS_INTEGRATIONS_META
from backend.app.core.settings import settings

META_OAUTH_STATE_SALT = "hostflow.meta.oauth.state.v1"
PENDING_TTL_SECONDS = 600


class MetaOAuthError(Exception):
    """Raised when Graph returns an error object."""


def meta_leads_oauth_redirect_uri() -> str | None:
    raw = (settings.meta_leads_oauth_redirect_uri or "").strip()
    if raw:
        return raw.rstrip("/")
    base = (settings.frontend_url or "").strip().rstrip("/")
    if not base:
        return None
    return f"{base}{SETTINGS_INTEGRATIONS_META}"


def oauth_configuration_ready() -> bool:
    app_id = (settings.meta_leads_app_id or "").strip()
    secret = (settings.meta_leads_shared_app_secret or "").strip()
    return bool(app_id and secret and meta_leads_oauth_redirect_uri())


def _state_signing_key() -> str:
    base = (settings.jwt_secret or settings.meta_credentials_key or "hostflow-dev-secret").strip()
    return f"{base}|{META_OAUTH_STATE_SALT}"


def sign_oauth_state(*, tenant_id: str, user_sub: str, ttl_seconds: int = 600) -> str:
    payload = {
        "t": tenant_id,
        "s": user_sub,
        "exp": int(time.time()) + ttl_seconds,
        "n": secrets.token_hex(8),
    }
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    sig = hmac.new(_state_signing_key().encode("utf-8"), body, hashlib.sha256).digest()
    token = base64.urlsafe_b64encode(body + b"::" + sig).decode("ascii").rstrip("=")
    return token


def verify_oauth_state(token: str) -> dict[str, Any]:
    pad = "=" * (-len(token) % 4)
    raw = base64.urlsafe_b64decode(token + pad)
    body_b, sep, sig_b = raw.partition(b"::")
    if sep != b"::" or not sig_b:
        raise ValueError("invalid_state")
    expect = hmac.new(_state_signing_key().encode("utf-8"), body_b, hashlib.sha256).digest()
    if not hmac.compare_digest(expect, sig_b):
        raise ValueError("bad_signature")
    data = json.loads(body_b.decode("utf-8"))
    if int(data.get("exp") or 0) < int(time.time()):
        raise ValueError("expired")
    return data


def build_facebook_authorize_url(*, state: str) -> str:
    app_id = (settings.meta_leads_app_id or "").strip()
    redirect_uri = meta_leads_oauth_redirect_uri()
    if not app_id or not redirect_uri:
        raise RuntimeError("meta_oauth_not_configured")
    gv = (settings.meta_graph_api_version or "v24.0").strip() or "v24.0"
    scopes = [
        "pages_read_engagement",
        "pages_manage_metadata",
        "pages_show_list",
        "leads_retrieval",
    ]
    q = urlencode(
        {
            "client_id": app_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "response_type": "code",
            "scope": ",".join(scopes),
        },
        safe="",
    )
    return f"https://www.facebook.com/{gv}/dialog/oauth?{q}"


def _graph_version() -> str:
    return (settings.meta_graph_api_version or "v24.0").strip() or "v24.0"


async def exchange_code_for_short_lived_user_token(*, code: str, redirect_uri: str) -> str:
    app_id = (settings.meta_leads_app_id or "").strip()
    secret = (settings.meta_leads_shared_app_secret or "").strip()
    if not app_id or not secret:
        raise RuntimeError("meta_oauth_not_configured")
    gv = _graph_version()
    url = f"https://graph.facebook.com/{gv}/oauth/access_token"
    params = {
        "client_id": app_id,
        "client_secret": secret,
        "redirect_uri": redirect_uri,
        "code": code,
    }
    async with httpx.AsyncClient(timeout=25.0) as client:
        r = await client.get(url, params=params)
        data = r.json()
    if r.status_code >= 400 or not isinstance(data, dict):
        raise MetaOAuthError(f"token_exchange_http_{r.status_code}")
    if data.get("error"):
        err = data.get("error") or {}
        raise MetaOAuthError(str(err.get("message") or err))
    token = (data.get("access_token") or "").strip()
    if not token:
        raise MetaOAuthError("missing_access_token")
    return token


async def exchange_for_long_lived_user_token(*, short_lived_user_token: str) -> str:
    app_id = (settings.meta_leads_app_id or "").strip()
    secret = (settings.meta_leads_shared_app_secret or "").strip()
    gv = _graph_version()
    url = f"https://graph.facebook.com/{gv}/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": secret,
        "fb_exchange_token": short_lived_user_token,
    }
    async with httpx.AsyncClient(timeout=25.0) as client:
        r = await client.get(url, params=params)
        data = r.json()
    if r.status_code >= 400 or not isinstance(data, dict):
        raise MetaOAuthError(f"long_lived_http_{r.status_code}")
    if data.get("error"):
        err = data.get("error") or {}
        raise MetaOAuthError(str(err.get("message") or err))
    token = (data.get("access_token") or "").strip()
    if not token:
        raise MetaOAuthError("missing_long_lived_token")
    return token


async def fetch_pages_with_tokens(*, user_access_token: str) -> List[dict[str, str]]:
    """Return [{id, name, access_token}, ...] from /me/accounts (paginated)."""
    gv = _graph_version()
    out: list[dict[str, str]] = []
    first_params = {
        "fields": "id,name,access_token",
        "access_token": user_access_token,
        "limit": "100",
    }
    next_url: str | None = f"https://graph.facebook.com/{gv}/me/accounts"
    async with httpx.AsyncClient(timeout=25.0) as client:
        first = True
        while next_url:
            if first:
                r = await client.get(next_url, params=first_params)
                first = False
            else:
                r = await client.get(next_url)
            data = r.json()
            if r.status_code >= 400 or not isinstance(data, dict):
                raise MetaOAuthError(f"me_accounts_http_{r.status_code}")
            if data.get("error"):
                err = data.get("error") or {}
                raise MetaOAuthError(str(err.get("message") or err))
            for row in data.get("data") or []:
                if not isinstance(row, dict):
                    continue
                pid = str(row.get("id") or "").strip()
                name = str(row.get("name") or pid).strip()
                tok = str(row.get("access_token") or "").strip()
                if pid and tok:
                    out.append({"id": pid, "name": name, "access_token": tok})
            paging = data.get("paging") or {}
            nxt = paging.get("next")
            next_url = str(nxt).strip() if nxt else None
    return out


async def subscribe_page_leadgen(*, page_id: str, page_access_token: str) -> None:
    gv = _graph_version()
    url = f"https://graph.facebook.com/{gv}/{page_id}/subscribed_apps"
    params = {"subscribed_fields": "leadgen", "access_token": page_access_token}
    async with httpx.AsyncClient(timeout=25.0) as client:
        r = await client.post(url, params=params)
        data = r.json() if r.content else {}
    if r.status_code >= 400:
        msg = str((data or {}).get("error") if isinstance(data, dict) else r.text)
        raise MetaOAuthError(msg or f"subscribe_http_{r.status_code}")
