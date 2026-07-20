"""C1 — platform thread working queues (Thread is the work object)."""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from sqlalchemy.sql import ColumnElement

from backend.app.models.communication import CommunicationMessage, CommunicationThread
from backend.app.models.communication_inbound_unresolved import (
    UNRESOLVED_STATUS_OPEN,
    CommunicationInboundUnresolved,
)

# Canonical queue keys for Inbox Workspace.
QUEUE_REQUIRES_REPLY = "requires_reply"
QUEUE_NEW_INBOUND = "new_inbound"
QUEUE_DELIVERY_ERRORS = "delivery_errors"
QUEUE_UNRESOLVED = "unresolved"
QUEUE_ASSIGNED_TO_ME = "assigned_to_me"
QUEUE_UNASSIGNED = "unassigned"
QUEUE_WAITING_FOR_REPLY = "waiting_for_reply"
QUEUE_CLOSED = "closed"

THREAD_QUEUES: frozenset[str] = frozenset(
    {
        QUEUE_REQUIRES_REPLY,
        QUEUE_NEW_INBOUND,
        QUEUE_DELIVERY_ERRORS,
        QUEUE_UNRESOLVED,
        QUEUE_ASSIGNED_TO_ME,
        QUEUE_UNASSIGNED,
        QUEUE_WAITING_FOR_REPLY,
        QUEUE_CLOSED,
    }
)

_CLOSED_STATUSES = frozenset({"closed", "done", "resolved", "archived"})


def normalize_thread_queue(value: str | None) -> str | None:
    key = str(value or "").strip().lower()
    if not key:
        return None
    if key not in THREAD_QUEUES:
        raise ValueError(f"unknown_thread_queue:{key}")
    return key


def thread_queue_clause(
    queue: str,
    *,
    tenant_id: str,
    actor_user_id: str | None,
) -> ColumnElement[Any]:
    """SQLAlchemy boolean clause restricting CommunicationThread rows to a C1 queue."""
    key = normalize_thread_queue(queue)
    assert key is not None
    T = CommunicationThread

    if key == QUEUE_NEW_INBOUND:
        return T.unread_count > 0

    if key == QUEUE_ASSIGNED_TO_ME:
        actor = str(actor_user_id or "").strip()
        if not actor:
            return sa.false()
        return T.assignee_id == actor

    if key == QUEUE_UNASSIGNED:
        return T.assignee_id.is_(None)

    if key == QUEUE_CLOSED:
        return sa.or_(
            T.is_archived.is_(True),
            sa.func.lower(sa.func.coalesce(T.status, "")).in_(tuple(_CLOSED_STATUSES)),
        )

    if key == QUEUE_REQUIRES_REPLY:
        # Inbound is newer than outbound (or inbound exists without outbound).
        return sa.and_(
            T.last_inbound_at.is_not(None),
            sa.or_(
                T.last_outbound_at.is_(None),
                T.last_inbound_at > T.last_outbound_at,
            ),
            T.is_archived.is_(False),
        )

    if key == QUEUE_WAITING_FOR_REPLY:
        return sa.and_(
            T.last_outbound_at.is_not(None),
            sa.or_(
                T.last_inbound_at.is_(None),
                T.last_outbound_at >= T.last_inbound_at,
            ),
            T.is_archived.is_(False),
        )

    if key == QUEUE_DELIVERY_ERRORS:
        failed_msg = (
            sa.select(CommunicationMessage.id)
            .where(
                CommunicationMessage.tenant_id == tenant_id,
                CommunicationMessage.thread_id == T.id,
                sa.func.lower(CommunicationMessage.delivery_status).in_(
                    ("failed", "undeliverable", "bounced", "rejected")
                ),
            )
            .correlate(T)
            .exists()
        )
        return sa.and_(failed_msg, T.is_archived.is_(False))

    if key == QUEUE_UNRESOLVED:
        open_unresolved = (
            sa.select(CommunicationInboundUnresolved.id)
            .where(
                CommunicationInboundUnresolved.tenant_id == tenant_id,
                CommunicationInboundUnresolved.thread_id == T.id,
                CommunicationInboundUnresolved.status == UNRESOLVED_STATUS_OPEN,
            )
            .correlate(T)
            .exists()
        )
        return open_unresolved

    raise ValueError(f"unhandled_thread_queue:{key}")
