"""Stage 4 PR-3 — Flight Runtime snapshot (ops shell read model)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.flights.runtime_commands import (
    FlightRuntimeError,
    get_flight,
)
from backend.app.acquisition.kpi_aggregates import (
    FlightKpiAggregate,
    KpiAggregateError,
    aggregate_flight_kpi,
)
from backend.app.models.campaign import CampaignRun


@dataclass(frozen=True)
class EndpointsSummary:
    forms_total: int
    forms_active: int
    intake_sources_total: int
    intake_sources_active: int

    def to_dict(self) -> dict[str, int]:
        return {
            "forms_total": self.forms_total,
            "forms_active": self.forms_active,
            "intake_sources_total": self.intake_sources_total,
            "intake_sources_active": self.intake_sources_active,
        }


@dataclass(frozen=True)
class FlightRuntimeSnapshot:
    tenant_id: str
    campaign_id: str
    flight_id: str
    campaign_status: str
    flight_status: str
    flight_name: str
    flight_code: str
    starts_at: datetime | None
    ends_at: datetime | None
    is_current: bool
    endpoints: EndpointsSummary
    kpi: FlightKpiAggregate
    generated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "campaign_id": self.campaign_id,
            "flight_id": self.flight_id,
            "campaign_status": self.campaign_status,
            "flight_status": self.flight_status,
            "flight_name": self.flight_name,
            "flight_code": self.flight_code,
            "starts_at": self.starts_at.isoformat() if self.starts_at else None,
            "ends_at": self.ends_at.isoformat() if self.ends_at else None,
            "is_current": self.is_current,
            "endpoints": self.endpoints.to_dict(),
            "kpi": self.kpi.to_dict(),
            "generated_at": self.generated_at.isoformat(),
        }


def _endpoints_summary(flight: CampaignRun) -> EndpointsSummary:
    forms = list(flight.form_links or [])
    sources = list(flight.intake_source_links or [])
    return EndpointsSummary(
        forms_total=len(forms),
        forms_active=sum(1 for f in forms if bool(f.is_active)),
        intake_sources_total=len(sources),
        intake_sources_active=sum(1 for s in sources if bool(s.is_active)),
    )


async def get_flight_runtime_snapshot(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    flight_id: str,
    own_company_id: str | None = None,
) -> FlightRuntimeSnapshot:
    """Compose Flight + Campaign status + endpoint counts + Flight KPI."""
    try:
        campaign, flight = await get_flight(
            db,
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            flight_id=flight_id,
            own_company_id=own_company_id,
        )
    except FlightRuntimeError:
        raise
    try:
        kpi = await aggregate_flight_kpi(
            db, tenant_id=str(tenant_id), flight_id=str(flight.id)
        )
    except KpiAggregateError as exc:
        raise FlightRuntimeError(str(exc), status_code=422) from exc

    return FlightRuntimeSnapshot(
        tenant_id=str(tenant_id),
        campaign_id=str(campaign.id),
        flight_id=str(flight.id),
        campaign_status=str(campaign.status or ""),
        flight_status=str(flight.status or ""),
        flight_name=str(flight.name or ""),
        flight_code=str(flight.code or ""),
        starts_at=flight.starts_at,
        ends_at=flight.ends_at,
        is_current=str(campaign.current_flight_id or "") == str(flight.id),
        endpoints=_endpoints_summary(flight),
        kpi=kpi,
        generated_at=datetime.now(timezone.utc),
    )


__all__ = [
    "EndpointsSummary",
    "FlightRuntimeSnapshot",
    "get_flight_runtime_snapshot",
]
