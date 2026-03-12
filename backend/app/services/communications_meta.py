from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class MetaGraphConfig:
    access_token: str
    api_version: str = "v20.0"
    timeout_seconds: int = 15


def _api_url(cfg: MetaGraphConfig, path: str) -> str:
    safe_path = path.lstrip("/")
    return f"https://graph.facebook.com/{cfg.api_version}/{safe_path}"


def _request_json(
    cfg: MetaGraphConfig,
    *,
    method: str,
    path: str,
    payload: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    body = json.dumps(payload or {}).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        _api_url(cfg, path),
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg.access_token}",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=cfg.timeout_seconds) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Meta Graph HTTP {exc.code}: {details}") from exc
    except Exception as exc:
        raise RuntimeError(f"Meta Graph request failed: {exc}") from exc
    try:
        parsed = json.loads(raw)
    except Exception as exc:
        raise RuntimeError(f"Meta Graph response parse failed: {exc}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError(f"Meta Graph API error: {parsed}")
    if isinstance(parsed.get("error"), dict):
        raise RuntimeError(f"Meta Graph API error: {parsed.get('error')}")
    return parsed


def meta_graph_get_object_sync(cfg: MetaGraphConfig, *, object_id: str, fields: str) -> Dict[str, Any]:
    query = f"?fields={urllib.parse.quote(fields, safe=',')}" if fields else ""
    return _request_json(cfg, method="GET", path=f"{object_id}{query}")


async def meta_graph_get_object(cfg: MetaGraphConfig, *, object_id: str, fields: str) -> Dict[str, Any]:
    return await asyncio.to_thread(meta_graph_get_object_sync, cfg, object_id=object_id, fields=fields)


def send_meta_text_message_sync(
    cfg: MetaGraphConfig,
    *,
    sender_id: str,
    recipient_id: str,
    text: str,
) -> Dict[str, Any]:
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text},
    }
    return _request_json(cfg, method="POST", path=f"{sender_id}/messages", payload=payload)


async def send_meta_text_message(
    cfg: MetaGraphConfig,
    *,
    sender_id: str,
    recipient_id: str,
    text: str,
) -> Dict[str, Any]:
    return await asyncio.to_thread(
        send_meta_text_message_sync,
        cfg,
        sender_id=sender_id,
        recipient_id=recipient_id,
        text=text,
    )


def normalize_meta_webhook(payload: Dict[str, Any], *, channel: str) -> List[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    entries = payload.get("entry")
    if not isinstance(entries, list):
        return []

    out: List[Dict[str, Any]] = []
    normalized_channel = str(channel or "").strip().lower() or "meta"
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        messaging = entry.get("messaging")
        if isinstance(messaging, list):
            for event in messaging:
                if not isinstance(event, dict):
                    continue
                sender = event.get("sender") if isinstance(event.get("sender"), dict) else {}
                recipient = event.get("recipient") if isinstance(event.get("recipient"), dict) else {}
                message = event.get("message") if isinstance(event.get("message"), dict) else {}
                sender_id = str(sender.get("id") or "").strip()
                recipient_id = str(recipient.get("id") or "").strip()
                if not sender_id or not recipient_id:
                    continue
                if bool(message.get("is_echo")):
                    continue
                text = str(message.get("text") or "").strip() or None
                attachments = message.get("attachments") if isinstance(message.get("attachments"), list) else []
                mid = str(message.get("mid") or "").strip()
                out.append(
                    {
                        "provider_chat_ref": sender_id,
                        "provider_thread_ref": sender_id,
                        "external_message_ref": f"{normalized_channel}:{mid}" if mid else None,
                        "sender_address": sender_id,
                        "sender_label": None,
                        "recipient_address": recipient_id,
                        "recipient_label": None,
                        "text": text,
                        "attachments": attachments if isinstance(attachments, list) else [],
                        "headers": {"meta_object": payload.get("object"), "meta_channel": normalized_channel},
                        "payload": {
                            "meta_mid": mid or None,
                            "meta_timestamp": event.get("timestamp"),
                            "meta_raw_event": event,
                        },
                    }
                )
            continue

        changes = entry.get("changes")
        if not isinstance(changes, list):
            continue
        for change in changes:
            if not isinstance(change, dict):
                continue
            value = change.get("value") if isinstance(change.get("value"), dict) else {}
            messages = value.get("messages") if isinstance(value.get("messages"), list) else []
            for msg in messages:
                if not isinstance(msg, dict):
                    continue
                sender_id = str(msg.get("from") or "").strip()
                recipient_id = str((value.get("metadata") or {}).get("phone_number_id") or "").strip()
                text = str((msg.get("text") or {}).get("body") or "").strip() or None
                mid = str(msg.get("id") or "").strip()
                if not sender_id:
                    continue
                out.append(
                    {
                        "provider_chat_ref": sender_id,
                        "provider_thread_ref": sender_id,
                        "external_message_ref": f"{normalized_channel}:{mid}" if mid else None,
                        "sender_address": sender_id,
                        "sender_label": None,
                        "recipient_address": recipient_id or None,
                        "recipient_label": None,
                        "text": text,
                        "attachments": [],
                        "headers": {"meta_object": payload.get("object"), "meta_channel": normalized_channel},
                        "payload": {
                            "meta_mid": mid or None,
                            "meta_change_field": change.get("field"),
                            "meta_raw_message": msg,
                        },
                    }
                )
    return out
