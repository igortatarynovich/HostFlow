"""Stage 6 PR-4 — cross-campaign portfolio analytics (read-only).

Composes company-scoped Campaign list + Stage 3D KPI aggregates.
Optional date window filters spend / attributions by ``created_at``.
No second metrics ledger.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.campaign_service import list_campaigns
from backend.app.acquisition.kpi_aggregates import (
    KpiAggregateError,
    _roi,
    aggregate_campaign_kpi,
)
from backend.app.models.campaign import CampaignFlightSpendEntry, CampaignResultAttribution

_DEFAULT_LIMIT = 50
_MAX_LIMIT = 100
ZERO = Decimal("0")
MONEY_QUANT = Decimal("0.0001")
RATIO_QUANT = Decimal("0.0001")

_NOTE_IMP_RE = re.compile(r"\bimpressions=(\d+)\b", re.I)
_NOTE_REACH_RE = re.compile(r"\breach=(\d+)\b", re.I)


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _ratio(spend: Decimal, denominator: int) -> Optional[Decimal]:
    if denominator <= 0:
        return None
    return (Decimal(spend) / Decimal(denominator)).quantize(RATIO_QUANT, rounding=ROUND_HALF_UP)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _day_key(value: datetime | None) -> date:
    if value is None:
        return date.min
    return _as_utc(value).date()


def _parse_note_metrics(note: str | None) -> tuple[int, int]:
    text = str(note or "")
    imp_m = _NOTE_IMP_RE.search(text)
    reach_m = _NOTE_REACH_RE.search(text)
    return (
        int(imp_m.group(1)) if imp_m else 0,
        int(reach_m.group(1)) if reach_m else 0,
    )


@dataclass(frozen=True)
class PortfolioCampaignRow:
    campaign_id: str
    name: str
    status: str
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
    is_best_cpl: bool
    impressions: Optional[int] = None
    reach: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "campaign_id": self.campaign_id,
            "name": self.name,
            "status": self.status,
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
            "is_best_cpl": self.is_best_cpl,
            "impressions": self.impressions,
            "reach": self.reach,
        }


@dataclass(frozen=True)
class PortfolioDayCampaignPoint:
    day: str
    campaign_id: str
    spend: Decimal
    leads: int
    impressions: int
    reach: int

    def to_dict(self) -> dict:
        return {
            "day": self.day,
            "campaign_id": self.campaign_id,
            "spend": str(self.spend),
            "leads": self.leads,
            "impressions": self.impressions,
            "reach": self.reach,
        }


@dataclass(frozen=True)
class PortfolioDayPoint:
    day: str
    spend: Decimal
    leads: int
    impressions: int
    reach: int

    def to_dict(self) -> dict:
        return {
            "day": self.day,
            "spend": str(self.spend),
            "leads": self.leads,
            "impressions": self.impressions,
            "reach": self.reach,
        }


@dataclass(frozen=True)
class PortfolioBundle:
    tenant_id: str
    own_company_id: Optional[str]
    currency: Optional[str]
    spend: Decimal
    leads: int
    qualified: int
    converted: int
    outcomes_completed: int
    cost_per_lead: Optional[Decimal]
    cost_per_outcome: Optional[Decimal]
    outcome_value: Optional[Decimal]
    roi: Optional[Decimal]
    campaigns: tuple[PortfolioCampaignRow, ...]
    scan_capped: bool
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    series: tuple[PortfolioDayPoint, ...] = ()
    series_by_campaign: tuple[PortfolioDayCampaignPoint, ...] = ()
    impressions: Optional[int] = None
    reach: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "tenant_id": self.tenant_id,
            "own_company_id": self.own_company_id,
            "currency": self.currency,
            "spend": str(self.spend),
            "leads": self.leads,
            "qualified": self.qualified,
            "converted": self.converted,
            "outcomes_completed": self.outcomes_completed,
            "cost_per_lead": None if self.cost_per_lead is None else str(self.cost_per_lead),
            "cost_per_outcome": None
            if self.cost_per_outcome is None
            else str(self.cost_per_outcome),
            "outcome_value": None if self.outcome_value is None else str(self.outcome_value),
            "roi": None if self.roi is None else str(self.roi),
            "campaigns": [c.to_dict() for c in self.campaigns],
            "scan_capped": self.scan_capped,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "series": [p.to_dict() for p in self.series],
            "series_by_campaign": [p.to_dict() for p in self.series_by_campaign],
            "impressions": self.impressions,
            "reach": self.reach,
        }


async def _reach_impressions_by_campaign(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_ids: list[str],
    date_from: Optional[datetime],
    date_to: Optional[datetime],
) -> dict[str, tuple[int, int]]:
    if not campaign_ids:
        return {}
    q = select(CampaignFlightSpendEntry).where(
        CampaignFlightSpendEntry.tenant_id == str(tenant_id),
        CampaignFlightSpendEntry.campaign_id.in_(campaign_ids),
    )
    if date_from is not None:
        q = q.where(CampaignFlightSpendEntry.created_at >= date_from)
    if date_to is not None:
        q = q.where(CampaignFlightSpendEntry.created_at < date_to)
    rows = (await db.execute(q)).scalars().all()
    out: dict[str, list[int]] = {}
    for row in rows:
        cid = str(row.campaign_id)
        imp, reach = _parse_note_metrics(row.note)
        bucket = out.setdefault(cid, [0, 0])
        bucket[0] += imp
        bucket[1] += reach
    return {cid: (vals[0], vals[1]) for cid, vals in out.items()}


async def _compose_series(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_ids: list[str],
    date_from: Optional[datetime],
    date_to: Optional[datetime],
) -> tuple[tuple[PortfolioDayPoint, ...], tuple[PortfolioDayCampaignPoint, ...]]:
    if not campaign_ids:
        return (), ()

    spend_q = select(CampaignFlightSpendEntry).where(
        CampaignFlightSpendEntry.tenant_id == str(tenant_id),
        CampaignFlightSpendEntry.campaign_id.in_(campaign_ids),
    )
    attr_q = select(CampaignResultAttribution).where(
        CampaignResultAttribution.tenant_id == str(tenant_id),
        CampaignResultAttribution.campaign_id.in_(campaign_ids),
    )
    if date_from is not None:
        spend_q = spend_q.where(CampaignFlightSpendEntry.created_at >= date_from)
        attr_q = attr_q.where(CampaignResultAttribution.created_at >= date_from)
    if date_to is not None:
        spend_q = spend_q.where(CampaignFlightSpendEntry.created_at < date_to)
        attr_q = attr_q.where(CampaignResultAttribution.created_at < date_to)

    spend_rows = (await db.execute(spend_q)).scalars().all()
    attr_rows = (await db.execute(attr_q)).scalars().all()
    if not spend_rows and not attr_rows:
        return (), ()

    spend_by: dict[tuple[str, date], Decimal] = {}
    imp_by: dict[tuple[str, date], int] = {}
    reach_by: dict[tuple[str, date], int] = {}
    for row in spend_rows:
        key = (str(row.campaign_id), _day_key(row.created_at))
        spend_by[key] = _money(spend_by.get(key, ZERO) + _money(Decimal(row.amount)))
        imp, reach = _parse_note_metrics(row.note)
        imp_by[key] = imp_by.get(key, 0) + imp
        reach_by[key] = reach_by.get(key, 0) + reach

    leads_by: dict[tuple[str, date], set[tuple[str, str]]] = {}
    for attr in attr_rows:
        key = (str(attr.campaign_id), _day_key(attr.created_at))
        leads_by.setdefault(key, set()).add((str(attr.result_type), str(attr.result_id)))

    keys = set(spend_by) | set(leads_by) | set(imp_by) | set(reach_by)
    days_present = sorted({d for _, d in keys if d != date.min})
    if not days_present:
        return (), ()

    start_day = _as_utc(date_from).date() if date_from else days_present[0]
    end_exclusive = (
        _as_utc(date_to).date()
        if date_to
        else days_present[-1] + timedelta(days=1)
    )

    by_campaign: list[PortfolioDayCampaignPoint] = []
    spend_day: dict[date, Decimal] = {}
    leads_day: dict[date, int] = {}
    imp_day: dict[date, int] = {}
    reach_day: dict[date, int] = {}

    for campaign_id, day in sorted(keys, key=lambda x: (x[1], x[0])):
        if day < start_day or day >= end_exclusive:
            continue
        spend = _money(spend_by.get((campaign_id, day), ZERO))
        leads = len(leads_by.get((campaign_id, day), set()))
        impressions = imp_by.get((campaign_id, day), 0)
        reach = reach_by.get((campaign_id, day), 0)
        if spend <= ZERO and leads <= 0 and impressions <= 0 and reach <= 0:
            continue
        by_campaign.append(
            PortfolioDayCampaignPoint(
                day=day.isoformat(),
                campaign_id=campaign_id,
                spend=spend,
                leads=leads,
                impressions=impressions,
                reach=reach,
            )
        )
        spend_day[day] = _money(spend_day.get(day, ZERO) + spend)
        leads_day[day] = leads_day.get(day, 0) + leads
        imp_day[day] = imp_day.get(day, 0) + impressions
        reach_day[day] = reach_day.get(day, 0) + reach

    # Sparse series — only days with activity (keeps payload small for long windows).
    points = [
        PortfolioDayPoint(
            day=d.isoformat(),
            spend=_money(spend_day.get(d, ZERO)),
            leads=leads_day.get(d, 0),
            impressions=imp_day.get(d, 0),
            reach=reach_day.get(d, 0),
        )
        for d in sorted(spend_day.keys() | leads_day.keys())
    ]
    return tuple(points), tuple(by_campaign)


async def compose_campaign_portfolio(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str | None,
    limit: int = _DEFAULT_LIMIT,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> PortfolioBundle:
    """Company-scoped Campaign KPI portfolio (read-only)."""
    lim = max(1, min(int(limit or _DEFAULT_LIMIT), _MAX_LIMIT))
    # Fetch lim+1 to detect cap without a second count query.
    campaigns = await list_campaigns(
        db,
        tenant_id=str(tenant_id),
        own_company_id=own_company_id,
        limit=lim + 1,
        offset=0,
    )
    scan_capped = len(campaigns) > lim
    campaigns = campaigns[:lim]

    draft: list[tuple[str, str, str, object]] = []
    currency: Optional[str] = None
    for camp in campaigns:
        kpi = await aggregate_campaign_kpi(
            db,
            tenant_id=str(tenant_id),
            campaign_id=str(camp.id),
            date_from=date_from,
            date_to=date_to,
        )
        if kpi.currency is not None:
            if currency is None:
                currency = kpi.currency
            elif currency != kpi.currency:
                raise KpiAggregateError(
                    f"mixed campaign currencies in portfolio: {currency} vs {kpi.currency}"
                )
        draft.append((str(camp.id), str(camp.name or ""), str(camp.status or ""), kpi))

    metrics = await _reach_impressions_by_campaign(
        db,
        tenant_id=str(tenant_id),
        campaign_ids=[cid for cid, _, _, _ in draft],
        date_from=date_from,
        date_to=date_to,
    )

    best_cpl: Optional[Decimal] = None
    for _, _, _, kpi in draft:
        if kpi.cost_per_lead is not None:
            cpl = Decimal(kpi.cost_per_lead)
            if best_cpl is None or cpl < best_cpl:
                best_cpl = cpl

    rows: list[PortfolioCampaignRow] = []
    total_spend = ZERO
    total_leads = 0
    total_qualified = 0
    total_converted = 0
    total_outcomes = 0
    total_value = ZERO
    any_value = False
    total_imp = 0
    total_reach = 0
    any_imp = False
    for campaign_id, name, status, kpi in draft:
        total_spend += kpi.spend
        total_leads += kpi.leads
        total_qualified += kpi.qualified
        total_converted += kpi.converted
        total_outcomes += kpi.outcomes_completed
        if kpi.outcome_value is not None:
            total_value += kpi.outcome_value
            any_value = True
        imp, reach = metrics.get(campaign_id, (0, 0))
        if imp or reach:
            any_imp = True
        total_imp += imp
        total_reach += reach
        is_best = (
            best_cpl is not None
            and kpi.cost_per_lead is not None
            and Decimal(kpi.cost_per_lead) == best_cpl
        )
        rows.append(
            PortfolioCampaignRow(
                campaign_id=campaign_id,
                name=name,
                status=status,
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
                is_best_cpl=is_best,
                impressions=imp if any_imp else None,
                reach=reach if any_imp else None,
            )
        )

    series, series_by_campaign = await _compose_series(
        db,
        tenant_id=str(tenant_id),
        campaign_ids=[cid for cid, _, _, _ in draft],
        date_from=date_from,
        date_to=date_to,
    )

    total_spend = _money(total_spend)
    outcome_value = _money(total_value) if any_value else None
    return PortfolioBundle(
        tenant_id=str(tenant_id),
        own_company_id=str(own_company_id) if own_company_id else None,
        currency=currency,
        spend=total_spend,
        leads=total_leads,
        qualified=total_qualified,
        converted=total_converted,
        outcomes_completed=total_outcomes,
        cost_per_lead=_ratio(total_spend, total_leads),
        cost_per_outcome=_ratio(total_spend, total_outcomes),
        outcome_value=outcome_value,
        roi=_roi(outcome_value, total_spend),
        campaigns=tuple(rows),
        scan_capped=scan_capped,
        date_from=_as_utc(date_from).date().isoformat() if date_from else None,
        date_to=(_as_utc(date_to).date() - timedelta(days=1)).isoformat() if date_to else None,
        series=series,
        series_by_campaign=series_by_campaign,
        impressions=total_imp if any_imp else None,
        reach=total_reach if any_imp else None,
    )


__all__ = [
    "PortfolioBundle",
    "PortfolioCampaignRow",
    "PortfolioDayCampaignPoint",
    "PortfolioDayPoint",
    "_DEFAULT_LIMIT",
    "_MAX_LIMIT",
    "compose_campaign_portfolio",
]
