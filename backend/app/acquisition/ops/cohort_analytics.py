"""Stage 6 PR-2/PR-3 — windowed cohort analytics (read-only).

Buckets leads / spend / completed outcomes by UTC calendar day or ISO week
(Monday start) from existing Attribution, Spend, and Outcome rows.
No second KPI ledger.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.kpi_aggregates import KpiAggregateError
from backend.app.acquisition.outcome_service import STATUS_COMPLETED
from backend.app.models.campaign import (
    Campaign,
    CampaignFlightSpendEntry,
    CampaignOutcome,
    CampaignResultAttribution,
)

_DEFAULT_WINDOW_DAYS = 14
_MAX_WINDOW_DAYS = 90
_ALLOWED_BUCKETS = frozenset({"day", "week"})
ZERO = Decimal("0")
MONEY_QUANT = Decimal("0.0001")
RATIO_QUANT = Decimal("0.0001")

BucketKind = Literal["day", "week"]


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _ratio(spend: Decimal, denominator: int) -> Optional[Decimal]:
    if denominator <= 0:
        return None
    return (Decimal(spend) / Decimal(denominator)).quantize(RATIO_QUANT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class CohortBucket:
    bucket_start: datetime
    bucket_end: datetime
    currency: Optional[str]
    spend: Decimal
    leads: int
    outcomes_completed: int
    cost_per_lead: Optional[Decimal]
    cost_per_outcome: Optional[Decimal]

    def to_dict(self) -> dict:
        return {
            "bucket_start": self.bucket_start.isoformat(),
            "bucket_end": self.bucket_end.isoformat(),
            "currency": self.currency,
            "spend": str(self.spend),
            "leads": self.leads,
            "outcomes_completed": self.outcomes_completed,
            "cost_per_lead": None if self.cost_per_lead is None else str(self.cost_per_lead),
            "cost_per_outcome": None
            if self.cost_per_outcome is None
            else str(self.cost_per_outcome),
        }


@dataclass(frozen=True)
class CohortSeries:
    tenant_id: str
    campaign_id: str
    window_days: int
    bucket: str
    window_start: datetime
    window_end: datetime
    currency: Optional[str]
    spend: Decimal
    leads: int
    outcomes_completed: int
    cost_per_lead: Optional[Decimal]
    cost_per_outcome: Optional[Decimal]
    buckets: tuple[CohortBucket, ...]

    def to_dict(self) -> dict:
        return {
            "tenant_id": self.tenant_id,
            "campaign_id": self.campaign_id,
            "window_days": self.window_days,
            "bucket": self.bucket,
            "window_start": self.window_start.isoformat(),
            "window_end": self.window_end.isoformat(),
            "currency": self.currency,
            "spend": str(self.spend),
            "leads": self.leads,
            "outcomes_completed": self.outcomes_completed,
            "cost_per_lead": None if self.cost_per_lead is None else str(self.cost_per_lead),
            # Wave-1 CAC proxy = cost per completed Outcome (3D cost_per_outcome).
            "cost_per_outcome": None
            if self.cost_per_outcome is None
            else str(self.cost_per_outcome),
            "buckets": [b.to_dict() for b in self.buckets],
        }


def _utc_day_start(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _day_key(dt: datetime) -> date:
    return _as_utc(dt).date()


def _monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _normalize_bucket(bucket: str | None) -> BucketKind:
    raw = str(bucket or "day").strip().lower()
    if raw not in _ALLOWED_BUCKETS:
        raise KpiAggregateError(f"unsupported cohort bucket: {bucket!r}")
    return raw  # type: ignore[return-value]


async def compose_campaign_cohorts(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    window_days: int = _DEFAULT_WINDOW_DAYS,
    bucket: str = "day",
    now: Optional[datetime] = None,
) -> CohortSeries:
    """UTC day or week cohorts for one Campaign over ``window_days`` ending now."""
    days = max(1, min(int(window_days or _DEFAULT_WINDOW_DAYS), _MAX_WINDOW_DAYS))
    bucket_kind = _normalize_bucket(bucket)
    campaign = await db.get(Campaign, str(campaign_id))
    if campaign is None or str(campaign.tenant_id) != str(tenant_id):
        raise KpiAggregateError("campaign not found for tenant")

    end = _as_utc(now or datetime.now(timezone.utc))
    # Inclusive calendar days: last day is today's UTC day.
    end_day = end.date()
    start_day = end_day - timedelta(days=days - 1)
    window_start = _utc_day_start(start_day)
    window_end = _utc_day_start(end_day + timedelta(days=1))

    attributions = (
        await db.execute(
            select(CampaignResultAttribution).where(
                CampaignResultAttribution.tenant_id == str(tenant_id),
                CampaignResultAttribution.campaign_id == str(campaign_id),
                CampaignResultAttribution.created_at >= window_start,
                CampaignResultAttribution.created_at < window_end,
            )
        )
    ).scalars().all()

    spend_rows = (
        await db.execute(
            select(CampaignFlightSpendEntry).where(
                CampaignFlightSpendEntry.tenant_id == str(tenant_id),
                CampaignFlightSpendEntry.campaign_id == str(campaign_id),
                CampaignFlightSpendEntry.created_at >= window_start,
                CampaignFlightSpendEntry.created_at < window_end,
            )
        )
    ).scalars().all()

    outcomes = (
        await db.execute(
            select(CampaignOutcome).where(
                CampaignOutcome.tenant_id == str(tenant_id),
                CampaignOutcome.campaign_id == str(campaign_id),
                CampaignOutcome.status == STATUS_COMPLETED,
            )
        )
    ).scalars().all()

    currency: Optional[str] = None
    spend_by_day: dict[date, Decimal] = {}
    for row in spend_rows:
        cur = str(row.currency or "").strip().upper()
        if len(cur) != 3 or not cur.isalpha():
            raise KpiAggregateError(f"invalid currency: {row.currency!r}")
        if currency is None:
            currency = cur
        elif currency != cur:
            raise KpiAggregateError(f"mixed currencies in campaign spend: {currency} vs {cur}")
        key = _day_key(row.created_at)
        spend_by_day[key] = _money(spend_by_day.get(key, ZERO) + _money(Decimal(row.amount)))

    leads_by_day: dict[date, set[tuple[str, str]]] = {}
    for attr in attributions:
        key = _day_key(attr.created_at)
        leads_by_day.setdefault(key, set()).add((str(attr.result_type), str(attr.result_id)))

    outcomes_by_day: dict[date, int] = {}
    for outcome in outcomes:
        stamp = outcome.completed_at or outcome.created_at
        if stamp is None:
            continue
        stamp_utc = _as_utc(stamp)
        if stamp_utc < window_start or stamp_utc >= window_end:
            continue
        key = _day_key(stamp_utc)
        outcomes_by_day[key] = outcomes_by_day.get(key, 0) + 1

    if bucket_kind == "day":
        period_starts = [start_day + timedelta(days=offset) for offset in range(days)]
        period_len = timedelta(days=1)
    else:
        first_monday = _monday_of(start_day)
        last_monday = _monday_of(end_day)
        period_starts = []
        cur = first_monday
        while cur <= last_monday:
            period_starts.append(cur)
            cur += timedelta(days=7)
        period_len = timedelta(days=7)

    buckets: list[CohortBucket] = []
    total_spend = ZERO
    total_leads = 0
    total_outcomes = 0
    for period_start in period_starts:
        b_start = _utc_day_start(period_start)
        b_end = _utc_day_start(period_start + period_len)
        # Clip aggregation to the requested window (partial first/last week).
        agg_from = max(period_start, start_day)
        agg_to = min(period_start + period_len - timedelta(days=1), end_day)
        spend = ZERO
        lead_keys: set[tuple[str, str]] = set()
        outs = 0
        day = agg_from
        while day <= agg_to:
            spend += spend_by_day.get(day, ZERO)
            lead_keys |= leads_by_day.get(day, set())
            outs += outcomes_by_day.get(day, 0)
            day += timedelta(days=1)
        spend = _money(spend)
        leads = len(lead_keys)
        total_spend += spend
        total_leads += leads
        total_outcomes += outs
        buckets.append(
            CohortBucket(
                bucket_start=b_start,
                bucket_end=b_end,
                currency=currency,
                spend=spend,
                leads=leads,
                outcomes_completed=outs,
                cost_per_lead=_ratio(spend, leads),
                cost_per_outcome=_ratio(spend, outs),
            )
        )

    total_spend = _money(total_spend)
    return CohortSeries(
        tenant_id=str(tenant_id),
        campaign_id=str(campaign_id),
        window_days=days,
        bucket=bucket_kind,
        window_start=window_start,
        window_end=window_end,
        currency=currency,
        spend=total_spend,
        leads=total_leads,
        outcomes_completed=total_outcomes,
        cost_per_lead=_ratio(total_spend, total_leads),
        cost_per_outcome=_ratio(total_spend, total_outcomes),
        buckets=tuple(buckets),
    )


__all__ = [
    "CohortBucket",
    "CohortSeries",
    "_ALLOWED_BUCKETS",
    "_DEFAULT_WINDOW_DAYS",
    "_MAX_WINDOW_DAYS",
    "compose_campaign_cohorts",
]
