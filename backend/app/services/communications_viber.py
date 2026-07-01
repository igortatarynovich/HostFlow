from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class ViberBotConfig:
    bot_token: str
    timeout_seconds: int = 15


def _request_json(
    cfg: ViberBotConfig,
    *,
    path: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    req = urllib.request.Request(
        f"https://chatapi.viber.com/pa/{path.lstrip('/')}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Viber-Auth-Token": cfg.bot_token,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=cfg.timeout_seconds) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Viber HTTP {exc.code}: {details}") from exc
    except Exception as exc:
        raise RuntimeError(f"Viber request failed: {exc}") from exc
    try:
        parsed = json.loads(raw)
    except Exception as exc:
        raise RuntimeError(f"Viber response parse failed: {exc}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError(f"Viber API error: {parsed}")
    if int(parsed.get("status") or 0) != 0:
        raise RuntimeError(f"Viber API error: {parsed}")
    return parsed


def viber_get_account_info_sync(cfg: ViberBotConfig) -> Dict[str, Any]:
    return _request_json(cfg, path="get_account_info", payload={})


async def viber_get_account_info(cfg: ViberBotConfig) -> Dict[str, Any]:
    return await asyncio.to_thread(viber_get_account_info_sync, cfg)


def send_viber_text_message_sync(
    cfg: ViberBotConfig,
    *,
    receiver: str,
    text: str,
) -> Dict[str, Any]:
    return _request_json(
        cfg,
        path="send_message",
        payload={
            "receiver": receiver,
            "type": "text",
            "text": text,
        },
    )


async def send_viber_text_message(
    cfg: ViberBotConfig,
    *,
    receiver: str,
    text: str,
) -> Dict[str, Any]:
    return await asyncio.to_thread(send_viber_text_message_sync, cfg, receiver=receiver, text=text)


def normalize_viber_webhook(payload: Dict[str, Any]) -> Dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    if str(payload.get("event") or "").strip().lower() != "message":
        return None
    sender = payload.get("sender") if isinstance(payload.get("sender"), dict) else {}
    message = payload.get("message") if isinstance(payload.get("message"), dict) else {}
    sender_id = str(sender.get("id") or "").strip()
    msg_token = payload.get("message_token")
    text = str(message.get("text") or "").strip()
    if not sender_id or not text:
        return None
    return {
        "provider_chat_ref": sender_id,
        "provider_thread_ref": sender_id,
        "external_message_ref": f"viber:{msg_token}" if msg_token is not None else None,
        "sender_address": sender_id,
        "sender_label": str(sender.get("name") or "").strip() or None,
        "recipient_address": None,
        "recipient_label": None,
        "text": text,
        "attachments": [],
        "headers": {"viber_event": payload.get("event")},
        "payload": {
            "viber_event_timestamp": payload.get("timestamp"),
            "viber_message_token": msg_token,
            "viber_sender": sender,
        },
    }
