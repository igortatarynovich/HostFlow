"""Channel-account OAuth + sync-cursor endpoints for the communications API.

Endpoints:

* POST   /communications/accounts/{account_id}/oauth/start
* POST   /communications/accounts/{account_id}/oauth/complete
* POST   /communications/accounts/{account_id}/oauth/refresh
* GET    /communications/accounts/{account_id}/sync-cursor
* PATCH  /communications/accounts/{account_id}/sync-cursor
"""

from __future__ import annotations

from datetime import timedelta
from typing import Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.core.crypto import generate_secret
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.communication import CommunicationChannelAccount
from backend.app.services.communications_access import assert_comm_feature_access
from backend.app.services.communications_oauth import (
    OAuthProviderError,
    exchange_oauth_code_for_tokens,
    refresh_oauth_access_token,
)

from .._helpers.access import _feature_for_channel, _get_tenant_or_404
from .._helpers.account_settings import _account_out, _normalize_account_settings_for_store
from .._helpers.oauth import (
    _build_oauth_auth_url,
    _oauth_client_secret,
    _oauth_default_scopes,
    _oauth_provider_for_account,
    _oauth_refresh_token,
)
from .._helpers.utils import _as_dict, _as_list, _now_utc
from ..schemas import (
    CommunicationAccountOAuthCompleteRequest,
    CommunicationAccountOAuthCompleteResponse,
    CommunicationAccountOAuthRefreshRequest,
    CommunicationAccountOAuthStartRequest,
    CommunicationAccountOAuthStartResponse,
    CommunicationAccountSyncCursorOut,
    CommunicationAccountSyncCursorPatch,
)

router = APIRouter(tags=["communications"])


@router.post("/accounts/{account_id}/oauth/start", response_model=CommunicationAccountOAuthStartResponse)
async def start_channel_account_oauth(
    account_id: str,
    body: CommunicationAccountOAuthStartRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationAccountOAuthStartResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    account = await db.get(CommunicationChannelAccount, account_id)
    if account is None or str(account.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Channel account not found")
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=_feature_for_channel(account.channel))  # type: ignore[arg-type]

    provider = _oauth_provider_for_account(account)
    if provider not in {"gmail", "microsoft_graph"}:
        raise HTTPException(status_code=422, detail=f"OAuth is not supported for provider: {provider}")

    settings = _as_dict(account.settings_json)
    oauth_json = _as_dict(settings.get("oauth"))
    state = generate_secret(40)
    scopes = [s for s in (body.scopes or []) if isinstance(s, str) and s.strip()] or _oauth_default_scopes(provider)
    redirect_from_body = str(body.redirect_uri or "").strip() or None
    client_from_body = str(body.client_id or "").strip() or None
    redirect_uri = redirect_from_body or str(oauth_json.get("redirect_uri") or "").strip() or None
    client_id = client_from_body or str(oauth_json.get("client_id") or "").strip() or None
    if not client_id:
        raise HTTPException(status_code=422, detail="OAuth client_id is not configured")
    if not redirect_uri:
        raise HTTPException(status_code=422, detail="OAuth redirect_uri is not configured")

    oauth_json.update(
        {
            "provider": provider,
            "state": state,
            "state_created_at": _now_utc().isoformat(),
            "redirect_uri": redirect_uri,
            "scopes": scopes,
            "oauth_status": "pending",
            "last_error": None,
        }
    )
    if client_from_body:
        oauth_json["client_id"] = client_from_body
    settings["oauth"] = oauth_json
    account.settings_json = settings
    await db.commit()
    await db.refresh(account)

    auth_url = _build_oauth_auth_url(
        provider=provider,
        client_id=client_id,
        redirect_uri=redirect_uri,
        scopes=scopes,
        state=state,
        force_consent=bool(body.force_consent),
    )
    return CommunicationAccountOAuthStartResponse(
        ok=True,
        action="oauth_start",
        provider=provider,
        state=state,
        auth_url=auth_url,
        account=_account_out(account),
    )


@router.post("/accounts/{account_id}/oauth/complete", response_model=CommunicationAccountOAuthCompleteResponse)
async def complete_channel_account_oauth(
    account_id: str,
    body: CommunicationAccountOAuthCompleteRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationAccountOAuthCompleteResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    account = await db.get(CommunicationChannelAccount, account_id)
    if account is None or str(account.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Channel account not found")
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=_feature_for_channel(account.channel))  # type: ignore[arg-type]

    provider = _oauth_provider_for_account(account)
    settings = _as_dict(account.settings_json)
    oauth_json = _as_dict(settings.get("oauth"))
    oauth_refresh_existed_before = bool(_oauth_refresh_token(oauth_json))
    expected_state = str(oauth_json.get("state") or "").strip()
    if expected_state and body.state != expected_state:
        raise HTTPException(status_code=409, detail="OAuth state mismatch")

    now = _now_utc()
    access_token = body.access_token
    refresh_token = body.refresh_token
    id_token = body.id_token
    exchanged_via_code = False

    if body.simulate_exchange and not access_token:
        # Foundation mode: allow callback completion without external token exchange.
        # Real adapters (Gmail/Graph) will exchange code and pass real tokens.
        if not (body.code or "").strip():
            raise HTTPException(status_code=422, detail="OAuth code is required")
        access_token = f"sim_{provider}_access_{generate_secret(24)}"
        refresh_token = refresh_token or f"sim_{provider}_refresh_{generate_secret(24)}"
        id_token = id_token or f"sim_{provider}_id_{generate_secret(24)}"
    elif not access_token:
        exchanged_via_code = True
        code = str(body.code or "").strip()
        if not code:
            raise HTTPException(status_code=422, detail="OAuth code is required")
        redirect_uri = str(body.redirect_uri or oauth_json.get("redirect_uri") or "").strip()
        client_id = str(body.client_id or oauth_json.get("client_id") or "").strip()
        client_secret = _oauth_client_secret(oauth_json)
        if not redirect_uri:
            raise HTTPException(status_code=422, detail="OAuth redirect_uri is required")
        if not client_id:
            raise HTTPException(status_code=422, detail="OAuth client_id is required")
        if provider == "gmail" and not (client_secret or "").strip():
            if str(oauth_json.get("client_secret_encrypted") or "").strip():
                raise HTTPException(
                    status_code=422,
                    detail="OAuth client_secret is stored but cannot be decrypted (META_CREDENTIALS_KEY / JWT secret likely changed since it was saved). Re-save the Google client secret on this mailbox, then OAuth start → OAuth complete with a fresh code.",
                )
            raise HTTPException(
                status_code=422,
                detail="OAuth client_secret is missing for this mailbox — enter the Google client secret, click Save mailbox, then OAuth start → OAuth complete with a fresh code.",
            )
        try:
            token_payload = await exchange_oauth_code_for_tokens(
                provider=provider,
                code=code,
                redirect_uri=redirect_uri,
                client_id=client_id,
                client_secret=client_secret,
                code_verifier=body.code_verifier,
            )
        except OAuthProviderError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
        access_token = token_payload.access_token
        refresh_token = refresh_token or token_payload.refresh_token
        id_token = id_token or token_payload.id_token
        if not body.scope and token_payload.scope:
            body.scope = token_payload.scope
        if not body.token_type and token_payload.token_type:
            body.token_type = token_payload.token_type
        if token_payload.expires_in:
            body.expires_in = token_payload.expires_in
        if token_payload.provider_payload:
            body.provider_payload = {**token_payload.provider_payload, **_as_dict(body.provider_payload)}

    if not str(access_token or "").strip():
        raise HTTPException(status_code=422, detail="OAuth access token is required")

    if (
        exchanged_via_code
        and not body.simulate_exchange
        and provider in ("gmail", "microsoft_graph")
        and not str(refresh_token or "").strip()
        and not oauth_refresh_existed_before
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "Provider did not return a refresh token; HostFlow needs it for background email sync. "
                "In Google open https://myaccount.google.com/permissions , remove access for this OAuth client, "
                "then in HostFlow: Save mailbox → OAuth start (use the in-app button, not an old bookmark) → sign in and accept all scopes."
            ),
        )

    oauth_mut = {
        **oauth_json,
        "provider": provider,
        "token_type": body.token_type or "Bearer",
        "scope": body.scope or " ".join(_as_list(oauth_json.get("scopes"))),
        "connected_at": now.isoformat(),
        "oauth_status": "connected",
        "last_error": None,
        "expires_at": (now + timedelta(seconds=int(body.expires_in or 3600))).isoformat(),
        "last_completed_by": str(getattr(current_user, "sub", "") or ""),
        "provider_payload": _as_dict(body.provider_payload),
    }
    oauth_mut["access_token"] = str(access_token)
    if refresh_token:
        oauth_mut["refresh_token"] = str(refresh_token)
    if id_token:
        oauth_mut["id_token"] = str(id_token)

    settings["oauth"] = _normalize_account_settings_for_store({"oauth": oauth_mut}).get("oauth", oauth_mut)
    account.settings_json = settings
    await db.commit()
    await db.refresh(account)

    return CommunicationAccountOAuthCompleteResponse(
        ok=True,
        action="oauth_complete",
        provider=provider,
        account=_account_out(account),
        detail="OAuth mailbox connected",
    )


@router.post("/accounts/{account_id}/oauth/refresh", response_model=CommunicationAccountOAuthCompleteResponse)
async def refresh_channel_account_oauth_token(
    account_id: str,
    body: CommunicationAccountOAuthRefreshRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationAccountOAuthCompleteResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    account = await db.get(CommunicationChannelAccount, account_id)
    if account is None or str(account.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Channel account not found")
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=_feature_for_channel(account.channel))  # type: ignore[arg-type]

    provider = _oauth_provider_for_account(account)
    settings = _as_dict(account.settings_json)
    oauth_json = _as_dict(settings.get("oauth"))
    refresh_token = _oauth_refresh_token(oauth_json)
    if not refresh_token:
        raise HTTPException(status_code=409, detail="OAuth refresh token is not configured")

    now = _now_utc()
    if body.simulate_refresh:
        oauth_mut = {
            **oauth_json,
            "access_token": f"sim_{provider}_access_{generate_secret(24)}",
            "expires_at": (now + timedelta(seconds=int(body.expires_in or 3600))).isoformat(),
            "oauth_status": "connected",
            "last_error": None,
            "last_refreshed_at": now.isoformat(),
            "provider_payload": {**_as_dict(oauth_json.get("provider_payload")), **_as_dict(body.provider_payload)},
        }
        settings["oauth"] = _normalize_account_settings_for_store({"oauth": oauth_mut}).get("oauth", oauth_mut)
        account.settings_json = settings
        await db.commit()
        await db.refresh(account)
        return CommunicationAccountOAuthCompleteResponse(
            ok=True,
            action="oauth_refresh",
            provider=provider,
            account=_account_out(account),
            detail="OAuth token refreshed (simulated)",
        )

    client_id = str(oauth_json.get("client_id") or "").strip()
    client_secret = _oauth_client_secret(oauth_json)
    if not client_id:
        raise HTTPException(status_code=422, detail="OAuth client_id is required")
    try:
        token_payload = await refresh_oauth_access_token(
            provider=provider,
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            scope=str(oauth_json.get("scope") or "").strip() or None,
        )
    except OAuthProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    oauth_mut = {
        **oauth_json,
        "access_token": token_payload.access_token,
        "expires_at": (now + timedelta(seconds=int(token_payload.expires_in or body.expires_in or 3600))).isoformat(),
        "token_type": token_payload.token_type or str(oauth_json.get("token_type") or "Bearer"),
        "scope": token_payload.scope or str(oauth_json.get("scope") or ""),
        "oauth_status": "connected",
        "last_error": None,
        "last_refreshed_at": now.isoformat(),
        "provider_payload": {
            **_as_dict(oauth_json.get("provider_payload")),
            **_as_dict(token_payload.provider_payload),
            **_as_dict(body.provider_payload),
        },
    }
    if token_payload.refresh_token:
        oauth_mut["refresh_token"] = token_payload.refresh_token
    if token_payload.id_token:
        oauth_mut["id_token"] = token_payload.id_token
    settings["oauth"] = _normalize_account_settings_for_store({"oauth": oauth_mut}).get("oauth", oauth_mut)
    account.settings_json = settings
    await db.commit()
    await db.refresh(account)

    return CommunicationAccountOAuthCompleteResponse(
        ok=True,
        action="oauth_refresh",
        provider=provider,
        account=_account_out(account),
        detail="OAuth token refreshed",
    )


@router.get("/accounts/{account_id}/sync-cursor", response_model=CommunicationAccountSyncCursorOut)
async def get_channel_account_sync_cursor(
    account_id: str,
    cursor_key: str = Query(..., min_length=1, max_length=128),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationAccountSyncCursorOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    account = await db.get(CommunicationChannelAccount, account_id)
    if account is None or str(account.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Channel account not found")
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=_feature_for_channel(account.channel))  # type: ignore[arg-type]

    settings = _as_dict(account.settings_json)
    cursors = _as_dict(settings.get("sync_cursors"))
    row = _as_dict(cursors.get(cursor_key))
    return CommunicationAccountSyncCursorOut(
        account_id=str(account.id),
        cursor_key=cursor_key,
        cursor_value=str(row.get("value")) if row.get("value") is not None else None,
        meta=_as_dict(row.get("meta")),
        updated_at=str(row.get("updated_at")) if row.get("updated_at") is not None else None,
    )


@router.patch("/accounts/{account_id}/sync-cursor", response_model=CommunicationAccountSyncCursorOut)
async def patch_channel_account_sync_cursor(
    account_id: str,
    body: CommunicationAccountSyncCursorPatch,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationAccountSyncCursorOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    account = await db.get(CommunicationChannelAccount, account_id)
    if account is None or str(account.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Channel account not found")
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=_feature_for_channel(account.channel))  # type: ignore[arg-type]

    settings = _as_dict(account.settings_json)
    cursors = _as_dict(settings.get("sync_cursors"))
    now_iso = _now_utc().isoformat()
    cursors[body.cursor_key] = {
        "value": body.cursor_value,
        "meta": _as_dict(body.meta),
        "updated_at": now_iso,
    }
    settings["sync_cursors"] = cursors
    account.settings_json = settings
    await db.commit()
    await db.refresh(account)
    return CommunicationAccountSyncCursorOut(
        account_id=str(account.id),
        cursor_key=body.cursor_key,
        cursor_value=body.cursor_value,
        meta=_as_dict(body.meta),
        updated_at=now_iso,
    )
