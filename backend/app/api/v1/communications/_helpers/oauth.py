"""OAuth helpers for the communications package.

Extracted from ``communications/__init__.py`` (Phase 1 god-module split).

Depends on:
* :mod:`backend.app.api.v1.communications._helpers.utils` — ``_as_dict``, ``_now_utc``
* :mod:`backend.app.api.v1.communications._helpers.account_settings` —
  ``_normalize_account_settings_for_store`` (re-stored after refresh).
* :mod:`backend.app.core.crypto` — ``decrypt_secret``
* :mod:`backend.app.core.settings` — ``settings.frontend_url``
* :mod:`backend.app.constants.spa_paths` — ``EMAIL_LEGACY``
* :mod:`backend.app.services.communications_oauth` — token refresh provider adapter
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from urllib.parse import urlencode

from backend.app.constants.spa_paths import EMAIL_LEGACY
from backend.app.core.crypto import decrypt_secret
from backend.app.core.settings import settings
from backend.app.models.communication import CommunicationChannelAccount
from backend.app.services.communications_oauth import refresh_oauth_access_token

from .account_settings import _normalize_account_settings_for_store
from .utils import _as_dict, _now_utc

__all__ = [
    "_oauth_client_secret",
    "_oauth_refresh_token",
    "_oauth_access_token",
    "_oauth_expires_soon",
    "_refresh_oauth_tokens_in_settings_json",
    "_ensure_oauth_access_for_mailbox",
    "_oauth_provider_for_account",
    "_oauth_authorize_url_for_provider",
    "_oauth_default_scopes",
    "_build_oauth_auth_url",
]


def _oauth_client_secret(oauth_json: Dict[str, Any]) -> str | None:
    encrypted = str(oauth_json.get("client_secret_encrypted") or "").strip()
    if encrypted:
        return decrypt_secret(encrypted) or None
    plain = str(oauth_json.get("client_secret") or "").strip()
    return plain or None


def _oauth_refresh_token(oauth_json: Dict[str, Any]) -> str | None:
    encrypted = str(oauth_json.get("refresh_token_encrypted") or "").strip()
    if encrypted:
        return decrypt_secret(encrypted) or None
    plain = str(oauth_json.get("refresh_token") or "").strip()
    return plain or None


def _oauth_access_token(oauth_json: Dict[str, Any]) -> str | None:
    encrypted = str(oauth_json.get("access_token_encrypted") or "").strip()
    if encrypted:
        return decrypt_secret(encrypted) or None
    plain = str(oauth_json.get("access_token") or "").strip()
    return plain or None


def _oauth_expires_soon(oauth_json: Dict[str, Any], *, skew_seconds: int = 120) -> bool:
    raw = str(oauth_json.get("expires_at") or "").strip()
    if not raw:
        return False
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt <= (_now_utc() + timedelta(seconds=skew_seconds))
    except Exception:
        return False


async def _refresh_oauth_tokens_in_settings_json(
    settings_json: Dict[str, Any], *, provider: str
) -> str:
    """
    Exchange refresh_token for a new access_token; mutates settings_json['oauth'] (encrypted/plain fields).
    Used when expires_at still looks valid but Google/Graph returns 401, or before normal expiry refresh.
    """
    oauth_json = _as_dict(settings_json.get("oauth"))
    refresh_token = _oauth_refresh_token(oauth_json)
    client_id = str(oauth_json.get("client_id") or "").strip()
    client_secret = _oauth_client_secret(oauth_json)
    if not refresh_token:
        raise RuntimeError("OAuth refresh token is not configured")
    if not client_id:
        raise RuntimeError("OAuth client_id is required")
    token_payload = await refresh_oauth_access_token(
        provider=provider,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        scope=str(oauth_json.get("scope") or "").strip() or None,
    )
    oauth_next = {
        **oauth_json,
        "access_token": token_payload.access_token,
        "expires_at": (
            _now_utc() + timedelta(seconds=int(token_payload.expires_in or 3600))
        ).isoformat(),
        "token_type": token_payload.token_type or str(oauth_json.get("token_type") or "Bearer"),
        "scope": token_payload.scope or str(oauth_json.get("scope") or ""),
        "oauth_status": "connected",
        "last_error": None,
        "last_refreshed_at": _now_utc().isoformat(),
        "provider_payload": {
            **_as_dict(oauth_json.get("provider_payload")),
            **_as_dict(token_payload.provider_payload),
        },
    }
    if token_payload.refresh_token:
        oauth_next["refresh_token"] = token_payload.refresh_token
    if token_payload.id_token:
        oauth_next["id_token"] = token_payload.id_token
    settings_json["oauth"] = _normalize_account_settings_for_store(
        {"oauth": oauth_next}
    ).get("oauth", oauth_next)
    out = _oauth_access_token(_as_dict(settings_json.get("oauth")))
    if not out:
        raise RuntimeError("OAuth access token is missing after refresh")
    return out


async def _ensure_oauth_access_for_mailbox(
    settings_json: Dict[str, Any], *, provider: str
) -> str:
    """
    Return a usable access_token for Gmail/Graph polling or send.
    Proactively refreshes only when a refresh_token is stored — avoids RuntimeError when Google
    omitted refresh_token on a prior OAuth complete (short-lived access only).
    """
    oauth_json = _as_dict(settings_json.get("oauth"))
    access_token = _oauth_access_token(oauth_json)
    refresh_ok = bool(_oauth_refresh_token(oauth_json))
    if not access_token:
        if not refresh_ok:
            raise RuntimeError(
                "OAuth access token is missing and no refresh token is configured — run mailbox OAuth again. "
                "In Google: https://myaccount.google.com/permissions → remove HostFlow → then OAuth start in HostFlow."
            )
        return await _refresh_oauth_tokens_in_settings_json(settings_json, provider=provider)
    if _oauth_expires_soon(oauth_json) and refresh_ok:
        return await _refresh_oauth_tokens_in_settings_json(settings_json, provider=provider)
    return access_token


def _oauth_provider_for_account(account: CommunicationChannelAccount) -> str:
    settings_obj = _as_dict(account.settings_json)
    oauth_json = _as_dict(settings_obj.get("oauth"))
    provider = (
        str(oauth_json.get("provider") or settings_obj.get("provider") or account.channel or "")
        .strip()
        .lower()
    )
    if provider in {"google", "gmail"}:
        return "gmail"
    if provider in {"microsoft", "ms", "graph", "microsoft_graph", "office365"}:
        return "microsoft_graph"
    return provider or "unknown"


def _oauth_authorize_url_for_provider(provider: str) -> str:
    if provider == "gmail":
        return "https://accounts.google.com/o/oauth2/v2/auth"
    if provider == "microsoft_graph":
        return "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    return "https://example.com/oauth/authorize"


def _oauth_default_scopes(provider: str) -> List[str]:
    if provider == "gmail":
        return [
            "openid",
            "email",
            "profile",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
        ]
    if provider == "microsoft_graph":
        return [
            "offline_access",
            "User.Read",
            "Mail.Read",
            "Mail.Send",
        ]
    return ["openid", "email"]


def _build_oauth_auth_url(
    *,
    provider: str,
    client_id: str | None,
    redirect_uri: str | None,
    scopes: List[str],
    state: str,
    force_consent: bool,
) -> str:
    base = _oauth_authorize_url_for_provider(provider)
    safe_client_id = client_id or "missing_client_id"
    _fe = (settings.frontend_url or "").strip().rstrip("/") or "https://hostflow.cc"
    safe_redirect_uri = redirect_uri or f"{_fe}{EMAIL_LEGACY}"
    scope_joined = (
        " ".join([s for s in scopes if isinstance(s, str) and s.strip()]) or "openid email"
    )
    # Google: access_type=offline is required for refresh_token; prompt is space-delimited per Google docs.
    # include_granted_scopes helps incremental authorization for Gmail API scopes.
    params: Dict[str, str] = {
        "client_id": safe_client_id,
        "redirect_uri": safe_redirect_uri,
        "response_type": "code",
        "scope": scope_joined,
        "state": state,
    }
    if provider == "gmail":
        params["access_type"] = "offline"
        params["include_granted_scopes"] = "true"
        # Always request consent so Google returns a refresh_token (it often omits it on re-auth otherwise).
        params["prompt"] = "consent select_account"
    else:
        params["prompt"] = "consent" if force_consent else "select_account"
    query = urlencode(params)
    return f"{base}?{query}"
