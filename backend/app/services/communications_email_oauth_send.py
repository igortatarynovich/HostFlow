from __future__ import annotations

import base64
from email.message import EmailMessage
from typing import Any, Dict, Optional

import httpx


class OAuthMailboxSendError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _build_raw_rfc822_message(
    *,
    to: str,
    subject: str,
    body_text: str,
    body_html: str | None = None,
    from_address: str | None = None,
    reply_to: str | None = None,
) -> str:
    msg = EmailMessage()
    if from_address:
        msg["From"] = from_address
    msg["To"] = to
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.set_content(body_text or "")
    if body_html:
        msg.add_alternative(body_html, subtype="html")
    raw = msg.as_bytes()
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


async def _send_gmail_message(
    *,
    access_token: str,
    to: str,
    subject: str,
    body_text: str,
    body_html: str | None = None,
    from_address: str | None = None,
    reply_to: str | None = None,
) -> Dict[str, Any]:
    raw = _build_raw_rfc822_message(
        to=to,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        from_address=from_address,
        reply_to=reply_to,
    )
    async with httpx.AsyncClient(timeout=25.0) as client:
        resp = await client.post(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json={"raw": raw},
        )
    if resp.status_code >= 400:
        raise OAuthMailboxSendError(f"Gmail send failed: {resp.status_code} {resp.text}", status_code=resp.status_code)
    payload = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    return {
        "provider": "gmail",
        "message_ref": str(payload.get("id") or "").strip() or None,
        "thread_ref": str(payload.get("threadId") or "").strip() or None,
        "payload": payload if isinstance(payload, dict) else {},
    }


async def _send_graph_message(
    *,
    access_token: str,
    to: str,
    subject: str,
    body_text: str,
    body_html: str | None = None,
    from_address: str | None = None,
    reply_to: str | None = None,
) -> Dict[str, Any]:
    body_content_type = "HTML" if body_html else "Text"
    body_content = body_html if body_html else body_text
    message: Dict[str, Any] = {
        "subject": subject,
        "body": {"contentType": body_content_type, "content": body_content},
        "toRecipients": [{"emailAddress": {"address": to}}],
    }
    if from_address:
        message["from"] = {"emailAddress": {"address": from_address}}
    if reply_to:
        message["replyTo"] = [{"emailAddress": {"address": reply_to}}]
    async with httpx.AsyncClient(timeout=25.0) as client:
        resp = await client.post(
            "https://graph.microsoft.com/v1.0/me/sendMail",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json={"message": message, "saveToSentItems": True},
        )
    if resp.status_code >= 400:
        raise OAuthMailboxSendError(f"Graph send failed: {resp.status_code} {resp.text}", status_code=resp.status_code)
    return {
        "provider": "microsoft_graph",
        "message_ref": None,
        "thread_ref": None,
        "payload": {"status_code": resp.status_code},
    }


async def send_oauth_email_message(
    *,
    provider: str,
    access_token: str,
    to: str,
    subject: str,
    body_text: str,
    body_html: str | None = None,
    from_address: str | None = None,
    reply_to: str | None = None,
) -> Dict[str, Any]:
    p = (provider or "").strip().lower()
    if p in {"gmail", "google"}:
        return await _send_gmail_message(
            access_token=access_token,
            to=to,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            from_address=from_address,
            reply_to=reply_to,
        )
    if p in {"microsoft_graph", "microsoft", "graph", "office365"}:
        return await _send_graph_message(
            access_token=access_token,
            to=to,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            from_address=from_address,
            reply_to=reply_to,
        )
    raise OAuthMailboxSendError(f"Unsupported outbound provider: {provider}")
