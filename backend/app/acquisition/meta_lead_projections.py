"""Project Meta webhook leads into Acquisition activity + result attribution.

Meta ingest stamps ``acquisition_routing_v1`` on ``Lead.normalized`` but historically
never called ``append_submission``, so Marketing Sources last_lead and portfolio KPI
leads stayed empty despite daily Meta traffic. This module closes that gap idempotently.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Mapping, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.endpoint_activity import (
    form_endpoint_id,
    intake_source_endpoint_id,
)
from backend.app.acquisition.lead_activity import record_lead_created
from backend.app.acquisition.result_attribution import try_record_result_attribution_from_routing
from backend.app.acquisition.submission_activity import record_submission_received
from backend.app.acquisition.submission_routing import (
    ACQUISITION_ROUTING_V1_KEY,
    RoutingDecisionStatus,
)
from backend.app.models.lead import Lead

logger = logging.getLogger(__name__)


def meta_lead_submission_id(lead_id: str) -> str:
    """Stable submission_id for Meta webhook leads (≤36 chars for activity column)."""
    return str(lead_id).strip()


def _routing_stamp(normalized: Mapping[str, Any] | None) -> dict[str, Any]:
    raw = (normalized or {}).get(ACQUISITION_ROUTING_V1_KEY)
    return dict(raw) if isinstance(raw, Mapping) else {}


def _endpoint_id_for_marketing_sources(stamp: Mapping[str, Any]) -> str | None:
    """Prefer intake_source endpoint — campaign Meta cards key last_lead by profile id."""
    profile_id = str(stamp.get("intake_source_profile_id") or "").strip()
    if profile_id:
        return intake_source_endpoint_id(profile_id)
    form_id = str(stamp.get("form_id") or "").strip()
    if form_id:
        return form_endpoint_id(form_id)
    return None


async def project_meta_lead_into_acquisition(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    normalized: Mapping[str, Any] | None = None,
) -> None:
    """Emit SubmissionReceived + LeadCreated and attribute when routing is ``routed``.

    Safe to call repeatedly: activity append and attribution are idempotent by
    ``source_event_id`` / result uniqueness.
    """
    lead_id = str(getattr(lead, "id", None) or "").strip()
    if not lead_id:
        return

    merged: dict[str, Any] = {}
    if isinstance(getattr(lead, "normalized", None), dict):
        merged.update(lead.normalized)
    if isinstance(normalized, Mapping):
        merged.update(dict(normalized))
    stamp = _routing_stamp(merged)
    campaign_id = str(stamp.get("campaign_id") or "").strip()
    if not campaign_id:
        return

    # Keep Lead.normalized aligned so attribution readers see the stamp.
    lead.normalized = merged

    # Skip orphan stamps (campaign deleted) — never block Meta ingest.
    from sqlalchemy import select

    from backend.app.models.campaign import Campaign

    campaign_exists = (
        await db.execute(
            select(Campaign.id).where(
                Campaign.tenant_id == str(tenant_id),
                Campaign.id == campaign_id,
            )
        )
    ).scalar_one_or_none()
    if campaign_exists is None:
        logger.warning(
            "meta_lead_projection_skip_missing_campaign tenant=%s lead=%s campaign=%s",
            tenant_id,
            lead_id,
            campaign_id,
        )
        return

    submission_id = meta_lead_submission_id(lead_id)
    flight_id = str(stamp.get("campaign_run_id") or "").strip() or None
    route_intent = str(stamp.get("route_intent") or "").strip() or None
    endpoint_id = _endpoint_id_for_marketing_sources(stamp)
    created_at = getattr(lead, "created_at", None)
    occurred_at = created_at if isinstance(created_at, datetime) else None

    try:
        await record_submission_received(
            db,
            tenant_id=str(tenant_id),
            campaign_id=campaign_id,
            submission_id=submission_id,
            flight_id=flight_id,
            endpoint_id=endpoint_id,
            occurred_at=occurred_at,
        )
        await record_lead_created(
            db,
            tenant_id=str(tenant_id),
            campaign_id=campaign_id,
            lead_id=lead_id,
            submission_id=submission_id,
            route_intent=route_intent,
            flight_id=flight_id,
            occurred_at=occurred_at,
        )
    except Exception:
        logger.exception(
            "meta_lead_activity_projection_failed tenant=%s lead=%s",
            tenant_id,
            lead_id,
        )
        return

    if str(stamp.get("status") or "").strip() != RoutingDecisionStatus.routed.value:
        return

    try:
        await try_record_result_attribution_from_routing(
            db,
            tenant_id=str(tenant_id),
            lead=lead,
            submission_id=submission_id,
            created_candidate_id=str(getattr(lead, "candidate_id", None) or "").strip() or None,
        )
    except Exception:
        logger.exception(
            "meta_lead_attribution_projection_failed tenant=%s lead=%s",
            tenant_id,
            lead_id,
        )


async def backfill_meta_lead_projections(
    db: AsyncSession,
    *,
    tenant_id: str,
    limit: int = 5000,
) -> dict[str, int]:
    """Project historical Meta leads that already carry ``acquisition_routing_v1``.

    Idempotent. Used to heal Marketing last_lead / portfolio lead KPIs after the
    ingest hook shipped. Also aligns attribution ``created_at`` to the lead's
    ``created_at`` so daily series match real traffic days.
    """
    from sqlalchemy import select, text

    from backend.app.models.campaign import CampaignResultAttribution

    stats = {"scanned": 0, "projected": 0, "skipped_no_campaign": 0, "dates_aligned": 0}
    rows = (
        await db.execute(
            select(Lead)
            .where(Lead.tenant_id == str(tenant_id), Lead.source == "meta")
            .order_by(Lead.created_at.desc())
            .limit(max(1, min(int(limit), 50_000)))
        )
    ).scalars().all()
    for lead in rows:
        stats["scanned"] += 1
        stamp = _routing_stamp(
            getattr(lead, "normalized", None)
            if isinstance(getattr(lead, "normalized", None), dict)
            else None
        )
        if not str(stamp.get("campaign_id") or "").strip():
            stats["skipped_no_campaign"] += 1
            continue
        await project_meta_lead_into_acquisition(
            db,
            tenant_id=str(tenant_id),
            lead=lead,
            normalized=lead.normalized if isinstance(lead.normalized, dict) else None,
        )
        stats["projected"] += 1
        created_at = getattr(lead, "created_at", None)
        if isinstance(created_at, datetime):
            attr = (
                await db.execute(
                    select(CampaignResultAttribution).where(
                        CampaignResultAttribution.tenant_id == str(tenant_id),
                        CampaignResultAttribution.lead_id == str(lead.id),
                    )
                )
            ).scalar_one_or_none()
            if attr is not None and getattr(attr, "created_at", None) != created_at:
                attr.created_at = created_at
                if hasattr(attr, "updated_at"):
                    attr.updated_at = created_at
                stats["dates_aligned"] += 1
    await db.flush()
    # Belt-and-suspenders for rows already present before this backfill revision.
    res = await db.execute(
        text(
            """
            UPDATE acq_result_attributions AS a
            SET created_at = l.created_at,
                updated_at = l.created_at
            FROM leads AS l
            WHERE a.tenant_id = :tid
              AND l.tenant_id = a.tenant_id
              AND l.id = a.lead_id
              AND l.source = 'meta'
              AND a.created_at IS DISTINCT FROM l.created_at
            """
        ),
        {"tid": str(tenant_id)},
    )
    try:
        stats["dates_aligned"] = max(stats["dates_aligned"], int(res.rowcount or 0))
    except Exception:
        pass
    return stats


__all__ = [
    "meta_lead_submission_id",
    "project_meta_lead_into_acquisition",
    "backfill_meta_lead_projections",
]
