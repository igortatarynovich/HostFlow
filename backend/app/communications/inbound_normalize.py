"""C0.2 — provider payload → NormalizedInboundMessage."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Mapping

from backend.app.communications.inbound_dto import NormalizedInboundMessage

_MSG_ID_RE = re.compile(r"<[^>]+>|[^<\s,;]+@[^>\s,;]+")


def _trim(value: Any, *, max_len: int | None = None) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if max_len is not None and len(text) > max_len:
        return text[:max_len]
    return text


def normalize_message_id(value: Any) -> str | None:
    """Normalize RFC822 Message-ID / In-Reply-To token for durable lookup."""
    raw = _trim(value)
    if not raw:
        return None
    inner = raw
    if inner.startswith("<") and inner.endswith(">") and len(inner) > 2:
        inner = inner[1:-1].strip()
    if not inner:
        return None
    return f"<{inner.lower()}>"


def looks_like_message_id(value: Any) -> bool:
    """True when value resembles an RFC822 Message-ID (not a Gmail threadId)."""
    raw = _trim(value)
    if not raw or "@" not in raw:
        return False
    # Conversation ids from Graph/Gmail rarely look like addr@domain.tld.
    if raw.startswith("<") and raw.endswith(">"):
        return True
    parts = raw.split("@", 1)
    return len(parts) == 2 and "." in parts[1] and " " not in raw


def extract_reply_message_ids(headers: Mapping[str, Any] | None) -> list[str]:
    """Ordered unique Message-IDs from In-Reply-To then References."""
    hdrs = dict(headers or {})
    lowered = {str(k).strip().lower(): v for k, v in hdrs.items()}
    chunks: list[str] = []
    for key in ("in-reply-to", "in_reply_to", "references"):
        val = lowered.get(key)
        if val is None:
            continue
        if isinstance(val, (list, tuple)):
            chunks.extend(str(x) for x in val if x is not None)
        else:
            chunks.append(str(val))
    found: list[str] = []
    seen: set[str] = set()
    for chunk in chunks:
        for match in _MSG_ID_RE.findall(chunk):
            norm = normalize_message_id(match)
            if norm and norm not in seen:
                seen.add(norm)
                found.append(norm)
    return found


def _header_map(headers: Mapping[str, Any] | None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in dict(headers or {}).items():
        k = _trim(key)
        if k:
            out[k] = value
    return out


def normalize_email_fields(
    *,
    tenant_id: str,
    channel_account_id: str | None = None,
    provider: str | None = None,
    provider_thread_ref: str | None = None,
    external_message_ref: str | None = None,
    subject: str | None = None,
    from_address: str | None = None,
    from_name: str | None = None,
    to_address: str | None = None,
    to_name: str | None = None,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    text: str | None = None,
    html: str | None = None,
    received_at: datetime | None = None,
    headers: Mapping[str, Any] | None = None,
    payload: Mapping[str, Any] | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    linked_candidate_id: str | None = None,
    linked_company_id: str | None = None,
) -> NormalizedInboundMessage:
    hdrs = _header_map(headers)
    msg_id = normalize_message_id(external_message_ref) or normalize_message_id(
        hdrs.get("Message-ID") or hdrs.get("message-id") or hdrs.get("Message-Id")
    )
    thread_ref = _trim(provider_thread_ref, max_len=255)

    # Legacy IMAP poll stored In-Reply-To as provider_thread_ref. Promote to headers
    # and clear thread_ref so reply_headers resolution owns Message-ID matching.
    if thread_ref and looks_like_message_id(thread_ref):
        if not extract_reply_message_ids(hdrs):
            hdrs = {**hdrs, "In-Reply-To": thread_ref}
        thread_ref = None

    return NormalizedInboundMessage(
        tenant_id=str(tenant_id),
        channel="email",
        provider=_trim(provider, max_len=64),
        channel_account_id=_trim(channel_account_id, max_len=36),
        provider_thread_ref=thread_ref,
        external_message_ref=msg_id or _trim(external_message_ref, max_len=255),
        subject=_trim(subject, max_len=512),
        sender_address=_trim(from_address, max_len=255),
        sender_label=_trim(from_name, max_len=255),
        recipient_address=_trim(to_address, max_len=255),
        recipient_label=_trim(to_name, max_len=255),
        body_text=text,
        body_html=html,
        received_at=received_at,
        headers=hdrs,
        payload=dict(payload or {}),
        hinted_entity_type=_trim(entity_type, max_len=64),
        hinted_entity_id=_trim(entity_id, max_len=120),
        linked_candidate_id=_trim(linked_candidate_id, max_len=36),
        linked_company_id=_trim(linked_company_id, max_len=36),
        cc=tuple(x for x in (_trim(v, max_len=255) for v in (cc or [])) if x),
        bcc=tuple(x for x in (_trim(v, max_len=255) for v in (bcc or [])) if x),
    )


def normalize_generic_fields(
    *,
    tenant_id: str,
    channel: str,
    channel_account_id: str | None = None,
    provider: str | None = None,
    provider_thread_ref: str | None = None,
    provider_chat_ref: str | None = None,
    external_message_ref: str | None = None,
    sender_address: str | None = None,
    sender_label: str | None = None,
    recipient_address: str | None = None,
    recipient_label: str | None = None,
    subject: str | None = None,
    text: str | None = None,
    html: str | None = None,
    received_at: datetime | None = None,
    headers: Mapping[str, Any] | None = None,
    payload: Mapping[str, Any] | None = None,
    attachments: list[dict[str, Any]] | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    linked_candidate_id: str | None = None,
    linked_company_id: str | None = None,
) -> NormalizedInboundMessage:
    channel_norm = (_trim(channel) or "").lower()
    thread_ref = _trim(provider_thread_ref, max_len=255) or _trim(
        provider_chat_ref, max_len=255
    )
    return NormalizedInboundMessage(
        tenant_id=str(tenant_id),
        channel=channel_norm,
        provider=_trim(provider, max_len=64),
        channel_account_id=_trim(channel_account_id, max_len=36),
        provider_thread_ref=thread_ref,
        external_message_ref=_trim(external_message_ref, max_len=255),
        subject=_trim(subject, max_len=512),
        sender_address=_trim(sender_address, max_len=255),
        sender_label=_trim(sender_label, max_len=255),
        recipient_address=_trim(recipient_address, max_len=255),
        recipient_label=_trim(recipient_label, max_len=255),
        body_text=text,
        body_html=html,
        received_at=received_at,
        headers=_header_map(headers),
        payload=dict(payload or {}),
        attachments=[dict(x) for x in (attachments or []) if isinstance(x, dict)],
        hinted_entity_type=_trim(entity_type, max_len=64),
        hinted_entity_id=_trim(entity_id, max_len=120),
        linked_candidate_id=_trim(linked_candidate_id, max_len=36),
        linked_company_id=_trim(linked_company_id, max_len=36),
    )
