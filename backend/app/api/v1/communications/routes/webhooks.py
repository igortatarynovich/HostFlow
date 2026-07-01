"""Public webhook endpoints for inbound provider deliveries.

Endpoints:

* POST /communications/public/telegram/{webhook_secret}
* GET  /communications/public/whatsapp/{webhook_secret}      — Meta verification challenge
* POST /communications/public/whatsapp/{webhook_secret}
* GET  /communications/public/messenger/{webhook_secret}     — Meta verification challenge
* POST /communications/public/messenger/{webhook_secret}
* GET  /communications/public/instagram/{webhook_secret}     — Meta verification challenge
* POST /communications/public/instagram/{webhook_secret}
* POST /communications/public/viber/{webhook_secret}

Each handler:
1. Resolves the channel account by webhook_secret (no auth header required).
2. Normalizes the provider payload via the matching service module.
3. Builds a ``GenericInboundIngestRequest`` and forwards it to
   ``ingest_generic_channel`` so the same dedup + thread-resolution +
   allocator pipeline applies as for authenticated ingest.

Telegram webhook additionally pre-routes the update through
``_process_public_telegram_candidate_command`` so that ``/start``,
``/intake``, ``/scan`` and free-text intake answers from candidates take
effect before the message is persisted.

Extracted from ``backend/app/api/v1/communications/__init__.py`` as part
of the Phase 1 god-module split (step 7/N).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.deps import get_db
from backend.app.services.communications_meta import normalize_meta_webhook
from backend.app.services.communications_telegram import normalize_telegram_update
from backend.app.services.communications_viber import normalize_viber_webhook
from backend.app.services.communications_whatsapp import normalize_whatsapp_webhook

from .._helpers.channels import _whatsapp_config_from_account_settings
from .._helpers.ingest import (
    _find_channel_account_by_webhook_secret,
    _find_telegram_account_by_webhook_secret,
    _find_whatsapp_account_by_webhook_secret,
)
from .._helpers.telegram_intake import _process_public_telegram_candidate_command
from .._helpers.utils import _as_dict
from ..schemas import GenericInboundIngestRequest, GenericInboundIngestResponse
from .ingest import ingest_generic_channel

router = APIRouter(tags=["communications"])


def _public_user_ctx(tenant_id: str) -> SimpleNamespace:
    """Synthesize a UserCtx-like object for public webhook ingestion."""
    return SimpleNamespace(
        sub=None,
        role="superadmin",
        tenant_id=tenant_id,
        email="",
        raw={},
    )


@router.post("/public/telegram/{webhook_secret}", response_model=GenericInboundIngestResponse, status_code=status.HTTP_201_CREATED)
async def telegram_webhook_public(
    webhook_secret: str,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> GenericInboundIngestResponse:
    account = await _find_telegram_account_by_webhook_secret(db, webhook_secret=webhook_secret)
    if account is None:
        raise HTTPException(status_code=404, detail="Telegram webhook not found")
    normalized = normalize_telegram_update(payload)
    if not normalized:
        raise HTTPException(status_code=422, detail="Unsupported Telegram update payload")

    tenant_id = str(account.tenant_id)
    try:
        tenant_uuid = UUID(tenant_id)
    except Exception:
        raise HTTPException(status_code=500, detail="Invalid tenant binding for telegram account")

    handled_command, linked_candidate_id = await _process_public_telegram_candidate_command(
        db,
        account=account,
        tenant_id=tenant_id,
        normalized=normalized,
    )

    req = GenericInboundIngestRequest(
        channel_account_id=str(account.id),
        provider="telegram_bot",
        provider_thread_ref=str(normalized.get("provider_thread_ref") or ""),
        provider_chat_ref=str(normalized.get("provider_chat_ref") or ""),
        external_message_ref=str(normalized.get("external_message_ref") or ""),
        sender_address=str(normalized.get("sender_address") or "") or None,
        sender_label=str(normalized.get("sender_label") or "") or None,
        recipient_address=str(normalized.get("recipient_address") or "") or None,
        recipient_label=str(normalized.get("recipient_label") or "") or None,
        text=(normalized.get("text") if isinstance(normalized.get("text"), str) else None),
        html=None,
        attachments=[x for x in (normalized.get("attachments") or []) if isinstance(x, dict)],
        payload=_as_dict(normalized.get("payload")),
        headers=_as_dict(normalized.get("headers")),
        linked_candidate_id=linked_candidate_id,
        auto_assign=True,
    )
    if handled_command:
        req.payload = {
            **_as_dict(req.payload),
            "telegram_command": True,
        }
    return await ingest_generic_channel(
        "telegram",
        req,
        db_tenant=(db, tenant_uuid),
        current_user=_public_user_ctx(tenant_id),
    )


@router.get("/public/whatsapp/{webhook_secret}", response_model=None)
async def whatsapp_webhook_verify(
    webhook_secret: str,
    mode: str | None = Query(None, alias="hub.mode"),
    challenge: str | None = Query(None, alias="hub.challenge"),
    verify_token: str | None = Query(None, alias="hub.verify_token"),
    db: AsyncSession = Depends(get_db),
) -> PlainTextResponse:
    account = await _find_whatsapp_account_by_webhook_secret(db, webhook_secret=webhook_secret)
    if account is None:
        raise HTTPException(status_code=404, detail="WhatsApp webhook not found")
    settings_json = _as_dict(account.settings_json)
    wa_json = _as_dict(settings_json.get("whatsapp"))
    expected = str(wa_json.get("webhook_verify_token") or "").strip()
    if str(mode or "").strip() == "subscribe" and expected and str(verify_token or "").strip() == expected:
        return PlainTextResponse(content=(challenge or ""))
    raise HTTPException(status_code=403, detail="Invalid verification token")


@router.post("/public/whatsapp/{webhook_secret}", response_model=GenericInboundIngestResponse, status_code=status.HTTP_201_CREATED)
async def whatsapp_webhook_public(
    webhook_secret: str,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> GenericInboundIngestResponse:
    account = await _find_whatsapp_account_by_webhook_secret(db, webhook_secret=webhook_secret)
    if account is None:
        raise HTTPException(status_code=404, detail="WhatsApp webhook not found")

    tenant_id = str(account.tenant_id)
    try:
        tenant_uuid = UUID(tenant_id)
    except Exception:
        raise HTTPException(status_code=500, detail="Invalid tenant binding for whatsapp account")

    normalized_items = normalize_whatsapp_webhook(payload)
    if not normalized_items:
        raise HTTPException(status_code=422, detail="Unsupported WhatsApp webhook payload")

    last_resp: GenericInboundIngestResponse | None = None
    for normalized in normalized_items:
        provider_recipient = str(normalized.get("recipient_address") or "").strip()
        cfg = _whatsapp_config_from_account_settings(account)
        if cfg is not None and provider_recipient and provider_recipient != cfg.phone_number_id:
            continue
        req = GenericInboundIngestRequest(
            channel_account_id=str(account.id),
            provider="whatsapp_cloud",
            provider_thread_ref=str(normalized.get("provider_thread_ref") or ""),
            provider_chat_ref=str(normalized.get("provider_chat_ref") or ""),
            external_message_ref=str(normalized.get("external_message_ref") or ""),
            sender_address=str(normalized.get("sender_address") or "") or None,
            sender_label=str(normalized.get("sender_label") or "") or None,
            recipient_address=provider_recipient or None,
            recipient_label=str(normalized.get("recipient_label") or "") or None,
            text=(normalized.get("text") if isinstance(normalized.get("text"), str) else None),
            html=None,
            attachments=[x for x in (normalized.get("attachments") or []) if isinstance(x, dict)],
            payload=_as_dict(normalized.get("payload")),
            headers=_as_dict(normalized.get("headers")),
            auto_assign=True,
        )
        last_resp = await ingest_generic_channel(
            "whatsapp",
            req,
            db_tenant=(db, tenant_uuid),
            current_user=_public_user_ctx(tenant_id),
        )
    if last_resp is None:
        raise HTTPException(status_code=422, detail="No WhatsApp messages to ingest")
    return last_resp


@router.get("/public/messenger/{webhook_secret}", response_model=None)
async def messenger_webhook_verify(
    webhook_secret: str,
    mode: str | None = Query(None, alias="hub.mode"),
    challenge: str | None = Query(None, alias="hub.challenge"),
    verify_token: str | None = Query(None, alias="hub.verify_token"),
    db: AsyncSession = Depends(get_db),
) -> PlainTextResponse:
    account = await _find_channel_account_by_webhook_secret(
        db,
        channel="messenger",
        config_key="messenger",
        webhook_secret=webhook_secret,
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Messenger webhook not found")
    msg_cfg = _as_dict(_as_dict(account.settings_json).get("messenger"))
    expected = str(msg_cfg.get("webhook_verify_token") or "").strip()
    if str(mode or "").strip() == "subscribe" and expected and str(verify_token or "").strip() == expected:
        return PlainTextResponse(content=(challenge or ""))
    raise HTTPException(status_code=403, detail="Invalid verification token")


@router.post("/public/messenger/{webhook_secret}", response_model=GenericInboundIngestResponse, status_code=status.HTTP_201_CREATED)
async def messenger_webhook_public(
    webhook_secret: str,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> GenericInboundIngestResponse:
    account = await _find_channel_account_by_webhook_secret(
        db,
        channel="messenger",
        config_key="messenger",
        webhook_secret=webhook_secret,
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Messenger webhook not found")
    tenant_id = str(account.tenant_id)
    try:
        tenant_uuid = UUID(tenant_id)
    except Exception:
        raise HTTPException(status_code=500, detail="Invalid tenant binding for messenger account")

    normalized_items = normalize_meta_webhook(payload, channel="messenger")
    if not normalized_items:
        raise HTTPException(status_code=422, detail="Unsupported Messenger webhook payload")

    last_resp: GenericInboundIngestResponse | None = None
    for normalized in normalized_items:
        req = GenericInboundIngestRequest(
            channel_account_id=str(account.id),
            provider="facebook_messenger",
            provider_thread_ref=str(normalized.get("provider_thread_ref") or ""),
            provider_chat_ref=str(normalized.get("provider_chat_ref") or ""),
            external_message_ref=str(normalized.get("external_message_ref") or ""),
            sender_address=str(normalized.get("sender_address") or "") or None,
            sender_label=str(normalized.get("sender_label") or "") or None,
            recipient_address=str(normalized.get("recipient_address") or "") or None,
            recipient_label=str(normalized.get("recipient_label") or "") or None,
            text=(normalized.get("text") if isinstance(normalized.get("text"), str) else None),
            html=None,
            attachments=[x for x in (normalized.get("attachments") or []) if isinstance(x, dict)],
            payload=_as_dict(normalized.get("payload")),
            headers=_as_dict(normalized.get("headers")),
            auto_assign=True,
        )
        last_resp = await ingest_generic_channel(
            "messenger",
            req,
            db_tenant=(db, tenant_uuid),
            current_user=_public_user_ctx(tenant_id),
        )
    if last_resp is None:
        raise HTTPException(status_code=422, detail="No Messenger messages to ingest")
    return last_resp


@router.get("/public/instagram/{webhook_secret}", response_model=None)
async def instagram_webhook_verify(
    webhook_secret: str,
    mode: str | None = Query(None, alias="hub.mode"),
    challenge: str | None = Query(None, alias="hub.challenge"),
    verify_token: str | None = Query(None, alias="hub.verify_token"),
    db: AsyncSession = Depends(get_db),
) -> PlainTextResponse:
    account = await _find_channel_account_by_webhook_secret(
        db,
        channel="instagram",
        config_key="instagram",
        webhook_secret=webhook_secret,
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Instagram webhook not found")
    ig_cfg = _as_dict(_as_dict(account.settings_json).get("instagram"))
    expected = str(ig_cfg.get("webhook_verify_token") or "").strip()
    if str(mode or "").strip() == "subscribe" and expected and str(verify_token or "").strip() == expected:
        return PlainTextResponse(content=(challenge or ""))
    raise HTTPException(status_code=403, detail="Invalid verification token")


@router.post("/public/instagram/{webhook_secret}", response_model=GenericInboundIngestResponse, status_code=status.HTTP_201_CREATED)
async def instagram_webhook_public(
    webhook_secret: str,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> GenericInboundIngestResponse:
    account = await _find_channel_account_by_webhook_secret(
        db,
        channel="instagram",
        config_key="instagram",
        webhook_secret=webhook_secret,
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Instagram webhook not found")
    tenant_id = str(account.tenant_id)
    try:
        tenant_uuid = UUID(tenant_id)
    except Exception:
        raise HTTPException(status_code=500, detail="Invalid tenant binding for instagram account")

    normalized_items = normalize_meta_webhook(payload, channel="instagram")
    if not normalized_items:
        raise HTTPException(status_code=422, detail="Unsupported Instagram webhook payload")

    last_resp: GenericInboundIngestResponse | None = None
    for normalized in normalized_items:
        req = GenericInboundIngestRequest(
            channel_account_id=str(account.id),
            provider="instagram_graph",
            provider_thread_ref=str(normalized.get("provider_thread_ref") or ""),
            provider_chat_ref=str(normalized.get("provider_chat_ref") or ""),
            external_message_ref=str(normalized.get("external_message_ref") or ""),
            sender_address=str(normalized.get("sender_address") or "") or None,
            sender_label=str(normalized.get("sender_label") or "") or None,
            recipient_address=str(normalized.get("recipient_address") or "") or None,
            recipient_label=str(normalized.get("recipient_label") or "") or None,
            text=(normalized.get("text") if isinstance(normalized.get("text"), str) else None),
            html=None,
            attachments=[x for x in (normalized.get("attachments") or []) if isinstance(x, dict)],
            payload=_as_dict(normalized.get("payload")),
            headers=_as_dict(normalized.get("headers")),
            auto_assign=True,
        )
        last_resp = await ingest_generic_channel(
            "instagram",
            req,
            db_tenant=(db, tenant_uuid),
            current_user=_public_user_ctx(tenant_id),
        )
    if last_resp is None:
        raise HTTPException(status_code=422, detail="No Instagram messages to ingest")
    return last_resp


@router.post("/public/viber/{webhook_secret}", response_model=GenericInboundIngestResponse, status_code=status.HTTP_201_CREATED)
async def viber_webhook_public(
    webhook_secret: str,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> GenericInboundIngestResponse:
    account = await _find_channel_account_by_webhook_secret(
        db,
        channel="viber",
        config_key="viber",
        webhook_secret=webhook_secret,
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Viber webhook not found")
    tenant_id = str(account.tenant_id)
    try:
        tenant_uuid = UUID(tenant_id)
    except Exception:
        raise HTTPException(status_code=500, detail="Invalid tenant binding for viber account")

    normalized = normalize_viber_webhook(payload)
    if not normalized:
        raise HTTPException(status_code=422, detail="Unsupported Viber webhook payload")

    req = GenericInboundIngestRequest(
        channel_account_id=str(account.id),
        provider="viber_bot",
        provider_thread_ref=str(normalized.get("provider_thread_ref") or ""),
        provider_chat_ref=str(normalized.get("provider_chat_ref") or ""),
        external_message_ref=str(normalized.get("external_message_ref") or ""),
        sender_address=str(normalized.get("sender_address") or "") or None,
        sender_label=str(normalized.get("sender_label") or "") or None,
        recipient_address=str(normalized.get("recipient_address") or "") or None,
        recipient_label=str(normalized.get("recipient_label") or "") or None,
        text=(normalized.get("text") if isinstance(normalized.get("text"), str) else None),
        html=None,
        attachments=[x for x in (normalized.get("attachments") or []) if isinstance(x, dict)],
        payload=_as_dict(normalized.get("payload")),
        headers=_as_dict(normalized.get("headers")),
        auto_assign=True,
    )
    return await ingest_generic_channel(
        "viber",
        req,
        db_tenant=(db, tenant_uuid),
        current_user=_public_user_ctx(tenant_id),
    )
