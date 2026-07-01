from __future__ import annotations

import asyncio
import imaplib
import socket
from dataclasses import dataclass
from email import message_from_bytes
from email.header import decode_header
from email.message import Message
from email.policy import default as default_policy
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional


def _decode_mime_header(value: str | None) -> str | None:
    if not value:
        return None
    parts = []
    for chunk, enc in decode_header(value):
        if isinstance(chunk, bytes):
            try:
                parts.append(chunk.decode(enc or "utf-8", errors="replace"))
            except Exception:
                parts.append(chunk.decode("utf-8", errors="replace"))
        else:
            parts.append(str(chunk))
    text = "".join(parts).strip()
    return text or None


def _extract_addresses(raw: str | None) -> List[str]:
    if not raw:
        return []
    values = [v.strip() for v in str(raw).replace(";", ",").split(",")]
    return [v for v in values if v]


def _extract_text_parts(msg: Message) -> tuple[str | None, str | None]:
    text_parts: List[str] = []
    html_parts: List[str] = []
    if msg.is_multipart():
        for part in msg.walk():
            if part.is_multipart():
                continue
            content_type = (part.get_content_type() or "").lower()
            disposition = (part.get("Content-Disposition") or "").lower()
            if "attachment" in disposition:
                continue
            try:
                payload_bytes = part.get_payload(decode=True)
            except Exception:
                payload_bytes = None
            charset = part.get_content_charset() or "utf-8"
            if payload_bytes is None:
                try:
                    payload_text = part.get_payload() or ""
                    payload_str = str(payload_text)
                except Exception:
                    payload_str = ""
            else:
                payload_str = payload_bytes.decode(charset, errors="replace")
            if content_type == "text/plain":
                text_parts.append(payload_str)
            elif content_type == "text/html":
                html_parts.append(payload_str)
    else:
        content_type = (msg.get_content_type() or "").lower()
        try:
            payload_bytes = msg.get_payload(decode=True)
        except Exception:
            payload_bytes = None
        charset = msg.get_content_charset() or "utf-8"
        if payload_bytes is None:
            payload_str = str(msg.get_payload() or "")
        else:
            payload_str = payload_bytes.decode(charset, errors="replace")
        if content_type == "text/html":
            html_parts.append(payload_str)
        else:
            text_parts.append(payload_str)
    text = "\n\n".join([x.strip() for x in text_parts if x and x.strip()]).strip() or None
    html = "\n\n".join([x for x in html_parts if x]).strip() or None
    return text, html


def _extract_attachments_meta(msg: Message) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for part in msg.walk():
        if part.is_multipart():
            continue
        disposition = (part.get("Content-Disposition") or "").lower()
        if "attachment" not in disposition:
            continue
        filename = _decode_mime_header(part.get_filename())
        size = None
        try:
            payload = part.get_payload(decode=True)
            if isinstance(payload, (bytes, bytearray)):
                size = len(payload)
        except Exception:
            size = None
        items.append(
            {
                "filename": filename,
                "content_type": part.get_content_type(),
                "size": size,
            }
        )
    return items


@dataclass
class ImapClientConfig:
    host: str
    port: int = 993
    user: str = ""
    password: str = ""
    use_ssl: bool = True
    folder: str = "INBOX"
    search_criteria: str = "UNSEEN"
    mark_seen: bool = False
    timeout_seconds: int = 15


def _open_imap_sync(cfg: ImapClientConfig):
    socket.setdefaulttimeout(cfg.timeout_seconds)
    if cfg.use_ssl:
        conn = imaplib.IMAP4_SSL(cfg.host, cfg.port)
    else:
        conn = imaplib.IMAP4(cfg.host, cfg.port)
    conn.login(cfg.user, cfg.password)
    return conn


def test_imap_connection_sync(cfg: ImapClientConfig) -> Dict[str, Any]:
    conn = _open_imap_sync(cfg)
    try:
        status, data = conn.select(cfg.folder, readonly=True)
        if status != "OK":
            raise RuntimeError(f"IMAP select failed: {data!r}")
        count = 0
        if data and data[0]:
            try:
                count = int(data[0])
            except Exception:
                count = 0
        return {"ok": True, "folder": cfg.folder, "message_count": count}
    finally:
        try:
            conn.logout()
        except Exception:
            pass


def poll_imap_messages_sync(cfg: ImapClientConfig, *, limit: int = 25) -> Dict[str, Any]:
    conn = _open_imap_sync(cfg)
    try:
        status, data = conn.select(cfg.folder, readonly=not cfg.mark_seen)
        if status != "OK":
            raise RuntimeError(f"IMAP select failed: {data!r}")

        status, ids_data = conn.search(None, cfg.search_criteria or "UNSEEN")
        if status != "OK":
            raise RuntimeError(f"IMAP search failed: {ids_data!r}")
        numbers = []
        if ids_data and ids_data[0]:
            numbers = [x for x in ids_data[0].split() if x]
        selected = numbers[-limit:]
        items: List[Dict[str, Any]] = []

        for num in selected:
            fetch_status, msg_data = conn.fetch(num, "(RFC822)")
            if fetch_status != "OK":
                continue
            raw_bytes = None
            for row in msg_data or []:
                if isinstance(row, tuple) and len(row) >= 2 and isinstance(row[1], (bytes, bytearray)):
                    raw_bytes = bytes(row[1])
                    break
            if not raw_bytes:
                continue
            parsed = message_from_bytes(raw_bytes, policy=default_policy)
            subject = _decode_mime_header(parsed.get("Subject"))
            from_raw = parsed.get("From")
            to_raw = parsed.get("To")
            cc_raw = parsed.get("Cc")
            msg_id = (parsed.get("Message-ID") or "").strip() or None
            in_reply_to = (parsed.get("In-Reply-To") or "").strip() or None
            refs = (parsed.get("References") or "").strip() or None
            text, html = _extract_text_parts(parsed)
            attachments = _extract_attachments_meta(parsed)
            received_at = None
            try:
                dt = parsedate_to_datetime(parsed.get("Date")) if parsed.get("Date") else None
                if dt is not None:
                    received_at = dt.astimezone().isoformat()
            except Exception:
                received_at = None

            items.append(
                {
                    "provider_thread_ref": in_reply_to or refs or None,
                    "external_message_ref": msg_id or f"imap:{cfg.user}:{num.decode(errors='ignore')}",
                    "subject": subject,
                    "from_address": from_raw,
                    "to_address": to_raw,
                    "cc": _extract_addresses(cc_raw),
                    "text": text,
                    "html": html,
                    "received_at": received_at,
                    "headers": {
                        "message_id": msg_id,
                        "in_reply_to": in_reply_to,
                        "references": refs,
                    },
                    "attachments": attachments,
                    "payload": {"imap_msg_num": num.decode(errors="ignore")},
                }
            )

        if cfg.mark_seen and selected:
            for num in selected:
                try:
                    conn.store(num, "+FLAGS", "\\Seen")
                except Exception:
                    pass

        return {
            "ok": True,
            "folder": cfg.folder,
            "search_criteria": cfg.search_criteria,
            "matched": len(numbers),
            "returned": len(items),
            "items": items,
        }
    finally:
        try:
            conn.logout()
        except Exception:
            pass


async def test_imap_connection(cfg: ImapClientConfig) -> Dict[str, Any]:
    return await asyncio.to_thread(test_imap_connection_sync, cfg)


async def poll_imap_messages(cfg: ImapClientConfig, *, limit: int = 25) -> Dict[str, Any]:
    return await asyncio.to_thread(poll_imap_messages_sync, cfg, limit=limit)

