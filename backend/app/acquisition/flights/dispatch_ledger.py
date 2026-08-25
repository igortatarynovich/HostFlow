"""Flights dispatch ledger operations (R5 provenance / exactly-once).

Exactly-once effect via Flights idempotency key + ledger check before adapter
invoke. Does NOT open a shared ACID transaction spanning Flights + destination
ORM tables. Destination modules use their own local transactions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.flights.destination_contract import (
    DestinationContractError,
    OpaqueResultRef,
)
from backend.app.models.flight_dispatch_ledger import (
    STATUS_CONFIRMED,
    STATUS_DISPATCHED,
    STATUS_FAILED,
    STATUS_UNRESOLVED,
    FlightDispatchLedger,
)


class DispatchProvenanceError(DestinationContractError):
    """Fail-closed provenance / ledger disposition."""

    code = "flights_dispatch_provenance_error"


@dataclass(frozen=True, slots=True)
class LedgerClaim:
    row: FlightDispatchLedger
    already_confirmed: bool


def build_dispatch_idempotency_key(
    *,
    tenant_id: str,
    transport_lead_id: str,
    route_intent: str,
    dispatcher_id: str,
    handoff_id: str | None = None,
) -> str:
    """Flights-scoped key — never a destination result id as the sole SoT."""
    hid = str(handoff_id or "").strip()
    if hid:
        return f"flights.dispatch:{tenant_id}:{hid}:{route_intent}:{dispatcher_id}"
    return (
        f"flights.dispatch:{tenant_id}:{transport_lead_id}:{route_intent}:{dispatcher_id}"
    )


def extract_handoff_id(intake_state: dict[str, Any] | None) -> str | None:
    state = intake_state if isinstance(intake_state, dict) else {}
    for key in ("handoff_id", "submission_id", "intake_handoff_id"):
        raw = str(state.get(key) or "").strip()
        if raw:
            return raw[:64]
    handoff = state.get("intake_handoff")
    if isinstance(handoff, dict):
        for key in ("handoff_id", "submission_id"):
            raw = str(handoff.get(key) or "").strip()
            if raw:
                return raw[:64]
    lf = state.get("lead_form")
    if isinstance(lf, dict):
        raw = str(lf.get("submission_id") or "").strip()
        if raw:
            return raw[:64]
    return None


def opaque_ref_from_ledger(row: FlightDispatchLedger) -> OpaqueResultRef:
    owner = str(row.module_owner or "").strip()
    rtype = str(row.result_type or "").strip()
    rid = str(row.result_id or "").strip()
    if not owner or not rtype or not rid:
        raise DispatchProvenanceError(
            "confirmed ledger row missing opaque result reference",
            details={
                "ledger_id": row.id,
                "status": row.status,
                "module_owner": row.module_owner,
                "result_type": row.result_type,
                "result_id": row.result_id,
                "reason": "ambiguous_or_missing_result",
            },
        )
    return OpaqueResultRef(module_owner=owner, result_type=rtype, result_id=rid)


async def get_ledger_by_idempotency(
    db: AsyncSession,
    *,
    tenant_id: str,
    idempotency_key: str,
) -> FlightDispatchLedger | None:
    stmt = select(FlightDispatchLedger).where(
        FlightDispatchLedger.tenant_id == tenant_id,
        FlightDispatchLedger.idempotency_key == idempotency_key,
    )
    return await db.scalar(stmt)


async def claim_dispatch_ledger(
    db: AsyncSession,
    *,
    tenant_id: str,
    idempotency_key: str,
    handoff_id: str | None,
    transport_lead_id: str,
    route_intent: str,
    destination: str,
    dispatcher_id: str,
) -> LedgerClaim:
    """Load or create Flights ledger row. Confirmed → short-circuit (no adapter)."""
    existing = await get_ledger_by_idempotency(
        db, tenant_id=tenant_id, idempotency_key=idempotency_key
    )
    if existing is not None:
        status = str(existing.status or "").strip()
        if status == STATUS_CONFIRMED:
            opaque_ref_from_ledger(existing)  # fail-closed if incomplete
            return LedgerClaim(row=existing, already_confirmed=True)
        if status == STATUS_UNRESOLVED:
            raise DispatchProvenanceError(
                "dispatch previously unresolved (fail-closed)",
                details={
                    "ledger_id": existing.id,
                    "status": status,
                    "failure_code": existing.failure_code,
                    "reason": "unresolved_disposition",
                },
            )
        if status == STATUS_FAILED:
            raise DispatchProvenanceError(
                "dispatch previously failed (fail-closed)",
                details={
                    "ledger_id": existing.id,
                    "status": status,
                    "failure_code": existing.failure_code,
                    "reason": "failed_disposition",
                },
            )
        # pending / dispatched → allow retry (at-least-once delivery)
        existing.status = STATUS_DISPATCHED
        await db.flush()
        return LedgerClaim(row=existing, already_confirmed=False)

    row = FlightDispatchLedger(
        id=str(uuid4()),
        tenant_id=tenant_id,
        idempotency_key=idempotency_key,
        handoff_id=handoff_id,
        transport_lead_id=transport_lead_id,
        route_intent=route_intent,
        destination=destination,
        dispatcher_id=dispatcher_id,
        status=STATUS_DISPATCHED,
        meta={"ledger_contract": "flights.dispatch_ledger.v1"},
    )
    db.add(row)
    await db.flush()
    return LedgerClaim(row=row, already_confirmed=False)


async def confirm_dispatch_ledger(
    db: AsyncSession,
    row: FlightDispatchLedger,
    *,
    opaque: OpaqueResultRef,
) -> FlightDispatchLedger:
    """Persist opaque result ref on Flights ledger only (no destination tables)."""
    if not opaque.module_owner or not opaque.result_type or not opaque.result_id:
        raise DispatchProvenanceError(
            "opaque result reference incomplete",
            details={
                "module_owner": opaque.module_owner,
                "result_type": opaque.result_type,
                "result_id": opaque.result_id,
                "reason": "ambiguous_or_missing_result",
            },
        )
    if opaque.module_owner != row.destination:
        raise DispatchProvenanceError(
            "opaque module_owner does not match destination",
            details={
                "module_owner": opaque.module_owner,
                "destination": row.destination,
            },
        )
    row.module_owner = opaque.module_owner
    row.result_type = opaque.result_type
    row.result_id = opaque.result_id
    row.status = STATUS_CONFIRMED
    row.confirmed_at = datetime.now(timezone.utc)
    row.failure_code = None
    row.failure_message = None
    await db.flush()
    return row


async def mark_dispatch_unresolved(
    db: AsyncSession,
    row: FlightDispatchLedger,
    *,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> FlightDispatchLedger:
    row.status = STATUS_UNRESOLVED
    row.failure_code = code[:128]
    row.failure_message = message
    meta = dict(row.meta or {})
    if details:
        meta["failure_details"] = details
    row.meta = meta
    await db.flush()
    return row


async def mark_dispatch_failed(
    db: AsyncSession,
    row: FlightDispatchLedger,
    *,
    code: str,
    message: str,
) -> FlightDispatchLedger:
    row.status = STATUS_FAILED
    row.failure_code = code[:128]
    row.failure_message = message
    await db.flush()
    return row
