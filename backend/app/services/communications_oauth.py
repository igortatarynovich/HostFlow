from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx


class OAuthProviderError(RuntimeError):
    def __init__(self, message: str, *, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass
class OAuthTokenPayload:
    access_token: str
    refresh_token: str | None = None
    token_type: str | None = None
    expires_in: int | None = None
    scope: str | None = None
    id_token: str | None = None
    provider_payload: Dict[str, Any] | None = None


def _token_endpoint(provider: str) -> str:
    p = (provider or "").strip().lower()
    if p == "gmail":
        return "https://oauth2.googleapis.com/token"
    if p in {"microsoft_graph", "microsoft", "outlook"}:
        return "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    raise OAuthProviderError(f"OAuth provider is not supported: {provider}", status_code=422)


def _extract_token_payload(raw: Dict[str, Any]) -> OAuthTokenPayload:
    access_token = str(raw.get("access_token") or "").strip()
    if not access_token:
        raise OAuthProviderError("Provider token response does not contain access_token", status_code=502)
    expires_raw = raw.get("expires_in")
    expires_in: Optional[int]
    try:
        expires_in = int(expires_raw) if expires_raw is not None else None
    except Exception:
        expires_in = None
    return OAuthTokenPayload(
        access_token=access_token,
        refresh_token=str(raw.get("refresh_token") or "").strip() or None,
        token_type=str(raw.get("token_type") or "").strip() or None,
        expires_in=expires_in,
        scope=str(raw.get("scope") or "").strip() or None,
        id_token=str(raw.get("id_token") or "").strip() or None,
        provider_payload=raw,
    )


async def _post_token_form(url: str, payload: Dict[str, Any]) -> OAuthTokenPayload:
    data: Dict[str, str] = {}
    for k, v in payload.items():
        if v is None:
            continue
        text = str(v).strip()
        if not text:
            continue
        data[k] = text
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
    except httpx.TimeoutException as exc:
        raise OAuthProviderError(f"OAuth provider timeout: {exc}", status_code=504) from exc
    except httpx.HTTPError as exc:
        raise OAuthProviderError(f"OAuth provider request error: {exc}", status_code=502) from exc

    raw: Dict[str, Any] = {}
    try:
        parsed = response.json()
        if isinstance(parsed, dict):
            raw = parsed
    except Exception:
        raw = {}
    if response.status_code >= 400:
        detail = str(raw.get("error_description") or raw.get("error") or response.text or "Provider token request failed")
        raise OAuthProviderError(detail, status_code=502)
    return _extract_token_payload(raw)


async def exchange_oauth_code_for_tokens(
    *,
    provider: str,
    code: str,
    redirect_uri: str,
    client_id: str,
    client_secret: str | None = None,
    code_verifier: str | None = None,
) -> OAuthTokenPayload:
    if not code.strip():
        raise OAuthProviderError("OAuth code is required", status_code=422)
    if not redirect_uri.strip():
        raise OAuthProviderError("OAuth redirect_uri is required", status_code=422)
    if not client_id.strip():
        raise OAuthProviderError("OAuth client_id is required", status_code=422)
    url = _token_endpoint(provider)
    return await _post_token_form(
        url,
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret or None,
            "code_verifier": code_verifier or None,
        },
    )


async def refresh_oauth_access_token(
    *,
    provider: str,
    refresh_token: str,
    client_id: str,
    client_secret: str | None = None,
    scope: str | None = None,
) -> OAuthTokenPayload:
    if not refresh_token.strip():
        raise OAuthProviderError("OAuth refresh token is required", status_code=422)
    if not client_id.strip():
        raise OAuthProviderError("OAuth client_id is required", status_code=422)
    url = _token_endpoint(provider)
    return await _post_token_form(
        url,
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret or None,
            "scope": scope or None,
        },
    )
