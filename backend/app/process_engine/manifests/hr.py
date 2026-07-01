"""HR module manifest for Process Engine — system stages only (P0).

Registers hr.* semantic stages separately from recruitment. No employee funnel,
pipeline template, or process profile runtime in this phase.
"""

from __future__ import annotations

from typing import Any

HR_MODULE = "hr"

# Placeholder handoff mode — documents inbound contract target; not wired to runtime routing.
HR_INBOUND_HANDOFF_PLACEHOLDER_MODE = "inbound_contract_placeholder"

# Recruitment legacy four-bucket values — HR manifest must not use these as analytics_bucket.
RECRUITMENT_LEGACY_ANALYTICS_BUCKETS = frozenset(
    {"new", "in_progress", "hired", "declined_rejected"}
)


def hr_module_manifest() -> dict[str, Any]:
    """Declarative manifest consumed by ProcessEngineRegistry.register_module."""
    system_stages = [
        _stage("received_from_recruitment", "hr_intake_v1", bucket="intake"),
        _stage("handoff_pending", "hr_intake_v1", bucket="intake"),
        _stage("accepted_by_hr", "hr_review_v1", bucket="review"),
        _stage("hr_review_in_progress", "hr_review_v1", bucket="review"),
        _stage("waiting_documents", "hr_waiting_v1", bucket="waiting"),
        _stage("waiting_payments", "hr_waiting_v1", bucket="waiting"),
        _stage("waiting_work_permit", "hr_waiting_v1", bucket="waiting"),
        _stage("waiting_red_paper", "hr_waiting_v1", bucket="waiting"),
        _stage("verification", "hr_verification_v1", bucket="verification"),
        _stage("approved_for_employment", "hr_employment_v1", bucket="employment"),
        _stage("contract", "hr_contract_v1", bucket="employment"),
        _stage("employment_pending", "hr_employment_v1", bucket="employment"),
        _stage("active", "hr_active_v1", bucket="active", terminal=True),
        _stage("employed", "hr_active_v1", bucket="active", terminal=True),
        _stage("returned_to_recruitment", "hr_returned_v1", bucket="returned", terminal=True),
        _stage("rejected_by_hr", "hr_rejected_v1", bucket="rejected", terminal=True),
    ]

    stage_templates = [
        _template("hr_intake_v1", "HR intake — handoff received"),
        _template("hr_review_v1", "HR acceptance and review in progress"),
        _template("hr_waiting_v1", "HR waiting substate (documents, payments, permits)"),
        _template("hr_verification_v1", "HR data and compliance verification"),
        _template("hr_contract_v1", "HR contract preparation"),
        _template("hr_employment_v1", "HR employment activation branch"),
        _template("hr_active_v1", "Active employment confirmed"),
        _template("hr_returned_v1", "Returned to recruitment"),
        _template("hr_rejected_v1", "Rejected by HR"),
    ]

    handoff_rules = [
        {
            "code": "hr_inbound_handoff_contract_v1",
            "name": "Inbound recruitment handoff (contract placeholder — not wired)",
            "handoff_mode": HR_INBOUND_HANDOFF_PLACEHOLDER_MODE,
            "config": {
                "contract_ref": "handoff_contract_v1",
                "entry_system_stage": "received_from_recruitment",
                "entity_type": "hr_case",
                "status": "placeholder",
                "note": (
                    "Future handoff contract entry point for HR module. "
                    "Recruitment outbound handoff references hr.received_from_recruitment; "
                    "cross-module runtime wiring is deferred."
                ),
            },
        },
    ]

    return {
        "module": HR_MODULE,
        "registry_version": "process_engine_v1",
        "system_stages": system_stages,
        "stage_templates": stage_templates,
        "pipeline_templates": [],
        "process_profiles": [],
        "transition_rules": [],
        "handoff_rules": handoff_rules,
        "field_requirements": [],
        "document_requirements": [],
        "override_rules": [],
    }


def _stage(
    code: str,
    template_code: str,
    *,
    bucket: str,
    terminal: bool = False,
) -> dict[str, Any]:
    return {
        "code": code,
        "name": code.replace("_", " ").title(),
        "template_code": template_code,
        "terminal": terminal,
        "analytics_bucket": bucket,
        "config": {"owner_lane": "hr"},
    }


def _template(code: str, name: str) -> dict[str, Any]:
    return {"code": code, "name": name, "config": {}}
