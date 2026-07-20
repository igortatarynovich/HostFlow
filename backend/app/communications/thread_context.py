"""C1 / C1.1 — ThreadContext: Workspace read model (not a domain SoT).

Assembled from canonical sources for interactive Composer / Workspace UI only:

* Thread (work object)
* G13 entity links
* participants (message projection)
* queue membership projection
* CapabilityResolver / Intent Policy
* delivery summary (diagnostics projection)
* draft (thread_meta projection)

ThreadContext never owns assignee/unread/capabilities/delivery as business truth.
It aggregates and returns them for Workspace presentation.

Not an entry path for Campaign / Automation / server-side bulk — those emit
CommunicationIntent / CommunicationCommand via their own adapters.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Bound participant/recipient scan — ThreadContext scales with Thread, not Message history.
CONTEXT_MESSAGE_SCAN_LIMIT = 40
CONTEXT_VERSION = 1

from backend.app.communications.capability_resolver import DefaultCapabilityResolver
from backend.app.communications.command import CommunicationOrigin
from backend.app.communications.intent import CommunicationIntent
from backend.app.communications.thread_queues import (
    CLOSED_THREAD_STATUSES,
    QUEUE_ASSIGNED_TO_ME,
    QUEUE_CLOSED,
    QUEUE_DELIVERY_ERRORS,
    QUEUE_NEW_INBOUND,
    QUEUE_REQUIRES_REPLY,
    QUEUE_SLA_BREACHED,
    QUEUE_UNASSIGNED,
    QUEUE_UNRESOLVED,
    QUEUE_WAITING_FOR_REPLY,
)
from backend.app.models.communication import CommunicationMessage, CommunicationThread
from backend.app.models.communication_inbound_unresolved import (
    UNRESOLVED_STATUS_OPEN,
    CommunicationInboundUnresolved,
)
from backend.app.models.communication_thread_next_action import (
    NEXT_ACTION_STATUS_ACTIVE,
    CommunicationThreadNextAction,
)


@dataclass(slots=True)
class ThreadContext:
    """Workspace read model — four blocks, no persistence of its own."""

    identity: dict[str, Any]
    work_state: dict[str, Any]
    capabilities: dict[str, Any]
    workspace: dict[str, Any]
    source: str = "communication.thread_context.v1"
    context_version: int = CONTEXT_VERSION
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _queue_memberships_from_thread(
    thread: CommunicationThread,
    *,
    actor_user_id: str | None,
    has_delivery_error: bool,
    has_open_unresolved: bool,
    sla_breached: bool = False,
) -> list[str]:
    """In-memory queue projection — no N+1 SQL per queue key."""
    active: list[str] = []
    unread = int(thread.unread_count or 0)
    archived = bool(thread.is_archived)
    status = str(thread.status or "").strip().lower()
    assignee = thread.assignee_id
    actor = str(actor_user_id or "").strip() or None
    inbound = thread.last_inbound_at
    outbound = thread.last_outbound_at

    if unread > 0:
        active.append(QUEUE_NEW_INBOUND)
    if actor and assignee == actor:
        active.append(QUEUE_ASSIGNED_TO_ME)
    if assignee is None:
        active.append(QUEUE_UNASSIGNED)
    if archived or status in CLOSED_THREAD_STATUSES:
        active.append(QUEUE_CLOSED)
    if not archived and inbound is not None and (outbound is None or inbound > outbound):
        active.append(QUEUE_REQUIRES_REPLY)
    if not archived and outbound is not None and (inbound is None or outbound >= inbound):
        active.append(QUEUE_WAITING_FOR_REPLY)
    if has_delivery_error and not archived:
        active.append(QUEUE_DELIVERY_ERRORS)
    if has_open_unresolved:
        active.append(QUEUE_UNRESOLVED)
    if sla_breached and not archived:
        active.append(QUEUE_SLA_BREACHED)
    return active


async def _delivery_and_unresolved_flags(
    db: AsyncSession, *, tenant_id: str, thread_id: str
) -> tuple[bool, bool, dict[str, Any] | None]:
    """One cheap pass: failed outbound summary + open unresolved flag."""
    failed = (
        await db.execute(
            select(CommunicationMessage)
            .where(
                CommunicationMessage.tenant_id == tenant_id,
                CommunicationMessage.thread_id == thread_id,
                CommunicationMessage.direction == "outbound",
                CommunicationMessage.delivery_status.in_(
                    ("failed", "undeliverable", "bounced", "rejected")
                ),
            )
            .order_by(CommunicationMessage.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    unresolved_hit = (
        await db.execute(
            select(CommunicationInboundUnresolved.id)
            .where(
                CommunicationInboundUnresolved.tenant_id == tenant_id,
                CommunicationInboundUnresolved.thread_id == thread_id,
                CommunicationInboundUnresolved.status == UNRESOLVED_STATUS_OPEN,
            )
            .limit(1)
        )
    ).scalar_one_or_none()

    summary: dict[str, Any] | None = None
    if failed is not None:
        # Projection only — do not pull full diagnostics timeline here.
        meta = _as_dict(getattr(failed, "payload", None))
        diag = _as_dict(meta.get("diagnostics")) if meta else {}
        summary = {
            "message_id": str(failed.id),
            "status": failed.delivery_status,
            "reason_code": diag.get("reason_code") or None,
            "retryable": diag.get("retryable"),
            "next_retry_at": diag.get("next_retry_at"),
            "safe_message": failed.error_message,
        }
    return failed is not None, unresolved_hit is not None, summary


def _participants_and_recipient(
    messages: list[CommunicationMessage],
) -> tuple[list[dict[str, Any]], str | None]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    recipient_default: str | None = None
    for m in messages:
        if recipient_default is None and m.direction == "outbound" and m.recipient_address:
            recipient_default = str(m.recipient_address)
        for role, addr, label in (
            ("sender", m.sender_address, m.sender_label),
            ("recipient", m.recipient_address, m.recipient_label),
        ):
            key = f"{role}:{(addr or label or '').strip().lower()}"
            if not key.endswith(":") and key not in seen:
                seen.add(key)
                out.append(
                    {
                        "role": role,
                        "address": addr,
                        "label": label,
                        "direction": m.direction,
                    }
                )
    if recipient_default is None:
        for m in messages:
            if m.direction == "inbound" and m.sender_address:
                recipient_default = str(m.sender_address)
                break
    return out[:12], recipient_default


async def build_thread_context(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread: CommunicationThread,
    actor_user_id: str | None = None,
) -> ThreadContext:
    from backend.app.communications.entity_link import get_thread_entity_links

    thread_id = str(thread.id)
    links = await get_thread_entity_links(
        db, tenant_id=tenant_id, thread_id=thread_id
    )
    linked = [lnk.to_dict() for lnk in links]
    if links:
        origin = CommunicationOrigin(
            entity_type=links[0].entity_type, entity_id=links[0].entity_id
        )
    else:
        origin = CommunicationOrigin(
            entity_type=str(thread.entity_type or "lead"),
            entity_id=str(thread.entity_id or thread.id),
        )

    # Capability resolve is sync registry lookup today — keep await for Protocol.
    caps = await DefaultCapabilityResolver().resolve(
        tenant_id=tenant_id,
        origin=origin,
        actor_id=actor_user_id,
    )
    thread_channel = str(thread.channel or "").strip().lower()
    allowed_channels = list(caps.allowed_channels)
    if thread_channel and thread_channel in allowed_channels:
        allowed_channels = [thread_channel]
    elif thread_channel and not allowed_channels:
        allowed_channels = []

    allowed_intents = list(caps.allowed_intents)
    default_intent = CommunicationIntent.MANUAL_OUTBOUND.value
    if default_intent not in allowed_intents:
        default_intent = allowed_intents[0] if allowed_intents else None

    recent = (
        await db.execute(
            select(CommunicationMessage)
            .where(
                CommunicationMessage.tenant_id == tenant_id,
                CommunicationMessage.thread_id == thread_id,
            )
            .order_by(CommunicationMessage.created_at.desc())
            .limit(CONTEXT_MESSAGE_SCAN_LIMIT)
        )
    ).scalars().all()
    participants, recipient_default = _participants_and_recipient(list(recent))

    has_delivery_error, has_open_unresolved, delivery_summary = (
        await _delivery_and_unresolved_flags(
            db, tenant_id=tenant_id, thread_id=thread_id
        )
    )

    active_na = (
        await db.execute(
            select(CommunicationThreadNextAction)
            .where(
                CommunicationThreadNextAction.tenant_id == tenant_id,
                CommunicationThreadNextAction.thread_id == thread_id,
                CommunicationThreadNextAction.status == NEXT_ACTION_STATUS_ACTIVE,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    next_action_proj = active_na.to_projection() if active_na is not None else None

    from backend.app.communications.sla_clock import project_thread_sla

    sla_proj = (
        await project_thread_sla(db, tenant_id=tenant_id, thread=thread)
    ).to_dict()

    can_compose = bool(allowed_intents) and bool(allowed_channels) and not thread.is_archived
    defaults = {
        "channel": thread_channel or (allowed_channels[0] if allowed_channels else None),
        "intent": default_intent,
        "recipient_address": recipient_default,
        "subject": thread.subject,
        "send_immediately": True,
        "internal_note_allowed": True,
    }
    meta = _as_dict(thread.thread_meta)
    draft = _as_dict(meta.get("composer_draft"))

    return ThreadContext(
        identity={
            "thread": {
                "id": thread_id,
                "channel": str(thread.channel or ""),
                "status": str(thread.status or ""),
                "subject": thread.subject,
            },
            "linked_entities": linked,
            "participants": participants,
            "origin": {
                "entity_type": caps.entity_type,
                "entity_id": caps.entity_id,
            },
        },
        work_state={
            "assignee_id": thread.assignee_id,
            "owner_id": getattr(thread, "owner_id", None),
            "unread_count": int(thread.unread_count or 0),
            "is_archived": bool(thread.is_archived),
            "work_version": int(getattr(thread, "work_version", 1) or 1),
            "priority": str(getattr(thread, "priority", None) or "normal"),
            "tags_json": list(getattr(thread, "tags_json", None) or []),
            "thread_meta": dict(getattr(thread, "thread_meta", None) or {}),
            "linked_candidate_id": getattr(thread, "linked_candidate_id", None),
            "linked_company_id": getattr(thread, "linked_company_id", None),
            "active_queues": _queue_memberships_from_thread(
                thread,
                actor_user_id=actor_user_id,
                has_delivery_error=has_delivery_error,
                has_open_unresolved=has_open_unresolved,
                sla_breached=bool(sla_proj.get("breached")),
            ),
            "sla_due_at": getattr(thread, "sla_due_at", None).isoformat()
            if getattr(thread, "sla_due_at", None) is not None
            else None,
            "sla": sla_proj,
            "next_action": next_action_proj,
        },
        capabilities={
            "allowed_intents": allowed_intents,
            "allowed_channels": allowed_channels,
            "bulk_allowed": bool(caps.bulk_allowed),
            "defaults": defaults,
            "policy_denials": dict(caps.denial_reasons or {}),
        },
        workspace={
            "draft": draft,
            "delivery_summary": delivery_summary,
            "timeline_cursor": {
                "hint_messages_limit": 50,
                "message_scan_limit": CONTEXT_MESSAGE_SCAN_LIMIT,
            },
            "ui_hints": {
                "can_compose": can_compose,
                "compose_blocked_reason": None
                if can_compose
                else (
                    "archived"
                    if thread.is_archived
                    else (
                        "no_allowed_intents"
                        if not allowed_intents
                        else "no_allowed_channels"
                    )
                ),
            },
        },
        context_version=CONTEXT_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


__all__ = [
    "CONTEXT_MESSAGE_SCAN_LIMIT",
    "CONTEXT_VERSION",
    "ThreadContext",
    "build_thread_context",
]
