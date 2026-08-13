"""Recruitment module manifest for Process Engine (platform catalog source)."""

from __future__ import annotations

from typing import Any

RECRUITMENT_MODULE = "recruitment"

HANDOFF_MODES = frozenset({"none", "client_portal", "internal_hr", "both"})

DEFAULT_PROFILE_CODE = "recruitment_default"
DEFAULT_PIPELINE_CODE = "recruitment_agency_default"
RECRUITMENT_PIPELINE_GATES_RULE_CODE = "recruitment_pipeline_gates_default"


def _default_pipeline_gates_rule_config() -> dict[str, Any]:
    """Lazy import avoids circular dependency with transition_rules_adapter."""
    from backend.app.process_engine.transition_rules_adapter import default_hiring_pipeline_gates_rule_config

    return default_hiring_pipeline_gates_rule_config()


def recruitment_module_manifest() -> dict[str, Any]:
    """Declarative manifest consumed by ProcessEngineRegistry.register_module."""
    system_stages = [
        _stage("new", "generic_progress_v1", terminal=False, bucket="new"),
        _stage("no_answer", "generic_progress_v1", terminal=False, bucket="in_progress"),
        _stage("contacted", "generic_progress_v1", terminal=False, bucket="in_progress"),
        _stage("questionnaire_submitted", "generic_progress_v1", terminal=False, bucket="in_progress"),
        _stage("waiting_documents", "documents_gate_v1", terminal=False, bucket="in_progress"),
        _stage("documents_received", "documents_received_v1", terminal=False, bucket="in_progress"),
        _stage("docs_wait", "documents_gate_v1", terminal=False, bucket="in_progress", alias_of="waiting_documents"),
        _stage("docs_got", "documents_received_v1", terminal=False, bucket="in_progress", alias_of="documents_received"),
        _stage("ready_for_handoff", "ready_for_handoff_v1", terminal=False, bucket="in_progress"),
        _stage("processing_by_client", "generic_progress_v1", terminal=False, bucket="in_progress"),
        _stage("processing_by_hr", "hr_intake_v1", terminal=False, bucket="in_progress"),
        _stage("rejected", "rejected_v1", terminal=True, bucket="declined_rejected"),
        _stage("declined", "rejected_v1", terminal=True, bucket="declined_rejected"),
        _stage("employed", "employed_v1", terminal=True, bucket="hired"),
        _stage("hired", "employed_v1", terminal=True, bucket="hired"),
    ]

    stage_templates = [
        _template("generic_progress_v1", "Generic in-progress stage"),
        _template("documents_gate_v1", "Waiting for required documents"),
        _template("documents_received_v1", "Documents received / under review"),
        _template(
            "ready_for_handoff_v1",
            "Ready for handoff — uses TransferPolicy evaluator adapter",
            evaluator_hook="recruitment.transfer_policy_v1",
            handoff_modes=list(HANDOFF_MODES),
        ),
        _template("rejected_v1", "Rejected / declined terminal stage", requires_reason=True),
        _template("employed_v1", "Employed / hired terminal stage"),
        _template("hr_intake_v1", "HR processing intake"),
    ]

    pipeline_stages = [
        _pipe_stage(10, "New", "new"),
        _pipe_stage(20, "Contacted", "contacted"),
        _pipe_stage(30, "Waiting for documents", "waiting_documents", legacy_code="docs_wait"),
        _pipe_stage(40, "Documents received", "documents_received", legacy_code="docs_got"),
        _pipe_stage(50, "Ready for handoff", "ready_for_handoff"),
        _pipe_stage(60, "Rejected", "rejected"),
    ]

    transition_rules = [
        {
            "code": "ready_for_handoff_gate",
            "name": "Ready for handoff transition gate",
            "priority": 10,
            "config": {
                "trigger": {"type": "enter_stage", "system_stage": "ready_for_handoff"},
                "evaluator_hook": "recruitment.transfer_policy_v1",
                "require_destination_for_handoff_create": True,
            },
        },
        {
            "code": RECRUITMENT_PIPELINE_GATES_RULE_CODE,
            "name": "Recruitment pipeline stage gates (profile-scoped)",
            "priority": 100,
            "process_profile_code": DEFAULT_PROFILE_CODE,
            "config": _default_pipeline_gates_rule_config(),
        },
    ]

    handoff_rules = [
        {
            "code": "handoff_none",
            "name": "Readiness only (no handoff destination)",
            "handoff_mode": "none",
            "config": {
                "source": {"module": RECRUITMENT_MODULE, "system_stage": "ready_for_handoff"},
                "enabled_when": {"modules_installed": [RECRUITMENT_MODULE]},
                "destination_impl": {"type": "none"},
            },
        },
        {
            "code": "handoff_client_portal",
            "name": "Client portal / magic link handoff",
            "handoff_mode": "client_portal",
            "config": {
                "source": {"module": RECRUITMENT_MODULE, "system_stage": "ready_for_handoff"},
                "enabled_when": {"modules_installed": [RECRUITMENT_MODULE]},
                "destination_impl": {"type": "client_portal", "impl_ref": "tenant_link"},
            },
        },
        {
            "code": "handoff_internal_hr",
            "name": "Internal HR handoff",
            "handoff_mode": "internal_hr",
            "config": {
                "source": {"module": RECRUITMENT_MODULE, "system_stage": "ready_for_handoff"},
                "target": {"module": "hr", "system_stage": "received_from_recruitment", "entity_type": "hr_case"},
                "enabled_when": {"modules_installed": [RECRUITMENT_MODULE, "hr"]},
                "destination_impl": {"type": "internal_hr", "contract": "handoff_contract_v1"},
            },
        },
        {
            "code": "handoff_both",
            "name": "HR and client portal destinations",
            "handoff_mode": "both",
            "config": {
                "source": {"module": RECRUITMENT_MODULE, "system_stage": "ready_for_handoff"},
                "enabled_when": {"modules_installed": [RECRUITMENT_MODULE]},
                "destination_impl": {"type": "both", "impl_ref": "tenant_link"},
            },
        },
    ]

    field_requirements = [
        {
            "code": "recruitment_contact_core",
            "name": "Core contact fields for handoff transition",
            "entity_type": "candidate",
            "config": {
                "requirement_kind": "canonical_fields",
                "context": "transition",
                "system_stage": "ready_for_handoff",
                "fields": [
                    {
                        "qualified_code": "recruitment.candidate.contacts.phone",
                        "level": "required",
                        "scope": "transition",
                    },
                    {
                        "qualified_code": "recruitment.candidate.contacts.email",
                        "level": "required",
                        "scope": "transition",
                    },
                    {
                        "qualified_code": "platform.identity.address",
                        "level": "required",
                        "scope": "transition",
                    },
                ],
            },
        },
    ]

    document_requirements = [
        {
            "code": "recruitment_handoff_documents",
            "name": "Document requirements resolved via Document Hub at transition",
            "entity_type": "candidate",
            "config": {
                "resolver": "document_hub.workforce_eligibility",
                "relaxed_by_override": True,
            },
        },
        {
            "code": "recruitment_handoff_medical",
            "name": "Medical certificate required at handoff transition",
            "entity_type": "candidate",
            "config": {
                "requirement_kind": "document_types",
                "context": "transition",
                "system_stage": "ready_for_handoff",
                "required_documents": [
                    {
                        "document_type_code": "medical_certificate",
                        "level": "blocking",
                        "verification": "optional",
                        "reason_code": "process_profile_handoff_medical",
                    }
                ],
            },
        },
    ]

    override_rules = [
        {
            "code": "recruitment_handoff_override",
            "name": "Approved pipeline override for handoff documents",
            "scope": "both",
            "config": {
                "relaxable": ["document_type_code"],
                "approval_roles": ["administrator", "team_lead"],
                "legacy_storage": "candidate_pipeline_overrides",
            },
        },
    ]

    process_profiles = [
        {
            "code": DEFAULT_PROFILE_CODE,
            "name": "Recruitment default",
            "is_default": True,
            "config": {
                "handoff_mode": "both",
                "stage_overrides": {
                    "ready_for_handoff": {
                        "handoff_mode": "both",
                        "destination_required": True,
                        "recruiter_confirmation_required": True,
                    },
                },
                "legacy_candidate_profile_code": "driver_ce_default",
            },
            "pipeline_code": DEFAULT_PIPELINE_CODE,
        },
    ]

    pipeline_templates = [
        {
            "code": DEFAULT_PIPELINE_CODE,
            "name": "Recruitment agency default pipeline",
            "config": {"stages": pipeline_stages},
        },
    ]

    return {
        "module": RECRUITMENT_MODULE,
        "registry_version": "process_engine_v1",
        "system_stages": system_stages,
        "stage_templates": stage_templates,
        "pipeline_templates": pipeline_templates,
        "process_profiles": process_profiles,
        "transition_rules": transition_rules,
        "handoff_rules": handoff_rules,
        "field_requirements": field_requirements,
        "document_requirements": document_requirements,
        "override_rules": override_rules,
    }


def _stage(
    code: str,
    template_code: str,
    *,
    terminal: bool,
    bucket: str,
    alias_of: str | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "code": code,
        "name": code.replace("_", " ").title(),
        "template_code": template_code,
        "terminal": terminal,
        "analytics_bucket": bucket,
        "config": {},
    }
    if alias_of:
        row["config"]["alias_of"] = alias_of
    return row


def _template(code: str, name: str, **extra: Any) -> dict[str, Any]:
    config = {k: v for k, v in extra.items() if k not in {"name", "code"}}
    return {"code": code, "name": name, "config": config}


def _pipe_stage(
    order: int,
    user_label: str,
    system_stage_code: str,
    *,
    legacy_code: str | None = None,
) -> dict[str, Any]:
    row = {
        "order": order,
        "user_label": user_label,
        "maps_to_module": RECRUITMENT_MODULE,
        "maps_to_code": system_stage_code,
    }
    if legacy_code:
        row["legacy_funnel_stage_code"] = legacy_code
    return row
