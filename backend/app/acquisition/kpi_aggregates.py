"""ADR-024 Stage 3D PR-3 — Acquisition KPI aggregates (read model).

Computes Flight and Campaign KPIs from canonical sources. Does **not** write
KPI fields onto Campaign/Flight rows.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.outcome_service import STATUS_COMPLETED
from backend.app.models.campaign import (
    Campaign,
    CampaignFlightSpendEntry,
    CampaignOutcome,
    CampaignResultAttribution,
    CampaignResultQualification,
    CampaignRun,
)

ZERO = Decimal("0")
MONEY_QUANT = Decimal("0.0001")
RATIO_QUANT = Decimal("0.0001")


class KpiAggregateError(ValueError):
    """KPI aggregation contract violation."""


@dataclass(frozen=True)
class FlightKpiAggregate:
    tenant_id: str
    campaign_id: str
    flight_id: str
    currency: Optional[str]
    spend: Decimal
    leads: int
    qualified: int
    converted: int
    outcomes_completed: int
    cost_per_lead: Optional[Decimal]
    cost_per_qualified: Optional[Decimal]
    cost_per_outcome: Optional[Decimal]

    def to_dict(self) -> dict:
        return {
            "tenant_id": self.tenant_id,
            "campaign_id": self.campaign_id,
            "flight_id": self.flight_id,
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
        }


@dataclass(frozen=True)
class CampaignKpiAggregate:
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
    flights: tuple[FlightKpiAggregate, ...]

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
            "flights": [f.to_dict() for f in self.flights],
        }


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _ratio(spend: Decimal, denominator: int) -> Optional[Decimal]:
    if denominator <= 0:
        return None
    return (Decimal(spend) / Decimal(denominator)).quantize(RATIO_QUANT, rounding=ROUND_HALF_UP)


def _normalize_currency(code: str) -> str:
    c = str(code or "").strip().upper()
    if len(c) != 3 or not c.isalpha():
        raise KpiAggregateError(f"invalid currency: {code!r}")
    return c


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def record_flight_spend(
    db: AsyncSession,
    *,
    tenant_id: str,
    flight_id: str,
    amount: Decimal | str | int,
    currency: str,
    note: Optional[str] = None,
) -> CampaignFlightSpendEntry:
    """Write canonical spend source for a Flight (not a KPI field on Campaign)."""
    flight = await db.get(CampaignRun, str(flight_id))
    if flight is None or str(flight.tenant_id) != str(tenant_id):
        raise KpiAggregateError("flight not found for tenant")
    amt = _money(Decimal(amount))
    if amt < ZERO:
        raise KpiAggregateError("spend amount must be >= 0")
    row = CampaignFlightSpendEntry(
        tenant_id=str(tenant_id),
        campaign_id=str(flight.campaign_id),
        campaign_run_id=str(flight.id),
        amount=amt,
        currency=_normalize_currency(currency),
        note=(str(note)[:255] if note else None),
    )
    db.add(row)
    await db.flush()
    return row


async def qualify_attribution(
    db: AsyncSession,
    *,
    tenant_id: str,
    attribution_id: str,
) -> CampaignResultQualification:
    """Explicit qualification contract — only these attributions count as Qualified."""
    attr = await db.get(CampaignResultAttribution, str(attribution_id))
    if attr is None or str(attr.tenant_id) != str(tenant_id):
        raise KpiAggregateError("attribution not found for tenant")
    existing = await db.execute(
        select(CampaignResultQualification).where(
            CampaignResultQualification.tenant_id == str(tenant_id),
            CampaignResultQualification.attribution_id == str(attribution_id),
        )
    )
    row = existing.scalar_one_or_none()
    if row is not None:
        return row
    row = CampaignResultQualification(
        tenant_id=str(tenant_id),
        attribution_id=str(attribution_id),
        qualified_at=_now(),
    )
    db.add(row)
    await db.flush()
    return row


async def aggregate_flight_kpi(
    db: AsyncSession,
    *,
    tenant_id: str,
    flight_id: str,
) -> FlightKpiAggregate:
    flight = await db.get(CampaignRun, str(flight_id))
    if flight is None or str(flight.tenant_id) != str(tenant_id):
        raise KpiAggregateError("flight not found for tenant")

    spend_rows = (
        await db.execute(
            select(CampaignFlightSpendEntry).where(
                CampaignFlightSpendEntry.tenant_id == str(tenant_id),
                CampaignFlightSpendEntry.campaign_run_id == str(flight_id),
            )
        )
    ).scalars().all()

    currency: Optional[str] = None
    spend = ZERO
    for row in spend_rows:
        cur = _normalize_currency(row.currency)
        if currency is None:
            currency = cur
        elif currency != cur:
            raise KpiAggregateError(
                f"mixed currencies in flight spend: {currency} vs {cur}"
            )
        spend += _money(Decimal(row.amount))
    spend = _money(spend)

    attributions = (
        await db.execute(
            select(CampaignResultAttribution).where(
                CampaignResultAttribution.tenant_id == str(tenant_id),
                CampaignResultAttribution.campaign_run_id == str(flight_id),
            )
        )
    ).scalars().all()

    # Unique Result identity — not submit-attempt count.
    lead_keys = {(str(a.result_type), str(a.result_id)) for a in attributions}
    leads = len(lead_keys)
    attr_ids = {str(a.id) for a in attributions}

    qualified = 0
    if attr_ids:
        q_rows = (
            await db.execute(
                select(CampaignResultQualification.attribution_id).where(
                    CampaignResultQualification.tenant_id == str(tenant_id),
                    CampaignResultQualification.attribution_id.in_(attr_ids),
                )
            )
        ).scalars().all()
        qualified = len({str(x) for x in q_rows})

    # Successful Outcomes = completed only (failed/cancelled excluded).
    # Cost per Outcome uses this count — soft-revoke of ledger links does not change it.
    outcomes_completed = (
        await db.execute(
            select(CampaignOutcome).where(
                CampaignOutcome.tenant_id == str(tenant_id),
                CampaignOutcome.campaign_run_id == str(flight_id),
                CampaignOutcome.status == STATUS_COMPLETED,
            )
        )
    ).scalars().all()
    outcomes_n = len(outcomes_completed)
    converted = outcomes_n

    return FlightKpiAggregate(
        tenant_id=str(tenant_id),
        campaign_id=str(flight.campaign_id),
        flight_id=str(flight.id),
        currency=currency,
        spend=spend,
        leads=leads,
        qualified=qualified,
        converted=converted,
        outcomes_completed=outcomes_n,
        cost_per_lead=_ratio(spend, leads),
        cost_per_qualified=_ratio(spend, qualified),
        cost_per_outcome=_ratio(spend, outcomes_n),
    )


async def aggregate_campaign_kpi(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
) -> CampaignKpiAggregate:
    campaign = await db.get(Campaign, str(campaign_id))
    if campaign is None or str(campaign.tenant_id) != str(tenant_id):
        raise KpiAggregateError("campaign not found for tenant")

    flights = (
        await db.execute(
            select(CampaignRun).where(
                CampaignRun.tenant_id == str(tenant_id),
                CampaignRun.campaign_id == str(campaign_id),
            )
        )
    ).scalars().all()

    flight_aggs: list[FlightKpiAggregate] = []
    for flight in flights:
        flight_aggs.append(
            await aggregate_flight_kpi(db, tenant_id=str(tenant_id), flight_id=str(flight.id))
        )

    currency: Optional[str] = None
    spend = ZERO
    leads = 0
    qualified = 0
    converted = 0
    outcomes_completed = 0
    for fa in flight_aggs:
        if fa.currency is not None:
            if currency is None:
                currency = fa.currency
            elif currency != fa.currency:
                raise KpiAggregateError(
                    f"mixed flight currencies in campaign: {currency} vs {fa.currency}"
                )
        spend += fa.spend
        leads += fa.leads
        qualified += fa.qualified
        converted += fa.converted
        outcomes_completed += fa.outcomes_completed

    spend = _money(spend)
    return CampaignKpiAggregate(
        tenant_id=str(tenant_id),
        campaign_id=str(campaign_id),
        currency=currency,
        spend=spend,
        leads=leads,
        qualified=qualified,
        converted=converted,
        outcomes_completed=outcomes_completed,
        cost_per_lead=_ratio(spend, leads),
        cost_per_qualified=_ratio(spend, qualified),
        cost_per_outcome=_ratio(spend, outcomes_completed),
        flights=tuple(flight_aggs),
    )
