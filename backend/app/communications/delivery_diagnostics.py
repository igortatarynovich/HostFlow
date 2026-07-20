"""C0.3 — delivery diagnostics platform path.

Single writer for:
  attempt journal · delivery/message state transitions · operator diagnostics view

Provider callbacks must enter via ``apply_delivery_callback`` (normalize → resolve →
transition → audit). Direct provider status checks outside this module are banned
by contract tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.communications.delivery_canon import (
    STATUS_ACCEPTED,
    STATUS_DELIVERED,
    STATUS_FAILED,
    STATUS_QUEUED,
    STATUS_SENT,
    can_transition,
    is_terminal_negative,
    normalize_canonical_status,
)
from backend.app.communications.delivery_errors import (
    REASON_SEND_FAILED,
    NormalizedDeliveryError,
    normalize_delivery_error,
)
from backend.app.communications.delivery_retry import (
    DEFAULT_MAX_ATTEMPTS,
    compute_next_retry_at,
    retry_decision,
)
from backend.app.models.communication import CommunicationMessage
from backend.app.models.communication_delivery import CommunicationDelivery
from backend.app.models.communication_delivery_attempt import CommunicationDeliveryAttempt
from backend.app.models.communication_delivery_callback_unresolved import (
    CALLBACK_UNRESOLVED_OPEN,
    CommunicationDeliveryCallbackUnresolved,
)

# Processed callback event ids (idempotency) stored under delivery.meta.
_CALLBACK_EVENTS_KEY = "callback_event_ids"
_DIAGNOSTICS_KEY = "diagnostics"


@dataclass(frozen=True, slots=True)
class DeliveryDiagnosticsView:
    message_id: str
    delivery_id: str | None
    status: str
    last_attempt_number: int | None
    reason_code: str | None
    retryable: bool | None
    next_retry_at: str | None
    provider_reference: str | None
    safe_message: str | None
    timeline: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "delivery_id": self.delivery_id,
            "status": self.status,
            "last_attempt": {
                "attempt_number": self.last_attempt_number,
                "reason_code": self.reason_code,
                "retryable": self.retryable,
                "safe_message": self.safe_message,
            },
            "next_retry_at": self.next_retry_at,
            "provider_reference": self.provider_reference,
            "timeline": list(self.timeline),
        }


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


async def _next_attempt_number(
    db: AsyncSession, *, tenant_id: str, delivery_id: str
) -> int:
    row = await db.execute(
        select(CommunicationDeliveryAttempt.attempt_number)
        .where(
            CommunicationDeliveryAttempt.tenant_id == tenant_id,
            CommunicationDeliveryAttempt.delivery_id == delivery_id,
        )
        .order_by(CommunicationDeliveryAttempt.attempt_number.desc())
        .limit(1)
    )
    current = row.scalar_one_or_none()
    return int(current or 0) + 1


async def record_delivery_attempt(
    db: AsyncSession,
    *,
    tenant_id: str,
    message_id: str,
    delivery_id: str,
    provider: str,
    canonical_result: str,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
    provider_account_id: str | None = None,
    provider_message_id: str | None = None,
    provider_status: str | None = None,
    provider_code: str | None = None,
    reason_code: str | None = None,
    raw_message: str | None = None,
    retry_after_seconds: int | None = None,
    raw_provider_payload: dict[str, Any] | None = None,
    correlation_id: str | None = None,
    trace_id: str | None = None,
    meta: dict[str, Any] | None = None,
    apply_state: bool = True,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> CommunicationDeliveryAttempt:
    """Append an immutable attempt and optionally transition delivery/message state."""
    result = normalize_canonical_status(canonical_result, default=STATUS_FAILED)
    err: NormalizedDeliveryError | None = None
    if is_terminal_negative(result) or reason_code:
        err = normalize_delivery_error(
            reason_code=reason_code or REASON_SEND_FAILED,
            provider_status=provider_status,
            provider_code=provider_code,
            raw_message=raw_message,
            retry_after_seconds=retry_after_seconds,
        )
        if not err.reason_code:
            raise ValueError("terminal failure requires reason_code")

    started = started_at or _now()
    finished = finished_at or _now()
    latency_ms: float | None = None
    if finished and started:
        latency_ms = max(0.0, (finished - started).total_seconds() * 1000.0)

    attempt_number = await _next_attempt_number(
        db, tenant_id=tenant_id, delivery_id=delivery_id
    )
    attempt = CommunicationDeliveryAttempt(
        id=str(uuid4()),
        tenant_id=tenant_id,
        message_id=message_id,
        delivery_id=delivery_id,
        attempt_number=attempt_number,
        provider=str(provider),
        provider_account_id=provider_account_id,
        provider_message_id=provider_message_id,
        started_at=started,
        finished_at=finished,
        canonical_result=result,
        provider_status=provider_status,
        provider_code=provider_code,
        reason_code=err.reason_code if err else reason_code,
        retryable=err.retryable if err else None,
        latency_ms=latency_ms,
        correlation_id=correlation_id,
        trace_id=trace_id,
        safe_message=err.safe_message if err else None,
        raw_provider_payload=dict(raw_provider_payload or {}),
        meta=dict(meta or {}),
    )
    db.add(attempt)
    await db.flush()

    if apply_state:
        await apply_delivery_state_transition(
            db,
            tenant_id=tenant_id,
            delivery_id=delivery_id,
            message_id=message_id,
            new_status=result,
            attempt=attempt,
            error=err,
            max_attempts=max_attempts,
        )
    return attempt


async def apply_delivery_state_transition(
    db: AsyncSession,
    *,
    tenant_id: str,
    delivery_id: str,
    message_id: str,
    new_status: str,
    attempt: CommunicationDeliveryAttempt | None = None,
    error: NormalizedDeliveryError | None = None,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    force: bool = False,
) -> bool:
    """Apply monotonic state transition to delivery + message. Returns False if skipped."""
    delivery = await db.get(CommunicationDelivery, delivery_id)
    message = await db.get(CommunicationMessage, message_id)
    if delivery is None or str(delivery.tenant_id) != tenant_id:
        return False
    if message is None or str(message.tenant_id) != tenant_id:
        return False

    target = normalize_canonical_status(new_status, default=STATUS_FAILED)
    current = normalize_canonical_status(delivery.status, default=STATUS_QUEUED)
    if not force and not can_transition(current, target):
        return False

    now = _now()
    delivery.status = target
    if target in {STATUS_ACCEPTED, STATUS_SENT} and delivery.sent_at is None:
        delivery.sent_at = now
    if target == STATUS_DELIVERED:
        delivery.delivered_at = delivery.delivered_at or now

    # Message layer: map progress to legacy message.delivery_status vocabulary.
    if target == STATUS_DELIVERED:
        message.delivery_status = STATUS_DELIVERED
        message.delivered_at = message.delivered_at or now
        message.sent_at = message.sent_at or now
        message.error_message = None
    elif target == STATUS_SENT:
        message.delivery_status = STATUS_SENT
        message.sent_at = message.sent_at or now
    elif target == STATUS_ACCEPTED:
        message.delivery_status = STATUS_SENT
        message.sent_at = message.sent_at or now
    elif target == STATUS_QUEUED:
        message.delivery_status = STATUS_QUEUED
    elif is_terminal_negative(target):
        message.delivery_status = STATUS_FAILED
        if error:
            message.error_message = error.safe_message
            delivery.error_code = error.reason_code
            delivery.error_detail = error.safe_message
        elif attempt and attempt.safe_message:
            message.error_message = attempt.safe_message
            delivery.error_code = attempt.reason_code
            delivery.error_detail = attempt.safe_message

    next_retry: datetime | None = None
    retryable: bool | None = None
    reason = error.reason_code if error else (attempt.reason_code if attempt else None)
    if error:
        retryable = error.retryable
        decision = retry_decision(
            reason_code=error.reason_code,
            attempt_number=attempt.attempt_number if attempt else max_attempts,
            retry_after_seconds=error.retry_after_seconds,
            max_attempts=max_attempts,
        )
        if decision["allowed"] and not decision["exhausted"]:
            next_retry = compute_next_retry_at(
                reason_code=error.reason_code,
                attempt_number=attempt.attempt_number if attempt else 1,
                retry_after_seconds=error.retry_after_seconds,
                max_attempts=max_attempts,
            )
            if next_retry is not None:
                # Keep message queued for worker pickup; delivery stays terminal-ish
                # failed until retry succeeds (new attempt).
                message.delivery_status = STATUS_QUEUED
                payload = _as_dict(message.payload)
                dispatch = _as_dict(payload.get("dispatch"))
                dispatch.update(
                    {
                        "status": "retry_scheduled",
                        "attempt_count": attempt.attempt_number if attempt else 0,
                        "next_retry_at": next_retry.isoformat(),
                        "last_error_reason": error.reason_code,
                        "diagnostics": True,
                    }
                )
                message.payload = {**payload, "dispatch": dispatch}
        elif decision["exhausted"] or decision["permanent_failure"]:
            # Explicit terminal after exhaustion / permanent.
            message.delivery_status = STATUS_FAILED

    meta = _as_dict(delivery.meta)
    diag = _as_dict(meta.get(_DIAGNOSTICS_KEY))
    diag.update(
        {
            "status": target,
            "reason_code": reason,
            "retryable": retryable,
            "next_retry_at": next_retry.isoformat() if next_retry else None,
            "last_attempt_number": attempt.attempt_number if attempt else diag.get(
                "last_attempt_number"
            ),
            "provider_reference": (
                (attempt.provider_message_id if attempt else None)
                or delivery.external_message_id
            ),
            "safe_message": (
                error.safe_message
                if error
                else (attempt.safe_message if attempt else diag.get("safe_message"))
            ),
            "updated_at": now.isoformat(),
        }
    )
    meta[_DIAGNOSTICS_KEY] = diag
    delivery.meta = meta
    if attempt and attempt.provider_message_id and not delivery.external_message_id:
        delivery.external_message_id = attempt.provider_message_id[:128]
    await db.flush()
    return True


@dataclass(frozen=True, slots=True)
class NormalizedDeliveryCallback:
    provider: str
    provider_event_id: str
    provider_message_id: str | None
    provider_account_id: str | None
    canonical_status: str
    provider_status: str | None
    provider_code: str | None
    reason_code: str | None
    retry_after_seconds: int | None
    occurred_at: datetime | None
    correlation_id: str | None
    raw_payload: dict[str, Any]


def normalize_delivery_callback(
    *,
    provider: str,
    payload: dict[str, Any],
    provider_account_id: str | None = None,
) -> NormalizedDeliveryCallback:
    """Normalize a provider delivery receipt into canonical fields (no ORM)."""
    data = _as_dict(payload)
    event_id = str(
        data.get("event_id")
        or data.get("provider_event_id")
        or data.get("id")
        or data.get("MessageId")
        or ""
    ).strip()
    if not event_id:
        # Deterministic fallback for idempotency when provider omits event id.
        import hashlib
        import json

        digest = hashlib.sha256(
            json.dumps(data, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()[:32]
        event_id = f"hash:{digest}"

    provider_message_id = (
        str(
            data.get("provider_message_id")
            or data.get("message_id")
            or data.get("external_message_id")
            or data.get("MessageId")
            or ""
        ).strip()
        or None
    )
    provider_status = (
        str(data.get("provider_status") or data.get("status") or "").strip() or None
    )
    provider_code = (
        str(data.get("provider_code") or data.get("code") or "").strip() or None
    )
    reason_in = (
        str(data.get("reason_code") or data.get("reason") or "").strip() or None
    )
    canonical_in = str(data.get("canonical_status") or "").strip().lower()
    if canonical_in:
        canonical = normalize_canonical_status(canonical_in, default=STATUS_FAILED)
    else:
        # Map common receipt words → canonical (never expose raw as canonical).
        st = (provider_status or "").lower()
        if st in {"delivered", "delivery", "ok", "success"}:
            canonical = STATUS_DELIVERED
        elif st in {"sent", "transmit", "submitted"}:
            canonical = STATUS_SENT
        elif st in {"accepted", "queued", "accepted_by_provider"}:
            canonical = STATUS_ACCEPTED
        elif st in {"bounce", "bounced"}:
            canonical = "bounced"
        elif st in {"reject", "rejected"}:
            canonical = "rejected"
        elif st in {"expire", "expired"}:
            canonical = "expired"
        elif st in {"cancel", "cancelled", "canceled"}:
            canonical = "cancelled"
        elif st in {"undeliverable", "undelivered"}:
            canonical = "undeliverable"
        else:
            canonical = STATUS_FAILED if (provider_status or reason_in) else STATUS_ACCEPTED

    retry_after = data.get("retry_after_seconds") or data.get("retry_after")
    try:
        retry_after_seconds = int(retry_after) if retry_after is not None else None
    except (TypeError, ValueError):
        retry_after_seconds = None

    occurred_raw = data.get("occurred_at") or data.get("timestamp")
    occurred_at: datetime | None = None
    if isinstance(occurred_raw, datetime):
        occurred_at = occurred_raw
    elif isinstance(occurred_raw, str) and occurred_raw.strip():
        try:
            occurred_at = datetime.fromisoformat(occurred_raw.replace("Z", "+00:00"))
        except ValueError:
            occurred_at = None

    err = None
    if is_terminal_negative(canonical) or reason_in:
        err = normalize_delivery_error(
            reason_code=reason_in,
            provider_status=provider_status,
            provider_code=provider_code,
            raw_message=str(data.get("message") or data.get("error") or "") or None,
            retry_after_seconds=retry_after_seconds,
        )

    return NormalizedDeliveryCallback(
        provider=str(provider).strip().lower() or "unknown",
        provider_event_id=event_id[:128],
        provider_message_id=provider_message_id[:128] if provider_message_id else None,
        provider_account_id=provider_account_id,
        canonical_status=canonical,
        provider_status=provider_status,
        provider_code=provider_code,
        reason_code=err.reason_code if err else reason_in,
        retry_after_seconds=retry_after_seconds,
        occurred_at=occurred_at,
        correlation_id=(
            str(data.get("correlation_id") or "").strip() or None
        ),
        raw_payload=data,
    )


async def resolve_delivery_for_callback(
    db: AsyncSession,
    *,
    tenant_id: str,
    callback: NormalizedDeliveryCallback,
    delivery_id: str | None = None,
    message_id: str | None = None,
) -> CommunicationDelivery | None:
    if delivery_id:
        row = await db.get(CommunicationDelivery, delivery_id)
        if row and str(row.tenant_id) == tenant_id:
            return row
    if message_id:
        msg = await db.get(CommunicationMessage, message_id)
        if msg and str(msg.tenant_id) == tenant_id:
            did = _as_dict(msg.payload).get("delivery_id")
            if did:
                d = await db.get(CommunicationDelivery, str(did))
                if d and str(d.tenant_id) == tenant_id:
                    return d
    if callback.provider_message_id:
        result = await db.execute(
            select(CommunicationDelivery)
            .where(
                CommunicationDelivery.tenant_id == tenant_id,
                CommunicationDelivery.external_message_id
                == callback.provider_message_id,
            )
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if row:
            return row
    return None


async def apply_delivery_callback(
    db: AsyncSession,
    *,
    tenant_id: str,
    provider: str,
    payload: dict[str, Any],
    provider_account_id: str | None = None,
    delivery_id: str | None = None,
    message_id: str | None = None,
) -> dict[str, Any]:
    """Unified callback path: normalize → resolve → transition → audit."""
    callback = normalize_delivery_callback(
        provider=provider,
        payload=payload,
        provider_account_id=provider_account_id,
    )
    delivery = await resolve_delivery_for_callback(
        db,
        tenant_id=tenant_id,
        callback=callback,
        delivery_id=delivery_id,
        message_id=message_id,
    )
    if delivery is None:
        unresolved = await _enqueue_unresolved_callback(
            db, tenant_id=tenant_id, callback=callback
        )
        return {
            "status": "unresolved",
            "unresolved_id": unresolved.id,
            "provider_event_id": callback.provider_event_id,
            "idempotent_replay": False,
        }

    meta = _as_dict(delivery.meta)
    seen = list(meta.get(_CALLBACK_EVENTS_KEY) or [])
    if callback.provider_event_id in seen:
        return {
            "status": "idempotent_replay",
            "delivery_id": str(delivery.id),
            "provider_event_id": callback.provider_event_id,
            "idempotent_replay": True,
            "canonical_status": normalize_canonical_status(delivery.status),
        }

    msg_id = message_id or str(
        _as_dict(delivery.meta).get("communication_message_id") or ""
    ).strip()
    if not msg_id:
        # Last resort: find message by delivery_id in payload.
        result = await db.execute(
            select(CommunicationMessage)
            .where(CommunicationMessage.tenant_id == tenant_id)
            .limit(50)
        )
        for m in result.scalars().all():
            if str(_as_dict(m.payload).get("delivery_id") or "") == str(delivery.id):
                msg_id = str(m.id)
                break
    if not msg_id:
        unresolved = await _enqueue_unresolved_callback(
            db, tenant_id=tenant_id, callback=callback
        )
        return {
            "status": "unresolved",
            "unresolved_id": unresolved.id,
            "provider_event_id": callback.provider_event_id,
            "idempotent_replay": False,
        }

    err = None
    if is_terminal_negative(callback.canonical_status) or callback.reason_code:
        err = normalize_delivery_error(
            reason_code=callback.reason_code,
            provider_status=callback.provider_status,
            provider_code=callback.provider_code,
            raw_message=str(callback.raw_payload.get("message") or "") or None,
            retry_after_seconds=callback.retry_after_seconds,
        )

    # Out-of-order / downgrade protection via can_transition inside apply.
    applied = await apply_delivery_state_transition(
        db,
        tenant_id=tenant_id,
        delivery_id=str(delivery.id),
        message_id=msg_id,
        new_status=callback.canonical_status,
        error=err,
    )

    # Always append an immutable attempt for timeline (even ignored OOO callbacks).
    await record_delivery_attempt(
        db,
        tenant_id=tenant_id,
        message_id=msg_id,
        delivery_id=str(delivery.id),
        provider=callback.provider,
        canonical_result=callback.canonical_status,
        started_at=callback.occurred_at or _now(),
        finished_at=callback.occurred_at or _now(),
        provider_account_id=callback.provider_account_id,
        provider_message_id=callback.provider_message_id,
        provider_status=callback.provider_status,
        provider_code=callback.provider_code,
        reason_code=err.reason_code if err else callback.reason_code,
        raw_provider_payload=callback.raw_payload,
        correlation_id=callback.correlation_id,
        apply_state=False,  # state already applied (or skipped for OOO)
        meta={
            "source": "provider_callback",
            "kind": "provider_callback",
            "applied": applied,
            "provider_event_id": callback.provider_event_id,
        },
    )

    # Always keep raw callback + event id for diagnostics / idempotency.
    meta = _as_dict(delivery.meta)
    seen = list(meta.get(_CALLBACK_EVENTS_KEY) or [])
    if callback.provider_event_id not in seen:
        seen.append(callback.provider_event_id)
    meta[_CALLBACK_EVENTS_KEY] = seen[-100:]
    callbacks = list(meta.get("callbacks") or [])
    callbacks.append(
        {
            "event_id": callback.provider_event_id,
            "canonical_status": callback.canonical_status,
            "applied": applied,
            "at": _now().isoformat(),
            "provider_status": callback.provider_status,
            "reason_code": err.reason_code if err else callback.reason_code,
        }
    )
    meta["callbacks"] = callbacks[-50:]
    meta["last_raw_callback"] = callback.raw_payload
    delivery.meta = meta
    await db.flush()

    return {
        "status": "applied" if applied else "ignored_out_of_order",
        "delivery_id": str(delivery.id),
        "message_id": msg_id,
        "provider_event_id": callback.provider_event_id,
        "canonical_status": normalize_canonical_status(delivery.status),
        "applied": applied,
        "idempotent_replay": False,
    }


async def _enqueue_unresolved_callback(
    db: AsyncSession,
    *,
    tenant_id: str,
    callback: NormalizedDeliveryCallback,
) -> CommunicationDeliveryCallbackUnresolved:
    existing = await db.execute(
        select(CommunicationDeliveryCallbackUnresolved).where(
            CommunicationDeliveryCallbackUnresolved.tenant_id == tenant_id,
            CommunicationDeliveryCallbackUnresolved.provider == callback.provider,
            CommunicationDeliveryCallbackUnresolved.provider_event_id
            == callback.provider_event_id,
        ).limit(1)
    )
    row = existing.scalar_one_or_none()
    if row:
        return row
    row = CommunicationDeliveryCallbackUnresolved(
        id=str(uuid4()),
        tenant_id=tenant_id,
        provider=callback.provider,
        provider_account_id=callback.provider_account_id,
        provider_event_id=callback.provider_event_id,
        provider_message_id=callback.provider_message_id,
        status=CALLBACK_UNRESOLVED_OPEN,
        reason="delivery_not_found",
        correlation_id=callback.correlation_id,
        raw_payload=callback.raw_payload,
    )
    db.add(row)
    await db.flush()
    return row


async def get_delivery_diagnostics(
    db: AsyncSession,
    *,
    tenant_id: str,
    message_id: str,
) -> DeliveryDiagnosticsView | None:
    message = await db.get(CommunicationMessage, message_id)
    if message is None or str(message.tenant_id) != tenant_id:
        return None

    delivery_id = str(_as_dict(message.payload).get("delivery_id") or "").strip() or None
    delivery: CommunicationDelivery | None = None
    if delivery_id:
        delivery = await db.get(CommunicationDelivery, delivery_id)

    attempts_q = await db.execute(
        select(CommunicationDeliveryAttempt)
        .where(
            CommunicationDeliveryAttempt.tenant_id == tenant_id,
            CommunicationDeliveryAttempt.message_id == message_id,
        )
        .order_by(CommunicationDeliveryAttempt.attempt_number.asc())
    )
    attempts = list(attempts_q.scalars().all())
    last = attempts[-1] if attempts else None
    diag = _as_dict(_as_dict(delivery.meta if delivery else None).get(_DIAGNOSTICS_KEY))

    # Timeline is reconstructed solely from immutable attempt rows (no current_status magic).
    timeline: list[dict[str, Any]] = []
    for a in attempts:
        meta = _as_dict(a.meta)
        kind = str(meta.get("kind") or meta.get("source") or "attempt")
        timeline.append(
            {
                "kind": kind,
                "attempt_number": a.attempt_number,
                "at": a.finished_at.isoformat() if a.finished_at else a.started_at.isoformat(),
                "canonical_result": a.canonical_result,
                "reason_code": a.reason_code,
                "retryable": a.retryable,
                "safe_message": a.safe_message,
                "provider_reference": a.provider_message_id,
                "provider_event_id": meta.get("provider_event_id"),
                "applied": meta.get("applied"),
                "initiated_by": meta.get("initiated_by"),
                "latency_ms": a.latency_ms,
                "correlation_id": a.correlation_id,
            }
        )

    status = (
        normalize_canonical_status(delivery.status)
        if delivery
        else normalize_canonical_status(message.delivery_status, default=STATUS_QUEUED)
    )
    # Operator summary prefers last attempt facts; next_retry may be mirrored on dispatch.
    dispatch = _as_dict(_as_dict(message.payload).get("dispatch"))
    return DeliveryDiagnosticsView(
        message_id=str(message.id),
        delivery_id=str(delivery.id) if delivery else delivery_id,
        status=status,
        last_attempt_number=last.attempt_number if last else None,
        reason_code=last.reason_code if last else None,
        retryable=last.retryable if last else None,
        next_retry_at=(
            str(dispatch.get("next_retry_at") or "").strip()
            or str(diag.get("next_retry_at") or "").strip()
            or None
        ),
        provider_reference=(
            (last.provider_message_id if last else None)
            or (delivery.external_message_id if delivery else None)
            or message.external_message_ref
        ),
        safe_message=(last.safe_message if last else None) or message.error_message,
        timeline=tuple(timeline),
    )


async def request_manual_retry(
    db: AsyncSession,
    *,
    tenant_id: str,
    message_id: str,
    actor_user_id: str | None,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> dict[str, Any]:
    """Schedule a manual retry (audited).

    Does **not** create a new Message/Delivery and does **not** rewind canonical
    delivery status (failed → queued is illegal). Worker pickup is signaled on
    the message dispatch mirror; a new Attempt is appended for timeline.
    """
    view = await get_delivery_diagnostics(
        db, tenant_id=tenant_id, message_id=message_id
    )
    if view is None:
        return {"allowed": False, "reason": "not_found"}
    if not view.delivery_id:
        return {"allowed": False, "reason": "no_delivery"}
    reason = view.reason_code or REASON_SEND_FAILED
    attempt_no = int(view.last_attempt_number or 0)
    decision = retry_decision(
        reason_code=reason,
        attempt_number=attempt_no,
        manual=True,
        max_attempts=max_attempts,
    )
    if not decision["allowed"]:
        return decision

    message = await db.get(CommunicationMessage, message_id)
    if message is None:
        return {"allowed": False, "reason": "not_found"}
    delivery = await db.get(CommunicationDelivery, view.delivery_id)
    if delivery is None or str(delivery.tenant_id) != tenant_id:
        return {"allowed": False, "reason": "no_delivery"}

    now = _now()
    # Message may return to queued for worker loops; delivery canonical status stays.
    payload = _as_dict(message.payload)
    dispatch = _as_dict(payload.get("dispatch"))
    dispatch.update(
        {
            "status": "manual_retry_requested",
            "attempt_count": attempt_no,
            "next_retry_at": now.isoformat(),
            "manual_retry": True,
            "manual_retry_by": actor_user_id,
            "manual_retry_at": now.isoformat(),
            "last_error_reason": reason,
            "diagnostics": True,
        }
    )
    message.payload = {**payload, "dispatch": dispatch}
    message.delivery_status = STATUS_QUEUED

    current_canonical = normalize_canonical_status(delivery.status, default=STATUS_FAILED)
    await record_delivery_attempt(
        db,
        tenant_id=tenant_id,
        message_id=message_id,
        delivery_id=str(delivery.id),
        provider=str(delivery.provider or "unknown"),
        canonical_result=current_canonical,
        started_at=now,
        finished_at=now,
        reason_code=reason,
        raw_message="manual_retry_requested",
        apply_state=False,
        meta={
            "kind": "manual_retry",
            "source": "manual_retry",
            "initiated_by": actor_user_id,
            "scheduled": True,
        },
    )
    meta = _as_dict(delivery.meta)
    diag = _as_dict(meta.get(_DIAGNOSTICS_KEY))
    diag.update(
        {
            "manual_retry_by": actor_user_id,
            "manual_retry_at": now.isoformat(),
            "next_retry_at": now.isoformat(),
            "retryable": True,
        }
    )
    meta[_DIAGNOSTICS_KEY] = diag
    delivery.meta = meta
    await db.flush()
    return {
        **decision,
        "scheduled": True,
        "message_id": message_id,
        "delivery_id": str(delivery.id),
    }


__all__ = [
    "DeliveryDiagnosticsView",
    "NormalizedDeliveryCallback",
    "apply_delivery_callback",
    "apply_delivery_state_transition",
    "get_delivery_diagnostics",
    "normalize_delivery_callback",
    "record_delivery_attempt",
    "request_manual_retry",
    "resolve_delivery_for_callback",
]
