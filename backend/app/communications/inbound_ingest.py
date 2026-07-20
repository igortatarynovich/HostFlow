"""C0.2 — platform inbound ingest: resolve → message → G13 or unresolved queue."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.communications._helpers.sla import _touch_thread_from_message
from backend.app.communications.entity_link import ensure_thread_entity_link
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
    UNRESOLVED_STATUS_OPEN,
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
    external_message_ref: str | None,
) -> CommunicationMessage | None:
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
        .where(
            CommunicationMessage.tenant_id == tenant_id,
            CommunicationMessage.channel == channel,
            CommunicationMessage.external_message_ref.in_(list(variants)),
        )
        .limit(1)
    )
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
    Persist every inbound message.

    Contract: linked to thread/entity **or** explicit unresolved queue row.
    Never drops the message.
    """
    duplicate = await _find_duplicate(
        db,
        tenant_id=inbound.tenant_id,
        channel=inbound.channel,
        external_message_ref=inbound.external_message_ref,
    )
    if duplicate is not None:
        # Reconstruct a lightweight resolution snapshot for the duplicate path.
        resolution = InboundResolution(
            reason="manual",
            thread_id=str(duplicate.thread_id),
            details={"duplicate": True},
        )
        payload = dict(duplicate.payload or {})
        audit = payload.get("inbound_audit") if isinstance(payload.get("inbound_audit"), dict) else {}
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

    resolution = await resolve_inbound(db, inbound)
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
    audit = {
        "schema_version": INBOUND_AUDIT_SCHEMA,
        "resolution_reason": resolution.reason,
        "entity_type": resolution.entity_type,
        "entity_id": resolution.entity_id,
        "correlation_id": correlation_id,
        "matched_outbound_message_id": resolution.matched_outbound_message_id,
        "details": dict(resolution.details or {}),
        "provider": inbound.provider,
        "provider_thread_ref": inbound.provider_thread_ref,
    }

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

    if resolution.has_entity:
        link = await ensure_thread_entity_link(
            db,
            tenant_id=inbound.tenant_id,
            thread_id=str(thread.id),
            entity_type=str(resolution.entity_type),
            entity_id=str(resolution.entity_id),
            is_immutable=True,
        )
        link_ids.append(link.link_id)
        # Keep legacy columns aligned when we have a primary entity.
        if not thread.entity_type:
            thread.entity_type = resolution.entity_type
        if not thread.entity_id:
            thread.entity_id = resolution.entity_id
        await db.flush()
    else:
        # Explicit unresolved queue — message already persisted (no silent drop).
        row = CommunicationInboundUnresolved(
            id=str(uuid4()),
            tenant_id=inbound.tenant_id,
            thread_id=str(thread.id),
            message_id=str(message.id),
            channel=inbound.channel,
            provider=inbound.provider,
            external_message_ref=_clamp(inbound.external_message_ref, 255),
            sender_address=_clamp(inbound.sender_address, 255),
            resolution_reason=resolution.reason,
            status=UNRESOLVED_STATUS_OPEN,
            correlation_id=correlation_id,
            details_json=dict(resolution.details or {}),
        )
        db.add(row)
        await db.flush()
        unresolved_id = str(row.id)
        meta = dict(thread.thread_meta or {})
        meta["inbound_unresolved_id"] = unresolved_id
        meta["inbound_resolution_reason"] = resolution.reason
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
