"""Channel-account CRUD + lifecycle operations for the communications API.

Endpoints:

* GET    /communications/accounts                              — list channel accounts
* POST   /communications/accounts                              — create new channel account
* PATCH  /communications/accounts/{account_id}                 — update label/settings
* DELETE /communications/accounts/{account_id}                 — soft-detach + remove
* POST   /communications/accounts/{account_id}/test-connection — provider-specific connectivity probe
* POST   /communications/accounts/{account_id}/telegram/webhook/set    — register Telegram webhook
* POST   /communications/accounts/{account_id}/telegram/webhook/delete — unregister Telegram webhook
* POST   /communications/accounts/{account_id}/sync-now        — manual sync trigger

Channel-creation auto-issues per-channel ``webhook_secret`` (and
``webhook_verify_token`` for Meta channels) so the public webhook URL is
ready to be configured in the provider console immediately after create.

OAuth-related endpoints (``/accounts/{id}/oauth/*`` and
``/accounts/{id}/sync-cursor``) live in ``.routes.oauth``.

Extracted from ``backend/app/api/v1/communications/__init__.py`` as part
of the Phase 1 god-module split (step 7/N).
"""

from __future__ import annotations

from typing import Tuple
from uuid import UUID

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.core.crypto import generate_secret
from backend.app.core.settings import settings
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.communication import (
    CommunicationChannelAccount,
    CommunicationThread,
)
from backend.app.services.communications_access import assert_comm_feature_access
from backend.app.services.communications_email_imap import test_imap_connection
from backend.app.services.communications_meta import meta_graph_get_object
from backend.app.services.communications_telegram import (
    telegram_delete_webhook,
    telegram_get_me,
    telegram_get_webhook_info,
    telegram_set_webhook,
)
from backend.app.services.communications_viber import viber_get_account_info
from backend.app.services.communications_whatsapp import whatsapp_get_phone_number_info
from backend.app.services.plan_feature_gates import (
    ensure_communication_channel_account_create_allowed,
)

from .._helpers.access import (
    _feature_for_channel,
    _get_tenant_or_404,
    _require_comm_feature,
)
from .._helpers.account_settings import (
    _account_out,
    _derive_account_status,
    _normalize_account_settings_for_store,
)
from .._helpers.channels import (
    _imap_config_from_account_settings,
    _instagram_graph_config_from_account_settings,
    _messenger_graph_config_from_account_settings,
    _telegram_config_from_account_settings,
    _viber_config_from_account_settings,
    _whatsapp_config_from_account_settings,
)
from .._helpers.oauth import _oauth_access_token, _oauth_refresh_token
from .._helpers.utils import _as_dict, _deep_merge_dict, _now_utc
from ..schemas import (
    CommunicationAccountActionResponse,
    CommunicationChannelAccountCreate,
    CommunicationChannelAccountListResponse,
    CommunicationChannelAccountOut,
    CommunicationChannelAccountPatch,
)

router = APIRouter(tags=["communications"])


@router.get("/accounts", response_model=CommunicationChannelAccountListResponse)
async def list_channel_accounts(
    channel: str | None = Query(None),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationChannelAccountListResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    if channel:
        await _require_comm_feature(db, tenant_id=tenant_id, current_user=current_user, feature=_feature_for_channel(channel))
    else:
        await _require_comm_feature(db, tenant_id=tenant_id, current_user=current_user, feature="communicationsAdmin")
    stmt = sa.select(CommunicationChannelAccount).where(CommunicationChannelAccount.tenant_id == tenant_id)
    if channel:
        stmt = stmt.where(CommunicationChannelAccount.channel == channel)
    stmt = stmt.order_by(sa.asc(CommunicationChannelAccount.channel), sa.asc(CommunicationChannelAccount.account_label))
    rows = (await db.execute(stmt)).scalars().all()
    return CommunicationChannelAccountListResponse(
        items=[_account_out(a) for a in rows]
    )


@router.post("/accounts", response_model=CommunicationChannelAccountOut, status_code=status.HTTP_201_CREATED)
async def create_channel_account(
    body: CommunicationChannelAccountCreate,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationChannelAccountOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_comm_feature(db, tenant_id=tenant_id, current_user=current_user, feature=_feature_for_channel(body.channel))
    await ensure_communication_channel_account_create_allowed(db, tenant_id)
    settings_in = _as_dict(body.settings_json)
    oauth_secret_plain = str(body.oauth_client_secret or "").strip()
    if oauth_secret_plain:
        oauth_blk = _as_dict(settings_in.get("oauth"))
        oauth_blk["client_secret"] = oauth_secret_plain
        settings_in["oauth"] = oauth_blk
    normalized_settings = _normalize_account_settings_for_store(settings_in)
    if str(body.channel).lower() == "telegram":
        settings_blk = _as_dict(normalized_settings)
        tg = _as_dict(settings_blk.get("telegram"))
        if not str(tg.get("webhook_secret") or "").strip():
            tg["webhook_secret"] = generate_secret(48)
        settings_blk["telegram"] = tg
        normalized_settings = settings_blk
    if str(body.channel).lower() == "whatsapp":
        settings_blk = _as_dict(normalized_settings)
        wa = _as_dict(settings_blk.get("whatsapp"))
        if not str(wa.get("webhook_secret") or "").strip():
            wa["webhook_secret"] = generate_secret(48)
        if not str(wa.get("webhook_verify_token") or "").strip():
            wa["webhook_verify_token"] = generate_secret(24)
        settings_blk["whatsapp"] = wa
        normalized_settings = settings_blk
    if str(body.channel).lower() == "messenger":
        settings_blk = _as_dict(normalized_settings)
        msg = _as_dict(settings_blk.get("messenger"))
        if not str(msg.get("webhook_secret") or "").strip():
            msg["webhook_secret"] = generate_secret(48)
        if not str(msg.get("webhook_verify_token") or "").strip():
            msg["webhook_verify_token"] = generate_secret(24)
        settings_blk["messenger"] = msg
        normalized_settings = settings_blk
    if str(body.channel).lower() == "instagram":
        settings_blk = _as_dict(normalized_settings)
        ig = _as_dict(settings_blk.get("instagram"))
        if not str(ig.get("webhook_secret") or "").strip():
            ig["webhook_secret"] = generate_secret(48)
        if not str(ig.get("webhook_verify_token") or "").strip():
            ig["webhook_verify_token"] = generate_secret(24)
        settings_blk["instagram"] = ig
        normalized_settings = settings_blk
    if str(body.channel).lower() == "viber":
        settings_blk = _as_dict(normalized_settings)
        viber = _as_dict(settings_blk.get("viber"))
        if not str(viber.get("webhook_secret") or "").strip():
            viber["webhook_secret"] = generate_secret(48)
        settings_blk["viber"] = viber
        normalized_settings = settings_blk

    account = CommunicationChannelAccount(
        tenant_id=tenant_id,
        channel=body.channel,
        account_label=body.account_label,
        external_account_ref=body.external_account_ref,
        inbox_address=body.inbox_address,
        is_active=body.is_active,
        settings_json=normalized_settings,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return _account_out(account)


@router.patch("/accounts/{account_id}", response_model=CommunicationChannelAccountOut)
async def patch_channel_account(
    account_id: str,
    body: CommunicationChannelAccountPatch,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationChannelAccountOut:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    account = await db.get(CommunicationChannelAccount, account_id)
    if account is None or str(account.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Channel account not found")
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=_feature_for_channel(account.channel))  # type: ignore[arg-type]

    patch = body.model_dump(exclude_unset=True)
    oauth_plain_secret = str(patch.pop("oauth_client_secret", None) or "").strip()
    if "account_label" in patch and patch["account_label"] is not None:
        account.account_label = str(patch["account_label"]).strip()
    if "external_account_ref" in patch:
        account.external_account_ref = patch["external_account_ref"]
    if "inbox_address" in patch:
        account.inbox_address = patch["inbox_address"]
    if "is_active" in patch and patch["is_active"] is not None:
        account.is_active = bool(patch["is_active"])
    settings_changed = "settings_json" in patch and patch["settings_json"] is not None
    if settings_changed or oauth_plain_secret:
        merged = _deep_merge_dict(
            _as_dict(account.settings_json),
            _as_dict(patch["settings_json"]) if settings_changed else {},
        )
        if oauth_plain_secret:
            mo = _as_dict(merged.get("oauth"))
            mo["client_secret"] = oauth_plain_secret
            merged["oauth"] = mo
        account.settings_json = _normalize_account_settings_for_store(merged)

    await db.commit()
    await db.refresh(account)
    return _account_out(account)


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None)
async def delete_channel_account(
    account_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> None:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    account = await db.get(CommunicationChannelAccount, account_id)
    if account is None or str(account.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Channel account not found")
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=_feature_for_channel(account.channel))  # type: ignore[arg-type]

    await db.execute(
        sa.update(CommunicationThread)
        .where(
            CommunicationThread.tenant_id == tenant_id,
            CommunicationThread.channel_account_id == account_id,
        )
        .values(channel_account_id=None)
    )
    await db.delete(account)
    await db.commit()


@router.post("/accounts/{account_id}/test-connection", response_model=CommunicationAccountActionResponse)
async def test_channel_account_connection(
    account_id: str,
    request: Request,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationAccountActionResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    actor_id = str(current_user.sub) if getattr(current_user, "sub", None) else None
    account = await db.get(CommunicationChannelAccount, account_id)
    if account is None or str(account.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Channel account not found")
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=_feature_for_channel(account.channel))  # type: ignore[arg-type]
    now = _now_utc()
    account_settings = _as_dict(account.settings_json)
    connection = _as_dict(account_settings.get("connection"))
    provider = str(account_settings.get("provider") or "").strip().lower()
    if account.is_active and provider == "imap":
        try:
            imap_cfg = _imap_config_from_account_settings(account)
            if imap_cfg is None:
                raise RuntimeError("IMAP settings are incomplete (host/user/password)")
            test_result = await test_imap_connection(imap_cfg)
            connection.update(
                {
                    "status": "ok",
                    "last_test_at": now.isoformat(),
                    "last_test_by": actor_id,
                    "last_error": None,
                    "provider_result": test_result,
                }
            )
        except Exception as exc:
            connection.update(
                {
                    "status": "error",
                    "last_test_at": now.isoformat(),
                    "last_test_by": actor_id,
                    "last_error": str(exc),
                }
            )
    elif account.is_active and str(account.channel).lower() == "telegram":
        try:
            tg_cfg = _telegram_config_from_account_settings(account)
            if tg_cfg is None:
                raise RuntimeError("Telegram settings are incomplete (bot token is required)")
            me_result = await telegram_get_me(tg_cfg)
            bot_meta = _as_dict(me_result.get("result"))
            tg_settings = _as_dict(account_settings.get("telegram"))
            webhook_secret = str(tg_settings.get("webhook_secret") or "").strip()
            webhook_base = str(settings.frontend_url or "").strip().rstrip("/") or str(request.base_url).rstrip("/")
            if webhook_base.endswith("/app"):
                webhook_base = webhook_base[:-4]
            webhook_url = f"{webhook_base}/api/v1/communications/public/telegram/{webhook_secret}" if webhook_secret else None
            webhook_info = None
            if webhook_url:
                await telegram_set_webhook(tg_cfg, webhook_url=webhook_url)
                webhook_info_result = await telegram_get_webhook_info(tg_cfg)
                webhook_info = _as_dict(webhook_info_result.get("result"))
            connection.update(
                {
                    "status": "ok",
                    "last_test_at": now.isoformat(),
                    "last_test_by": actor_id,
                    "last_error": None,
                    "provider_result": {
                        "method": "getMe",
                        "id": bot_meta.get("id"),
                        "username": bot_meta.get("username"),
                        "first_name": bot_meta.get("first_name"),
                        "can_join_groups": bot_meta.get("can_join_groups"),
                        "can_read_all_group_messages": bot_meta.get("can_read_all_group_messages"),
                        "supports_inline_queries": bot_meta.get("supports_inline_queries"),
                        "webhook_url": webhook_url,
                        "webhook_info": {
                            "url": webhook_info.get("url") if isinstance(webhook_info, dict) else None,
                            "has_custom_certificate": webhook_info.get("has_custom_certificate") if isinstance(webhook_info, dict) else None,
                            "pending_update_count": webhook_info.get("pending_update_count") if isinstance(webhook_info, dict) else None,
                            "last_error_date": webhook_info.get("last_error_date") if isinstance(webhook_info, dict) else None,
                            "last_error_message": webhook_info.get("last_error_message") if isinstance(webhook_info, dict) else None,
                            "ip_address": webhook_info.get("ip_address") if isinstance(webhook_info, dict) else None,
                        } if webhook_info is not None else None,
                    },
                }
            )
        except Exception as exc:
            connection.update(
                {
                    "status": "error",
                    "last_test_at": now.isoformat(),
                    "last_test_by": actor_id,
                    "last_error": str(exc),
                }
            )
    elif account.is_active and str(account.channel).lower() == "whatsapp":
        try:
            wa_cfg = _whatsapp_config_from_account_settings(account)
            if wa_cfg is None:
                raise RuntimeError("WhatsApp settings are incomplete (phone_number_id/access_token)")
            info_result = await whatsapp_get_phone_number_info(wa_cfg)
            info = _as_dict(info_result)
            wa_settings = _as_dict(account_settings.get("whatsapp"))
            webhook_secret = str(wa_settings.get("webhook_secret") or "").strip()
            verify_token = str(wa_settings.get("webhook_verify_token") or "").strip()
            webhook_base = str(settings.frontend_url or "").strip().rstrip("/") or str(request.base_url).rstrip("/")
            if webhook_base.endswith("/app"):
                webhook_base = webhook_base[:-4]
            webhook_url = f"{webhook_base}/api/v1/communications/public/whatsapp/{webhook_secret}" if webhook_secret else None
            connection.update(
                {
                    "status": "ok",
                    "last_test_at": now.isoformat(),
                    "last_test_by": actor_id,
                    "last_error": None,
                    "provider_result": {
                        "method": "phone_number_info",
                        "id": info.get("id"),
                        "display_phone_number": info.get("display_phone_number"),
                        "verified_name": info.get("verified_name"),
                        "quality_rating": info.get("quality_rating"),
                        "webhook_url": webhook_url,
                        "webhook_verify_token": verify_token,
                    },
                }
            )
        except Exception as exc:
            connection.update(
                {
                    "status": "error",
                    "last_test_at": now.isoformat(),
                    "last_test_by": actor_id,
                    "last_error": str(exc),
                }
            )
    elif account.is_active and str(account.channel).lower() == "messenger":
        try:
            meta_cfg, page_id = _messenger_graph_config_from_account_settings(account)
            if meta_cfg is None or not page_id:
                raise RuntimeError("Messenger settings are incomplete (page_id/access_token)")
            info = await meta_graph_get_object(meta_cfg, object_id=page_id, fields="id,name")
            msg_settings = _as_dict(account_settings.get("messenger"))
            webhook_secret = str(msg_settings.get("webhook_secret") or "").strip()
            verify_token = str(msg_settings.get("webhook_verify_token") or "").strip()
            webhook_base = str(settings.frontend_url or "").strip().rstrip("/") or str(request.base_url).rstrip("/")
            if webhook_base.endswith("/app"):
                webhook_base = webhook_base[:-4]
            webhook_url = f"{webhook_base}/api/v1/communications/public/messenger/{webhook_secret}" if webhook_secret else None
            connection.update(
                {
                    "status": "ok",
                    "last_test_at": now.isoformat(),
                    "last_test_by": actor_id,
                    "last_error": None,
                    "provider_result": {
                        "method": "meta_page_info",
                        "id": info.get("id"),
                        "name": info.get("name"),
                        "webhook_url": webhook_url,
                        "webhook_verify_token": verify_token,
                    },
                }
            )
        except Exception as exc:
            connection.update(
                {
                    "status": "error",
                    "last_test_at": now.isoformat(),
                    "last_test_by": actor_id,
                    "last_error": str(exc),
                }
            )
    elif account.is_active and str(account.channel).lower() == "instagram":
        try:
            meta_cfg, ig_account_id = _instagram_graph_config_from_account_settings(account)
            if meta_cfg is None or not ig_account_id:
                raise RuntimeError("Instagram settings are incomplete (account_id/access_token)")
            info = await meta_graph_get_object(meta_cfg, object_id=ig_account_id, fields="id,username,name")
            ig_settings = _as_dict(account_settings.get("instagram"))
            webhook_secret = str(ig_settings.get("webhook_secret") or "").strip()
            verify_token = str(ig_settings.get("webhook_verify_token") or "").strip()
            webhook_base = str(settings.frontend_url or "").strip().rstrip("/") or str(request.base_url).rstrip("/")
            if webhook_base.endswith("/app"):
                webhook_base = webhook_base[:-4]
            webhook_url = f"{webhook_base}/api/v1/communications/public/instagram/{webhook_secret}" if webhook_secret else None
            connection.update(
                {
                    "status": "ok",
                    "last_test_at": now.isoformat(),
                    "last_test_by": actor_id,
                    "last_error": None,
                    "provider_result": {
                        "method": "instagram_account_info",
                        "id": info.get("id"),
                        "username": info.get("username"),
                        "name": info.get("name"),
                        "webhook_url": webhook_url,
                        "webhook_verify_token": verify_token,
                    },
                }
            )
        except Exception as exc:
            connection.update(
                {
                    "status": "error",
                    "last_test_at": now.isoformat(),
                    "last_test_by": actor_id,
                    "last_error": str(exc),
                }
            )
    elif account.is_active and str(account.channel).lower() == "viber":
        try:
            viber_cfg = _viber_config_from_account_settings(account)
            if viber_cfg is None:
                raise RuntimeError("Viber settings are incomplete (bot token)")
            info = await viber_get_account_info(viber_cfg)
            viber_settings = _as_dict(account_settings.get("viber"))
            webhook_secret = str(viber_settings.get("webhook_secret") or "").strip()
            webhook_base = str(settings.frontend_url or "").strip().rstrip("/") or str(request.base_url).rstrip("/")
            if webhook_base.endswith("/app"):
                webhook_base = webhook_base[:-4]
            webhook_url = f"{webhook_base}/api/v1/communications/public/viber/{webhook_secret}" if webhook_secret else None
            connection.update(
                {
                    "status": "ok",
                    "last_test_at": now.isoformat(),
                    "last_test_by": actor_id,
                    "last_error": None,
                    "provider_result": {
                        "method": "get_account_info",
                        "name": info.get("name"),
                        "id": info.get("id"),
                        "webhook_url": webhook_url,
                    },
                }
            )
        except Exception as exc:
            connection.update(
                {
                    "status": "error",
                    "last_test_at": now.isoformat(),
                    "last_test_by": actor_id,
                    "last_error": str(exc),
                }
            )
    elif account.is_active and provider in {"gmail", "microsoft_graph"}:
        oauth = _as_dict(account_settings.get("oauth"))
        has_access_token = bool(_oauth_access_token(oauth))
        has_refresh_token = bool(_oauth_refresh_token(oauth))
        has_client_id = bool(str(oauth.get("client_id") or "").strip())
        oauth_error = None
        if not has_access_token and not has_refresh_token:
            oauth_error = "OAuth is incomplete: access_token or refresh_token is required"
        elif has_refresh_token and not has_client_id:
            oauth_error = "OAuth is incomplete: client_id is required when refresh_token is used"
        connection.update(
            {
                "status": "ok" if oauth_error is None else "error",
                "last_test_at": now.isoformat(),
                "last_test_by": actor_id,
                "last_error": oauth_error,
                "provider_result": {
                    "provider": provider,
                    "has_access_token": has_access_token,
                    "has_refresh_token": has_refresh_token,
                    "has_client_id": has_client_id,
                },
            }
        )
    else:
        connection.update(
            {
                "status": "ok" if account.is_active else "disabled",
                "last_test_at": now.isoformat(),
                "last_test_by": actor_id,
                "last_error": None if account.is_active else "Account disabled",
            }
        )
    account_settings["connection"] = connection
    account.settings_json = account_settings
    await db.commit()
    await db.refresh(account)
    status_value, detail = _derive_account_status(account)
    return CommunicationAccountActionResponse(
        ok=status_value in {"connected", "disabled"},
        action="test_connection",
        status=status_value,
        detail=detail,
        account=_account_out(account),
    )


@router.post("/accounts/{account_id}/telegram/webhook/set", response_model=CommunicationAccountActionResponse)
async def set_telegram_channel_account_webhook(
    account_id: str,
    request: Request,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationAccountActionResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    actor_id = str(current_user.sub) if getattr(current_user, "sub", None) else None
    account = await db.get(CommunicationChannelAccount, account_id)
    if account is None or str(account.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Channel account not found")
    if str(account.channel).lower() != "telegram":
        raise HTTPException(status_code=422, detail="Webhook management is supported only for Telegram accounts")
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=_feature_for_channel(account.channel))  # type: ignore[arg-type]

    now = _now_utc()
    account_settings = _as_dict(account.settings_json)
    connection = _as_dict(account_settings.get("connection"))
    tg_settings = _as_dict(account_settings.get("telegram"))
    webhook_secret = str(tg_settings.get("webhook_secret") or "").strip()
    if not webhook_secret:
        webhook_secret = generate_secret(48)
        tg_settings["webhook_secret"] = webhook_secret
    webhook_base = str(settings.frontend_url or "").strip().rstrip("/") or str(request.base_url).rstrip("/")
    if webhook_base.endswith("/app"):
        webhook_base = webhook_base[:-4]
    webhook_url = f"{webhook_base}/api/v1/communications/public/telegram/{webhook_secret}"

    try:
        tg_cfg = _telegram_config_from_account_settings(account)
        if tg_cfg is None:
            raise RuntimeError("Telegram settings are incomplete (bot token is required)")
        await telegram_set_webhook(tg_cfg, webhook_url=webhook_url)
        webhook_info_result = await telegram_get_webhook_info(tg_cfg)
        webhook_info = _as_dict(webhook_info_result.get("result"))
        connection.update(
            {
                "status": "ok",
                "last_test_at": now.isoformat(),
                "last_test_by": actor_id,
                "last_error": None,
                "provider_result": {
                    "method": "setWebhook",
                    "webhook_url": webhook_url,
                    "webhook_info": webhook_info,
                },
            }
        )
    except Exception as exc:
        connection.update(
            {
                "status": "error",
                "last_test_at": now.isoformat(),
                "last_test_by": actor_id,
                "last_error": str(exc),
            }
        )
        account_settings["telegram"] = tg_settings
        account_settings["connection"] = connection
        account.settings_json = account_settings
        await db.commit()
        await db.refresh(account)
        raise HTTPException(status_code=400, detail=f"Failed to set Telegram webhook: {exc}")

    account_settings["telegram"] = tg_settings
    account_settings["connection"] = connection
    account.settings_json = account_settings
    await db.commit()
    await db.refresh(account)
    status_value, detail = _derive_account_status(account)
    return CommunicationAccountActionResponse(
        ok=status_value in {"connected", "disabled"},
        action="telegram_webhook_set",
        status=status_value,
        detail=detail,
        account=_account_out(account),
    )


@router.post("/accounts/{account_id}/telegram/webhook/delete", response_model=CommunicationAccountActionResponse)
async def delete_telegram_channel_account_webhook(
    account_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationAccountActionResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    actor_id = str(current_user.sub) if getattr(current_user, "sub", None) else None
    account = await db.get(CommunicationChannelAccount, account_id)
    if account is None or str(account.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Channel account not found")
    if str(account.channel).lower() != "telegram":
        raise HTTPException(status_code=422, detail="Webhook management is supported only for Telegram accounts")
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=_feature_for_channel(account.channel))  # type: ignore[arg-type]

    now = _now_utc()
    account_settings = _as_dict(account.settings_json)
    connection = _as_dict(account_settings.get("connection"))

    try:
        tg_cfg = _telegram_config_from_account_settings(account)
        if tg_cfg is None:
            raise RuntimeError("Telegram settings are incomplete (bot token is required)")
        await telegram_delete_webhook(tg_cfg)
        webhook_info_result = await telegram_get_webhook_info(tg_cfg)
        webhook_info = _as_dict(webhook_info_result.get("result"))
        connection.update(
            {
                "status": "ok",
                "last_test_at": now.isoformat(),
                "last_test_by": actor_id,
                "last_error": None,
                "provider_result": {
                    "method": "deleteWebhook",
                    "webhook_url": webhook_info.get("url"),
                    "webhook_info": webhook_info,
                },
            }
        )
    except Exception as exc:
        connection.update(
            {
                "status": "error",
                "last_test_at": now.isoformat(),
                "last_test_by": actor_id,
                "last_error": str(exc),
            }
        )
        account_settings["connection"] = connection
        account.settings_json = account_settings
        await db.commit()
        await db.refresh(account)
        raise HTTPException(status_code=400, detail=f"Failed to delete Telegram webhook: {exc}")

    account_settings["connection"] = connection
    account.settings_json = account_settings
    await db.commit()
    await db.refresh(account)
    status_value, detail = _derive_account_status(account)
    return CommunicationAccountActionResponse(
        ok=status_value in {"connected", "disabled"},
        action="telegram_webhook_delete",
        status=status_value,
        detail=detail,
        account=_account_out(account),
    )


@router.post("/accounts/{account_id}/sync-now", response_model=CommunicationAccountActionResponse)
async def sync_channel_account_now(
    account_id: str,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationAccountActionResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    actor_id = str(current_user.sub) if getattr(current_user, "sub", None) else None
    account = await db.get(CommunicationChannelAccount, account_id)
    if account is None or str(account.tenant_id) != tenant_id:
        raise HTTPException(status_code=404, detail="Channel account not found")
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature=_feature_for_channel(account.channel))  # type: ignore[arg-type]
    now = _now_utc()
    account_settings = _as_dict(account.settings_json)
    sync = _as_dict(account_settings.get("sync"))
    sync.update(
        {
            "status": "ok" if account.is_active else "error",
            "last_sync_at": now.isoformat(),
            "last_sync_by": actor_id,
            "last_error": None if account.is_active else "Account disabled",
            "mode": "manual_trigger",
        }
    )
    account_settings["sync"] = sync
    account.settings_json = account_settings
    await db.commit()
    await db.refresh(account)
    status_value, detail = _derive_account_status(account)
    return CommunicationAccountActionResponse(
        ok=bool(account.is_active),
        action="sync_now",
        status=status_value,
        detail=detail,
        account=_account_out(account),
    )
