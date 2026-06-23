"""P3A — Process Profile requirement source for Requirement Rules Engine."""

from __future__ import annotations

from typing import Any, Optional

from backend.app.process_engine.manifests.recruitment import (
    DEFAULT_PROFILE_CODE,
    recruitment_module_manifest,
)
from backend.app.requirement_rules.constants import (
    RULE_TYPE_DOCUMENT_REQUIRED,
    RULE_TYPE_FIELD_REQUIRED,
    SOURCE_PROCESS_PROFILE,
    VALID_CONTEXTS,
)


def get_process_profile_catalog(process_profile_code: str) -> Optional[dict[str, Any]]:
    """Load module manifest for a known process profile code."""
    code = str(process_profile_code or "").strip()
    if code == DEFAULT_PROFILE_CODE:
        return recruitment_module_manifest()
    return None


def _norm_stage(value: str | None) -> str:
    return str(value or "").strip().lower()


def _stage_matches(
    requirement_stage: str | None,
    *,
    stage_code: str | None,
) -> bool:
    """Process Profile rules apply only when system_stage matches stage_code."""
    req_stage = _norm_stage(requirement_stage)
    if not req_stage:
        return True
    target = _norm_stage(stage_code)
    if not target:
        return False
    return req_stage == target


def _context_matches(requirement_context: str | None, evaluation_context: str) -> bool:
    req_ctx = _norm_stage(requirement_context)
    if not req_ctx:
        return True
    return req_ctx == _norm_stage(evaluation_context)


def build_process_profile_rules(
    *,
    process_profile_code: str,
    context: str,
    stage_code: str | None = None,
    transition_code: str | None = None,
    occupied_field_targets: set[str] | None = None,
    occupied_doc_targets: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Compile stage-scoped Process Profile rules (additive only — no overrides)."""
    code = str(process_profile_code or "").strip()
    if not code:
        return []

    ctx = str(context or "readiness").strip().lower()
    if ctx not in VALID_CONTEXTS:
        ctx = "readiness"

    catalog = get_process_profile_catalog(code)
    if catalog is None:
        return []

    occupied_fields = {str(item).strip() for item in (occupied_field_targets or set()) if str(item).strip()}
    occupied_docs = {str(item).strip().lower() for item in (occupied_doc_targets or set()) if str(item).strip()}

    rules: list[dict[str, Any]] = []
    transition_ref = str(transition_code or "").strip() or None

    for row in catalog.get("field_requirements") or []:
        if not isinstance(row, dict):
            continue
        req_config = row.get("config") if isinstance(row.get("config"), dict) else {}
        if str(req_config.get("requirement_kind") or "canonical_fields").strip().lower() != "canonical_fields":
            continue
        if not _context_matches(req_config.get("context"), ctx):
            continue
        if not _stage_matches(req_config.get("system_stage"), stage_code=stage_code):
            continue
        req_code = str(row.get("code") or "").strip()
        for field_row in req_config.get("fields") or []:
            if not isinstance(field_row, dict):
                continue
            qualified_code = str(field_row.get("qualified_code") or "").strip()
            if not qualified_code or qualified_code in occupied_fields:
                continue
            level = str(field_row.get("level") or "required").strip().lower()
            rules.append(
                {
                    "rule_type": RULE_TYPE_FIELD_REQUIRED,
                    "source": SOURCE_PROCESS_PROFILE,
                    "source_ref": code,
                    "target": qualified_code,
                    "qualified_code": qualified_code,
                    "level": "blocking" if level == "required" else "warning",
                    "context": ctx,
                    "stage_code": _norm_stage(req_config.get("system_stage")) or None,
                    "transition_code": transition_ref,
                    "reason_code": f"process_profile_field_required:{qualified_code}",
                    "process_requirement_code": req_code or None,
                }
            )

    for row in catalog.get("document_requirements") or []:
        if not isinstance(row, dict):
            continue
        req_config = row.get("config") if isinstance(row.get("config"), dict) else {}
        if str(req_config.get("requirement_kind") or "").strip().lower() != "document_types":
            continue
        if req_config.get("resolver"):
            continue
        if not _context_matches(req_config.get("context"), ctx):
            continue
        if not _stage_matches(req_config.get("system_stage"), stage_code=stage_code):
            continue
        req_code = str(row.get("code") or "").strip()
        for doc_row in req_config.get("required_documents") or []:
            if not isinstance(doc_row, dict):
                continue
            doc_code = str(doc_row.get("document_type_code") or "").strip().lower()
            if not doc_code or doc_code in occupied_docs:
                continue
            rules.append(
                {
                    "rule_type": RULE_TYPE_DOCUMENT_REQUIRED,
                    "source": SOURCE_PROCESS_PROFILE,
                    "source_ref": code,
                    "target": doc_code,
                    "document_type_code": doc_code,
                    "pack_code": None,
                    "level": str(doc_row.get("level") or "blocking").strip().lower(),
                    "verification": str(doc_row.get("verification") or "optional").strip().lower(),
                    "context": ctx,
                    "stage_code": _norm_stage(req_config.get("system_stage")) or None,
                    "transition_code": transition_ref,
                    "reason_code": str(doc_row.get("reason_code") or f"process_profile_document_required:{doc_code}"),
                    "process_requirement_code": req_code or None,
                }
            )

    return rules
