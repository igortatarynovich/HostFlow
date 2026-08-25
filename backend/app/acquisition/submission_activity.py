"""Submission → Activity Timeline (Stage 3E PR-2).

``SubmissionReceived`` is emitted only when an Acquisition routing stamp with
``campaign_id`` is present — never for non-Acquisition questionnaire traffic.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.activity.append_service import append_activity_event
from backend.app.acquisition.activity.catalog import get_activity_event_contract
from backend.app.acquisition.endpoint_activity import (
    form_endpoint_id,
    intake_source_endpoint_id,
)
from backend.app.models.acquisition_activity_event import (
    ACTOR_TYPE_SYSTEM,
    AcquisitionActivityEvent,
)


def submission_received_source_event_id(submission_id: str) -> str:
    return f"acq.submission.received:{str(submission_id).strip()}"


def _endpoint_id_from_routing(routing: Mapping[str, Any]) -> str | None:
    form_id = str(routing.get("form_id") or "").strip()
    if form_id:
        return form_endpoint_id(form_id)
    profile_id = str(routing.get("intake_source_profile_id") or "").strip()
    if profile_id:
        return intake_source_endpoint_id(profile_id)
    return None


async def record_submission_received(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    submission_id: str,
    flight_id: str | None = None,
    endpoint_id: str | None = None,
    normalized_schema_version: str | None = None,
    actor_type: str = ACTOR_TYPE_SYSTEM,
    actor_id: str | None = None,
    occurred_at: datetime | None = None,
    reason_code: str | None = None,
) -> AcquisitionActivityEvent:
    """Append ``SubmissionReceived`` for an Acquisition-scoped submission."""
    contract = get_activity_event_contract("SubmissionReceived")
    if contract is None:
        raise RuntimeError("SubmissionReceived missing from activity catalog")
    payload: dict[str, Any] = {}
    if normalized_schema_version and str(normalized_schema_version).strip():
        payload["normalized_schema_version"] = str(normalized_schema_version).strip()
    if reason_code and str(reason_code).strip():
        payload["reason_code"] = str(reason_code).strip()

    return await append_activity_event(
        db,
        tenant_id=str(tenant_id),
        campaign_id=str(campaign_id),
        flight_id=str(flight_id).strip() if flight_id else None,
        endpoint_id=str(endpoint_id).strip() if endpoint_id else None,
        submission_id=str(submission_id).strip(),
        event_type="SubmissionReceived",
        event_version=contract.event_version,
        payload=payload,
        actor_type=actor_type,
        actor_id=actor_id,
        source_event_id=submission_received_source_event_id(submission_id),
        occurred_at=occurred_at,
        provider=None,
    )


async def maybe_record_submission_received_from_entry_context(
    db: AsyncSession,
    *,
    tenant_id: str,
    submission_entry: Mapping[str, Any],
    entry_context: Mapping[str, Any] | None,
    actor_type: str = ACTOR_TYPE_SYSTEM,
    actor_id: str | None = None,
) -> AcquisitionActivityEvent | None:
    """Emit only when ``entry_context`` carries Acquisition routing with campaign_id."""
    ctx = dict(entry_context or {})
    routing = ctx.get("acquisition_routing_v1")
    if not isinstance(routing, Mapping):
        return None
    campaign_id = str(routing.get("campaign_id") or "").strip()
    if not campaign_id:
        return None
    submission_id = str(submission_entry.get("submission_id") or "").strip()
    if not submission_id:
        return None
    flight_id = str(routing.get("campaign_run_id") or "").strip() or None
    endpoint_id = _endpoint_id_from_routing(routing)
    schema_version = str(submission_entry.get("schema_version") or "").strip() or None
    return await record_submission_received(
        db,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        submission_id=submission_id,
        flight_id=flight_id,
        endpoint_id=endpoint_id,
        normalized_schema_version=schema_version,
        actor_type=actor_type,
        actor_id=actor_id,
    )


__all__ = [
    "maybe_record_submission_received_from_entry_context",
    "record_submission_received",
    "submission_received_source_event_id",
]
