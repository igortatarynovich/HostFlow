"""Append-only Submission storage on Lead (ADR-021 §5.1, ADR-022 §5.4)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from backend.app.intake_platform.constants import SUBMISSIONS_V1_KEY
from backend.app.intake_platform.schemas import EffectivePolicy, MatchResult
from backend.app.models.lead import Lead


def _record(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_submissions(lead: Lead) -> list[dict[str, Any]]:
    normalized = _record(lead.normalized)
    raw = normalized.get(SUBMISSIONS_V1_KEY)
    if not isinstance(raw, list):
        return []
    return [dict(x) for x in raw if isinstance(x, dict)]


def find_submission_by_idempotency_key(lead: Lead, idempotency_key: str) -> Optional[dict[str, Any]]:
    key = str(idempotency_key or "").strip()
    if not key:
        return None
    for entry in list_submissions(lead):
        if str(entry.get("idempotency_key") or "").strip() == key:
            return entry
    return None


def _build_submission_entry(
    *,
    effective_policy: EffectivePolicy,
    normalized_values: dict[str, Any],
    presentation_code: Optional[str],
    raw_values: Optional[dict[str, Any]],
    consent_metadata: Optional[dict[str, Any]],
    match_result: Optional[MatchResult],
    entry_context: Optional[dict[str, Any]],
    idempotency_key: Optional[str],
) -> dict[str, Any]:
    entry = {
        "submission_id": str(uuid4()),
        "submitted_at": _now_iso(),
        "schema_version": "submission_v1",
        "purpose": effective_policy.purpose,
        "target_entity_profile_code": effective_policy.target_entity_profile_code,
        "form_id": effective_policy.form_id,
        "published_version": effective_policy.published_version,
        "presentation_code": presentation_code,
        "publication_id": effective_policy.publication_id,
        "invite_id": effective_policy.invite_id,
        "application_id": None,
        "idempotency_key": str(idempotency_key).strip() if idempotency_key else None,
        "effective_submission_policy": effective_policy.to_snapshot(),
        "source": {
            **dict(effective_policy.source or {}),
            **dict(entry_context or {}),
        },
        "normalized_values": dict(normalized_values or {}),
        "raw_values": dict(raw_values or {}),
        "consent_metadata": dict(consent_metadata or {}),
    }
    if match_result is not None:
        entry["match_result_v1"] = match_result.to_dict()
    return entry


async def append_submission(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_id: str,
    effective_policy: EffectivePolicy,
    normalized_values: dict[str, Any],
    presentation_code: Optional[str] = None,
    raw_values: Optional[dict[str, Any]] = None,
    consent_metadata: Optional[dict[str, Any]] = None,
    match_result: Optional[MatchResult] = None,
    entry_context: Optional[dict[str, Any]] = None,
    idempotency_key: Optional[str] = None,
) -> dict[str, Any]:
    """Append submission under row lock; idempotent when idempotency_key repeats."""
    result = await db.execute(
        select(Lead)
        .where(Lead.id == str(lead_id), Lead.tenant_id == str(tenant_id))
        .with_for_update()
    )
    lead = result.scalar_one_or_none()
    if lead is None:
        raise ValueError("Lead not found for submission append")

    if idempotency_key:
        existing = find_submission_by_idempotency_key(lead, idempotency_key)
        if existing is not None:
            return existing

    entry = _build_submission_entry(
        effective_policy=effective_policy,
        normalized_values=normalized_values,
        presentation_code=presentation_code,
        raw_values=raw_values,
        consent_metadata=consent_metadata,
        match_result=match_result,
        entry_context=entry_context,
        idempotency_key=idempotency_key,
    )
    entry["application_id"] = str(lead.id)

    normalized = _record(lead.normalized)
    submissions = list_submissions(lead)
    submissions.append(entry)
    normalized[SUBMISSIONS_V1_KEY] = submissions

    # Persist offering attribution for future match_or_create gates.
    attribution = _record(normalized.get("intake_attribution_v1"))
    if effective_policy.publication_id:
        attribution["publication_id"] = effective_policy.publication_id
    source = dict(effective_policy.source or {})
    if source.get("campaign"):
        attribution["campaign"] = source.get("campaign")
    if attribution:
        normalized["intake_attribution_v1"] = attribution

    lead.normalized = normalized
    flag_modified(lead, "normalized")
    await db.flush()
    return entry
