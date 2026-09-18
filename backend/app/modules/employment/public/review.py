"""Workforce-facing Employment review / directory helpers.

Lazy re-exports avoid import cycles with Recruitment pipeline / Workforce.
"""

from __future__ import annotations

from typing import Any

_EXPORTS = {
    "CATALOG_TO_DOCUMENT_KEY",
    "DATA_ONLY_VERIFICATION_KEYS",
    "OPTIONAL_FILE_VERIFICATION_KEYS",
    "VERIFICATION_GATED_CHECKLIST",
    "VERIFICATION_SLOT_DEFS",
    "address_dict_complete",
    "build_hr_verification_plan",
    "document_verification_counts_by_review",
    "documents_for_approval_from_plan",
    "enrich_approval_rows_with_verification",
    "enrich_hr_review_panel",
    "list_document_control_tasks",
    "list_hr_documents_expiring",
    "list_hr_documents_missing",
    "list_operational_risk_items",
    "load_hr_expected_documents",
    "merge_candidate_documents_into_approval_rows",
    "plan_blocks_approve",
    "promote_address_fields",
    "rebuild_panel_checklists_after_data_verification",
    "resolve_critical_field_codes",
    "resolve_position_category_for_review",
    "sync_checklist_from_verifications",
    "sync_verification_plan_with_enriched_docs",
}

_SOURCE = {
    "CATALOG_TO_DOCUMENT_KEY": ("backend.app.services.hr_verification_plan", "CATALOG_TO_DOCUMENT_KEY"),
    "DATA_ONLY_VERIFICATION_KEYS": ("backend.app.services.hr_verified_field_catalog", "DATA_ONLY_VERIFICATION_KEYS"),
    "OPTIONAL_FILE_VERIFICATION_KEYS": ("backend.app.services.hr_verified_field_catalog", "OPTIONAL_FILE_VERIFICATION_KEYS"),
    "VERIFICATION_GATED_CHECKLIST": ("backend.app.services.hr_document_verification", "VERIFICATION_GATED_CHECKLIST"),
    "VERIFICATION_SLOT_DEFS": ("backend.app.services.hr_verification_plan", "VERIFICATION_SLOT_DEFS"),
    "address_dict_complete": ("backend.app.services.hr_profile_address", "address_dict_complete"),
    "build_hr_verification_plan": ("backend.app.services.hr_verification_plan", "build_hr_verification_plan"),
    "document_verification_counts_by_review": (
        "backend.app.services.hr_inbox",
        "_document_verification_counts_by_review",
    ),
    "documents_for_approval_from_plan": ("backend.app.services.hr_verification_plan", "documents_for_approval_from_plan"),
    "enrich_approval_rows_with_verification": (
        "backend.app.services.hr_document_verification",
        "enrich_approval_rows_with_verification",
    ),
    "enrich_hr_review_panel": ("backend.app.services.hr_review_case_ux", "enrich_hr_review_panel"),
    "list_document_control_tasks": ("backend.app.services.hr_document_control_tasks", "list_document_control_tasks"),
    "list_hr_documents_expiring": ("backend.app.services.hr_documents_queue", "list_hr_documents_expiring"),
    "list_hr_documents_missing": ("backend.app.services.hr_documents_queue", "list_hr_documents_missing"),
    "list_operational_risk_items": ("backend.app.services.hr_operational_risk", "list_operational_risk_items"),
    "load_hr_expected_documents": ("backend.app.services.hr_expected_documents", "load_hr_expected_documents"),
    "merge_candidate_documents_into_approval_rows": (
        "backend.app.services.hr_review_document_resolution",
        "merge_candidate_documents_into_approval_rows",
    ),
    "plan_blocks_approve": ("backend.app.services.hr_verification_plan", "plan_blocks_approve"),
    "promote_address_fields": ("backend.app.services.hr_profile_address", "promote_address_fields"),
    "rebuild_panel_checklists_after_data_verification": (
        "backend.app.services.hr_data_verification",
        "rebuild_panel_checklists_after_data_verification",
    ),
    "resolve_critical_field_codes": ("backend.app.services.hr_verification_requirements", "resolve_critical_field_codes"),
    "resolve_position_category_for_review": (
        "backend.app.services.hr_verification_requirements",
        "resolve_position_category_for_review",
    ),
    "sync_checklist_from_verifications": (
        "backend.app.services.hr_document_verification",
        "sync_checklist_from_verifications",
    ),
    "sync_verification_plan_with_enriched_docs": (
        "backend.app.services.hr_verification_plan",
        "sync_verification_plan_with_enriched_docs",
    ),
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    if name not in _SOURCE:
        raise AttributeError(name)
    mod_name, attr = _SOURCE[name]
    import importlib

    mod = importlib.import_module(mod_name)
    return getattr(mod, attr)


def __dir__() -> list[str]:
    return list(__all__)
