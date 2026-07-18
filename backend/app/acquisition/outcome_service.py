"""ADR-024 Stage 3D PR-2 — Outcome lifecycle + attributed Result ledger.

Separated from intake/submit hooks (PR-1). Callers pass an existing
``CampaignResultAttribution``; this service links it to an Outcome and
updates progress idempotently.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.campaign import (
    Campaign,
    CampaignOutcome,
    CampaignOutcomeResultLink,
    CampaignResultAttribution,
    CampaignRun,
)

STATUS_CREATED = "created"
STATUS_ACTIVE = "active"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_CANCELLED = "cancelled"

TERMINAL_STATUSES = frozenset({STATUS_COMPLETED, STATUS_FAILED, STATUS_CANCELLED})
PROGRESS_BLOCKING_STATUSES = frozenset({STATUS_COMPLETED, STATUS_FAILED, STATUS_CANCELLED})


class OutcomeError(ValueError):
    """Outcome lifecycle / linking violation."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _assert_transition(current: str, target: str) -> None:
    allowed = {
        STATUS_CREATED: {STATUS_ACTIVE, STATUS_CANCELLED},
        STATUS_ACTIVE: {STATUS_COMPLETED, STATUS_FAILED, STATUS_CANCELLED},
        STATUS_COMPLETED: set(),
        STATUS_FAILED: set(),
        STATUS_CANCELLED: set(),
    }
    if target not in allowed.get(current, set()):
        raise OutcomeError(f"illegal transition {current} → {target}")


async def create_outcome(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    flight_id: str,
    progress_target: int = 1,
) -> CampaignOutcome:
    """Create Outcome in ``created`` status for a Campaign Flight."""
    target = int(progress_target)
    if target < 1:
        raise OutcomeError("progress_target must be >= 1")

    campaign = await db.get(Campaign, str(campaign_id))
    if campaign is None or str(campaign.tenant_id) != str(tenant_id):
        raise OutcomeError("campaign not found for tenant")

    flight = await db.get(CampaignRun, str(flight_id))
    if (
        flight is None
        or str(flight.tenant_id) != str(tenant_id)
        or str(flight.campaign_id) != str(campaign_id)
    ):
        raise OutcomeError("flight not found for campaign/tenant")

    row = CampaignOutcome(
        tenant_id=str(tenant_id),
        campaign_id=str(campaign_id),
        campaign_run_id=str(flight_id),
        status=STATUS_CREATED,
        progress_current=0,
        progress_target=target,
    )
    db.add(row)
    await db.flush()
    return row


async def get_outcome(
    db: AsyncSession,
    *,
    tenant_id: str,
    outcome_id: str,
) -> Optional[CampaignOutcome]:
    row = await db.get(CampaignOutcome, str(outcome_id))
    if row is None or str(row.tenant_id) != str(tenant_id):
        return None
    return row


async def mark_outcome_failed(
    db: AsyncSession,
    *,
    tenant_id: str,
    outcome_id: str,
) -> CampaignOutcome:
    outcome = await get_outcome(db, tenant_id=tenant_id, outcome_id=outcome_id)
    if outcome is None:
        raise OutcomeError("outcome not found for tenant")
    _assert_transition(outcome.status, STATUS_FAILED)
    now = _now()
    outcome.status = STATUS_FAILED
    outcome.failed_at = now
    await db.flush()
    return outcome


async def mark_outcome_cancelled(
    db: AsyncSession,
    *,
    tenant_id: str,
    outcome_id: str,
) -> CampaignOutcome:
    outcome = await get_outcome(db, tenant_id=tenant_id, outcome_id=outcome_id)
    if outcome is None:
        raise OutcomeError("outcome not found for tenant")
    _assert_transition(outcome.status, STATUS_CANCELLED)
    now = _now()
    outcome.status = STATUS_CANCELLED
    outcome.cancelled_at = now
    await db.flush()
    return outcome


async def apply_attribution_to_outcome(
    db: AsyncSession,
    *,
    tenant_id: str,
    outcome_id: str,
    attribution_id: str,
) -> tuple[CampaignOutcome, CampaignOutcomeResultLink, bool]:
    """Link an attributed Result to Outcome and bump progress once.

    Returns ``(outcome, link, progress_applied)`` where ``progress_applied`` is
    False when the Result was already counted (idempotent re-apply).
    """
    outcome = await get_outcome(db, tenant_id=tenant_id, outcome_id=outcome_id)
    if outcome is None:
        raise OutcomeError("outcome not found for tenant")

    attribution = await db.get(CampaignResultAttribution, str(attribution_id))
    if attribution is None or str(attribution.tenant_id) != str(tenant_id):
        raise OutcomeError("attribution not found for tenant")

    if str(attribution.campaign_id) != str(outcome.campaign_id) or str(
        attribution.campaign_run_id
    ) != str(outcome.campaign_run_id):
        raise OutcomeError("attribution campaign/flight does not match outcome")

    if outcome.status in PROGRESS_BLOCKING_STATUSES:
        raise OutcomeError(f"outcome status {outcome.status} rejects progress mutations")

    existing = await db.execute(
        select(CampaignOutcomeResultLink).where(
            CampaignOutcomeResultLink.tenant_id == str(tenant_id),
            CampaignOutcomeResultLink.outcome_id == str(outcome.id),
            CampaignOutcomeResultLink.result_type == str(attribution.result_type),
            CampaignOutcomeResultLink.result_id == str(attribution.result_id),
        )
    )
    link = existing.scalar_one_or_none()
    if link is not None:
        # Idempotent: already counted (even if later soft-revoked — progress stays).
        return outcome, link, False

    by_attr = await db.execute(
        select(CampaignOutcomeResultLink).where(
            CampaignOutcomeResultLink.tenant_id == str(tenant_id),
            CampaignOutcomeResultLink.attribution_id == str(attribution.id),
        )
    )
    if by_attr.scalar_one_or_none() is not None:
        raise OutcomeError("attribution already linked to an outcome")

    now = _now()
    if outcome.status == STATUS_CREATED:
        _assert_transition(STATUS_CREATED, STATUS_ACTIVE)
        outcome.status = STATUS_ACTIVE
        outcome.activated_at = now

    link = CampaignOutcomeResultLink(
        tenant_id=str(tenant_id),
        outcome_id=str(outcome.id),
        attribution_id=str(attribution.id),
        result_type=str(attribution.result_type),
        result_id=str(attribution.result_id),
        counted_at=now,
    )
    db.add(link)
    outcome.progress_current = int(outcome.progress_current) + 1

    if outcome.progress_current >= int(outcome.progress_target):
        if outcome.status == STATUS_ACTIVE:
            _assert_transition(STATUS_ACTIVE, STATUS_COMPLETED)
            outcome.status = STATUS_COMPLETED
            outcome.completed_at = now

    await db.flush()
    return outcome, link, True


async def soft_revoke_outcome_result(
    db: AsyncSession,
    *,
    tenant_id: str,
    outcome_id: str,
    result_type: str,
    result_id: str,
    reason: str = "result_deleted",
) -> CampaignOutcomeResultLink:
    """Soft-revoke ledger link. Does **not** decrease Outcome.progress_current."""
    outcome = await get_outcome(db, tenant_id=tenant_id, outcome_id=outcome_id)
    if outcome is None:
        raise OutcomeError("outcome not found for tenant")

    row = await db.execute(
        select(CampaignOutcomeResultLink).where(
            CampaignOutcomeResultLink.tenant_id == str(tenant_id),
            CampaignOutcomeResultLink.outcome_id == str(outcome_id),
            CampaignOutcomeResultLink.result_type == str(result_type),
            CampaignOutcomeResultLink.result_id == str(result_id),
        )
    )
    link = row.scalar_one_or_none()
    if link is None:
        raise OutcomeError("outcome result link not found")
    if link.revoked_at is None:
        link.revoked_at = _now()
        link.revoke_reason = str(reason or "result_deleted")[:128]
        await db.flush()
    return link
