"""Inbound-message ingest endpoints for the communications API.

Endpoints:

* POST /communications/email/worker/poll          — pull from IMAP/Gmail/Graph/mock and ingest
* POST /communications/ingest/email               — single inbound email (auth-required UI/API)
* POST /communications/ingest/{channel}           — generic inbound for non-email channels
* POST /communications/telegram/webhook-simulate  — internal helper to mimic Telegram webhook

Public webhook endpoints (``/communications/public/{channel}/{secret}``)
live in ``.routes.webhooks`` and call into ``ingest_generic_channel``
defined here.

Extracted from ``backend/app/api/v1/communications/__init__.py`` as part
of the Phase 1 god-module split (step 7/N).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple
from uuid import UUID

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.communications.inbound_dto import NormalizedInboundMessage
from backend.app.communications.inbound_ingest import ingest_inbound_message
from backend.app.communications.inbound_normalize import (
    normalize_email_fields,
    normalize_generic_fields,
)
from backend.app.models.communication_inbound_unresolved import REASON_CORRUPT_PAYLOAD
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.communication import (
    CommunicationChannelAccount,
    CommunicationMessage,
)
from backend.app.services.communications_access import assert_comm_feature_access
from backend.app.services.communications_allocator import allocate_thread
from backend.app.services.communications_email_imap import poll_imap_messages
from backend.app.services.communications_email_oauth import (
    OAuthMailboxPollError,
    poll_oauth_mailbox_messages,
)
from backend.app.services.communications_oauth import OAuthProviderError
from backend.app.services.communications_telegram import normalize_telegram_update

from .._helpers.access import (
    _default_own_company_id_for_tenant,
    _get_tenant_or_404,
    _get_thread_or_404,
    _require_comm_feature,
)
from .._helpers.channels import _imap_config_from_account_settings
from .._helpers.dto import _message_out, _thread_out
from .._helpers.ingest import (
    _ingest_email_outbound_from_mailbox,
)
from .._helpers.oauth import (
    _ensure_oauth_access_for_mailbox,
    _oauth_refresh_token,
    _refresh_oauth_tokens_in_settings_json,
)
from .._helpers.utils import _as_dict, _clamp_db_str, _coerce_datetime, _now_utc
from ..schemas import (
    CommunicationEmailWorkerPollRequest,
    CommunicationEmailWorkerPollResponse,
    EmailIngestRequest,
    EmailIngestResponse,
    GenericInboundIngestRequest,
    GenericInboundIngestResponse,
    TelegramWebhookSimulateRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["communications"])


@router.post("/email/worker/poll", response_model=CommunicationEmailWorkerPollResponse)
async def run_email_poll_worker(
    body: CommunicationEmailWorkerPollRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> CommunicationEmailWorkerPollResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_comm_feature(db, tenant_id=tenant_id, current_user=current_user, feature="email")
    tenant = await _get_tenant_or_404(db, tenant_id)
    stmt = sa.select(CommunicationChannelAccount).where(
        CommunicationChannelAccount.tenant_id == tenant_id,
        CommunicationChannelAccount.channel == "email",
        CommunicationChannelAccount.is_active.is_(True),
    )
    if body.only_account_id:
        stmt = stmt.where(CommunicationChannelAccount.id == body.only_account_id)
    accounts = (await db.execute(stmt.order_by(sa.asc(CommunicationChannelAccount.account_label)))).scalars().all()

    results: List[Dict[str, Any]] = []
    supported_accounts = 0
    unsupported_accounts = 0
    ingested_messages = 0
    created_threads = 0
    skipped_messages = 0

    for account in accounts:
        # After commit/rollback on a prior account, all rows in this session may be expired;
        # lazy-load of JSON columns triggers sync IO → MissingGreenlet in async SQLAlchemy.
        await db.refresh(account)
        settings_json = _as_dict(account.settings_json)
        provider = str(settings_json.get("provider") or "manual").strip().lower()
        mock_queue = settings_json.get("mock_inbox")
        if provider not in {"manual", "manual-test", "imap_mock", "imap", "gmail", "microsoft_graph"}:
            unsupported_accounts += 1
            results.append(
                {
                    "account_id": str(account.id),
                    "account_label": account.account_label,
                    "provider": provider,
                    "status": "unsupported_provider",
                    "processed": 0,
                }
            )
            continue

        supported_accounts += 1
        queue_list = [x for x in (mock_queue if isinstance(mock_queue, list) else []) if isinstance(x, dict)]
        fetched_items: List[Dict[str, Any]]
        if provider == "imap":
            try:
                imap_cfg = _imap_config_from_account_settings(account)
                if imap_cfg is None:
                    raise RuntimeError("IMAP settings are incomplete (host/user/password)")
                poll_result = await poll_imap_messages(imap_cfg, limit=body.limit_per_account)
                fetched_items = [x for x in (poll_result.get("items") if isinstance(poll_result, dict) else []) or [] if isinstance(x, dict)]
                settings_json = _as_dict(account.settings_json)
                sync = _as_dict(settings_json.get("sync"))
                sync.update(
                    {
                        "status": "ok",
                        "last_sync_at": _now_utc().isoformat(),
                        "mode": "imap_poll_worker",
                        "provider_result": {
                            "matched": poll_result.get("matched"),
                            "returned": poll_result.get("returned"),
                            "folder": poll_result.get("folder"),
                            "search_criteria": poll_result.get("search_criteria"),
                        },
                        "last_error": None,
                    }
                )
                settings_json["sync"] = sync
                account.settings_json = settings_json
                await db.commit()
            except Exception as exc:
                unsupported_accounts += 0
                skipped_messages += 1
                try:
                    await db.refresh(account)
                except Exception:
                    pass
                settings_json = _as_dict(account.settings_json)
                sync = _as_dict(settings_json.get("sync"))
                sync.update(
                    {
                        "status": "error",
                        "last_sync_at": _now_utc().isoformat(),
                        "mode": "imap_poll_worker",
                        "last_error": str(exc),
                    }
                )
                settings_json["sync"] = sync
                account.settings_json = settings_json
                await db.commit()
                logger.exception("communications imap poll failed account=%s", account.id)
                results.append(
                    {
                        "account_id": str(account.id),
                        "account_label": account.account_label,
                        "provider": provider,
                        "status": "error",
                        "error": str(exc),
                    }
                )
                continue
        elif provider in {"gmail", "microsoft_graph"}:
            try:
                access_token = await _ensure_oauth_access_for_mailbox(settings_json, provider=provider)

                if not access_token:
                    raise RuntimeError("OAuth access token is missing")
                cursor_map = _as_dict(settings_json.get("sync_cursors"))
                fetched_items = []
                oauth_folder_results: Dict[str, Dict[str, Any]] = {}
                for folder in ("inbox", "sent"):
                    cursor_key = f"{folder}_cursor"
                    cursor_row = _as_dict(cursor_map.get(cursor_key))
                    cursor = str(cursor_row.get("value") or "").strip() or None
                    unauthorized_retried = False
                    while True:
                        try:
                            oauth_poll_result = await poll_oauth_mailbox_messages(
                                provider=provider,
                                access_token=access_token,
                                limit=body.limit_per_account,
                                cursor=cursor,
                                folder=folder,
                            )
                            break
                        except OAuthMailboxPollError as poll_exc:
                            if getattr(poll_exc, "status_code", None) == 401 and not unauthorized_retried:
                                unauthorized_retried = True
                                if _oauth_refresh_token(_as_dict(settings_json.get("oauth"))):
                                    access_token = await _refresh_oauth_tokens_in_settings_json(
                                        settings_json, provider=provider
                                    )
                                    continue
                                raise OAuthMailboxPollError(
                                    "OAuth token expired (401) and no refresh token is stored — remove HostFlow in Google permissions and run OAuth setup again.",
                                    status_code=401,
                                ) from poll_exc
                            raise
                    oauth_folder_results[folder] = {
                        "returned": oauth_poll_result.returned,
                        "next_cursor": oauth_poll_result.next_cursor,
                        "raw": oauth_poll_result.raw,
                    }
                    for row in oauth_poll_result.items:
                        if not isinstance(row, dict):
                            continue
                        fetched_items.append({**row, "_mailbox_source": folder})
                    if oauth_poll_result.next_cursor is not None:
                        cursor_map[cursor_key] = {
                            "value": oauth_poll_result.next_cursor,
                            "meta": {"provider": provider, "source": f"oauth_poll_worker:{folder}"},
                            "updated_at": _now_utc().isoformat(),
                        }
                sync = _as_dict(settings_json.get("sync"))
                sync.update(
                    {
                        "status": "ok",
                        "last_sync_at": _now_utc().isoformat(),
                        "mode": f"{provider}_poll_worker",
                        "provider_result": oauth_folder_results,
                        "last_error": None,
                    }
                )
                settings_json["sync"] = sync
                settings_json["sync_cursors"] = cursor_map
                account.settings_json = settings_json
                await db.commit()
            except (OAuthMailboxPollError, OAuthProviderError, Exception) as exc:
                skipped_messages += 1
                try:
                    await db.rollback()
                except Exception:
                    pass
                try:
                    await db.refresh(account)
                except Exception:
                    pass
                settings_json = _as_dict(account.settings_json)
                oauth_json = _as_dict(settings_json.get("oauth"))
                oauth_json["last_error"] = str(exc)
                settings_json["oauth"] = oauth_json
                sync = _as_dict(settings_json.get("sync"))
                sync.update(
                    {
                        "status": "error",
                        "last_sync_at": _now_utc().isoformat(),
                        "mode": f"{provider}_poll_worker",
                        "last_error": str(exc),
                    }
                )
                settings_json["sync"] = sync
                account.settings_json = settings_json
                await db.commit()
                logger.exception("communications oauth email poll failed account=%s provider=%s", account.id, provider)
                results.append(
                    {
                        "account_id": str(account.id),
                        "account_label": account.account_label,
                        "provider": provider,
                        "status": "error",
                        "error": str(exc),
                    }
                )
                continue
        else:
            fetched_items = queue_list

        await db.refresh(account)
        account_id_str = str(account.id)
        account_inbox_snap = account.inbox_address
        account_label_snap = str(account.account_label or "")

        if not fetched_items:
            results.append(
                {
                    "account_id": account_id_str,
                    "account_label": account_label_snap,
                    "provider": provider,
                    "status": "empty",
                    "processed": 0,
                }
            )
            continue

        processed = 0
        consumed = 0
        source_items = fetched_items[: body.limit_per_account]
        for raw in source_items:
            consumed += 1
            await db.refresh(account)
            try:
                mailbox_source = str(raw.get("_mailbox_source") or "inbox").strip().lower()
                if mailbox_source == "sent":
                    created_thread, duplicate = await _ingest_email_outbound_from_mailbox(
                        db,
                        tenant_id=tenant_id,
                        channel_account_id=account_id_str,
                        provider=provider,
                        provider_thread_ref=_clamp_db_str(raw.get("provider_thread_ref"), 255),
                        external_message_ref=_clamp_db_str(raw.get("external_message_ref"), 255),
                        subject=_clamp_db_str(raw.get("subject"), 512),
                        from_address=_clamp_db_str(raw.get("from_address"), 255)
                        or _clamp_db_str(account_inbox_snap, 255),
                        to_address=_clamp_db_str(raw.get("to_address"), 255),
                        to_name=_clamp_db_str(raw.get("to_name"), 255),
                        text=(raw.get("text") if isinstance(raw.get("text"), str) else None),
                        html=(raw.get("html") if isinstance(raw.get("html"), str) else None),
                        headers=_as_dict(raw.get("headers")),
                        payload=_as_dict(raw.get("payload")),
                        sent_at=_coerce_datetime(raw.get("received_at")),
                        tenant=tenant,
                    )
                    processed += 1
                    ingested_messages += 1
                    if created_thread:
                        created_threads += 1
                    if duplicate:
                        skipped_messages += 1
                    await db.commit()
                else:
                    cc_list = (
                        [_clamp_db_str(x, 255) for x in raw.get("cc", []) if x is not None]
                        if isinstance(raw.get("cc"), list)
                        else []
                    )
                    bcc_list = (
                        [_clamp_db_str(x, 255) for x in raw.get("bcc", []) if x is not None]
                        if isinstance(raw.get("bcc"), list)
                        else []
                    )
                    to_ingest = _clamp_db_str(raw.get("to_address"), 255) or _clamp_db_str(account_inbox_snap, 255)
                    payload = EmailIngestRequest(
                        channel_account_id=account_id_str,
                        provider=_clamp_db_str(provider, 64) or provider,
                        provider_thread_ref=_clamp_db_str(raw.get("provider_thread_ref"), 255),
                        external_message_ref=_clamp_db_str(raw.get("external_message_ref"), 255),
                        subject=_clamp_db_str(raw.get("subject"), 512),
                        from_address=_clamp_db_str(raw.get("from_address"), 255),
                        from_name=_clamp_db_str(raw.get("from_name"), 255),
                        to_address=to_ingest,
                        to_name=_clamp_db_str(raw.get("to_name"), 255),
                        cc=[x for x in cc_list if x],
                        bcc=[x for x in bcc_list if x],
                        text=(raw.get("text") if isinstance(raw.get("text"), str) else None),
                        html=(raw.get("html") if isinstance(raw.get("html"), str) else None),
                        headers=_as_dict(raw.get("headers")),
                        payload=_as_dict(raw.get("payload")),
                        entity_type=_clamp_db_str(raw.get("entity_type"), 64),
                        entity_id=_clamp_db_str(raw.get("entity_id"), 120),
                        linked_candidate_id=_clamp_db_str(raw.get("linked_candidate_id"), 36),
                        linked_company_id=_clamp_db_str(raw.get("linked_company_id"), 36),
                        assignee_id=_clamp_db_str(raw.get("assignee_id"), 36),
                        auto_assign=bool(raw.get("auto_assign", True)),
                    )
                    resp = await ingest_email(payload, db_tenant=(db, tenant_uuid), current_user=current_user)
                    processed += 1
                    ingested_messages += 1
                    if resp.created_thread:
                        created_threads += 1
                    if resp.duplicate_message:
                        skipped_messages += 1
                    # ADR / art.14: DSN bounce/deferral reopens lead RODO gate.
                    try:
                        from backend.app.services.lead_rodo_delivery_feedback import (
                            maybe_apply_rodo_delivery_feedback_from_inbound,
                        )

                        body_txt = raw.get("text") if isinstance(raw.get("text"), str) else None
                        if not body_txt and isinstance(raw.get("html"), str):
                            body_txt = raw.get("html")
                        updated_leads = await maybe_apply_rodo_delivery_feedback_from_inbound(
                            db,
                            tenant_id=tenant_id,
                            subject=_clamp_db_str(raw.get("subject"), 512),
                            body_text=body_txt,
                            from_address=_clamp_db_str(raw.get("from_address"), 255),
                            external_message_ref=_clamp_db_str(raw.get("external_message_ref"), 255),
                            inbox_address=_clamp_db_str(account_inbox_snap, 255),
                            actor_id=str(getattr(current_user, "id", "") or "") or None,
                        )
                        if updated_leads:
                            await db.commit()
                    except Exception:
                        logger.exception(
                            "communications email poll RODO delivery feedback failed account=%s",
                            account_id_str,
                        )
            except Exception as exc:
                skipped_messages += 1
                try:
                    await db.rollback()
                except Exception:
                    pass
                logger.exception("communications email poll ingest failed account=%s", account_id_str)
                results.append(
                    {
                        "account_id": account_id_str,
                        "account_label": account_label_snap,
                        "provider": provider,
                        "status": "error",
                        "error": str(exc),
                    }
                )
                break

        remaining = queue_list[consumed:] if provider in {"manual", "manual-test", "imap_mock"} else []
        if provider in {"manual", "manual-test", "imap_mock"}:
          await db.refresh(account)
          settings_json = _as_dict(account.settings_json)
          settings_json["mock_inbox"] = remaining
          sync = _as_dict(settings_json.get("sync"))
          sync.update(
              {
                  "status": "ok",
                  "last_sync_at": _now_utc().isoformat(),
                  "last_polled_count": processed,
                  "remaining_mock_queue": len(remaining),
                  "mode": "mock_poll_worker",
                  "last_error": None,
              }
          )
          settings_json["sync"] = sync
          account.settings_json = settings_json
          await db.commit()

        results.append(
            {
                "account_id": account_id_str,
                "account_label": account_label_snap,
                "provider": provider,
                "status": "ok",
                "processed": processed,
                "remaining": len(remaining) if provider in {"manual", "manual-test", "imap_mock"} else None,
            }
        )

    return CommunicationEmailWorkerPollResponse(
        polled_accounts=len(accounts),
        supported_accounts=supported_accounts,
        ingested_messages=ingested_messages,
        created_threads=created_threads,
        skipped_messages=skipped_messages,
        unsupported_accounts=unsupported_accounts,
        items=results,
    )


@router.post("/ingest/email", response_model=EmailIngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_email(
    body: EmailIngestRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> EmailIngestResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    actor_id = str(current_user.sub) if getattr(current_user, "sub", None) else None
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature="email")
    default_own_id = await _default_own_company_id_for_tenant(db, tenant_id)

    if body.channel_account_id:
        account = await db.get(CommunicationChannelAccount, body.channel_account_id)
        if account is None or str(account.tenant_id) != tenant_id or account.channel != "email":
            raise HTTPException(status_code=404, detail="Email channel account not found")

    try:
        inbound = normalize_email_fields(
            tenant_id=tenant_id,
            channel_account_id=body.channel_account_id,
            provider=body.provider,
            provider_thread_ref=body.provider_thread_ref,
            external_message_ref=body.external_message_ref,
            subject=body.subject,
            from_address=body.from_address,
            from_name=body.from_name,
            to_address=body.to_address,
            to_name=body.to_name,
            cc=body.cc,
            bcc=body.bcc,
            text=body.text,
            html=body.html,
            received_at=body.received_at,
            headers=body.headers,
            payload=body.payload,
            entity_type=body.entity_type,
            entity_id=body.entity_id,
            linked_candidate_id=body.linked_candidate_id,
            linked_company_id=body.linked_company_id,
        )
    except Exception as exc:  # noqa: BLE001 — never drop corrupt payloads
        inbound = NormalizedInboundMessage(
            tenant_id=tenant_id,
            channel="email",
            provider=body.provider,
            channel_account_id=body.channel_account_id,
            external_message_ref=body.external_message_ref,
            subject=body.subject,
            sender_address=body.from_address,
            sender_label=body.from_name,
            recipient_address=body.to_address,
            recipient_label=body.to_name,
            body_text=body.text,
            body_html=body.html,
            received_at=body.received_at,
            headers=dict(body.headers or {}),
            payload={**(body.payload or {}), "normalize_error": str(exc) or type(exc).__name__},
            force_unresolved_reason_code=REASON_CORRUPT_PAYLOAD,
        )
    # Platform ingest only — no legacy thread heuristic bypass.
    result = await ingest_inbound_message(
        db,
        inbound=inbound,
        own_company_id=default_own_id,
        tenant=tenant,
    )
    thread = await _get_thread_or_404(db, tenant_id, result.thread_id)
    msg = await db.get(CommunicationMessage, result.message_id)
    if msg is None:
        raise HTTPException(status_code=500, detail="Inbound message persist failed")

    if body.assignee_id and not thread.assignee_id:
        thread.assignee_id = body.assignee_id
        thread.queue_assigned_by = "manual"
        thread.owner_id = actor_id or thread.owner_id
        await db.flush()

    auto_assigned = False
    auto_assign_reason: str | None = None
    if result.duplicate_message:
        auto_assign_reason = "duplicate_message"
    elif body.auto_assign and not thread.assignee_id:
        alloc = await allocate_thread(db, tenant=tenant, thread=thread, actor_user_id=actor_id)
        auto_assigned = bool(alloc.get("assigned"))
        auto_assign_reason = None if auto_assigned else str(alloc.get("reason") or "no_eligible_managers")

    if not result.duplicate_message:
        try:
            from backend.app.services import uos_auto_activities

            await uos_auto_activities.ensure_inbound_thread_reply_task(db, tenant_id, actor_id, thread)
        except Exception:
            pass

    await db.commit()
    await db.refresh(thread)
    await db.refresh(msg)
    return EmailIngestResponse(
        created_thread=result.created_thread,
        duplicate_message=result.duplicate_message,
        auto_assigned=auto_assigned,
        auto_assign_reason=auto_assign_reason,
        thread=_thread_out(thread),
        message=_message_out(msg),
    )


@router.post("/ingest/{channel}", response_model=GenericInboundIngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_generic_channel(
    channel: str,
    body: GenericInboundIngestRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> GenericInboundIngestResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    actor_id = str(current_user.sub) if getattr(current_user, "sub", None) else None
    tenant = await _get_tenant_or_404(db, tenant_id)
    assert_comm_feature_access(tenant=tenant, current_user=current_user, tenant_id=tenant_id, feature="messages")
    default_own_id = await _default_own_company_id_for_tenant(db, tenant_id)
    channel_norm = (channel or "").strip().lower()
    if channel_norm in {"", "email"}:
        raise HTTPException(status_code=400, detail="Use /communications/ingest/email for email channel")

    if body.channel_account_id:
        account = await db.get(CommunicationChannelAccount, body.channel_account_id)
        if account is None or str(account.tenant_id) != tenant_id or str(account.channel).lower() != channel_norm:
            raise HTTPException(status_code=404, detail="Channel account not found")

    try:
        inbound = normalize_generic_fields(
            tenant_id=tenant_id,
            channel=channel_norm,
            channel_account_id=body.channel_account_id,
            provider=body.provider,
            provider_thread_ref=body.provider_thread_ref,
            provider_chat_ref=body.provider_chat_ref,
            external_message_ref=body.external_message_ref,
            sender_address=body.sender_address,
            sender_label=body.sender_label,
            recipient_address=body.recipient_address,
            recipient_label=body.recipient_label,
            subject=body.subject,
            text=body.text,
            html=body.html,
            received_at=body.received_at,
            headers=body.headers,
            payload={
                **(body.payload or {}),
                "provider_chat_ref": body.provider_chat_ref,
            },
            attachments=body.attachments,
            entity_type=body.entity_type,
            entity_id=body.entity_id,
            linked_candidate_id=body.linked_candidate_id,
            linked_company_id=body.linked_company_id,
        )
    except Exception as exc:  # noqa: BLE001 — never drop corrupt payloads
        inbound = NormalizedInboundMessage(
            tenant_id=tenant_id,
            channel=channel_norm,
            provider=body.provider,
            channel_account_id=body.channel_account_id,
            provider_thread_ref=body.provider_thread_ref or body.provider_chat_ref,
            external_message_ref=body.external_message_ref,
            subject=body.subject,
            sender_address=body.sender_address,
            sender_label=body.sender_label,
            recipient_address=body.recipient_address,
            recipient_label=body.recipient_label,
            body_text=body.text,
            body_html=body.html,
            received_at=body.received_at,
            headers=dict(body.headers or {}),
            payload={
                **(body.payload or {}),
                "provider_chat_ref": body.provider_chat_ref,
                "normalize_error": str(exc) or type(exc).__name__,
            },
            attachments=[dict(x) for x in (body.attachments or []) if isinstance(x, dict)],
            force_unresolved_reason_code=REASON_CORRUPT_PAYLOAD,
        )
    # Platform ingest only — no legacy thread heuristic bypass.
    result = await ingest_inbound_message(
        db,
        inbound=inbound,
        own_company_id=default_own_id,
        tenant=tenant,
    )
    thread = await _get_thread_or_404(db, tenant_id, result.thread_id)
    msg = await db.get(CommunicationMessage, result.message_id)
    if msg is None:
        raise HTTPException(status_code=500, detail="Inbound message persist failed")

    if (
        channel_norm == "telegram"
        and bool(_as_dict(body.payload).get("telegram_command"))
        and msg.read_at is None
    ):
        msg.read_at = msg.delivered_at or _now_utc()
        await db.flush()

    if body.assignee_id and not thread.assignee_id:
        thread.assignee_id = body.assignee_id
        thread.queue_assigned_by = "manual"
        thread.owner_id = actor_id or thread.owner_id
        await db.flush()

    auto_assigned = False
    auto_assign_reason: str | None = None
    if result.duplicate_message:
        auto_assign_reason = "duplicate_message"
    elif body.auto_assign and not thread.assignee_id:
        alloc = await allocate_thread(db, tenant=tenant, thread=thread, actor_user_id=actor_id)
        auto_assigned = bool(alloc.get("assigned"))
        auto_assign_reason = None if auto_assigned else str(alloc.get("reason") or "no_eligible_managers")

    if not result.duplicate_message:
        try:
            from backend.app.services import uos_auto_activities

            await uos_auto_activities.ensure_inbound_thread_reply_task(db, tenant_id, actor_id, thread)
        except Exception:
            pass

    await db.commit()
    await db.refresh(thread)
    await db.refresh(msg)
    return GenericInboundIngestResponse(
        created_thread=result.created_thread,
        duplicate_message=result.duplicate_message,
        auto_assigned=auto_assigned,
        auto_assign_reason=auto_assign_reason,
        thread=_thread_out(thread),
        message=_message_out(msg),
    )


@router.post("/telegram/webhook-simulate", response_model=GenericInboundIngestResponse, status_code=status.HTTP_201_CREATED)
async def simulate_telegram_webhook(
    body: TelegramWebhookSimulateRequest,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    current_user: UserCtx = Depends(get_current_user),
) -> GenericInboundIngestResponse:
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    await _require_comm_feature(db, tenant_id=tenant_id, current_user=current_user, feature="messages")
    account = await db.get(CommunicationChannelAccount, body.channel_account_id)
    if account is None or str(account.tenant_id) != tenant_id or str(account.channel).lower() != "telegram":
        raise HTTPException(status_code=404, detail="Telegram channel account not found")
    normalized = normalize_telegram_update(body.update)
    if not normalized:
        raise HTTPException(status_code=422, detail="Unsupported Telegram update payload")
    req = GenericInboundIngestRequest(
        channel_account_id=body.channel_account_id,
        provider="telegram_bot",
        provider_thread_ref=str(normalized.get("provider_thread_ref") or ""),
        provider_chat_ref=str(normalized.get("provider_chat_ref") or ""),
        external_message_ref=str(normalized.get("external_message_ref") or ""),
        sender_address=str(normalized.get("sender_address") or "") or None,
        sender_label=str(normalized.get("sender_label") or "") or None,
        recipient_address=str(normalized.get("recipient_address") or "") or None,
        recipient_label=str(normalized.get("recipient_label") or "") or None,
        subject=None,
        text=(normalized.get("text") if isinstance(normalized.get("text"), str) else None),
        html=None,
        attachments=[x for x in (normalized.get("attachments") or []) if isinstance(x, dict)],
        payload=_as_dict(normalized.get("payload")),
        headers=_as_dict(normalized.get("headers")),
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        linked_candidate_id=body.linked_candidate_id,
        linked_company_id=body.linked_company_id,
        auto_assign=body.auto_assign,
    )
    return await ingest_generic_channel(
        "telegram",
        req,
        db_tenant=db_tenant,
        current_user=current_user,
    )
