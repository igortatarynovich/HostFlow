"""Sync Meta Ad Account Insights spend into Acquisition Flight spend ledger.

Portfolio KPI (Wydatek / CPL) reads only ``acq_flight_spend_entries``. Live Graph
Insights are a separate SoT shown on the Meta card. This module bridges them
idempotently when the company has a single Meta-attributed active campaign
(account-level spend cannot be split across campaigns without campaign Insights).
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.kpi_aggregates import record_flight_spend
from backend.app.models.campaign import Campaign, CampaignFlightSpendEntry, CampaignRun

logger = logging.getLogger(__name__)

_NOTE_PREFIX = "meta_insights:"


def meta_insights_spend_note(
    *,
    date_preset: str,
    ad_account_id: str,
    impressions: int | None = None,
    reach: int | None = None,
) -> str:
    """Stable note key + optional snapshot metrics parsed by portfolio analytics."""
    preset = (date_preset or "last_7d").strip() or "last_7d"
    act = str(ad_account_id or "").removeprefix("act_").strip()
    base = f"{_NOTE_PREFIX}{preset}:act_{act}"
    parts = [base]
    if impressions is not None and int(impressions) >= 0:
        parts.append(f"impressions={int(impressions)}")
    if reach is not None and int(reach) >= 0:
        parts.append(f"reach={int(reach)}")
    return " ".join(parts)[:255]


def meta_insights_spend_note_prefix(*, date_preset: str, ad_account_id: str) -> str:
    preset = (date_preset or "last_7d").strip() or "last_7d"
    act = str(ad_account_id or "").removeprefix("act_").strip()
    return f"{_NOTE_PREFIX}{preset}:act_{act}"


async def _meta_linked_active_campaigns(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str,
) -> list[Campaign]:
    """Campaigns under the company that already have Meta-routed attributions."""
    from backend.app.models.campaign import CampaignResultAttribution

    campaign_ids = (
        await db.execute(
            select(CampaignResultAttribution.campaign_id)
            .where(
                CampaignResultAttribution.tenant_id == str(tenant_id),
                CampaignResultAttribution.endpoint_intake_source_profile_id.is_not(None),
            )
            .distinct()
        )
    ).scalars().all()
    if not campaign_ids:
        # Fallback: any active campaign for the company (Domo single-campaign tenants).
        rows = (
            await db.execute(
                select(Campaign).where(
                    Campaign.tenant_id == str(tenant_id),
                    Campaign.own_company_id == str(own_company_id),
                    Campaign.status == "active",
                )
            )
        ).scalars().all()
        return list(rows)

    rows = (
        await db.execute(
            select(Campaign).where(
                Campaign.tenant_id == str(tenant_id),
                Campaign.own_company_id == str(own_company_id),
                Campaign.id.in_([str(x) for x in campaign_ids]),
                Campaign.status == "active",
            )
        )
    ).scalars().all()
    return list(rows)


async def upsert_meta_insights_spend_for_company(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str,
    amount: Decimal | float | str,
    currency: str,
    date_preset: str,
    ad_account_id: str,
    impressions: int | None = None,
    reach: int | None = None,
) -> dict[str, Any]:
    """Replace prior Meta Insights spend row for this preset/account on the target flight.

    Returns a small status dict. No-op (skipped) when spend cannot be attributed to
    exactly one active Meta-linked campaign.
    """
    campaigns = await _meta_linked_active_campaigns(
        db, tenant_id=str(tenant_id), own_company_id=str(own_company_id)
    )
    if len(campaigns) != 1:
        return {
            "synced": False,
            "reason": "ambiguous_or_empty_campaign_set",
            "campaign_count": len(campaigns),
        }

    campaign = campaigns[0]
    flight_id = str(getattr(campaign, "current_flight_id", None) or "").strip()
    if not flight_id:
        flight = (
            await db.execute(
                select(CampaignRun)
                .where(
                    CampaignRun.tenant_id == str(tenant_id),
                    CampaignRun.campaign_id == str(campaign.id),
                    CampaignRun.status == "active",
                )
                .order_by(CampaignRun.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        flight_id = str(flight.id) if flight is not None else ""
    if not flight_id:
        return {"synced": False, "reason": "no_active_flight", "campaign_id": str(campaign.id)}

    note_prefix = meta_insights_spend_note_prefix(
        date_preset=date_preset, ad_account_id=ad_account_id
    )
    note = meta_insights_spend_note(
        date_preset=date_preset,
        ad_account_id=ad_account_id,
        impressions=impressions,
        reach=reach,
    )
    # Drop prior sync rows for this preset/account (with or without metric suffix).
    await db.execute(
        delete(CampaignFlightSpendEntry).where(
            CampaignFlightSpendEntry.tenant_id == str(tenant_id),
            CampaignFlightSpendEntry.campaign_run_id == flight_id,
            CampaignFlightSpendEntry.note.like(f"{note_prefix}%"),
        )
    )
    row = await record_flight_spend(
        db,
        tenant_id=str(tenant_id),
        flight_id=flight_id,
        amount=amount,
        currency=currency or "PLN",
        note=note,
    )
    logger.info(
        "meta_insights_spend_synced tenant=%s campaign=%s flight=%s amount=%s %s note=%s",
        tenant_id,
        campaign.id,
        flight_id,
        row.amount,
        row.currency,
        note,
    )
    return {
        "synced": True,
        "campaign_id": str(campaign.id),
        "flight_id": flight_id,
        "amount": str(row.amount),
        "currency": row.currency,
        "note": note,
        "impressions": impressions,
        "reach": reach,
    }


__all__ = [
    "meta_insights_spend_note",
    "meta_insights_spend_note_prefix",
    "upsert_meta_insights_spend_for_company",
]
