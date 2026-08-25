"""ADR-024 Stage 3D PR-2 — Outcome lifecycle + attributed Result ledger.

Separated from intake/submit hooks (PR-1). Callers pass an existing
``CampaignResultAttribution``; this service links it to an Outcome and
updates progress idempotently.

Stage 3E PR-2: status mutations emit ``OutcomeChanged`` via
``append_activity_event`` (service choke-point only — not HTTP handlers).
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


def outcome_changed_source_event_id(
    *,
    outcome_id: str,
    previous_status: str | None,
    new_status: str,
) -> str:
    """Deterministic idempotency key for one Outcome status transition."""
    prev = str(previous_status).strip() if previous_status else "_"
    return f"acq.outcome.changed:{str(outcome_id).strip()}:{prev}:{str(new_status).strip()}"


async def _emit_outcome_changed(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    flight_id: str,
    outcome_id: str,
    status: str,
    previous_status: str | None = None,
    actor_type: str = "system",
    actor_id: str | None = None,
) -> None:
    """Stage 3E PR-2: Activity Timeline projection after Outcome status persist."""
    from backend.app.acquisition.activity.append_service import append_activity_event
    from backend.app.acquisition.activity.catalog import get_activity_event_contract
    from backend.app.models.acquisition_activity_event import ACTOR_TYPES

    contract = get_activity_event_contract("OutcomeChanged")
    if contract is None:
        raise RuntimeError("OutcomeChanged missing from activity catalog")
    actor = str(actor_type or "system").strip()
    if actor not in ACTOR_TYPES:
        actor = "system"
    payload: dict[str, str] = {"status": str(status).strip()}
    if previous_status is not None and str(previous_status).strip():
        payload["previous_status"] = str(previous_status).strip()
    await append_activity_event(
        db,
        tenant_id=str(tenant_id),
        campaign_id=str(campaign_id),
        flight_id=str(flight_id),
        outcome_id=str(outcome_id),
        event_type="OutcomeChanged",
        event_version=contract.event_version,
        payload=payload,
        actor_type=actor,
        actor_id=str(actor_id).strip() if actor_id else None,
        source_event_id=outcome_changed_source_event_id(
            outcome_id=outcome_id,
            previous_status=previous_status,
            new_status=status,
        ),
        provider=None,
    )


async def create_outcome(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    flight_id: str,
    progress_target: int = 1,
    actor_type: str = "system",
    actor_id: str | None = None,
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
    await _emit_outcome_changed(
        db,
        tenant_id=str(tenant_id),
        campaign_id=str(campaign_id),
        flight_id=str(flight_id),
        outcome_id=str(row.id),
        status=STATUS_CREATED,
        previous_status=None,
        actor_type=actor_type,
        actor_id=actor_id,
    )
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
    actor_type: str = "system",
    actor_id: str | None = None,
) -> CampaignOutcome:
    outcome = await get_outcome(db, tenant_id=tenant_id, outcome_id=outcome_id)
    if outcome is None:
        raise OutcomeError("outcome not found for tenant")
    previous = str(outcome.status)
    _assert_transition(previous, STATUS_FAILED)
    now = _now()
    outcome.status = STATUS_FAILED
    outcome.failed_at = now
    await db.flush()
    await _emit_outcome_changed(
        db,
        tenant_id=str(tenant_id),
        campaign_id=str(outcome.campaign_id),
        flight_id=str(outcome.campaign_run_id),
        outcome_id=str(outcome.id),
        status=STATUS_FAILED,
        previous_status=previous,
        actor_type=actor_type,
        actor_id=actor_id,
    )
    return outcome


async def mark_outcome_cancelled(
    db: AsyncSession,
    *,
    tenant_id: str,
    outcome_id: str,
    actor_type: str = "system",
    actor_id: str | None = None,
) -> CampaignOutcome:
    outcome = await get_outcome(db, tenant_id=tenant_id, outcome_id=outcome_id)
    if outcome is None:
        raise OutcomeError("outcome not found for tenant")
    previous = str(outcome.status)
    _assert_transition(previous, STATUS_CANCELLED)
    now = _now()
    outcome.status = STATUS_CANCELLED
    outcome.cancelled_at = now
    await db.flush()
    await _emit_outcome_changed(
        db,
        tenant_id=str(tenant_id),
        campaign_id=str(outcome.campaign_id),
        flight_id=str(outcome.campaign_run_id),
        outcome_id=str(outcome.id),
        status=STATUS_CANCELLED,
        previous_status=previous,
        actor_type=actor_type,
        actor_id=actor_id,
    )
    return outcome


async def apply_attribution_to_outcome(
    db: AsyncSession,
    *,
    tenant_id: str,
    outcome_id: str,
    attribution_id: str,
    actor_type: str = "system",
    actor_id: str | None = None,
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
    status_transitions: list[tuple[str | None, str]] = []
    if outcome.status == STATUS_CREATED:
        _assert_transition(STATUS_CREATED, STATUS_ACTIVE)
        outcome.status = STATUS_ACTIVE
        outcome.activated_at = now
        status_transitions.append((STATUS_CREATED, STATUS_ACTIVE))

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
            status_transitions.append((STATUS_ACTIVE, STATUS_COMPLETED))

    await db.flush()
    for previous, new_status in status_transitions:
        await _emit_outcome_changed(
            db,
            tenant_id=str(tenant_id),
            campaign_id=str(outcome.campaign_id),
            flight_id=str(outcome.campaign_run_id),
            outcome_id=str(outcome.id),
            status=new_status,
            previous_status=previous,
            actor_type=actor_type,
            actor_id=actor_id,
        )
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
