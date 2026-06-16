"""Process Engine package — platform process registry and runtime adapters."""

from backend.app.process_engine.constants import DEFAULT_REGISTRY_VERSION, RECRUITMENT_MODULE
from backend.app.process_engine.evaluator_adapter import TransitionEvaluatorAdapter
from backend.app.process_engine.handoff_evaluator import (
    HandoffEvaluation,
    evaluate_handoff_destinations,
    handoff_evaluation_to_dict,
)
from backend.app.process_engine.pipeline_mapping import (
    QualifiedSystemStage,
    infer_pe_system_stage_code,
    recruitment_legacy_to_pe_map,
    resolve_qualified_system_stage,
    resolve_qualified_system_stage_for_candidate,
)
from backend.app.process_engine.profile_resolver import (
    EffectiveProcessProfile,
    effective_process_profile_to_dict,
    resolve_effective_process_profile,
    resolve_effective_process_profile_for_candidate,
    resolve_effective_process_profile_for_candidate_id,
)
from backend.app.process_engine.registry import ProcessEngineRegistry

__all__ = [
    "DEFAULT_REGISTRY_VERSION",
    "EffectiveProcessProfile",
    "HandoffEvaluation",
    "ProcessEngineRegistry",
    "QualifiedSystemStage",
    "RECRUITMENT_MODULE",
    "TransitionEvaluatorAdapter",
    "effective_process_profile_to_dict",
    "evaluate_handoff_destinations",
    "handoff_evaluation_to_dict",
    "infer_pe_system_stage_code",
    "recruitment_legacy_to_pe_map",
    "resolve_effective_process_profile",
    "resolve_effective_process_profile_for_candidate",
    "resolve_effective_process_profile_for_candidate_id",
    "resolve_qualified_system_stage",
    "resolve_qualified_system_stage_for_candidate",
]
