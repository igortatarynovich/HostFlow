"""Platform outbound executor — SendCommunication (C0.1).

Business entry is Communication Intent → CommunicationCommand →
``prepare_and_send_communication``. This module persists thread + G13 +
message + delivery. Product modules must not invent parallel email writers.

Atomic unit (same session / flush boundary before transport):
  resolve|create thread → G13 origin (+ related) → CommunicationMessage → delivery/outbox
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.communications._helpers.sla import _touch_thread_from_message
from backend.app.communications.command import (
    CommunicationCommand,
    CommunicationOrigin,
    CommunicationRecipient,
    SendCommunicationContent,
    SendCommunicationRequest,
)
from backend.app.communications.entity_link import (
    ThreadEntityLinkError,
    ThreadEntityLinkRequiredError,
    ensure_thread_entity_link,
    get_thread_entity_links,
)
from backend.app.communications.intent import normalize_intent
from backend.app.communications.intent_policy import evaluate_intent_policy
from backend.app.communications.snapshot import build_outbound_snapshot
from backend.app.models.communication import CommunicationMessage, CommunicationThread
from backend.app.communications.delivery_canon import STATUS_QUEUED, STATUS_SENT
from backend.app.communications.delivery_diagnostics import record_delivery_attempt
from backend.app.communications.delivery_errors import REASON_SEND_FAILED
from backend.app.models.communication_delivery import (
    DELIVERY_CHANNEL_EMAIL,
    DELIVERY_PROVIDER_SMTP,
    DELIVERY_STATUS_ACCEPTED,
    DELIVERY_STATUS_QUEUED,
    CommunicationDelivery,
)
from backend.app.models.communication_thread_entity_link import CommunicationThreadEntityLink

SUPPORTED_ORIGIN_TYPES = frozenset(
    {
        "candidate",
        "application",
        "sales_inquiry",
        "client_account",
        "lead",
        "company",
        "service_order",
        "employee",
        "user",
    }
)


class SendCommunicationError(Exception):
    code = "send_communication_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


@dataclass(frozen=True, slots=True)
class SendCommunicationResult:
    thread_id: str
    message_id: str
    delivery_id: str | None
    origin_entity_type: str
    origin_entity_id: str
    created_thread: bool
    idempotent_replay: bool
    entity_link_ids: tuple[str, ...] = ()


TransportFn = Callable[[], Awaitable[Any]]

# Re-export command types for existing imports.
__all__ = [
    "CommunicationCommand",
    "CommunicationOrigin",
    "CommunicationRecipient",
    "SendCommunicationContent",
    "SendCommunicationError",
    "SendCommunicationRequest",
    "SendCommunicationResult",
    "SUPPORTED_ORIGIN_TYPES",
    "TransportFn",
    "find_thread_id_for_origin",
    "send_communication",
]


def _trim(value: Any) -> str:
    return str(value or "").strip()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _message_hash(*, subject: str | None, body: str | None) -> str:
    raw = f"{subject or ''}\n{body or ''}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


async def find_thread_id_for_origin(
    db: AsyncSession,
    *,
    tenant_id: str,
    channel: str,
    origin: CommunicationOrigin,
) -> str | None:
    """Reuse an existing open thread already G13-linked to this origin (work context)."""
    origin = origin.normalized()
    stmt = (
        select(CommunicationThread.id)
        .join(
            CommunicationThreadEntityLink,
            CommunicationThreadEntityLink.thread_id == CommunicationThread.id,
        )
        .where(
            CommunicationThread.tenant_id == str(tenant_id),
            CommunicationThread.channel == str(channel),
            CommunicationThread.is_archived.is_(False),
            CommunicationThreadEntityLink.tenant_id == str(tenant_id),
            CommunicationThreadEntityLink.entity_type == origin.entity_type,
            CommunicationThreadEntityLink.entity_id == origin.entity_id,
        )
        .order_by(CommunicationThread.updated_at.desc())
        .limit(1)
    )
    return await db.scalar(stmt)


async def _load_message_by_idempotency(
    db: AsyncSession,
    *,
    tenant_id: str,
    idempotency_key: str,
) -> CommunicationMessage | None:
    key = _trim(idempotency_key)
    if not key:
        return None
    # Prefer delivery journal unique key when present.
    delivery = await db.scalar(
        select(CommunicationDelivery).where(
            CommunicationDelivery.tenant_id == str(tenant_id),
            CommunicationDelivery.idempotency_key == key,
        )
    )
    if delivery is not None:
        meta = dict(delivery.meta or {})
        mid = _trim(meta.get("communication_message_id"))
        if mid:
            msg = await db.get(CommunicationMessage, mid)
            if msg is not None and str(msg.tenant_id) == str(tenant_id):
                return msg
    # Fallback: scan recent outbound messages for payload key (bounded).
    rows = (
        await db.execute(
            select(CommunicationMessage)
            .where(
                CommunicationMessage.tenant_id == str(tenant_id),
                CommunicationMessage.direction == "outbound",
            )
            .order_by(CommunicationMessage.created_at.desc())
            .limit(200)
        )
    ).scalars().all()
    for msg in rows:
        payload = dict(msg.payload or {})
        if _trim(payload.get("idempotency_key")) == key:
            return msg
    return None


async def send_communication(
    db: AsyncSession,
    request: CommunicationCommand | SendCommunicationRequest,
    *,
    transport: TransportFn | None = None,
    skip_transport: bool = False,
) -> SendCommunicationResult:
    """Platform SendCommunication — thread + G13 + message + delivery (atomic before transport)."""
    origin = request.origin.normalized()
    if not origin.entity_type or not origin.entity_id:
        raise SendCommunicationError(
            "origin.entity_type and origin.entity_id are required",
            details={"reason": "missing_origin"},
        )
    if origin.entity_type not in SUPPORTED_ORIGIN_TYPES:
        raise SendCommunicationError(
            f"unsupported origin entity_type: {origin.entity_type}",
            details={"reason": "unsupported_origin", "entity_type": origin.entity_type},
        )
    content = request.content
    if content is None:
        raise SendCommunicationError(
            "content is required",
            details={"reason": "missing_content"},
        )
    raw_intent = getattr(request, "intent", None)
    if raw_intent is None or (isinstance(raw_intent, str) and not str(raw_intent).strip()):
        raise SendCommunicationError(
            "CommunicationIntent is required; do not call send_communication with template_key alone",
            details={"reason": "intent_required"},
        )
    intent = normalize_intent(raw_intent)
    channel = _trim(request.channel).lower() or "email"
    policy = evaluate_intent_policy(
        intent_key=intent.value,
        entity_type=origin.entity_type,
        channel=channel,
        automation=bool(_trim(getattr(request, "automation_identity", None))),
        template_key=request.template_key,
    )
    if not policy.allowed:
        raise SendCommunicationError(
            policy.reason_message,
            details={
                "reason": policy.reason_code,
                "intent": policy.intent_key,
                "entity_type": origin.entity_type,
                "channel": channel,
                "policy": policy.to_dict(),
            },
        )
    if not request.recipients:
        raise SendCommunicationError(
            "at least one recipient is required",
            details={"reason": "missing_recipients"},
        )
    primary = request.recipients[0]
    address = _trim(primary.address)
    if not address:
        raise SendCommunicationError(
            "recipient address is required",
            details={"reason": "missing_recipient_address"},
        )

    idem = _trim(request.idempotency_key) or None
    if idem:
        existing = await _load_message_by_idempotency(
            db, tenant_id=request.tenant_id, idempotency_key=idem
        )
        if existing is not None:
            links = await get_thread_entity_links(
                db, tenant_id=request.tenant_id, thread_id=str(existing.thread_id)
            )
            if not any(
                lnk.entity_type == origin.entity_type and lnk.entity_id == origin.entity_id
                for lnk in links
            ):
                raise SendCommunicationError(
                    "idempotent message exists but is not linked to origin",
                    details={
                        "reason": "idempotency_origin_mismatch",
                        "message_id": str(existing.id),
                        "thread_id": str(existing.thread_id),
                    },
                )
            delivery_id = _trim((existing.payload or {}).get("delivery_id")) or None
            return SendCommunicationResult(
                thread_id=str(existing.thread_id),
                message_id=str(existing.id),
                delivery_id=delivery_id,
                origin_entity_type=origin.entity_type,
                origin_entity_id=origin.entity_id,
                created_thread=False,
                idempotent_replay=True,
                entity_link_ids=tuple(lnk.link_id for lnk in links),
            )

    created_thread = False
    thread_id = _trim(request.thread_id) or None
    if not thread_id:
        thread_id = await find_thread_id_for_origin(
            db,
            tenant_id=request.tenant_id,
            channel=channel,
            origin=origin,
        )
    if thread_id:
        thread = await db.get(CommunicationThread, thread_id)
        if thread is None or str(thread.tenant_id) != str(request.tenant_id):
            raise SendCommunicationError(
                "thread not found for tenant",
                details={"thread_id": thread_id, "reason": "thread_not_found"},
            )
    else:
        subject = (
            _trim(request.thread_subject)
            or _trim(content.subject)
            or f"{origin.entity_type} · {origin.entity_id[:8]}"
        )
        thread = CommunicationThread(
            id=str(uuid4()),
            tenant_id=str(request.tenant_id),
            own_company_id=_trim(request.own_company_id) or None,
            channel=channel,
            subject=subject[:512],
            status="open",
            direction_hint="outbound",
            entity_type=origin.entity_type,
            entity_id=origin.entity_id,
            owner_id=_trim(request.actor_id) or None,
            participants_json={"recipients": [address]},
            thread_meta={
                "source": "communications.send_communication",
                "intent": intent.value,
                "origin_entity_type": origin.entity_type,
                "origin_entity_id": origin.entity_id,
                **dict(request.meta or {}),
            },
        )
        db.add(thread)
        await db.flush()
        thread_id = str(thread.id)
        created_thread = True

    # G13: origin is mandatory; related entities optional.
    try:
        origin_link = await ensure_thread_entity_link(
            db,
            tenant_id=request.tenant_id,
            thread_id=str(thread_id),
            entity_type=origin.entity_type,
            entity_id=origin.entity_id,
            is_immutable=True,
        )
        link_ids = [origin_link.link_id]
        for related in request.related_entities or ():
            rel = related.normalized()
            if not rel.entity_type or not rel.entity_id:
                continue
            if rel.entity_type == origin.entity_type and rel.entity_id == origin.entity_id:
                continue
            view = await ensure_thread_entity_link(
                db,
                tenant_id=request.tenant_id,
                thread_id=str(thread_id),
                entity_type=rel.entity_type,
                entity_id=rel.entity_id,
                is_immutable=True,
            )
            link_ids.append(view.link_id)
    except ThreadEntityLinkError as exc:
        raise SendCommunicationError(
            str(getattr(exc, "message", None) or exc),
            details={
                **dict(getattr(exc, "details", None) or {}),
                "reason": getattr(exc, "code", "thread_entity_link_error"),
            },
        ) from exc

    links = await get_thread_entity_links(
        db, tenant_id=request.tenant_id, thread_id=str(thread_id)
    )
    if not any(
        lnk.entity_type == origin.entity_type and lnk.entity_id == origin.entity_id
        for lnk in links
    ):
        raise ThreadEntityLinkRequiredError(
            "SendCommunication requires a durable G13 link to origin",
            details={
                "thread_id": str(thread_id),
                "origin": {"entity_type": origin.entity_type, "entity_id": origin.entity_id},
                "reason": "missing_thread_entity_link",
            },
        )

    now = _now()
    snapshot = build_outbound_snapshot(request, policy=policy)
    snapshot_dict = snapshot.to_dict()
    # Prefer snapshot already stamped by prepare_and_send when present.
    meta_snapshot = dict((request.meta or {}).get("snapshot") or {})
    if meta_snapshot.get("schema_version"):
        snapshot_dict = meta_snapshot
    # Stable Message-ID so inbound In-Reply-To / References can join this thread (C0.2).
    msg_uuid = str(uuid4())
    message_id_hdr = f"<hf-{msg_uuid}@hostflow.local>"
    message = CommunicationMessage(
        id=msg_uuid,
        tenant_id=str(request.tenant_id),
        thread_id=str(thread_id),
        own_company_id=_trim(request.own_company_id) or getattr(thread, "own_company_id", None),
        channel=channel,
        message_type=_trim(content.message_type) or ("email" if channel == "email" else "text"),
        direction="outbound",
        sender_type="user",
        sender_id=_trim(request.actor_id) or None,
        recipient_type=_trim(primary.recipient_type) or origin.entity_type,
        recipient_id=_trim(primary.recipient_id) or origin.entity_id,
        recipient_label=_trim(primary.label) or None,
        recipient_address=address,
        subject=_trim(content.subject) or None,
        body_text=_trim(content.body_text) or None,
        body_html=content.body_html,
        delivery_status="queued",
        external_message_ref=message_id_hdr[:255],
        payload={
            "platform": "communications.send_communication.v1",
            "snapshot": snapshot_dict,
            "intent": snapshot_dict.get("intent_key") or intent.value,
            "intent_version": snapshot_dict.get("intent_version"),
            "purpose": _trim(request.purpose) or snapshot_dict.get("purpose"),
            "origin": snapshot_dict.get("origin")
            or {
                "entity_type": origin.entity_type,
                "entity_id": origin.entity_id,
            },
            "origin_entity_type": origin.entity_type,
            "origin_entity_id": origin.entity_id,
            "idempotency_key": idem,
            "template_key": snapshot_dict.get("template_key"),
            "template_version": snapshot_dict.get("template_version"),
            "resolved_links": snapshot_dict.get("links") or [],
            "policy_decision": snapshot_dict.get("policy_decision") or policy.to_dict(),
            "compliance_decision": snapshot_dict.get("compliance_decision") or {},
            "correlation_id": snapshot_dict.get("correlation_id"),
            "source_event_id": snapshot_dict.get("source_event_id"),
            "automation_identity": snapshot_dict.get("automation_identity"),
            "render_variables": snapshot_dict.get("resolved_variables") or {},
            "headers": {"Message-ID": message_id_hdr},
            **{
                k: v
                for k, v in dict(request.meta or {}).items()
                if k
                not in {
                    "source",
                    "intent",
                    "resolved_links",
                    "policy_decision",
                    "render_variables",
                    "snapshot",
                    "headers",
                }
            },
        },
    )
    db.add(message)
    await db.flush()
    _touch_thread_from_message(thread, message)

    delivery_id: str | None = None
    if channel == "email":
        delivery = CommunicationDelivery(
            tenant_id=str(request.tenant_id),
            company_id=_trim(request.own_company_id) or None,
            entity_type=origin.entity_type,
            entity_id=origin.entity_id,
            purpose=_trim(request.delivery_purpose) or _trim(request.purpose) or "outbound_message",
            channel=DELIVERY_CHANNEL_EMAIL,
            provider=DELIVERY_PROVIDER_SMTP,
            recipient_normalized=address[:32],
            template_key=_trim(request.template_key) or "platform_outbound_v1",
            template_version=int(request.template_version or 1),
            message_hash=_message_hash(
                subject=message.subject, body=message.body_text
            ),
            encoding="utf8",
            parts_count=1,
            status=DELIVERY_STATUS_ACCEPTED,
            sent_by_user_id=_trim(request.actor_id) or None,
            queued_at=now,
            sent_at=None,
            idempotency_key=idem or f"send_communication_msg:{message.id}"[:128],
            meta={
                "recipient_email": address,
                "subject": message.subject,
                "communication_message_id": str(message.id),
                "thread_id": str(thread_id),
                "snapshot": snapshot_dict,
                "intent": snapshot_dict.get("intent_key") or intent.value,
                "intent_version": snapshot_dict.get("intent_version"),
                "origin": snapshot_dict.get("origin")
                or {
                    "entity_type": origin.entity_type,
                    "entity_id": origin.entity_id,
                },
                "origin_entity_type": origin.entity_type,
                "origin_entity_id": origin.entity_id,
                "template_key": snapshot_dict.get("template_key"),
                "template_version": snapshot_dict.get("template_version"),
                "resolved_links": snapshot_dict.get("links") or [],
                "policy_decision": snapshot_dict.get("policy_decision") or policy.to_dict(),
                "compliance_decision": snapshot_dict.get("compliance_decision") or {},
                "correlation_id": snapshot_dict.get("correlation_id"),
                "source_event_id": snapshot_dict.get("source_event_id"),
            },
        )
        db.add(delivery)
        await db.flush()
        delivery_id = str(delivery.id)
        message.payload = {**dict(message.payload or {}), "delivery_id": delivery_id}
        await db.flush()

        if transport is not None and not skip_transport:
            attempt_started = datetime.now(timezone.utc)
            try:
                await transport()
            except Exception as exc:  # noqa: BLE001
                detail = str(exc) or type(exc).__name__
                await record_delivery_attempt(
                    db,
                    tenant_id=str(request.tenant_id),
                    message_id=str(message.id),
                    delivery_id=delivery_id,
                    provider=DELIVERY_PROVIDER_SMTP,
                    canonical_result="failed",
                    started_at=attempt_started,
                    finished_at=datetime.now(timezone.utc),
                    reason_code=REASON_SEND_FAILED,
                    raw_message=detail,
                    raw_provider_payload={"error": detail, "type": type(exc).__name__},
                    correlation_id=str(snapshot_dict.get("correlation_id") or "")
                    or None,
                    meta={"source": "send_communication.transport"},
                )
                raise SendCommunicationError(
                    detail or "transport failed",
                    details={
                        "reason": "transport_failed",
                        "reason_code": REASON_SEND_FAILED,
                        "message_id": str(message.id),
                        "thread_id": str(thread_id),
                        "delivery_id": delivery_id,
                    },
                ) from exc
            await record_delivery_attempt(
                db,
                tenant_id=str(request.tenant_id),
                message_id=str(message.id),
                delivery_id=delivery_id,
                provider=DELIVERY_PROVIDER_SMTP,
                canonical_result=STATUS_SENT,
                started_at=attempt_started,
                finished_at=datetime.now(timezone.utc),
                correlation_id=str(snapshot_dict.get("correlation_id") or "") or None,
                meta={"source": "send_communication.transport"},
            )
        elif skip_transport:
            # Outbox-only: message + delivery queued; worker/callback advances status.
            delivery.status = DELIVERY_STATUS_QUEUED
            message.delivery_status = STATUS_QUEUED
            await db.flush()
    elif transport is not None and not skip_transport:
        try:
            await transport()
        except Exception as exc:  # noqa: BLE001
            message.delivery_status = "failed"
            detail = str(exc) or type(exc).__name__
            message.error_message = detail
            # No CommunicationDelivery row for non-email channels yet —
            # still require a reason code on the message payload for operators.
            payload = dict(message.payload or {})
            payload["diagnostics"] = {
                "status": "failed",
                "reason_code": REASON_SEND_FAILED,
                "retryable": True,
                "safe_message": detail[:200],
            }
            message.payload = payload
            await db.flush()
            raise SendCommunicationError(
                message.error_message or "transport failed",
                details={
                    "reason": "transport_failed",
                    "reason_code": REASON_SEND_FAILED,
                    "message_id": str(message.id),
                    "thread_id": str(thread_id),
                },
            ) from exc
        message.delivery_status = "sent"
        message.sent_at = now
        await db.flush()

    return SendCommunicationResult(
        thread_id=str(thread_id),
        message_id=str(message.id),
        delivery_id=delivery_id,
        origin_entity_type=origin.entity_type,
        origin_entity_id=origin.entity_id,
        created_thread=created_thread,
        idempotent_replay=False,
        entity_link_ids=tuple(link_ids),
    )
