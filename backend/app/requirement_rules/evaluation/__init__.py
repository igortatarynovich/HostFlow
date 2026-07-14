"""Requirement Evaluation domain (ADR-018 PR 2B-1 / 2B-2 / 2B-3)."""

from backend.app.requirement_rules.evaluation.fingerprint import (
    EvaluationFingerprintInput,
    compute_evaluation_input_fingerprint,
)
from backend.app.requirement_rules.evaluation.process_state import (
    ProcessCompletionSufficient,
    ProcessState,
    map_process_state_to_requirement_status,
)
from backend.app.requirement_rules.evaluation.result_contract import (
    EvaluationReason,
    EvaluationReasonCode,
    EvaluationReasonSeverity,
    EvaluationReasonSourceType,
    ExcludedAlternative,
    MatchRole,
    MatchedDocumentReference,
    MatchedProcessReference,
    NextActionCode,
    OverallEvaluationStatus,
    RequirementApplicability,
    RequirementEvaluationResult,
    RequirementEvaluationRow,
    RequirementEvaluationStatus,
    RequirementOwnership,
    compute_can_transition,
    compute_is_blocking,
    compute_overall_status,
    recompute_blocking_for_target_stage,
    validate_matched_document_reference,
)
from backend.app.requirement_rules.evaluation.service import (
    RequirementEvaluationRunInput,
    evaluate_requirements,
)
from backend.app.requirement_rules.evaluation.tie_break import (
    TieBreakCandidate,
    select_best_document_candidate,
)
from backend.app.requirement_rules.evaluation.workspace_adapter import (
    evaluation_result_to_checklist,
    evaluation_result_to_pipeline_blockers,
    evaluation_result_to_requirement_gate,
)

__all__ = [
    "EvaluationFingerprintInput",
    "EvaluationReason",
    "EvaluationReasonCode",
    "EvaluationReasonSeverity",
    "EvaluationReasonSourceType",
    "ExcludedAlternative",
    "MatchRole",
    "MatchedDocumentReference",
    "MatchedProcessReference",
    "NextActionCode",
    "OverallEvaluationStatus",
    "ProcessCompletionSufficient",
    "ProcessState",
    "RequirementApplicability",
    "RequirementEvaluationResult",
    "RequirementEvaluationRow",
    "RequirementEvaluationStatus",
    "RequirementEvaluationRunInput",
    "RequirementOwnership",
    "TieBreakCandidate",
    "compute_can_transition",
    "compute_evaluation_input_fingerprint",
    "compute_is_blocking",
    "compute_overall_status",
    "evaluate_requirements",
    "evaluation_result_to_checklist",
    "evaluation_result_to_pipeline_blockers",
    "evaluation_result_to_requirement_gate",
    "map_process_state_to_requirement_status",
    "recompute_blocking_for_target_stage",
    "select_best_document_candidate",
    "validate_matched_document_reference",
]
