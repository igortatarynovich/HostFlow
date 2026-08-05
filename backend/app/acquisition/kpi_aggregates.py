"""ADR-024 Stage 3D PR-3 — Acquisition KPI aggregates (read model).

Computes Flight and Campaign KPIs from canonical sources. Does **not** write
KPI fields onto Campaign/Flight rows.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy import func, select
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
    outcome_value: Optional[Decimal]
    roi: Optional[Decimal]

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
            "outcome_value": None if self.outcome_value is None else str(self.outcome_value),
            "roi": None if self.roi is None else str(self.roi),
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
    outcome_value: Optional[Decimal]
    roi: Optional[Decimal]
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
            "outcome_value": None if self.outcome_value is None else str(self.outcome_value),
            "roi": None if self.roi is None else str(self.roi),
            "flights": [f.to_dict() for f in self.flights],
        }


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _ratio(spend: Decimal, denominator: int) -> Optional[Decimal]:
    if denominator <= 0:
        return None
    return (Decimal(spend) / Decimal(denominator)).quantize(RATIO_QUANT, rounding=ROUND_HALF_UP)


def _roi(outcome_value: Optional[Decimal], spend: Decimal) -> Optional[Decimal]:
    """Locked Stage 6 formula: (outcome_value − spend) / spend when spend > 0."""
    if outcome_value is None or spend <= ZERO:
        return None
    return ((Decimal(outcome_value) - Decimal(spend)) / Decimal(spend)).quantize(
        RATIO_QUANT, rounding=ROUND_HALF_UP
    )


def _sum_outcome_values(
    outcomes: list[CampaignOutcome],
    *,
    spend_currency: Optional[str],
) -> Optional[Decimal]:
    """Sum declared commercial values on completed outcomes; null if none set."""
    total = ZERO
    value_currency: Optional[str] = None
    any_value = False
    for row in outcomes:
        if row.commercial_value_amount is None or not row.commercial_value_currency:
            continue
        cur = _normalize_currency(str(row.commercial_value_currency))
        if value_currency is None:
            value_currency = cur
        elif value_currency != cur:
            raise KpiAggregateError(
                f"mixed currencies in outcome commercial value: {value_currency} vs {cur}"
            )
        if spend_currency is not None and cur != spend_currency:
            raise KpiAggregateError(
                f"outcome value currency {cur} does not match spend currency {spend_currency}"
            )
        total += _money(Decimal(row.commercial_value_amount))
        any_value = True
    if not any_value:
        return None
    return _money(total)


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
    spent_at: Optional[datetime] = None,
) -> CampaignFlightSpendEntry:
    """Write canonical spend source for a Flight (not a KPI field on Campaign).

    ``spent_at`` stamps ``created_at`` / ``updated_at`` so windowed KPI / cohorts
    can filter by the real spend day (e.g. Meta Ads daily import).
    """
    flight = await db.get(CampaignRun, str(flight_id))
    if flight is None or str(flight.tenant_id) != str(tenant_id):
        raise KpiAggregateError("flight not found for tenant")
    amt = _money(Decimal(amount))
    if amt < ZERO:
        raise KpiAggregateError("spend amount must be >= 0")
    stamp = spent_at or _now()
    row = CampaignFlightSpendEntry(
        tenant_id=str(tenant_id),
        campaign_id=str(flight.campaign_id),
        campaign_run_id=str(flight.id),
        amount=amt,
        currency=_normalize_currency(currency),
        note=(str(note)[:255] if note else None),
        created_at=stamp,
        updated_at=stamp,
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
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> FlightKpiAggregate:
    flight = await db.get(CampaignRun, str(flight_id))
    if flight is None or str(flight.tenant_id) != str(tenant_id):
        raise KpiAggregateError("flight not found for tenant")

    spend_q = select(CampaignFlightSpendEntry).where(
        CampaignFlightSpendEntry.tenant_id == str(tenant_id),
        CampaignFlightSpendEntry.campaign_run_id == str(flight_id),
    )
    if date_from is not None:
        spend_q = spend_q.where(CampaignFlightSpendEntry.created_at >= date_from)
    if date_to is not None:
        spend_q = spend_q.where(CampaignFlightSpendEntry.created_at < date_to)
    spend_rows = (await db.execute(spend_q)).scalars().all()

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

    attr_q = select(CampaignResultAttribution).where(
        CampaignResultAttribution.tenant_id == str(tenant_id),
        CampaignResultAttribution.campaign_run_id == str(flight_id),
    )
    if date_from is not None:
        attr_q = attr_q.where(CampaignResultAttribution.created_at >= date_from)
    if date_to is not None:
        attr_q = attr_q.where(CampaignResultAttribution.created_at < date_to)
    attributions = (await db.execute(attr_q)).scalars().all()

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
    outcome_q = select(CampaignOutcome).where(
        CampaignOutcome.tenant_id == str(tenant_id),
        CampaignOutcome.campaign_run_id == str(flight_id),
        CampaignOutcome.status == STATUS_COMPLETED,
    )
    if date_from is not None or date_to is not None:
        # Prefer completed_at; fall back to created_at for incomplete stamps.
        stamp = func.coalesce(CampaignOutcome.completed_at, CampaignOutcome.created_at)
        if date_from is not None:
            outcome_q = outcome_q.where(stamp >= date_from)
        if date_to is not None:
            outcome_q = outcome_q.where(stamp < date_to)
    outcomes_completed = (await db.execute(outcome_q)).scalars().all()
    outcomes_n = len(outcomes_completed)
    converted = outcomes_n
    outcome_value = _sum_outcome_values(list(outcomes_completed), spend_currency=currency)

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
        outcome_value=outcome_value,
        roi=_roi(outcome_value, spend),
    )


async def aggregate_campaign_kpi(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
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
            await aggregate_flight_kpi(
                db,
                tenant_id=str(tenant_id),
                flight_id=str(flight.id),
                date_from=date_from,
                date_to=date_to,
            )
        )

    currency: Optional[str] = None
    spend = ZERO
    leads = 0
    qualified = 0
    converted = 0
    outcomes_completed = 0
    outcome_value_total = ZERO
    any_outcome_value = False
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
        if fa.outcome_value is not None:
            outcome_value_total += fa.outcome_value
            any_outcome_value = True

    spend = _money(spend)
    outcome_value = _money(outcome_value_total) if any_outcome_value else None
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
        outcome_value=outcome_value,
        roi=_roi(outcome_value, spend),
        flights=tuple(flight_aggs),
    )
