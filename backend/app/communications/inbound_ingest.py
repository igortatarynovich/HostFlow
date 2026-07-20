"""C0.2 — platform inbound ingest: resolve → message → G13 or unresolved queue.

Transactional contract (same session / flush boundary before caller commit):
  idempotency check → resolve → ensure thread → **create CommunicationMessage**
  → G13 **or** unresolved queue row.

Optional downstream (auto-assign, UOS) must run only after this returns.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.communications._helpers.sla import _touch_thread_from_message
from backend.app.communications.entity_link import (
    _normalize_entity_type,
    ensure_thread_entity_link,
)
from backend.app.communications.inbound_dto import (
    INBOUND_AUDIT_SCHEMA,
    InboundIngestResult,
    InboundResolution,
    NormalizedInboundMessage,
)
from backend.app.communications.inbound_normalize import normalize_message_id
from backend.app.communications.inbound_resolve import resolve_inbound
from backend.app.models.communication import CommunicationMessage, CommunicationThread
from backend.app.models.communication_inbound_unresolved import (
    REASON_RESOLVER_ERROR,
    UNRESOLVED_STATUS_OPEN,
    UNRESOLVED_STATUS_RESOLVED,
    CommunicationInboundUnresolved,
)
from backend.app.models.tenant import Tenant


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _trim(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _clamp(value: Any, max_len: int) -> str | None:
    text = _trim(value)
    if text is None:
        return None
    return text[:max_len]


async def _find_duplicate(
    db: AsyncSession,
    *,
    tenant_id: str,
    channel: str,
    channel_account_id: str | None,
    external_message_ref: str | None,
) -> CommunicationMessage | None:
    """Idempotency key: tenant + channel + channel_account + provider message id."""
    ref = _trim(external_message_ref)
    if not ref:
        return None
    variants = {ref}
    norm = normalize_message_id(ref)
    if norm:
        variants.add(norm)
        variants.add(norm.strip("<>"))
    stmt = (
        sa.select(CommunicationMessage)
        .join(
            CommunicationThread,
            CommunicationThread.id == CommunicationMessage.thread_id,
        )
        .where(
            CommunicationMessage.tenant_id == tenant_id,
            CommunicationMessage.channel == channel,
            CommunicationMessage.external_message_ref.in_(list(variants)),
        )
        .limit(1)
    )
    account = _trim(channel_account_id)
    if account:
        stmt = stmt.where(CommunicationThread.channel_account_id == account)
    else:
        stmt = stmt.where(CommunicationThread.channel_account_id.is_(None))
    return (await db.execute(stmt)).scalars().first()


async def _ensure_thread(
    db: AsyncSession,
    *,
    inbound: NormalizedInboundMessage,
    resolution: InboundResolution,
    own_company_id: str | None,
) -> tuple[CommunicationThread, bool]:
    if resolution.thread_id:
        thread = await db.get(CommunicationThread, resolution.thread_id)
        if thread is not None and str(thread.tenant_id) == inbound.tenant_id:
            return thread, False

    participants: dict[str, Any] = {
        "senders": [inbound.sender_address] if inbound.sender_address else [],
        "recipients": [inbound.recipient_address] if inbound.recipient_address else [],
        "cc": list(inbound.cc),
        "bcc": list(inbound.bcc),
    }
    thread = CommunicationThread(
        tenant_id=inbound.tenant_id,
        own_company_id=own_company_id,
        channel=inbound.channel,
        channel_account_id=inbound.channel_account_id,
        channel_thread_ref=inbound.provider_thread_ref,
        subject=inbound.subject,
        status="open",
        direction_hint="inbound",
        entity_type=resolution.entity_type,
        entity_id=resolution.entity_id,
        linked_candidate_id=(
            inbound.linked_candidate_id
            if inbound.linked_candidate_id
            else (resolution.entity_id if resolution.entity_type == "candidate" else None)
        ),
        linked_company_id=inbound.linked_company_id,
        priority="normal",
        participants_json=participants,
        tags_json=[],
        thread_meta={
            "provider": inbound.provider,
            "inbound_resolution_reason": resolution.reason,
        },
    )
    db.add(thread)
    await db.flush()
    return thread, True


def _merge_participants(thread: CommunicationThread, inbound: NormalizedInboundMessage) -> None:
    participants = dict(thread.participants_json or {})
    senders = participants.get("senders")
    if not isinstance(senders, list):
        senders = []
    if inbound.sender_address and inbound.sender_address not in senders:
        senders.append(inbound.sender_address)
    participants["senders"] = senders
    recipients = participants.get("recipients")
    if not isinstance(recipients, list):
        recipients = []
    if inbound.recipient_address and inbound.recipient_address not in recipients:
        recipients.append(inbound.recipient_address)
    participants["recipients"] = recipients
    if inbound.cc:
        participants["cc"] = list(inbound.cc)
    thread.participants_json = participants
    if inbound.subject and not thread.subject:
        thread.subject = inbound.subject
    if inbound.provider_thread_ref and not thread.channel_thread_ref:
        thread.channel_thread_ref = inbound.provider_thread_ref


async def ingest_inbound_message(
    db: AsyncSession,
    *,
    inbound: NormalizedInboundMessage,
    own_company_id: str | None = None,
    tenant: Tenant | None = None,
) -> InboundIngestResult:
    """
    Persist every inbound message in one transactional unit with the caller.

    Contract: linked to thread/entity **or** explicit unresolved queue row.
    Never drops the message. Caller commits after optional side effects.
    """
    duplicate = await _find_duplicate(
        db,
        tenant_id=inbound.tenant_id,
        channel=inbound.channel,
        channel_account_id=inbound.channel_account_id,
        external_message_ref=inbound.external_message_ref,
    )
    if duplicate is not None:
        resolution = InboundResolution(
            reason="manual",
            thread_id=str(duplicate.thread_id),
            details={"duplicate": True},
        )
        payload = dict(duplicate.payload or {})
        audit = (
            payload.get("inbound_audit")
            if isinstance(payload.get("inbound_audit"), dict)
            else {}
        )
        reason = str(audit.get("resolution_reason") or "manual")
        if reason in {
            "reply_headers",
            "provider_thread",
            "known_participant",
            "entity_contact",
            "manual",
            "unresolved",
        }:
            resolution = InboundResolution(
                reason=reason,  # type: ignore[arg-type]
                thread_id=str(duplicate.thread_id),
                entity_type=_trim(audit.get("entity_type")),
                entity_id=_trim(audit.get("entity_id")),
                correlation_id=_trim(audit.get("correlation_id")),
                details={"duplicate": True},
            )
        return InboundIngestResult(
            thread_id=str(duplicate.thread_id),
            message_id=str(duplicate.id),
            created_thread=False,
            duplicate_message=True,
            resolution=resolution,
            correlation_id=resolution.correlation_id,
        )

    try:
        resolution = await resolve_inbound(db, inbound)
    except Exception as exc:  # noqa: BLE001 — never lose inbound on resolver failure
        resolution = InboundResolution(
            reason="unresolved",
            details={
                "reason_code": REASON_RESOLVER_ERROR,
                "error": str(exc) or type(exc).__name__,
                "sender_address": inbound.sender_address,
            },
        )

    thread, created_thread = await _ensure_thread(
        db,
        inbound=inbound,
        resolution=resolution,
        own_company_id=own_company_id,
    )
    if not created_thread:
        _merge_participants(thread, inbound)
        if resolution.entity_type and not thread.entity_type:
            thread.entity_type = resolution.entity_type
        if resolution.entity_id and not thread.entity_id:
            thread.entity_id = resolution.entity_id
        if own_company_id and not getattr(thread, "own_company_id", None):
            thread.own_company_id = own_company_id

    received_at = inbound.received_at or _now()
    correlation_id = resolution.correlation_id or str(uuid4())
    reason_code = _trim((resolution.details or {}).get("reason_code")) or resolution.reason
    audit = {
        "schema_version": INBOUND_AUDIT_SCHEMA,
        "resolution_reason": resolution.reason,
        "reason_code": reason_code,
        "entity_type": resolution.entity_type,
        "entity_id": resolution.entity_id,
        "correlation_id": correlation_id,
        "matched_outbound_message_id": resolution.matched_outbound_message_id,
        "details": dict(resolution.details or {}),
        "provider": inbound.provider,
        "provider_thread_ref": inbound.provider_thread_ref,
        "channel_account_id": inbound.channel_account_id,
    }

    # Durable message first — before optional downstream side effects in the route.
    message = CommunicationMessage(
        tenant_id=inbound.tenant_id,
        thread_id=str(thread.id),
        own_company_id=getattr(thread, "own_company_id", None) or own_company_id,
        channel=inbound.channel,
        message_type="email" if inbound.channel == "email" else "text",
        direction="inbound",
        sender_type="external",
        sender_label=inbound.sender_label,
        sender_address=inbound.sender_address,
        recipient_type="tenant",
        recipient_label=inbound.recipient_label,
        recipient_address=inbound.recipient_address,
        subject=inbound.subject,
        body_text=inbound.body_text,
        body_html=inbound.body_html,
        attachments_json=list(inbound.attachments or []),
        payload={
            **dict(inbound.payload or {}),
            "headers": dict(inbound.headers or {}),
            "cc": list(inbound.cc),
            "bcc": list(inbound.bcc),
            "provider": inbound.provider,
            "platform": "communications.inbound_ingest.v1",
            "inbound_audit": audit,
            "correlation_id": correlation_id,
        },
        external_message_ref=_clamp(inbound.external_message_ref, 255),
        delivery_status="delivered",
        sent_at=received_at,
        delivered_at=received_at,
        read_at=None,
        is_internal_note=False,
    )
    db.add(message)
    await db.flush()

    if tenant is not None:
        _touch_thread_from_message(thread, message, tenant=tenant)
    else:
        _touch_thread_from_message(thread, message)

    link_ids: list[str] = []
    unresolved_id: str | None = None

    if resolution.has_entity and resolution.reason != "unresolved":
        link = await ensure_thread_entity_link(
            db,
            tenant_id=inbound.tenant_id,
            thread_id=str(thread.id),
            entity_type=str(resolution.entity_type),
            entity_id=str(resolution.entity_id),
            is_immutable=True,
        )
        link_ids.append(link.link_id)
        if not thread.entity_type:
            thread.entity_type = resolution.entity_type
        if not thread.entity_id:
            thread.entity_id = resolution.entity_id
        await db.flush()
    else:
        # Same transactional boundary as message (caller commit).
        row = CommunicationInboundUnresolved(
            id=str(uuid4()),
            tenant_id=inbound.tenant_id,
            thread_id=str(thread.id),
            message_id=str(message.id),
            channel=inbound.channel,
            provider=inbound.provider,
            external_message_ref=_clamp(inbound.external_message_ref, 255),
            sender_address=_clamp(inbound.sender_address, 255),
            resolution_reason=reason_code or "unresolved",
            status=UNRESOLVED_STATUS_OPEN,
            correlation_id=correlation_id,
            details_json=dict(resolution.details or {}),
        )
        db.add(row)
        await db.flush()
        unresolved_id = str(row.id)
        meta = dict(thread.thread_meta or {})
        meta["inbound_unresolved_id"] = unresolved_id
        meta["inbound_resolution_reason"] = reason_code or resolution.reason
        thread.thread_meta = meta
        await db.flush()

    return InboundIngestResult(
        thread_id=str(thread.id),
        message_id=str(message.id),
        created_thread=created_thread,
        duplicate_message=False,
        resolution=resolution,
        entity_link_ids=tuple(link_ids),
        unresolved_id=unresolved_id,
        correlation_id=correlation_id,
    )


async def mark_inbound_unresolved_resolved(
    db: AsyncSession,
    *,
    tenant_id: str,
    unresolved_id: str,
    actor_user_id: str,
    entity_type: str,
    entity_id: str,
    thread_id: str | None = None,
) -> CommunicationInboundUnresolved:
    """Manual resolution audit: who / when / which entity+thread. Retains the queue row."""
    row = await db.get(CommunicationInboundUnresolved, unresolved_id)
    if row is None or str(row.tenant_id) != str(tenant_id):
        raise ValueError("unresolved inbound row not found")
    et = _normalize_entity_type(entity_type)
    eid = _trim(entity_id)
    if not et or not eid:
        raise ValueError("entity_type and entity_id are required")
    target_thread = _trim(thread_id) or str(row.thread_id)
    await ensure_thread_entity_link(
        db,
        tenant_id=str(tenant_id),
        thread_id=target_thread,
        entity_type=et,
        entity_id=eid,
        is_immutable=True,
    )
    row.status = UNRESOLVED_STATUS_RESOLVED
    row.resolved_by_user_id = _trim(actor_user_id)
    row.resolved_at = _now()
    row.resolved_entity_type = et
    row.resolved_entity_id = eid
    row.resolved_thread_id = target_thread
    details = dict(row.details_json or {})
    details["manual_resolution"] = {
        "resolved_by_user_id": row.resolved_by_user_id,
        "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
        "resolved_entity_type": et,
        "resolved_entity_id": eid,
        "resolved_thread_id": target_thread,
    }
    row.details_json = details
    await db.flush()
    return row
