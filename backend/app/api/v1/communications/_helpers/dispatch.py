"""Outbound dispatch helpers for the communications API.

Houses everything required to *send* a queued ``CommunicationMessage`` to
an external provider:

* address / body normalization (``_pick_thread_recipient_address``,
  ``_normalize_email_text``, ``_parse_iso_datetime``);
* retry bookkeeping (``_dispatch_attempt_count``,
  ``_dispatch_next_retry_at``, ``_schedule_dispatch_retry``);
* per-channel send adapters that mutate ``msg.delivery_status`` /
  ``msg.payload`` and return ``None`` on success or a short error code
  string on failure (``_dispatch_email_message_via_tenant_smtp``,
  ``_dispatch_telegram_message_via_bot_api``,
  ``_dispatch_whatsapp_message_via_cloud_api``,
  ``_dispatch_messenger_message_via_graph_api``,
  ``_dispatch_instagram_message_via_graph_api``,
  ``_dispatch_viber_message_via_bot_api``);
* attachment-path resolution (``_resolve_comm_local_attachment_path``).

Extracted from ``backend/app/api/v1/communications/__init__.py`` as part
of the Phase 1 god-module split (step 4/N). All public symbols keep
their underscore-prefixed names so the parent package can re-export them
unchanged for route handlers.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.communication import (
    CommunicationChannelAccount,
    CommunicationMessage,
    CommunicationThread,
)
from backend.app.modules.documents.storage import get_uploads_root
from backend.app.services.communications_email_oauth_send import (
    OAuthMailboxSendError,
    send_oauth_email_message,
)
from backend.app.services.communications_meta import send_meta_text_message
from backend.app.services.communications_oauth import OAuthProviderError
from backend.app.services.communications_telegram import (
    send_telegram_document,
    send_telegram_text,
)
from backend.app.services.communications_viber import send_viber_text_message
from backend.app.services.communications_whatsapp import send_whatsapp_text
from backend.app.services.tenant_email import send_email_for_tenant

from .channels import (
    _instagram_graph_config_from_account_settings,
    _messenger_graph_config_from_account_settings,
    _telegram_config_from_account_settings,
    _viber_config_from_account_settings,
    _whatsapp_config_from_account_settings,
)
from .oauth import (
    _ensure_oauth_access_for_mailbox,
    _oauth_refresh_token,
    _refresh_oauth_tokens_in_settings_json,
)
from .utils import _as_dict, _as_list, _now_utc

__all__ = [
    "_pick_thread_recipient_address",
    "_normalize_email_text",
    "_parse_iso_datetime",
    "_dispatch_attempt_count",
    "_dispatch_next_retry_at",
    "_schedule_dispatch_retry",
    "_resolve_comm_local_attachment_path",
    "_mock_dispatch_outbound_message",
    "_dispatch_email_message_via_tenant_smtp",
    "_dispatch_telegram_message_via_bot_api",
    "_dispatch_whatsapp_message_via_cloud_api",
    "_dispatch_messenger_message_via_graph_api",
    "_dispatch_instagram_message_via_graph_api",
    "_dispatch_viber_message_via_bot_api",
]


def _mock_dispatch_outbound_message(
    *,
    thread: CommunicationThread,
    msg: CommunicationMessage,
    actor_id: str | None,
    mark_delivered: bool,
    simulate_failure: bool,
    provider_message_ref: str | None,
    provider_payload: Dict[str, Any] | None,
) -> str | None:
    """Test/development fallback adapter used when no real channel adapter
    fits the thread (e.g. for ``mock`` channel or in unit tests). Mutates
    ``msg`` in place and returns ``None`` on success / a short error code
    string on failure (mirrors the real adapters' contract).
    """
    now = _now_utc()
    if msg.is_internal_note:
        return "internal_note"
    if msg.direction != "outbound":
        return "not_outbound"
    if simulate_failure:
        msg.delivery_status = "failed"
        msg.error_message = "Simulated dispatch failure"
        msg.payload = {
            **_as_dict(msg.payload),
            "dispatch": {
                "status": "failed",
                "attempted_at": now.isoformat(),
                "actor_user_id": actor_id,
                "thread_channel": thread.channel,
                **(_as_dict(provider_payload) if provider_payload else {}),
            },
        }
        return "simulated_failure"

    msg.delivery_status = "delivered" if mark_delivered else "sent"
    msg.sent_at = msg.sent_at or now
    if mark_delivered:
        msg.delivered_at = msg.delivered_at or now
    msg.error_message = None
    if provider_message_ref and not msg.external_message_ref:
        msg.external_message_ref = provider_message_ref
    if not msg.external_message_ref:
        msg.external_message_ref = f"{thread.channel}:{thread.id}:{msg.id}"
    msg.payload = {
        **_as_dict(msg.payload),
        "dispatch": {
            "status": msg.delivery_status,
            "attempted_at": now.isoformat(),
            "actor_user_id": actor_id,
            "thread_channel": thread.channel,
            "channel_account_id": thread.channel_account_id,
            **(_as_dict(provider_payload) if provider_payload else {}),
        },
    }
    return None


logger = logging.getLogger("backend.app.api.v1.communications")


def _pick_thread_recipient_address(thread: CommunicationThread) -> str | None:
    participants = _as_dict(thread.participants_json)
    recipients = participants.get("recipients")
    if isinstance(recipients, list):
        for item in recipients:
            value = str(item or "").strip()
            if value:
                return value
    senders = participants.get("senders")
    if isinstance(senders, list):
        for item in senders:
            value = str(item or "").strip()
            if value:
                return value
    return None


def _normalize_email_text(text: str | None, html: str | None) -> str:
    body = (text or "").strip()
    if body:
        return body
    if html:
        # MVP fallback: keep HTML as plain text payload to avoid losing message.
        return str(html)
    return ""


def _parse_iso_datetime(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _dispatch_attempt_count(msg: CommunicationMessage) -> int:
    dispatch = _as_dict(_as_dict(msg.payload).get("dispatch"))
    try:
        return max(0, int(dispatch.get("attempt_count") or 0))
    except Exception:
        return 0


def _dispatch_next_retry_at(msg: CommunicationMessage) -> datetime | None:
    dispatch = _as_dict(_as_dict(msg.payload).get("dispatch"))
    return _parse_iso_datetime(dispatch.get("next_retry_at"))


def _schedule_dispatch_retry(
    *,
    msg: CommunicationMessage,
    reason: str,
    actor_id: str | None,
    now: datetime,
    current_attempt: Optional[int] = None,
    max_attempts: int = 5,
) -> bool:
    current_attempt_value = (
        current_attempt if current_attempt is not None else _dispatch_attempt_count(msg)
    )
    next_attempt = current_attempt_value + 1
    dispatch = _as_dict(_as_dict(msg.payload).get("dispatch"))
    dispatch.update(
        {
            "status": "retry_scheduled",
            "attempted_at": now.isoformat(),
            "actor_user_id": actor_id,
            "attempt_count": next_attempt,
            "last_error_reason": reason,
        }
    )
    if next_attempt >= max_attempts:
        dispatch["status"] = "failed"
        msg.delivery_status = "failed"
        msg.error_message = reason
        msg.payload = {**_as_dict(msg.payload), "dispatch": dispatch}
        return False
    delay_seconds = min(3600, 60 * (2 ** max(0, next_attempt - 1)))
    next_retry_at = now + timedelta(seconds=delay_seconds)
    dispatch["next_retry_at"] = next_retry_at.isoformat()
    msg.delivery_status = "queued"
    msg.error_message = reason
    msg.payload = {**_as_dict(msg.payload), "dispatch": dispatch}
    return True


def _resolve_comm_local_attachment_path(
    *, tenant_id: str, storage_path: str
) -> Path | None:
    raw = str(storage_path or "").strip().replace("\\", "/")
    if not raw:
        return None
    parts = raw.split("/")
    if ".." in parts:
        return None
    prefix = f"{tenant_id}/communications/"
    if not raw.startswith(prefix):
        return None
    root = get_uploads_root().resolve()
    try:
        full = (root / raw).resolve()
        full.relative_to(root)
    except ValueError:
        return None
    if not full.is_file():
        return None
    return full


async def _dispatch_email_message_via_tenant_smtp(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
    msg: CommunicationMessage,
    actor_id: str | None,
) -> str | None:
    if msg.is_internal_note:
        return "internal_note"
    if msg.direction != "outbound":
        return "not_outbound"
    to_addr = (
        msg.recipient_address or _pick_thread_recipient_address(thread) or ""
    ).strip()
    if not to_addr:
        msg.delivery_status = "failed"
        msg.error_message = "Missing recipient address"
        return "missing_recipient"
    subject = (msg.subject or thread.subject or "").strip() or (
        f"HostFlow {str(thread.channel).upper()} message"
    )
    body = _normalize_email_text(msg.body_text, msg.body_html)
    if not body:
        msg.delivery_status = "failed"
        msg.error_message = "Empty email body"
        return "empty_body"

    # Preferred path: send via connected OAuth mailbox account when thread is
    # bound to one.
    if thread.channel_account_id:
        account = await db.get(CommunicationChannelAccount, str(thread.channel_account_id))
        if (
            account is not None
            and str(account.tenant_id) == str(tenant_id)
            and str(account.channel).lower() == "email"
            and bool(account.is_active)
        ):
            account_settings = _as_dict(account.settings_json)
            provider = str(account_settings.get("provider") or "").strip().lower()
            if provider in {"gmail", "microsoft_graph"}:
                try:
                    access_token = await _ensure_oauth_access_for_mailbox(
                        account_settings, provider=provider
                    )
                    account.settings_json = account_settings
                except OAuthProviderError as exc:
                    msg.delivery_status = "failed"
                    msg.error_message = str(exc)
                    return "oauth_refresh_failed"
                except RuntimeError as exc:
                    msg.delivery_status = "failed"
                    msg.error_message = str(exc)
                    return "oauth_refresh_token_missing"
                if not access_token:
                    msg.delivery_status = "failed"
                    msg.error_message = "OAuth access token is not configured"
                    return "oauth_access_token_missing"

                def _oauth_send_failed_payload() -> Dict[str, Any]:
                    return {
                        **_as_dict(msg.payload),
                        "dispatch": {
                            "status": "failed",
                            "attempted_at": _now_utc().isoformat(),
                            "actor_user_id": actor_id,
                            "adapter": f"{provider}_oauth",
                        },
                    }

                try:
                    provider_resp = await send_oauth_email_message(
                        provider=provider,
                        access_token=access_token,
                        to=to_addr,
                        subject=subject,
                        body_text=body,
                        body_html=msg.body_html,
                        from_address=(account.inbox_address or None),
                        reply_to=(account.inbox_address or None),
                    )
                except OAuthMailboxSendError as send_exc:
                    if getattr(send_exc, "status_code", None) != 401:
                        msg.delivery_status = "failed"
                        msg.error_message = str(send_exc)
                        msg.payload = _oauth_send_failed_payload()
                        return "oauth_send_failed"
                    try:
                        if _oauth_refresh_token(_as_dict(account_settings.get("oauth"))):
                            access_token = await _refresh_oauth_tokens_in_settings_json(
                                account_settings, provider=provider
                            )
                            account.settings_json = account_settings
                        else:
                            raise RuntimeError(
                                "OAuth access was rejected (401) and no refresh token is stored — reconnect mailbox OAuth in HostFlow."
                            )
                    except Exception as refresh_exc:
                        msg.delivery_status = "failed"
                        msg.error_message = str(refresh_exc)
                        msg.payload = _oauth_send_failed_payload()
                        return "oauth_send_failed"
                    try:
                        provider_resp = await send_oauth_email_message(
                            provider=provider,
                            access_token=access_token,
                            to=to_addr,
                            subject=subject,
                            body_text=body,
                            body_html=msg.body_html,
                            from_address=(account.inbox_address or None),
                            reply_to=(account.inbox_address or None),
                        )
                    except Exception as retry_exc:
                        msg.delivery_status = "failed"
                        msg.error_message = str(retry_exc)
                        msg.payload = _oauth_send_failed_payload()
                        return "oauth_send_failed"
                except Exception as exc:
                    msg.delivery_status = "failed"
                    msg.error_message = str(exc)
                    msg.payload = _oauth_send_failed_payload()
                    return "oauth_send_failed"
                now = _now_utc()
                msg.delivery_status = "sent"
                msg.sent_at = msg.sent_at or now
                msg.error_message = None
                provider_message_ref = (
                    str(_as_dict(provider_resp).get("message_ref") or "").strip() or None
                )
                if not msg.external_message_ref:
                    msg.external_message_ref = (
                        provider_message_ref or f"{provider}_out:{thread.id}:{msg.id}"
                    )
                msg.payload = {
                    **_as_dict(msg.payload),
                    "dispatch": {
                        "status": "sent",
                        "attempted_at": now.isoformat(),
                        "actor_user_id": actor_id,
                        "adapter": f"{provider}_oauth",
                        "recipient": to_addr,
                        "provider_result": provider_resp,
                    },
                }
                return None

    try:
        await send_email_for_tenant(
            db, tenant_id=tenant_id, to=to_addr, subject=subject, body=body
        )
    except Exception as exc:
        logger.exception(
            "communications email dispatch failed tenant=%s thread=%s msg=%s",
            tenant_id,
            thread.id,
            msg.id,
        )
        msg.delivery_status = "failed"
        msg.error_message = str(exc)
        msg.payload = {
            **_as_dict(msg.payload),
            "dispatch": {
                "status": "failed",
                "attempted_at": _now_utc().isoformat(),
                "actor_user_id": actor_id,
                "adapter": "tenant_smtp",
            },
        }
        return "send_failed"

    now = _now_utc()
    msg.delivery_status = "sent"
    msg.sent_at = msg.sent_at or now
    msg.error_message = None
    if not msg.external_message_ref:
        msg.external_message_ref = f"smtp:{thread.id}:{msg.id}"
    msg.payload = {
        **_as_dict(msg.payload),
        "dispatch": {
            "status": "sent",
            "attempted_at": now.isoformat(),
            "actor_user_id": actor_id,
            "adapter": "tenant_smtp",
            "recipient": to_addr,
        },
    }
    return None


async def _dispatch_telegram_message_via_bot_api(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
    msg: CommunicationMessage,
    actor_id: str | None,
) -> str | None:
    if msg.is_internal_note:
        return "internal_note"
    if msg.direction != "outbound":
        return "not_outbound"
    if not thread.channel_account_id:
        return "missing_channel_account"
    account = await db.get(CommunicationChannelAccount, str(thread.channel_account_id))
    if (
        account is None
        or str(account.tenant_id) != tenant_id
        or str(account.channel).lower() != "telegram"
    ):
        return "channel_account_not_found"
    cfg = _telegram_config_from_account_settings(account)
    if cfg is None:
        return "missing_bot_token"

    chat_id = str(msg.recipient_address or thread.channel_thread_ref or "").strip()
    if not chat_id:
        recipients = _as_dict(thread.participants_json).get("recipients")
        if isinstance(recipients, list) and recipients:
            chat_id = str(recipients[0] or "").strip()
    if not chat_id:
        msg.delivery_status = "failed"
        msg.error_message = "Missing Telegram chat_id"
        return "missing_chat_id"

    text = (msg.body_text or "").strip()
    doc_paths: list[Tuple[Path, str, str | None]] = []
    for item in _as_list(msg.attachments_json):
        if not isinstance(item, dict):
            continue
        if str(item.get("kind") or "").strip().lower() != "local_file":
            continue
        sp = str(item.get("storage_path") or "").strip()
        fn = str(item.get("filename") or Path(sp).name or "attachment")
        mime = item.get("mime")
        mime_s = str(mime).strip() if mime else None
        resolved = _resolve_comm_local_attachment_path(
            tenant_id=tenant_id, storage_path=sp
        )
        if resolved is None:
            msg.delivery_status = "failed"
            msg.error_message = f"Invalid or missing attachment: {fn}"
            return "attachment_not_found"
        doc_paths.append((resolved, fn, mime_s))

    if not text and not doc_paths:
        msg.delivery_status = "failed"
        msg.error_message = "Empty Telegram message body"
        return "empty_body"

    reply_to_id = None
    try:
        inbound_msg_id = _as_dict(msg.payload).get("reply_to_telegram_message_id")
        if inbound_msg_id is not None:
            reply_to_id = int(inbound_msg_id)
    except Exception:
        reply_to_id = None

    now = _now_utc()
    last_provider_resp: Dict[str, Any] = {}
    last_telegram_message_id: Any = None
    try:
        if doc_paths:
            for idx, (abs_path, filename, mime_s) in enumerate(doc_paths):
                caption = text if idx == 0 else None
                reply_for = reply_to_id if idx == 0 else None
                provider_resp = await send_telegram_document(
                    cfg,
                    chat_id=chat_id,
                    file_path=str(abs_path),
                    filename=filename,
                    mime_type=mime_s,
                    caption=caption,
                    reply_to_message_id=reply_for,
                )
                last_provider_resp = provider_resp
                result = _as_dict(provider_resp.get("result"))
                last_telegram_message_id = result.get("message_id")
        else:
            last_provider_resp = await send_telegram_text(
                cfg, chat_id=chat_id, text=text, reply_to_message_id=reply_to_id
            )
            result = _as_dict(last_provider_resp.get("result"))
            last_telegram_message_id = result.get("message_id")
    except Exception as exc:
        logger.exception(
            "communications telegram dispatch failed tenant=%s thread=%s msg=%s",
            tenant_id,
            thread.id,
            msg.id,
        )
        msg.delivery_status = "failed"
        msg.error_message = str(exc)
        msg.payload = {
            **_as_dict(msg.payload),
            "dispatch": {
                "status": "failed",
                "attempted_at": _now_utc().isoformat(),
                "actor_user_id": actor_id,
                "adapter": "telegram_bot_api",
            },
        }
        return "send_failed"

    msg.delivery_status = "sent"
    msg.sent_at = msg.sent_at or now
    msg.error_message = None
    if not msg.external_message_ref and last_telegram_message_id is not None:
        msg.external_message_ref = (
            f"telegram_out:{thread.channel_thread_ref or chat_id}:{last_telegram_message_id}"
        )
    msg.payload = {
        **_as_dict(msg.payload),
        "dispatch": {
            "status": "sent",
            "attempted_at": now.isoformat(),
            "actor_user_id": actor_id,
            "adapter": "telegram_bot_api",
            "chat_id": chat_id,
            "provider_result": last_provider_resp,
            "attachment_count": len(doc_paths),
        },
        "telegram_message_id": last_telegram_message_id,
    }
    return None


async def _dispatch_whatsapp_message_via_cloud_api(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
    msg: CommunicationMessage,
    actor_id: str | None,
) -> str | None:
    now = _now_utc()
    if msg.is_internal_note:
        return "internal_note"
    if msg.direction != "outbound":
        return "not_outbound"
    if thread.channel != "whatsapp":
        return "unsupported_channel"

    account = await db.get(
        CommunicationChannelAccount, str(thread.channel_account_id or "")
    )
    if (
        account is None
        or str(account.tenant_id) != tenant_id
        or str(account.channel).lower() != "whatsapp"
    ):
        msg.delivery_status = "failed"
        msg.error_message = "WhatsApp channel account is not configured"
        msg.payload = {
            **_as_dict(msg.payload),
            "dispatch": {
                "status": "failed",
                "attempted_at": now.isoformat(),
                "actor_user_id": actor_id,
                "thread_channel": thread.channel,
                "channel_account_id": thread.channel_account_id,
                "adapter": "whatsapp_cloud_api",
                "error": msg.error_message,
            },
        }
        return "missing_whatsapp_account"

    cfg = _whatsapp_config_from_account_settings(account)
    if cfg is None:
        msg.delivery_status = "failed"
        msg.error_message = (
            "WhatsApp settings are incomplete (phone_number_id/access_token)"
        )
        msg.payload = {
            **_as_dict(msg.payload),
            "dispatch": {
                "status": "failed",
                "attempted_at": now.isoformat(),
                "actor_user_id": actor_id,
                "thread_channel": thread.channel,
                "channel_account_id": thread.channel_account_id,
                "adapter": "whatsapp_cloud_api",
                "error": msg.error_message,
            },
        }
        return "missing_whatsapp_config"

    to_number = (
        str(msg.recipient_address or "").strip()
        or str(_pick_thread_recipient_address(thread) or "").strip()
    )
    text = _normalize_email_text(msg.body_text, msg.body_html).strip()
    if not to_number:
        msg.delivery_status = "failed"
        msg.error_message = "Recipient number is missing for WhatsApp dispatch"
        msg.payload = {
            **_as_dict(msg.payload),
            "dispatch": {
                "status": "failed",
                "attempted_at": now.isoformat(),
                "actor_user_id": actor_id,
                "thread_channel": thread.channel,
                "channel_account_id": thread.channel_account_id,
                "adapter": "whatsapp_cloud_api",
                "error": msg.error_message,
            },
        }
        return "missing_recipient"
    if not text:
        msg.delivery_status = "failed"
        msg.error_message = "Message body is empty"
        msg.payload = {
            **_as_dict(msg.payload),
            "dispatch": {
                "status": "failed",
                "attempted_at": now.isoformat(),
                "actor_user_id": actor_id,
                "thread_channel": thread.channel,
                "channel_account_id": thread.channel_account_id,
                "adapter": "whatsapp_cloud_api",
                "error": msg.error_message,
            },
        }
        return "empty_body"

    try:
        provider_resp = await send_whatsapp_text(cfg, to=to_number, text=text)
    except Exception as exc:
        logger.exception(
            "communications whatsapp dispatch failed tenant=%s thread=%s msg=%s",
            tenant_id,
            thread.id,
            msg.id,
        )
        msg.delivery_status = "failed"
        msg.error_message = str(exc)
        msg.payload = {
            **_as_dict(msg.payload),
            "dispatch": {
                "status": "failed",
                "attempted_at": now.isoformat(),
                "actor_user_id": actor_id,
                "thread_channel": thread.channel,
                "channel_account_id": thread.channel_account_id,
                "adapter": "whatsapp_cloud_api",
                "error": str(exc),
            },
        }
        return "provider_error"

    messages = (
        provider_resp.get("messages")
        if isinstance(provider_resp.get("messages"), list)
        else []
    )
    wa_message_id = None
    if messages and isinstance(messages[0], dict):
        wa_message_id = messages[0].get("id")

    msg.delivery_status = "sent"
    msg.sent_at = msg.sent_at or now
    msg.error_message = None
    if not msg.external_message_ref and wa_message_id:
        msg.external_message_ref = (
            f"whatsapp_out:{thread.channel_thread_ref or to_number}:{wa_message_id}"
        )
    msg.payload = {
        **_as_dict(msg.payload),
        "dispatch": {
            "status": "sent",
            "attempted_at": now.isoformat(),
            "actor_user_id": actor_id,
            "thread_channel": thread.channel,
            "channel_account_id": thread.channel_account_id,
            "adapter": "whatsapp_cloud_api",
        },
        "whatsapp_response": provider_resp,
        "whatsapp_message_id": wa_message_id,
    }
    return None


async def _dispatch_messenger_message_via_graph_api(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
    msg: CommunicationMessage,
    actor_id: str | None,
) -> str | None:
    now = _now_utc()
    if msg.is_internal_note:
        return "internal_note"
    if msg.direction != "outbound":
        return "not_outbound"
    if thread.channel != "messenger":
        return "unsupported_channel"

    account = await db.get(
        CommunicationChannelAccount, str(thread.channel_account_id or "")
    )
    if (
        account is None
        or str(account.tenant_id) != tenant_id
        or str(account.channel).lower() != "messenger"
    ):
        return "missing_messenger_account"
    cfg, page_id = _messenger_graph_config_from_account_settings(account)
    if cfg is None or not page_id:
        return "missing_messenger_config"

    recipient_id = (
        str(msg.recipient_address or "").strip()
        or str(_pick_thread_recipient_address(thread) or "").strip()
        or str(thread.channel_thread_ref or "").strip()
    )
    text = _normalize_email_text(msg.body_text, msg.body_html).strip()
    if not recipient_id:
        msg.delivery_status = "failed"
        msg.error_message = "Recipient PSID is missing for Messenger dispatch"
        return "missing_recipient"
    if not text:
        msg.delivery_status = "failed"
        msg.error_message = "Message body is empty"
        return "empty_body"

    try:
        provider_resp = await send_meta_text_message(
            cfg, sender_id=page_id, recipient_id=recipient_id, text=text
        )
    except Exception as exc:
        logger.exception(
            "communications messenger dispatch failed tenant=%s thread=%s msg=%s",
            tenant_id,
            thread.id,
            msg.id,
        )
        msg.delivery_status = "failed"
        msg.error_message = str(exc)
        return "provider_error"

    message_id = provider_resp.get("message_id")
    msg.delivery_status = "sent"
    msg.sent_at = msg.sent_at or now
    msg.error_message = None
    if not msg.external_message_ref and message_id:
        msg.external_message_ref = (
            f"messenger_out:{thread.channel_thread_ref or recipient_id}:{message_id}"
        )
    msg.payload = {
        **_as_dict(msg.payload),
        "dispatch": {
            "status": "sent",
            "attempted_at": now.isoformat(),
            "actor_user_id": actor_id,
            "thread_channel": thread.channel,
            "channel_account_id": thread.channel_account_id,
            "adapter": "meta_messenger_graph",
        },
        "messenger_response": provider_resp,
        "messenger_message_id": message_id,
    }
    return None


async def _dispatch_instagram_message_via_graph_api(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
    msg: CommunicationMessage,
    actor_id: str | None,
) -> str | None:
    now = _now_utc()
    if msg.is_internal_note:
        return "internal_note"
    if msg.direction != "outbound":
        return "not_outbound"
    if thread.channel != "instagram":
        return "unsupported_channel"

    account = await db.get(
        CommunicationChannelAccount, str(thread.channel_account_id or "")
    )
    if (
        account is None
        or str(account.tenant_id) != tenant_id
        or str(account.channel).lower() != "instagram"
    ):
        return "missing_instagram_account"
    cfg, account_id = _instagram_graph_config_from_account_settings(account)
    if cfg is None or not account_id:
        return "missing_instagram_config"

    recipient_id = (
        str(msg.recipient_address or "").strip()
        or str(_pick_thread_recipient_address(thread) or "").strip()
        or str(thread.channel_thread_ref or "").strip()
    )
    text = _normalize_email_text(msg.body_text, msg.body_html).strip()
    if not recipient_id:
        msg.delivery_status = "failed"
        msg.error_message = "Recipient user id is missing for Instagram dispatch"
        return "missing_recipient"
    if not text:
        msg.delivery_status = "failed"
        msg.error_message = "Message body is empty"
        return "empty_body"

    try:
        provider_resp = await send_meta_text_message(
            cfg, sender_id=account_id, recipient_id=recipient_id, text=text
        )
    except Exception as exc:
        logger.exception(
            "communications instagram dispatch failed tenant=%s thread=%s msg=%s",
            tenant_id,
            thread.id,
            msg.id,
        )
        msg.delivery_status = "failed"
        msg.error_message = str(exc)
        return "provider_error"

    message_id = provider_resp.get("message_id")
    msg.delivery_status = "sent"
    msg.sent_at = msg.sent_at or now
    msg.error_message = None
    if not msg.external_message_ref and message_id:
        msg.external_message_ref = (
            f"instagram_out:{thread.channel_thread_ref or recipient_id}:{message_id}"
        )
    msg.payload = {
        **_as_dict(msg.payload),
        "dispatch": {
            "status": "sent",
            "attempted_at": now.isoformat(),
            "actor_user_id": actor_id,
            "thread_channel": thread.channel,
            "channel_account_id": thread.channel_account_id,
            "adapter": "meta_instagram_graph",
        },
        "instagram_response": provider_resp,
        "instagram_message_id": message_id,
    }
    return None


async def _dispatch_viber_message_via_bot_api(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
    msg: CommunicationMessage,
    actor_id: str | None,
) -> str | None:
    now = _now_utc()
    if msg.is_internal_note:
        return "internal_note"
    if msg.direction != "outbound":
        return "not_outbound"
    if thread.channel != "viber":
        return "unsupported_channel"

    account = await db.get(
        CommunicationChannelAccount, str(thread.channel_account_id or "")
    )
    if (
        account is None
        or str(account.tenant_id) != tenant_id
        or str(account.channel).lower() != "viber"
    ):
        return "missing_viber_account"
    cfg = _viber_config_from_account_settings(account)
    if cfg is None:
        return "missing_viber_config"

    recipient_id = (
        str(msg.recipient_address or "").strip()
        or str(_pick_thread_recipient_address(thread) or "").strip()
        or str(thread.channel_thread_ref or "").strip()
    )
    text = _normalize_email_text(msg.body_text, msg.body_html).strip()
    if not recipient_id:
        msg.delivery_status = "failed"
        msg.error_message = "Recipient id is missing for Viber dispatch"
        return "missing_recipient"
    if not text:
        msg.delivery_status = "failed"
        msg.error_message = "Message body is empty"
        return "empty_body"

    try:
        provider_resp = await send_viber_text_message(cfg, receiver=recipient_id, text=text)
    except Exception as exc:
        logger.exception(
            "communications viber dispatch failed tenant=%s thread=%s msg=%s",
            tenant_id,
            thread.id,
            msg.id,
        )
        msg.delivery_status = "failed"
        msg.error_message = str(exc)
        return "provider_error"

    message_token = provider_resp.get("message_token")
    msg.delivery_status = "sent"
    msg.sent_at = msg.sent_at or now
    msg.error_message = None
    if not msg.external_message_ref and message_token:
        msg.external_message_ref = (
            f"viber_out:{thread.channel_thread_ref or recipient_id}:{message_token}"
        )
    msg.payload = {
        **_as_dict(msg.payload),
        "dispatch": {
            "status": "sent",
            "attempted_at": now.isoformat(),
            "actor_user_id": actor_id,
            "thread_channel": thread.channel,
            "channel_account_id": thread.channel_account_id,
            "adapter": "viber_bot_api",
        },
        "viber_response": provider_resp,
        "viber_message_token": message_token,
    }
    return None
