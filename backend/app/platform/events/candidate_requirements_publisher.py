"""Persist evaluation + publish candidate.requirements_evaluated (PR 3A-1)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.platform.events.outbox.model import RequirementEvaluationResultRecord
from backend.app.platform.events.outbox.publisher import build_envelope, publish_domain_event


class RequirementEvaluationLike(Protocol):
    entity_type: str
    entity_id: str
    policy_ref: str
    policy_version: str
    target_stage: str
    evaluated_at: datetime
    input_fingerprint: str
    can_transition: bool
    blocking_requirements: list[str]

    def to_dict(self) -> dict[str, Any]: ...

EVENT_TYPE = "candidate.requirements_evaluated"
EVENT_VERSION = "v1"


def _outbox_enabled() -> bool:
    """Default off until production call sites and dispatcher worker are wired."""
    return os.environ.get("PLATFORM_EVENT_OUTBOX_ENABLED", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _evaluation_payload(
    *,
    candidate_id: str,
    evaluation_result_id: str,
    entity_revision: str,
    policy_ref: str,
    entity_profile_code: Optional[str],
    can_transition: bool,
    target_stage: str,
    blocker_codes: list[str],
    evaluated_at: datetime,
) -> dict:
    payload = {
        "candidate_id": candidate_id,
        "evaluation_result_id": evaluation_result_id,
        "entity_revision": entity_revision,
        "policy_ref": policy_ref,
        "can_transition": can_transition,
        "target_stage": target_stage,
        "blocker_codes": blocker_codes,
        "evaluated_at": evaluated_at.isoformat(),
    }
    if entity_profile_code:
        payload["entity_profile_code"] = entity_profile_code
    return payload


@dataclass(frozen=True)
class PersistedRequirementEvaluation:
    result: RequirementEvaluationLike
    evaluation_result_id: str
    event_id: Optional[str]


async def persist_requirement_evaluation_record(
    db: AsyncSession,
    *,
    tenant_id: str,
    result: RequirementEvaluationLike,
    company_id: Optional[str] = None,
    evaluation_result_id: Optional[str] = None,
) -> RequirementEvaluationResultRecord:
    evaluated_at = result.evaluated_at
    if evaluated_at.tzinfo is None:
        evaluated_at = evaluated_at.replace(tzinfo=timezone.utc)

    record = RequirementEvaluationResultRecord(
        id=evaluation_result_id or None,
        tenant_id=str(tenant_id),
        entity_type=result.entity_type,
        entity_id=result.entity_id,
        company_id=company_id,
        policy_ref=result.policy_ref,
        policy_version=result.policy_version,
        target_stage=result.target_stage,
        entity_revision=result.input_fingerprint,
        can_transition=result.can_transition,
        blocker_codes=list(result.blocking_requirements),
        result_snapshot=result.to_dict(),
        evaluated_at=evaluated_at,
    )
    db.add(record)
    await db.flush()
    return record


async def publish_candidate_requirements_evaluated_event(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Any,
    result: RequirementEvaluationLike,
    evaluation_result_id: str,
    correlation_id: Optional[str] = None,
    causation_id: Optional[str] = None,
) -> str:
    evaluated_at = result.evaluated_at
    if evaluated_at.tzinfo is None:
        evaluated_at = evaluated_at.replace(tzinfo=timezone.utc)

    profile_code = str(getattr(candidate, "entity_profile_code", "") or "").strip() or None
    company_id = str(getattr(candidate, "company_id", "") or "").strip() or None

    payload = _evaluation_payload(
        candidate_id=str(candidate.id),
        evaluation_result_id=evaluation_result_id,
        entity_revision=result.input_fingerprint,
        policy_ref=result.policy_ref,
        entity_profile_code=profile_code,
        can_transition=result.can_transition,
        target_stage=result.target_stage,
        blocker_codes=list(result.blocking_requirements),
        evaluated_at=evaluated_at,
    )
    envelope = build_envelope(
        event_type=EVENT_TYPE,
        event_version=EVENT_VERSION,
        aggregate_type="candidate",
        aggregate_id=str(candidate.id),
        tenant_id=str(tenant_id),
        company_id=company_id,
        payload=payload,
        occurred_at=evaluated_at,
        correlation_id=correlation_id,
        causation_id=causation_id,
    )
    await publish_domain_event(db, envelope)
    return envelope.event_id


async def evaluate_persist_and_publish_candidate_requirements(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Any,
    target_stage: str,
    correlation_id: Optional[str] = None,
    causation_id: Optional[str] = None,
) -> PersistedRequirementEvaluation:
    """
    Evaluate, persist result, enqueue outbox event — single transaction (caller commits).

    Does not invoke legacy automation_rules. No business actions.
    """
    from backend.app.requirement_rules.evaluation.candidate_bridge import (
        evaluate_candidate_requirements_v2,
    )

    result = await evaluate_candidate_requirements_v2(
        db,
        tenant_id=str(tenant_id),
        candidate=candidate,
        target_stage=target_stage,
    )
    company_id = str(getattr(candidate, "company_id", "") or "").strip() or None
    record = await persist_requirement_evaluation_record(
        db,
        tenant_id=str(tenant_id),
        result=result,
        company_id=company_id,
    )
    event_id: Optional[str] = None
    if _outbox_enabled():
        event_id = await publish_candidate_requirements_evaluated_event(
            db,
            tenant_id=str(tenant_id),
            candidate=candidate,
            result=result,
            evaluation_result_id=record.id,
            correlation_id=correlation_id,
            causation_id=causation_id,
        )
    return PersistedRequirementEvaluation(
        result=result,
        evaluation_result_id=record.id,
        event_id=event_id,
    )


__all__ = [
    "PersistedRequirementEvaluation",
    "evaluate_persist_and_publish_candidate_requirements",
    "persist_requirement_evaluation_record",
    "publish_candidate_requirements_evaluated_event",
    "EVENT_TYPE",
    "EVENT_VERSION",
]
