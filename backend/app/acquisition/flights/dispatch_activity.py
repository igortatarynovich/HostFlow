"""Stage 4 PR-5 — Timeline visibility for Flights destination dispatch failures."""

from __future__ import annotations

from typing import Any, Mapping

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.activity.append_service import append_activity_event
from backend.app.acquisition.activity.catalog import get_activity_event_contract
from backend.app.models.acquisition_activity_event import ACTOR_TYPE_SYSTEM


def delivery_error_source_event_id(ledger_id: str) -> str:
    return f"acq.dispatch.delivery_error:{str(ledger_id).strip()}"


def _routing_blob(intake_state: Mapping[str, Any] | None, draft_lead: Any) -> dict[str, Any]:
    if isinstance(intake_state, Mapping):
        for key in ("acquisition_routing_v1", "acquisition_routing"):
            raw = intake_state.get(key)
            if isinstance(raw, dict) and raw:
                return dict(raw)
    normalized = getattr(draft_lead, "normalized", None)
    if isinstance(normalized, Mapping):
        raw = normalized.get("acquisition_routing_v1")
        if isinstance(raw, dict) and raw:
            return dict(raw)
    return {}


async def maybe_emit_delivery_error(
    db: AsyncSession,
    *,
    tenant_id: str,
    draft_lead: Any,
    intake_state: Mapping[str, Any] | None,
    ledger_id: str,
    error_code: str,
    note: str | None = None,
) -> None:
    """Best-effort ``DeliveryErrorOccurred`` when Acquisition campaign context exists.

    Never raises — dispatch failure must remain the primary exception.
    """
    routing = _routing_blob(intake_state, draft_lead)
    campaign_id = str(routing.get("campaign_id") or "").strip()
    if not campaign_id or not str(ledger_id or "").strip():
        return
    flight_id = str(routing.get("flight_id") or routing.get("campaign_run_id") or "").strip() or None
    contract = get_activity_event_contract("DeliveryErrorOccurred")
    if contract is None:
        return
    code = str(error_code or "dispatch_failed").strip() or "dispatch_failed"
    payload: dict[str, Any] = {"error_code": code[:120]}
    if note and str(note).strip():
        payload["note"] = str(note).strip()[:500]
    try:
        await append_activity_event(
            db,
            tenant_id=str(tenant_id),
            campaign_id=campaign_id,
            flight_id=flight_id,
            event_type="DeliveryErrorOccurred",
            event_version=contract.event_version,
            payload=payload,
            actor_type=ACTOR_TYPE_SYSTEM,
            actor_id=None,
            source_event_id=delivery_error_source_event_id(ledger_id),
            provider=None,
        )
    except Exception:
        return


__all__ = [
    "delivery_error_source_event_id",
    "maybe_emit_delivery_error",
]
