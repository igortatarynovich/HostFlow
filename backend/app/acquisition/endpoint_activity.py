"""Endpoint association → Activity Timeline (Stage 3E PR-2).

V1 Endpoints are transitional Form / IntakeSource bindings on a Flight.
Emit ``EndpointChanged`` only via ``append_activity_event`` — no provider SoT.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.activity.append_service import append_activity_event
from backend.app.acquisition.activity.catalog import get_activity_event_contract
from backend.app.models.acquisition_activity_event import AcquisitionActivityEvent

CHANGE_KIND_ATTACHED = "attached"
CHANGE_KIND_DETACHED = "detached"
CHANGE_KIND_UPDATED = "updated"

ENDPOINT_KIND_FORM = "form"
ENDPOINT_KIND_INTAKE_SOURCE = "intake_source"


def form_endpoint_id(form_id: str) -> str:
    return f"{ENDPOINT_KIND_FORM}:{str(form_id).strip()}"


def intake_source_endpoint_id(profile_id: str) -> str:
    return f"{ENDPOINT_KIND_INTAKE_SOURCE}:{str(profile_id).strip()}"


def endpoint_source_event_id(link_id: str, change_kind: str, *, suffix: str = "") -> str:
    """Deterministic idempotency key for one Endpoint association mutation."""
    base = f"acq.endpoint.lifecycle:{link_id}:{change_kind}"
    extra = str(suffix or "").strip()
    return f"{base}:{extra}" if extra else base


async def append_endpoint_changed(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    flight_id: str,
    endpoint_id: str,
    change_kind: str,
    source_event_id: str,
    actor_type: str,
    actor_id: str | None = None,
    occurred_at: datetime | None = None,
    note: str | None = None,
) -> AcquisitionActivityEvent:
    contract = get_activity_event_contract("EndpointChanged")
    if contract is None:
        raise RuntimeError("EndpointChanged missing from activity catalog")
    payload: dict[str, Any] = {
        "endpoint_id": str(endpoint_id).strip(),
        "change_kind": str(change_kind).strip(),
    }
    if note is not None and str(note).strip():
        payload["note"] = str(note).strip()
    return await append_activity_event(
        db,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        flight_id=flight_id,
        endpoint_id=str(endpoint_id).strip(),
        event_type="EndpointChanged",
        event_version=contract.event_version,
        payload=payload,
        actor_type=actor_type,
        actor_id=actor_id,
        source_event_id=source_event_id,
        occurred_at=occurred_at,
        provider=None,
    )


__all__ = [
    "CHANGE_KIND_ATTACHED",
    "CHANGE_KIND_DETACHED",
    "CHANGE_KIND_UPDATED",
    "ENDPOINT_KIND_FORM",
    "ENDPOINT_KIND_INTAKE_SOURCE",
    "append_endpoint_changed",
    "endpoint_source_event_id",
    "form_endpoint_id",
    "intake_source_endpoint_id",
]
