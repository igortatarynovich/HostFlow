"""Requirement Rules evaluator (P1) — pure evaluation, no side effects."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from backend.app.document_runtime.evaluator import (
    evaluate_document_runtime,
    map_runtime_to_requirement_items,
    runtime_precedence,
)
from backend.app.document_runtime.readiness_bridge import (
    build_document_runtime_section,
    enrich_documents_with_runtime,
)
from backend.app.requirement_rules.constants import (
    LEVEL_BLOCKING,
    REQUIREMENT_EVALUATION_V1,
    RULE_TYPE_DOCUMENT_REQUIRED,
    RULE_TYPE_FIELD_REQUIRED,
)
from backend.app.requirement_rules.registry import build_requirement_rule_set


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False


def _payload_value(normalized_payload: dict[str, Any], qualified_code: str) -> Any:
    if not isinstance(normalized_payload, dict):
        return None
    if qualified_code in normalized_payload:
        return normalized_payload.get(qualified_code)
    legacy_aliases = {
        "recruitment.candidate.first_name": ["first_name"],
        "recruitment.candidate.last_name": ["last_name"],
        "recruitment.candidate.contacts.phone": ["phone"],
        "recruitment.candidate.contacts.email": ["email"],
        "platform.identity.citizenship": ["citizenship"],
        "platform.identity.birth_date": ["birth_date"],
        "platform.identity.address": ["address"],
        "recruitment.candidate.experience.years_ce": ["experience_eu_years", "years_ce"],
    }
    for key in legacy_aliases.get(qualified_code, []):
        if key in normalized_payload and not _is_empty(normalized_payload.get(key)):
            return normalized_payload.get(key)
    return None


def _document_type_code(doc: dict[str, Any]) -> str:
    for key in ("document_type_code", "type", "type_code", "doc_type"):
        raw = doc.get(key)
        if raw is not None and str(raw).strip():
            return str(raw).strip().lower()
    return ""


def _documents_index(documents: list[Any]) -> dict[str, dict[str, Any]]:
    """Index best document instance per type using Document Runtime precedence."""
    index: dict[str, dict[str, Any]] = {}
    runtime_by_code: dict[str, dict[str, Any]] = {}
    for raw in documents or []:
        if not isinstance(raw, dict):
            continue
        code = _document_type_code(raw)
        if not code:
            continue
        runtime = raw.get("document_runtime")
        if not isinstance(runtime, dict):
            runtime = evaluate_document_runtime(raw, document_type_code=code)
        existing = index.get(code)
        if existing is None:
            index[code] = raw
            runtime_by_code[code] = runtime
            continue
        existing_runtime = runtime_by_code.get(code) or {}
        if runtime_precedence(runtime) >= runtime_precedence(existing_runtime):
            index[code] = raw
            runtime_by_code[code] = runtime
    return index


def evaluate_requirement_rules(
    profile_view: dict[str, Any],
    *,
    context: str,
    normalized_payload: Optional[dict[str, Any]] = None,
    documents: Optional[list[Any]] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    stage_code: str | None = None,
    transition_code: str | None = None,
    tenant_overrides: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Evaluate Entity Profile + Document Pack + Process Profile + Tenant Overrides."""
    rule_set = build_requirement_rule_set(
        profile_view,
        context=context,
        stage_code=stage_code,
        transition_code=transition_code,
        tenant_overrides=tenant_overrides,
    )
    payload = dict(normalized_payload or {})
    doc_list = enrich_documents_with_runtime(list(documents or []))
    doc_index = _documents_index(doc_list)

    required_fields: list[dict[str, Any]] = []
    required_documents: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    for rule in rule_set.get("rules") or []:
        if not isinstance(rule, dict):
            continue
        rule_type = str(rule.get("rule_type") or "").strip()
        level = str(rule.get("level") or LEVEL_BLOCKING).strip().lower()
        reason_code = str(rule.get("reason_code") or "").strip()

        if rule_type == RULE_TYPE_FIELD_REQUIRED:
            code = str(rule.get("qualified_code") or rule.get("target") or "").strip()
            if not code:
                continue
            entry = {
                "qualified_code": code,
                "level": level,
                "reason_code": reason_code or f"field_required:{code}",
                "source": rule.get("source"),
                "source_ref": rule.get("source_ref"),
            }
            required_fields.append(entry)
            if _is_empty(_payload_value(payload, code)):
                blocker = {
                    "code": reason_code or f"field_required:{code}",
                    "message": f"Required field missing: {code}",
                    "source_rule_id": code,
                    "layer": "requirement_rules",
                    "qualified_code": code,
                }
                if level == LEVEL_BLOCKING:
                    blockers.append(blocker)
                else:
                    warnings.append(blocker)

        elif rule_type == RULE_TYPE_DOCUMENT_REQUIRED:
            doc_code = str(rule.get("document_type_code") or rule.get("target") or "").strip().lower()
            if not doc_code:
                continue
            verification = str(rule.get("verification") or "optional").strip().lower()
            entry = {
                "document_type_code": doc_code,
                "pack_code": rule.get("pack_code"),
                "level": level,
                "verification": verification,
                "reason_code": reason_code or f"document_required:{doc_code}",
                "source": rule.get("source"),
                "source_ref": rule.get("source_ref"),
            }
            required_documents.append(entry)
            doc_row = doc_index.get(doc_code)
            runtime = (
                doc_row.get("document_runtime")
                if isinstance(doc_row, dict) and isinstance(doc_row.get("document_runtime"), dict)
                else evaluate_document_runtime(doc_row, document_type_code=doc_code)
            )
            if not runtime.get("satisfies_requirement"):
                doc_blockers, doc_warnings = map_runtime_to_requirement_items(
                    runtime,
                    doc_code=doc_code,
                    verification=verification,
                    reason_code=reason_code or f"document_required:{doc_code}",
                    level=level,
                )
                if level == LEVEL_BLOCKING:
                    blockers.extend(doc_blockers)
                    warnings.extend(doc_warnings)
                else:
                    warnings.extend(doc_blockers)
                    warnings.extend(doc_warnings)

    return {
        "evaluation_version": REQUIREMENT_EVALUATION_V1,
        "entity_profile_code": rule_set["entity_profile_code"],
        "entity_type": entity_type or rule_set.get("entity_type"),
        "entity_id": entity_id,
        "context": rule_set["context"],
        "stage_code": rule_set.get("stage_code"),
        "transition_code": rule_set.get("transition_code"),
        "process_profile_code": rule_set.get("process_profile_code"),
        "required_fields": required_fields,
        "required_documents": required_documents,
        "blockers": blockers,
        "warnings": warnings,
        "satisfied": len(blockers) == 0,
        "rule_sources_applied": rule_set.get("rule_sources_applied") or [],
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "p1_sources_only": bool(rule_set.get("p1_sources_only", True)),
        "document_runtime": build_document_runtime_section(doc_list),
    }
