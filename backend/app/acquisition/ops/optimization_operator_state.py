"""Stage 5 PR-2 — operator acknowledge/dismiss for Flight optimization signals.

Append-only Activity audit. Does **not** mutate Campaign/Flight status and does
**not** change ``evaluate_flight_optimization`` assessment.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.activity.append_service import append_activity_event
from backend.app.acquisition.activity.catalog import get_activity_event_contract
from backend.app.models.acquisition_activity_event import AcquisitionActivityEvent

OperatorAction = Literal["acknowledge", "dismiss"]

_EVENT_BY_ACTION: dict[str, str] = {
    "acknowledge": "OptimizationSignalAcknowledged",
    "dismiss": "OptimizationSignalDismissed",
}
_ACTION_BY_EVENT: dict[str, OperatorAction] = {
    "OptimizationSignalAcknowledged": "acknowledge",
    "OptimizationSignalDismissed": "dismiss",
}


@dataclass(frozen=True)
class OptimizationOperatorState:
    action: OperatorAction
    signal_fingerprint: str
    occurred_at: datetime
    actor_type: str
    actor_id: str | None
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "signal_fingerprint": self.signal_fingerprint,
            "occurred_at": self.occurred_at.isoformat(),
            "actor_type": self.actor_type,
            "actor_id": self.actor_id,
            "note": self.note,
        }


async def get_optimization_operator_state(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    flight_id: str,
    signal_fingerprint: str,
) -> OptimizationOperatorState | None:
    """Latest acknowledge/dismiss for this fingerprint (None if never acted)."""
    fp = str(signal_fingerprint or "").strip()
    if not fp:
        return None
    stmt = (
        select(AcquisitionActivityEvent)
        .where(
            AcquisitionActivityEvent.tenant_id == str(tenant_id),
            AcquisitionActivityEvent.campaign_id == str(campaign_id),
            AcquisitionActivityEvent.flight_id == str(flight_id),
            AcquisitionActivityEvent.event_type.in_(list(_ACTION_BY_EVENT.keys())),
        )
        .order_by(AcquisitionActivityEvent.occurred_at.desc())
        .limit(50)
    )
    rows = (await db.execute(stmt)).scalars().all()
    for row in rows:
        payload = dict(row.payload or {})
        if str(payload.get("signal_fingerprint") or "").strip() != fp:
            continue
        action = _ACTION_BY_EVENT.get(str(row.event_type))
        if action is None:
            continue
        note = payload.get("note")
        return OptimizationOperatorState(
            action=action,
            signal_fingerprint=fp,
            occurred_at=row.occurred_at,
            actor_type=str(row.actor_type),
            actor_id=str(row.actor_id) if row.actor_id else None,
            note=str(note) if note is not None else None,
        )
    return None


async def record_optimization_operator_action(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    flight_id: str,
    action: OperatorAction,
    signal_fingerprint: str,
    assessment: str,
    recommended_action: str,
    window_hours: int,
    actor_type: str,
    actor_id: str | None,
    note: str | None = None,
) -> OptimizationOperatorState:
    """Append acknowledge/dismiss Activity row (idempotent per source_event_id)."""
    event_type = _EVENT_BY_ACTION.get(action)
    if event_type is None:
        raise ValueError(f"unsupported optimization operator action: {action!r}")
    contract = get_activity_event_contract(event_type)
    if contract is None:
        raise RuntimeError(f"missing activity catalog entry for {event_type!r}")

    fp = str(signal_fingerprint).strip()
    payload: dict[str, Any] = {
        "signal_fingerprint": fp,
        "assessment": str(assessment),
        "recommended_action": str(recommended_action),
        "window_hours": int(window_hours),
    }
    if note and str(note).strip():
        payload["note"] = str(note).strip()[:500]

    # One durable action per (flight, fingerprint, action) — retries reuse row.
    source_event_id = f"opt-op:{flight_id}:{fp}:{action}"
    row = await append_activity_event(
        db,
        tenant_id=str(tenant_id),
        campaign_id=str(campaign_id),
        flight_id=str(flight_id),
        event_type=event_type,
        event_version=contract.event_version,
        payload=payload,
        actor_type=actor_type,
        actor_id=actor_id,
        source_event_id=source_event_id,
        correlation_id=str(uuid4()),
    )
    return OptimizationOperatorState(
        action=action,
        signal_fingerprint=fp,
        occurred_at=row.occurred_at,
        actor_type=str(row.actor_type),
        actor_id=str(row.actor_id) if row.actor_id else None,
        note=str(payload["note"]) if "note" in payload else None,
    )


__all__ = [
    "OperatorAction",
    "OptimizationOperatorState",
    "get_optimization_operator_state",
    "record_optimization_operator_action",
]
