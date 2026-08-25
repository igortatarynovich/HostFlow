"""Stage 6 PR-1 — Flight wave compare (read-only analytics compose).

Reuses Stage 3D ``aggregate_campaign_kpi`` + Flight identity. No second KPI ledger.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.kpi_aggregates import (
    CampaignKpiAggregate,
    FlightKpiAggregate,
    KpiAggregateError,
    aggregate_campaign_kpi,
)
from backend.app.models.campaign import Campaign, CampaignRun


@dataclass(frozen=True)
class FlightCompareRow:
    flight_id: str
    code: str
    name: str
    status: str
    is_current: bool
    currency: Optional[str]
    spend: Decimal
    leads: int
    qualified: int
    converted: int
    outcomes_completed: int
    cost_per_lead: Optional[Decimal]
    cost_per_qualified: Optional[Decimal]
    cost_per_outcome: Optional[Decimal]
    outcome_value: Optional[Decimal]
    roi: Optional[Decimal]
    lead_share: Optional[Decimal]
    cpl_delta: Optional[Decimal]
    is_best_cpl: bool

    def to_dict(self) -> dict:
        return {
            "flight_id": self.flight_id,
            "code": self.code,
            "name": self.name,
            "status": self.status,
            "is_current": self.is_current,
            "currency": self.currency,
            "spend": str(self.spend),
            "leads": self.leads,
            "qualified": self.qualified,
            "converted": self.converted,
            "outcomes_completed": self.outcomes_completed,
            "cost_per_lead": None if self.cost_per_lead is None else str(self.cost_per_lead),
            "cost_per_qualified": None
            if self.cost_per_qualified is None
            else str(self.cost_per_qualified),
            "cost_per_outcome": None
            if self.cost_per_outcome is None
            else str(self.cost_per_outcome),
            "outcome_value": None if self.outcome_value is None else str(self.outcome_value),
            "roi": None if self.roi is None else str(self.roi),
            "lead_share": None if self.lead_share is None else str(self.lead_share),
            "cpl_delta": None if self.cpl_delta is None else str(self.cpl_delta),
            "is_best_cpl": self.is_best_cpl,
        }


@dataclass(frozen=True)
class FlightCompareBundle:
    tenant_id: str
    campaign_id: str
    currency: Optional[str]
    spend: Decimal
    leads: int
    qualified: int
    converted: int
    outcomes_completed: int
    cost_per_lead: Optional[Decimal]
    cost_per_qualified: Optional[Decimal]
    cost_per_outcome: Optional[Decimal]
    outcome_value: Optional[Decimal]
    roi: Optional[Decimal]
    flights: tuple[FlightCompareRow, ...]

    def to_dict(self) -> dict:
        return {
            "tenant_id": self.tenant_id,
            "campaign_id": self.campaign_id,
            "currency": self.currency,
            "spend": str(self.spend),
            "leads": self.leads,
            "qualified": self.qualified,
            "converted": self.converted,
            "outcomes_completed": self.outcomes_completed,
            "cost_per_lead": None if self.cost_per_lead is None else str(self.cost_per_lead),
            "cost_per_qualified": None
            if self.cost_per_qualified is None
            else str(self.cost_per_qualified),
            "cost_per_outcome": None
            if self.cost_per_outcome is None
            else str(self.cost_per_outcome),
            "outcome_value": None if self.outcome_value is None else str(self.outcome_value),
            "roi": None if self.roi is None else str(self.roi),
            "flights": [f.to_dict() for f in self.flights],
        }


def _lead_share(flight_leads: int, campaign_leads: int) -> Optional[Decimal]:
    if campaign_leads <= 0:
        return None
    return (Decimal(flight_leads) / Decimal(campaign_leads)).quantize(Decimal("0.0001"))


def _cpl_delta(
    flight_cpl: Optional[Decimal], campaign_cpl: Optional[Decimal]
) -> Optional[Decimal]:
    if flight_cpl is None or campaign_cpl is None:
        return None
    return (Decimal(flight_cpl) - Decimal(campaign_cpl)).quantize(Decimal("0.0001"))


def _best_cpl_flight_ids(aggs: list[FlightKpiAggregate]) -> set[str]:
    defined = [a for a in aggs if a.cost_per_lead is not None]
    if not defined:
        return set()
    best = min(Decimal(a.cost_per_lead) for a in defined)  # type: ignore[arg-type]
    return {
        str(a.flight_id)
        for a in defined
        if a.cost_per_lead is not None and Decimal(a.cost_per_lead) == best
    }


async def compose_flight_compare(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
) -> FlightCompareBundle:
    """Read-only wave compare for one Campaign."""
    campaign = await db.get(Campaign, str(campaign_id))
    if campaign is None or str(campaign.tenant_id) != str(tenant_id):
        raise KpiAggregateError("campaign not found for tenant")

    kpi: CampaignKpiAggregate = await aggregate_campaign_kpi(
        db, tenant_id=str(tenant_id), campaign_id=str(campaign_id)
    )
    best_ids = _best_cpl_flight_ids(list(kpi.flights))
    current_id = str(campaign.current_flight_id) if campaign.current_flight_id else None

    by_id: dict[str, FlightKpiAggregate] = {str(f.flight_id): f for f in kpi.flights}
    rows: list[FlightCompareRow] = []
    for flight_id, agg in by_id.items():
        flight = await db.get(CampaignRun, flight_id)
        if flight is None or str(flight.tenant_id) != str(tenant_id):
            continue
        if str(flight.campaign_id) != str(campaign_id):
            continue
        rows.append(
            FlightCompareRow(
                flight_id=flight_id,
                code=str(flight.code or ""),
                name=str(flight.name or ""),
                status=str(flight.status or ""),
                is_current=bool(current_id and flight_id == current_id),
                currency=agg.currency,
                spend=agg.spend,
                leads=agg.leads,
                qualified=agg.qualified,
                converted=agg.converted,
                outcomes_completed=agg.outcomes_completed,
                cost_per_lead=agg.cost_per_lead,
                cost_per_qualified=agg.cost_per_qualified,
                cost_per_outcome=agg.cost_per_outcome,
                outcome_value=agg.outcome_value,
                roi=agg.roi,
                lead_share=_lead_share(agg.leads, kpi.leads),
                cpl_delta=_cpl_delta(agg.cost_per_lead, kpi.cost_per_lead),
                is_best_cpl=flight_id in best_ids,
            )
        )

    rows.sort(key=lambda r: (r.code, r.flight_id))
    return FlightCompareBundle(
        tenant_id=str(tenant_id),
        campaign_id=str(campaign_id),
        currency=kpi.currency,
        spend=kpi.spend,
        leads=kpi.leads,
        qualified=kpi.qualified,
        converted=kpi.converted,
        outcomes_completed=kpi.outcomes_completed,
        cost_per_lead=kpi.cost_per_lead,
        cost_per_qualified=kpi.cost_per_qualified,
        cost_per_outcome=kpi.cost_per_outcome,
        outcome_value=kpi.outcome_value,
        roi=kpi.roi,
        flights=tuple(rows),
    )


__all__ = [
    "FlightCompareBundle",
    "FlightCompareRow",
    "compose_flight_compare",
]
