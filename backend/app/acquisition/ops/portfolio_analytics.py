"""Stage 6 PR-4 — cross-campaign portfolio analytics (read-only).

Composes company-scoped Campaign list + Stage 3D KPI aggregates.
No second metrics ledger.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.campaign_service import list_campaigns
from backend.app.acquisition.kpi_aggregates import (
    KpiAggregateError,
    aggregate_campaign_kpi,
)

_DEFAULT_LIMIT = 50
_MAX_LIMIT = 100
ZERO = Decimal("0")
MONEY_QUANT = Decimal("0.0001")
RATIO_QUANT = Decimal("0.0001")


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _ratio(spend: Decimal, denominator: int) -> Optional[Decimal]:
    if denominator <= 0:
        return None
    return (Decimal(spend) / Decimal(denominator)).quantize(RATIO_QUANT, rounding=ROUND_HALF_UP)


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
    is_best_cpl: bool

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
            "is_best_cpl": self.is_best_cpl,
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
    campaigns: tuple[PortfolioCampaignRow, ...]
    scan_capped: bool

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
            "campaigns": [c.to_dict() for c in self.campaigns],
            "scan_capped": self.scan_capped,
        }


async def compose_campaign_portfolio(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str | None,
    limit: int = _DEFAULT_LIMIT,
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
            db, tenant_id=str(tenant_id), campaign_id=str(camp.id)
        )
        if kpi.currency is not None:
            if currency is None:
                currency = kpi.currency
            elif currency != kpi.currency:
                raise KpiAggregateError(
                    f"mixed campaign currencies in portfolio: {currency} vs {kpi.currency}"
                )
        draft.append((str(camp.id), str(camp.name or ""), str(camp.status or ""), kpi))

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
    for campaign_id, name, status, kpi in draft:
        total_spend += kpi.spend
        total_leads += kpi.leads
        total_qualified += kpi.qualified
        total_converted += kpi.converted
        total_outcomes += kpi.outcomes_completed
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
                is_best_cpl=is_best,
            )
        )

    total_spend = _money(total_spend)
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
        campaigns=tuple(rows),
        scan_capped=scan_capped,
    )


__all__ = [
    "PortfolioBundle",
    "PortfolioCampaignRow",
    "_DEFAULT_LIMIT",
    "_MAX_LIMIT",
    "compose_campaign_portfolio",
]
