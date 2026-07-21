"""Stage 4 PR-1 — Flight Runtime command service.

Sole operational entry for Launch / Pause / Resume / Complete.
Flight status writes stay in ``transition_flight_status``; Campaign status is
synced only for launch/resume/pause (not complete). Cancel is deferred.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.acquisition.activity.append_service import append_activity_event
from backend.app.acquisition.activity.catalog import get_activity_event_contract
from backend.app.acquisition.flights.lifecycle import (
    FLIGHT_STATUS_ACTIVE,
    FLIGHT_STATUS_COMPLETED,
    FLIGHT_STATUS_PAUSED,
    FlightLifecycleError,
    transition_flight_status,
)
from backend.app.models.acquisition_activity_event import AcquisitionActivityEvent
from backend.app.models.campaign import Campaign, CampaignRun

FlightCommand = Literal["launch", "pause", "resume", "complete"]

_COMMAND_TO_FLIGHT_STATUS: dict[str, str] = {
    "launch": FLIGHT_STATUS_ACTIVE,
    "pause": FLIGHT_STATUS_PAUSED,
    "resume": FLIGHT_STATUS_ACTIVE,
    "complete": FLIGHT_STATUS_COMPLETED,
}

_ALLOWED_COMMANDS = frozenset(_COMMAND_TO_FLIGHT_STATUS)


class FlightRuntimeError(ValueError):
    def __init__(self, detail: str, *, status_code: int = 422) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


@dataclass(frozen=True)
class FlightCommandResult:
    campaign: Campaign
    flight: CampaignRun
    flight_event: AcquisitionActivityEvent
    campaign_event: AcquisitionActivityEvent | None
    command: str


def campaign_sync_source_event_id(
    *, campaign_id: str, event_type: str, flight_source_event_id: str
) -> str:
    """Idempotency key for Campaign sync emit tied to the Flight command event."""
    return f"acq.campaign.sync:{campaign_id}:{event_type}:{flight_source_event_id}"


async def get_flight(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    flight_id: str,
    own_company_id: str | None = None,
) -> tuple[Campaign, CampaignRun]:
    campaign = await _load_campaign(
        db,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        own_company_id=own_company_id,
    )
    flight = next((f for f in (campaign.flights or []) if str(f.id) == str(flight_id)), None)
    if flight is None:
        raise FlightRuntimeError("Flight not found", status_code=404)
    return campaign, flight


async def list_flights(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    own_company_id: str | None = None,
) -> tuple[Campaign, list[CampaignRun]]:
    campaign = await _load_campaign(
        db,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        own_company_id=own_company_id,
    )
    return campaign, list(campaign.flights or [])


async def update_flight_metadata(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    flight_id: str,
    own_company_id: str | None = None,
    name: str | None = None,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
    clear_starts_at: bool = False,
    clear_ends_at: bool = False,
) -> tuple[Campaign, CampaignRun]:
    """Update non-lifecycle Flight fields. Status is never accepted here."""
    campaign, flight = await get_flight(
        db,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        flight_id=flight_id,
        own_company_id=own_company_id,
    )
    if name is not None:
        name_n = str(name).strip()
        if not name_n:
            raise FlightRuntimeError("name cannot be empty", status_code=422)
        flight.name = name_n
    if clear_starts_at:
        flight.starts_at = None
    elif starts_at is not None:
        flight.starts_at = starts_at
    if clear_ends_at:
        flight.ends_at = None
    elif ends_at is not None:
        flight.ends_at = ends_at
    if (
        flight.starts_at is not None
        and flight.ends_at is not None
        and flight.ends_at < flight.starts_at
    ):
        raise FlightRuntimeError("ends_at must be >= starts_at", status_code=422)
    await db.flush()
    return campaign, flight


async def execute_flight_command(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    flight_id: str,
    command: str,
    actor_type: str,
    actor_id: str | None = None,
    reason: str | None = None,
    occurred_at: datetime | None = None,
    own_company_id: str | None = None,
) -> FlightCommandResult:
    """Apply a Flight Runtime command and sync Campaign status when required.

    Coupling (same transaction; caller owns commit):
    - launch / resume → Campaign ``active`` + ``CampaignActivated`` if status changed
    - pause → Campaign ``paused`` + ``CampaignPaused`` if status changed
    - complete → Flight only (Campaign status untouched)
    """
    cmd = str(command or "").strip().lower()
    if cmd not in _ALLOWED_COMMANDS:
        raise FlightRuntimeError(
            f"unsupported flight command: {command!r}",
            status_code=422,
        )
    target_status = _COMMAND_TO_FLIGHT_STATUS[cmd]

    campaign, flight = await get_flight(
        db,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        flight_id=flight_id,
        own_company_id=own_company_id,
    )

    try:
        flight_event = await transition_flight_status(
            db,
            flight=flight,
            new_status=target_status,
            actor_type=actor_type,
            actor_id=actor_id,
            reason=reason,
            occurred_at=occurred_at,
        )
    except FlightLifecycleError as exc:
        raise FlightRuntimeError(str(exc.detail), status_code=422) from exc

    campaign_event: AcquisitionActivityEvent | None = None
    if cmd in {"launch", "resume"}:
        campaign_event = await _sync_campaign_status(
            db,
            campaign=campaign,
            flight=flight,
            target_status="active",
            event_type="CampaignActivated",
            flight_source_event_id=str(flight_event.source_event_id),
            actor_type=actor_type,
            actor_id=actor_id,
            occurred_at=occurred_at,
            note=reason,
        )
    elif cmd == "pause":
        campaign_event = await _sync_campaign_status(
            db,
            campaign=campaign,
            flight=flight,
            target_status="paused",
            event_type="CampaignPaused",
            flight_source_event_id=str(flight_event.source_event_id),
            actor_type=actor_type,
            actor_id=actor_id,
            occurred_at=occurred_at,
            note=reason,
        )

    return FlightCommandResult(
        campaign=campaign,
        flight=flight,
        flight_event=flight_event,
        campaign_event=campaign_event,
        command=cmd,
    )


async def _load_campaign(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    own_company_id: str | None,
) -> Campaign:
    stmt = (
        select(Campaign)
        .where(Campaign.id == campaign_id, Campaign.tenant_id == tenant_id)
        .options(selectinload(Campaign.flights))
    )
    if own_company_id:
        stmt = stmt.where(Campaign.own_company_id == own_company_id)
    row = await db.execute(stmt)
    campaign = row.scalar_one_or_none()
    if campaign is None:
        raise FlightRuntimeError("Campaign not found", status_code=404)
    return campaign


async def _sync_campaign_status(
    db: AsyncSession,
    *,
    campaign: Campaign,
    flight: CampaignRun,
    target_status: str,
    event_type: str,
    flight_source_event_id: str,
    actor_type: str,
    actor_id: str | None,
    occurred_at: datetime | None,
    note: str | None,
) -> AcquisitionActivityEvent | None:
    current = str(campaign.status or "").strip().lower()
    target = str(target_status).strip().lower()
    if current == target:
        return None

    campaign.status = target
    await db.flush()

    contract = get_activity_event_contract(event_type)
    if contract is None:
        raise FlightRuntimeError(f"unknown campaign event_type: {event_type!r}")

    payload: dict[str, Any] = {}
    if note is not None and str(note).strip():
        payload["note"] = str(note).strip()

    source_event_id = campaign_sync_source_event_id(
        campaign_id=str(campaign.id),
        event_type=event_type,
        flight_source_event_id=flight_source_event_id,
    )
    return await append_activity_event(
        db,
        tenant_id=str(campaign.tenant_id),
        campaign_id=str(campaign.id),
        flight_id=str(flight.id),
        event_type=event_type,
        event_version=contract.event_version,
        payload=payload,
        actor_type=actor_type,
        actor_id=actor_id,
        source_event_id=source_event_id,
        occurred_at=occurred_at,
        causation_id=flight_source_event_id,
        provider=None,
    )


__all__ = [
    "FlightCommand",
    "FlightCommandResult",
    "FlightRuntimeError",
    "campaign_sync_source_event_id",
    "execute_flight_command",
    "get_flight",
    "list_flights",
    "update_flight_metadata",
]
