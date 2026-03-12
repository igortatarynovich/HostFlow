from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class TelegramBotConfig:
    bot_token: str
    timeout_seconds: int = 15


def _api_url(token: str, method: str) -> str:
    return f"https://api.telegram.org/bot{token}/{method}"


def telegram_get_me_sync(cfg: TelegramBotConfig) -> Dict[str, Any]:
    req = urllib.request.Request(
        _api_url(cfg.bot_token, "getMe"),
        headers={"Content-Type": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=cfg.timeout_seconds) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Telegram HTTP {exc.code}: {details}") from exc
    except Exception as exc:
        raise RuntimeError(f"Telegram getMe failed: {exc}") from exc
    try:
        parsed = json.loads(body)
    except Exception as exc:
        raise RuntimeError(f"Telegram response parse failed: {exc}") from exc
    if not isinstance(parsed, dict) or not parsed.get("ok"):
        raise RuntimeError(f"Telegram API error: {parsed}")
    return parsed


async def telegram_get_me(cfg: TelegramBotConfig) -> Dict[str, Any]:
    return await asyncio.to_thread(telegram_get_me_sync, cfg)


def telegram_set_webhook_sync(cfg: TelegramBotConfig, *, webhook_url: str) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"url": webhook_url}
    req = urllib.request.Request(
        _api_url(cfg.bot_token, "setWebhook"),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=cfg.timeout_seconds) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Telegram HTTP {exc.code}: {details}") from exc
    except Exception as exc:
        raise RuntimeError(f"Telegram setWebhook failed: {exc}") from exc
    try:
        parsed = json.loads(body)
    except Exception as exc:
        raise RuntimeError(f"Telegram response parse failed: {exc}") from exc
    if not isinstance(parsed, dict) or not parsed.get("ok"):
        raise RuntimeError(f"Telegram API error: {parsed}")
    return parsed


async def telegram_set_webhook(cfg: TelegramBotConfig, *, webhook_url: str) -> Dict[str, Any]:
    return await asyncio.to_thread(telegram_set_webhook_sync, cfg, webhook_url=webhook_url)


def telegram_delete_webhook_sync(cfg: TelegramBotConfig) -> Dict[str, Any]:
    req = urllib.request.Request(
        _api_url(cfg.bot_token, "deleteWebhook"),
        data=json.dumps({}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=cfg.timeout_seconds) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Telegram HTTP {exc.code}: {details}") from exc
    except Exception as exc:
        raise RuntimeError(f"Telegram deleteWebhook failed: {exc}") from exc
    try:
        parsed = json.loads(body)
    except Exception as exc:
        raise RuntimeError(f"Telegram response parse failed: {exc}") from exc
    if not isinstance(parsed, dict) or not parsed.get("ok"):
        raise RuntimeError(f"Telegram API error: {parsed}")
    return parsed


async def telegram_delete_webhook(cfg: TelegramBotConfig) -> Dict[str, Any]:
    return await asyncio.to_thread(telegram_delete_webhook_sync, cfg)


def telegram_get_webhook_info_sync(cfg: TelegramBotConfig) -> Dict[str, Any]:
    req = urllib.request.Request(
        _api_url(cfg.bot_token, "getWebhookInfo"),
        headers={"Content-Type": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=cfg.timeout_seconds) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Telegram HTTP {exc.code}: {details}") from exc
    except Exception as exc:
        raise RuntimeError(f"Telegram getWebhookInfo failed: {exc}") from exc
    try:
        parsed = json.loads(body)
    except Exception as exc:
        raise RuntimeError(f"Telegram response parse failed: {exc}") from exc
    if not isinstance(parsed, dict) or not parsed.get("ok"):
        raise RuntimeError(f"Telegram API error: {parsed}")
    return parsed


async def telegram_get_webhook_info(cfg: TelegramBotConfig) -> Dict[str, Any]:
    return await asyncio.to_thread(telegram_get_webhook_info_sync, cfg)


def send_telegram_text_sync(
    cfg: TelegramBotConfig,
    *,
    chat_id: str,
    text: str,
    reply_to_message_id: int | None = None,
    reply_markup: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
    }
    if reply_to_message_id is not None:
        payload["reply_to_message_id"] = reply_to_message_id
    if isinstance(reply_markup, dict) and reply_markup:
        payload["reply_markup"] = reply_markup
    req = urllib.request.Request(
        _api_url(cfg.bot_token, "sendMessage"),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=cfg.timeout_seconds) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Telegram HTTP {exc.code}: {details}") from exc
    except Exception as exc:
        raise RuntimeError(f"Telegram send failed: {exc}") from exc
    try:
        parsed = json.loads(body)
    except Exception as exc:
        raise RuntimeError(f"Telegram response parse failed: {exc}") from exc
    if not isinstance(parsed, dict) or not parsed.get("ok"):
        raise RuntimeError(f"Telegram API error: {parsed}")
    return parsed


async def send_telegram_text(
    cfg: TelegramBotConfig,
    *,
    chat_id: str,
    text: str,
    reply_to_message_id: int | None = None,
    reply_markup: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    return await asyncio.to_thread(
        send_telegram_text_sync,
        cfg,
        chat_id=chat_id,
        text=text,
        reply_to_message_id=reply_to_message_id,
        reply_markup=reply_markup,
    )


def normalize_telegram_update(update: Dict[str, Any]) -> Dict[str, Any] | None:
    if not isinstance(update, dict):
        return None
    message = None
    source_kind = None
    for key in ("message", "edited_message", "channel_post", "edited_channel_post"):
        value = update.get(key)
        if isinstance(value, dict):
            message = value
            source_kind = key
            break
    if message is None:
        return None

    chat = message.get("chat") if isinstance(message.get("chat"), dict) else {}
    from_user = message.get("from") if isinstance(message.get("from"), dict) else {}
    chat_id = chat.get("id")
    if chat_id is None:
        return None

    text = message.get("text")
    if not isinstance(text, str) or not text.strip():
        text = message.get("caption") if isinstance(message.get("caption"), str) else None

    contact = message.get("contact") if isinstance(message.get("contact"), dict) else {}
    contact_phone = str(contact.get("phone_number") or "").strip() or None

    first_name = str(from_user.get("first_name") or "").strip()
    last_name = str(from_user.get("last_name") or "").strip()
    username = str(from_user.get("username") or "").strip()
    sender_label = " ".join(x for x in [first_name, last_name] if x).strip() or (f"@{username}" if username else None)
    sender_address = str(from_user.get("id") or "").strip() or None
    recipient_label = str(chat.get("title") or chat.get("username") or chat.get("id") or "").strip() or None
    recipient_address = str(chat_id)
    message_id = message.get("message_id")
    update_id = update.get("update_id")

    attachments = []
    if isinstance(message.get("photo"), list) and message["photo"]:
        attachments.append({"kind": "photo", "count": len(message["photo"])})
    if isinstance(message.get("document"), dict):
        doc = message["document"]
        attachments.append(
            {
                "kind": "document",
                "filename": doc.get("file_name"),
                "content_type": doc.get("mime_type"),
                "size": doc.get("file_size"),
            }
        )

    return {
        "provider_chat_ref": recipient_address,
        "provider_thread_ref": recipient_address,
        "external_message_ref": f"telegram:{update_id}:{message_id}",
        "sender_address": sender_address,
        "sender_label": sender_label,
        "recipient_address": recipient_address,
        "recipient_label": recipient_label,
        "subject": None,
        "text": text or contact_phone,
        "html": None,
        "attachments": attachments,
        "headers": {"telegram_source": source_kind},
        "payload": {
            "telegram_update_id": update_id,
            "telegram_message_id": message_id,
            "telegram_chat_type": chat.get("type"),
            "telegram_username": username or None,
            "telegram_contact_phone": contact_phone,
            "telegram_contact_user_id": str(contact.get("user_id") or "").strip() or None,
            "telegram_contact_first_name": str(contact.get("first_name") or "").strip() or None,
            "telegram_contact_last_name": str(contact.get("last_name") or "").strip() or None,
        },
    }
