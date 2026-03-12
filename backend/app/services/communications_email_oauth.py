from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx


class OAuthMailboxPollError(RuntimeError):
    pass


@dataclass
class OAuthMailboxPollResult:
    ok: bool
    provider: str
    returned: int
    items: List[Dict[str, Any]] = field(default_factory=list)
    next_cursor: str | None = None
    raw: Dict[str, Any] = field(default_factory=dict)


def _decode_base64url_text(value: str | None) -> str | None:
    if not value:
        return None
    token = value.strip()
    if not token:
        return None
    padding = "=" * ((4 - len(token) % 4) % 4)
    try:
        data = base64.urlsafe_b64decode((token + padding).encode("utf-8"))
        return data.decode("utf-8", errors="replace")
    except Exception:
        return None


def _gmail_header(headers: List[Dict[str, Any]], name: str) -> str | None:
    target = name.strip().lower()
    for row in headers:
        if str(row.get("name") or "").strip().lower() == target:
            text = str(row.get("value") or "").strip()
            return text or None
    return None


def _gmail_extract_body(payload: Dict[str, Any]) -> tuple[str | None, str | None]:
    text = None
    html = None
    mime = str(payload.get("mimeType") or "").lower()
    data = _decode_base64url_text(payload.get("body", {}).get("data"))
    if mime == "text/plain":
        text = data
    elif mime == "text/html":
        html = data
    parts = payload.get("parts")
    if isinstance(parts, list):
        for part in parts:
            if not isinstance(part, dict):
                continue
            p_text, p_html = _gmail_extract_body(part)
            if not text and p_text:
                text = p_text
            if not html and p_html:
                html = p_html
    return text, html


async def _poll_gmail(
    *,
    access_token: str,
    limit: int,
    cursor: str | None,
    folder: str = "inbox",
) -> OAuthMailboxPollResult:
    headers = {"Authorization": f"Bearer {access_token}"}
    params: Dict[str, Any] = {"maxResults": max(1, min(int(limit), 200))}
    if (folder or "").strip().lower() == "sent":
        params["q"] = "in:sent"
    if cursor:
        params["pageToken"] = cursor
    async with httpx.AsyncClient(timeout=25.0) as client:
        listing = await client.get("https://gmail.googleapis.com/gmail/v1/users/me/messages", headers=headers, params=params)
        if listing.status_code >= 400:
            raise OAuthMailboxPollError(f"Gmail list failed: {listing.status_code} {listing.text}")
        listing_json = listing.json() if listing.headers.get("content-type", "").startswith("application/json") else {}
        rows = listing_json.get("messages") if isinstance(listing_json, dict) else []
        if not isinstance(rows, list):
            rows = []
        items: List[Dict[str, Any]] = []
        for row in rows[:limit]:
            msg_id = str((row or {}).get("id") or "").strip()
            if not msg_id:
                continue
            details = await client.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}",
                headers=headers,
                params={"format": "full"},
            )
            if details.status_code >= 400:
                continue
            data = details.json() if details.headers.get("content-type", "").startswith("application/json") else {}
            payload = data.get("payload") if isinstance(data, dict) and isinstance(data.get("payload"), dict) else {}
            hdrs = payload.get("headers") if isinstance(payload.get("headers"), list) else []
            from_address = _gmail_header(hdrs, "From")
            to_address = _gmail_header(hdrs, "To")
            cc_raw = _gmail_header(hdrs, "Cc")
            subject = _gmail_header(hdrs, "Subject")
            msg_ref = _gmail_header(hdrs, "Message-ID") or str(data.get("id") or "").strip() or None
            in_reply_to = _gmail_header(hdrs, "In-Reply-To")
            refs = _gmail_header(hdrs, "References")
            received_at = _gmail_header(hdrs, "Date")
            text, html = _gmail_extract_body(payload)
            snippet = str(data.get("snippet") or "").strip() or None
            if not text and snippet:
                text = snippet
            cc = [x.strip() for x in str(cc_raw or "").replace(";", ",").split(",") if x and x.strip()]
            items.append(
                {
                    "provider_thread_ref": str(data.get("threadId") or in_reply_to or refs or "") or None,
                    "external_message_ref": msg_ref,
                    "subject": subject,
                    "from_address": from_address,
                    "to_address": to_address,
                    "cc": cc,
                    "text": text,
                    "html": html,
                    "received_at": received_at,
                    "headers": {
                        "message_id": msg_ref,
                        "in_reply_to": in_reply_to,
                        "references": refs,
                    },
                    "payload": {
                        "gmail_message_id": data.get("id"),
                        "gmail_thread_id": data.get("threadId"),
                    },
                }
            )
        return OAuthMailboxPollResult(
            ok=True,
            provider="gmail",
            returned=len(items),
            next_cursor=str(listing_json.get("nextPageToken") or "") or None,
            items=items,
            raw={"resultSizeEstimate": listing_json.get("resultSizeEstimate")},
        )


def _graph_recipients(values: Any) -> List[str]:
    out: List[str] = []
    if not isinstance(values, list):
        return out
    for row in values:
        if not isinstance(row, dict):
            continue
        email_addr = row.get("emailAddress")
        if isinstance(email_addr, dict):
            addr = str(email_addr.get("address") or "").strip()
            if addr:
                out.append(addr)
    return out


async def _poll_microsoft_graph(
    *,
    access_token: str,
    limit: int,
    cursor: str | None,
    folder: str = "inbox",
) -> OAuthMailboxPollResult:
    headers = {"Authorization": f"Bearer {access_token}"}
    params: Dict[str, Any] = {
        "$top": max(1, min(int(limit), 200)),
        "$orderby": "receivedDateTime desc",
        "$select": "id,internetMessageId,conversationId,subject,from,toRecipients,ccRecipients,receivedDateTime,bodyPreview,body,inReplyTo",
    }
    folder_key = "sentitems" if (folder or "").strip().lower() == "sent" else "inbox"
    url = cursor or f"https://graph.microsoft.com/v1.0/me/mailFolders/{folder_key}/messages"
    async with httpx.AsyncClient(timeout=25.0) as client:
        listing = await client.get(url, headers=headers, params=None if cursor else params)
        if listing.status_code >= 400:
            raise OAuthMailboxPollError(f"Graph list failed: {listing.status_code} {listing.text}")
        listing_json = listing.json() if listing.headers.get("content-type", "").startswith("application/json") else {}
        rows = listing_json.get("value") if isinstance(listing_json, dict) else []
        if not isinstance(rows, list):
            rows = []
        items: List[Dict[str, Any]] = []
        for data in rows[:limit]:
            if not isinstance(data, dict):
                continue
            from_addr = None
            if isinstance(data.get("from"), dict):
                email_addr = data["from"].get("emailAddress")
                if isinstance(email_addr, dict):
                    from_addr = str(email_addr.get("address") or "").strip() or None
            to_list = _graph_recipients(data.get("toRecipients"))
            cc_list = _graph_recipients(data.get("ccRecipients"))
            body = data.get("body") if isinstance(data.get("body"), dict) else {}
            content_type = str(body.get("contentType") or "").lower()
            body_content = str(body.get("content") or "") or None
            text = str(data.get("bodyPreview") or "").strip() or None
            html = body_content if content_type == "html" else None
            if content_type == "text" and body_content and not text:
                text = body_content
            items.append(
                {
                    "provider_thread_ref": str(data.get("conversationId") or data.get("inReplyTo") or "") or None,
                    "external_message_ref": str(data.get("internetMessageId") or data.get("id") or "").strip() or None,
                    "subject": str(data.get("subject") or "").strip() or None,
                    "from_address": from_addr,
                    "to_address": to_list[0] if to_list else None,
                    "cc": cc_list,
                    "text": text,
                    "html": html,
                    "received_at": str(data.get("receivedDateTime") or "").strip() or None,
                    "headers": {
                        "message_id": str(data.get("internetMessageId") or "").strip() or None,
                        "in_reply_to": str(data.get("inReplyTo") or "").strip() or None,
                    },
                    "payload": {
                        "graph_message_id": data.get("id"),
                        "graph_conversation_id": data.get("conversationId"),
                    },
                }
            )
        next_cursor = str(listing_json.get("@odata.nextLink") or "").strip() or None if isinstance(listing_json, dict) else None
        return OAuthMailboxPollResult(
            ok=True,
            provider="microsoft_graph",
            returned=len(items),
            next_cursor=next_cursor,
            items=items,
            raw={"count": len(rows)},
        )


async def poll_oauth_mailbox_messages(
    *,
    provider: str,
    access_token: str,
    limit: int = 25,
    cursor: str | None = None,
    folder: str = "inbox",
) -> OAuthMailboxPollResult:
    p = (provider or "").strip().lower()
    if p in {"google", "gmail"}:
        return await _poll_gmail(access_token=access_token, limit=limit, cursor=cursor, folder=folder)
    if p in {"microsoft", "microsoft_graph", "graph", "office365"}:
        return await _poll_microsoft_graph(access_token=access_token, limit=limit, cursor=cursor, folder=folder)
    raise OAuthMailboxPollError(f"Unsupported OAuth mailbox provider: {provider}")
