from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class WhatsAppCloudConfig:
    access_token: str
    phone_number_id: str
    api_version: str = "v20.0"
    timeout_seconds: int = 15


def _api_url(cfg: WhatsAppCloudConfig, path: str) -> str:
    safe_path = path.lstrip("/")
    return f"https://graph.facebook.com/{cfg.api_version}/{safe_path}"


def _request_json(
    cfg: WhatsAppCloudConfig,
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
        raise RuntimeError(f"WhatsApp HTTP {exc.code}: {details}") from exc
    except Exception as exc:
        raise RuntimeError(f"WhatsApp request failed: {exc}") from exc
    try:
        parsed = json.loads(raw)
    except Exception as exc:
        raise RuntimeError(f"WhatsApp response parse failed: {exc}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError(f"WhatsApp API error: {parsed}")
    return parsed


def whatsapp_get_phone_number_info_sync(cfg: WhatsAppCloudConfig) -> Dict[str, Any]:
    return _request_json(
        cfg,
        method="GET",
        path=f"{cfg.phone_number_id}?fields=id,display_phone_number,verified_name,quality_rating",
    )


async def whatsapp_get_phone_number_info(cfg: WhatsAppCloudConfig) -> Dict[str, Any]:
    return await asyncio.to_thread(whatsapp_get_phone_number_info_sync, cfg)


def send_whatsapp_text_sync(
    cfg: WhatsAppCloudConfig,
    *,
    to: str,
    text: str,
) -> Dict[str, Any]:
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }
    return _request_json(
        cfg,
        method="POST",
        path=f"{cfg.phone_number_id}/messages",
        payload=payload,
    )


async def send_whatsapp_text(
    cfg: WhatsAppCloudConfig,
    *,
    to: str,
    text: str,
) -> Dict[str, Any]:
    return await asyncio.to_thread(send_whatsapp_text_sync, cfg, to=to, text=text)


def normalize_whatsapp_webhook(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    entries = payload.get("entry")
    if not isinstance(entries, list):
        return []

    out: List[Dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        changes = entry.get("changes")
        if not isinstance(changes, list):
            continue
        for change in changes:
            if not isinstance(change, dict):
                continue
            value = change.get("value")
            if not isinstance(value, dict):
                continue
            contacts = value.get("contacts") if isinstance(value.get("contacts"), list) else []
            sender_names: Dict[str, str] = {}
            for contact in contacts:
                if not isinstance(contact, dict):
                    continue
                wa_id = str(contact.get("wa_id") or "").strip()
                profile = contact.get("profile") if isinstance(contact.get("profile"), dict) else {}
                name = str(profile.get("name") or "").strip()
                if wa_id and name:
                    sender_names[wa_id] = name

            metadata = value.get("metadata") if isinstance(value.get("metadata"), dict) else {}
            phone_number_id = str(metadata.get("phone_number_id") or "").strip()
            display_phone = str(metadata.get("display_phone_number") or "").strip()
            messages = value.get("messages") if isinstance(value.get("messages"), list) else []

            for msg in messages:
                if not isinstance(msg, dict):
                    continue
                msg_id = str(msg.get("id") or "").strip()
                from_wa = str(msg.get("from") or "").strip()
                msg_type = str(msg.get("type") or "").strip().lower() or "unknown"
                text_body = None
                attachments: List[Dict[str, Any]] = []
                if msg_type == "text":
                    text_body = str((msg.get("text") or {}).get("body") or "").strip() or None
                elif msg_type in {"image", "audio", "video", "document", "sticker"}:
                    media = msg.get(msg_type) if isinstance(msg.get(msg_type), dict) else {}
                    caption = str(media.get("caption") or "").strip()
                    text_body = caption or None
                    attachments.append(
                        {
                            "kind": msg_type,
                            "id": media.get("id"),
                            "mime_type": media.get("mime_type"),
                            "sha256": media.get("sha256"),
                            "filename": media.get("filename"),
                        }
                    )
                elif msg_type == "button":
                    button = msg.get("button") if isinstance(msg.get("button"), dict) else {}
                    text_body = str(button.get("text") or button.get("payload") or "").strip() or None
                elif msg_type == "interactive":
                    interactive = msg.get("interactive") if isinstance(msg.get("interactive"), dict) else {}
                    text_body = json.dumps(interactive, ensure_ascii=False)
                elif msg_type == "location":
                    location = msg.get("location") if isinstance(msg.get("location"), dict) else {}
                    text_body = json.dumps(location, ensure_ascii=False)
                else:
                    text_body = json.dumps(msg, ensure_ascii=False)

                sender_label = sender_names.get(from_wa)
                out.append(
                    {
                        "provider_chat_ref": from_wa,
                        "provider_thread_ref": from_wa,
                        "external_message_ref": f"whatsapp:{msg_id}" if msg_id else None,
                        "sender_address": from_wa or None,
                        "sender_label": sender_label or None,
                        "recipient_address": phone_number_id or None,
                        "recipient_label": display_phone or None,
                        "subject": None,
                        "text": text_body,
                        "html": None,
                        "attachments": attachments,
                        "headers": {"whatsapp_field": change.get("field")},
                        "payload": {
                            "whatsapp_message_id": msg_id or None,
                            "whatsapp_type": msg_type,
                            "whatsapp_timestamp": msg.get("timestamp"),
                            "whatsapp_context": msg.get("context"),
                            "whatsapp_metadata": metadata,
                        },
                    }
                )
    return out

