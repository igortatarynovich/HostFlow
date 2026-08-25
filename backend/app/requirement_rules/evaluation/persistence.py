"""Backward-compatible re-export — prefer platform.events.candidate_requirements_publisher."""

from backend.app.platform.events.candidate_requirements_publisher import (
    EVENT_TYPE,
    EVENT_VERSION,
    PersistedRequirementEvaluation,
    evaluate_persist_and_publish_candidate_requirements,
    persist_requirement_evaluation_record,
    publish_candidate_requirements_evaluated_event,
)

__all__ = [
    "PersistedRequirementEvaluation",
    "evaluate_persist_and_publish_candidate_requirements",
    "persist_requirement_evaluation_record",
    "publish_candidate_requirements_evaluated_event",
    "EVENT_TYPE",
    "EVENT_VERSION",
]
