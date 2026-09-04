"""P3B — Tenant override layer for Requirement Rules Engine."""

from __future__ import annotations

from typing import Any, Optional

from backend.app.reference.requirement_policy_parallel_authority_retirement import (
    filter_out_document_required_overrides,
)
from backend.app.requirement_rules.constants import (
    LEVEL_BLOCKING,
    LEVEL_WARNING,
    OVERRIDE_KIND_ADD,
    OVERRIDE_KIND_RELAX,
    OVERRIDE_KIND_SEVERITY,
    OVERRIDE_STATUS_ACTIVE,
    RULE_TYPE_DOCUMENT_REQUIRED,
    RULE_TYPE_FIELD_REQUIRED,
    SOURCE_ENTITY_PROFILE,
    SOURCE_TENANT_OVERRIDE,
)
from backend.app.services.pipeline_override_policy import NON_OVERRIDABLE_DOC_TYPES


def _rule_dedup_key(rule: dict[str, Any]) -> tuple[str, str]:
    rule_type = str(rule.get("rule_type") or "").strip()
    if rule_type == RULE_TYPE_FIELD_REQUIRED:
        return ("field", str(rule.get("qualified_code") or rule.get("target") or "").strip())
    if rule_type == RULE_TYPE_DOCUMENT_REQUIRED:
        return ("document", str(rule.get("document_type_code") or rule.get("target") or "").strip().lower())
    return ("other", str(rule.get("target") or rule.get("reason_code") or ""))


class TenantOverridePolicyError(ValueError):
    """Raised when a tenant override violates platform policy."""


def _norm(value: str | None) -> str:
    return str(value or "").strip().lower()


def _override_target_key(override: dict[str, Any]) -> tuple[str, str]:
    rule_type = str(override.get("rule_type") or "").strip()
    target = str(override.get("target_code") or "").strip()
    if rule_type == RULE_TYPE_DOCUMENT_REQUIRED:
        return ("document", target.lower())
    return ("field", target)


def _matches_scope(
    override: dict[str, Any],
    *,
    entity_profile_code: str,
    context: str,
    stage_code: str | None,
) -> bool:
    profile = str(override.get("entity_profile_code") or "").strip()
    if profile and profile != entity_profile_code:
        return False
    ov_context = str(override.get("context") or "").strip()
    if ov_context and _norm(ov_context) != _norm(context):
        return False
    ov_stage = str(override.get("stage_code") or "").strip()
    if ov_stage and _norm(ov_stage) != _norm(stage_code or ""):
        return False
    return True


def filter_applicable_tenant_overrides(
    overrides: list[dict[str, Any]],
    *,
    entity_profile_code: str,
    context: str,
    stage_code: str | None,
) -> list[dict[str, Any]]:
    applicable: list[dict[str, Any]] = []
    for row in overrides or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("status") or OVERRIDE_STATUS_ACTIVE).strip().lower() != OVERRIDE_STATUS_ACTIVE:
            continue
        if not _matches_scope(
            row,
            entity_profile_code=entity_profile_code,
            context=context,
            stage_code=stage_code,
        ):
            continue
        applicable.append(row)
    return applicable


def validate_tenant_override_policy(
    override: dict[str, Any],
    *,
    canonical_field_targets: set[str],
    existing_rule: dict[str, Any] | None = None,
) -> None:
    """Enforce P3B hard rules at write/compile time."""
    kind = str(override.get("override_kind") or "").strip().lower()
    rule_type = str(override.get("rule_type") or "").strip()
    target = str(override.get("target_code") or "").strip()
    if not target:
        raise TenantOverridePolicyError("target_code is required")

    if rule_type == RULE_TYPE_FIELD_REQUIRED and target in canonical_field_targets:
        if kind in {OVERRIDE_KIND_RELAX, OVERRIDE_KIND_SEVERITY}:
            raise TenantOverridePolicyError(
                f"Cannot relax or change severity for canonical Entity Profile field: {target}"
            )

    if rule_type == RULE_TYPE_DOCUMENT_REQUIRED and _norm(target) in NON_OVERRIDABLE_DOC_TYPES:
        if kind in {OVERRIDE_KIND_RELAX, OVERRIDE_KIND_SEVERITY}:
            raise TenantOverridePolicyError(
                f"Cannot relax or change severity for non-overridable document type: {target}"
            )

    if existing_rule and str(existing_rule.get("source") or "") == SOURCE_ENTITY_PROFILE:
        if kind in {OVERRIDE_KIND_RELAX, OVERRIDE_KIND_SEVERITY}:
            raise TenantOverridePolicyError("Cannot override Entity Profile canonical requirements")

    if kind == OVERRIDE_KIND_SEVERITY:
        level = _norm(override.get("level"))
        if level not in {LEVEL_BLOCKING, LEVEL_WARNING}:
            raise TenantOverridePolicyError("severity override requires level blocking or warning")


def _compile_add_rule(override: dict[str, Any], *, context: str) -> dict[str, Any]:
    rule_type = str(override.get("rule_type") or "").strip()
    target = str(override.get("target_code") or "").strip()
    level = _norm(override.get("level")) or LEVEL_BLOCKING
    override_id = str(override.get("id") or override.get("override_id") or "").strip() or "tenant"
    if rule_type == RULE_TYPE_DOCUMENT_REQUIRED:
        doc_code = target.lower()
        return {
            "rule_type": RULE_TYPE_DOCUMENT_REQUIRED,
            "source": SOURCE_TENANT_OVERRIDE,
            "source_ref": override_id,
            "target": doc_code,
            "document_type_code": doc_code,
            "pack_code": None,
            "level": level,
            "verification": "optional",
            "context": context,
            "reason_code": f"tenant_override_add:{doc_code}",
            "override_kind": OVERRIDE_KIND_ADD,
        }
    return {
        "rule_type": RULE_TYPE_FIELD_REQUIRED,
        "source": SOURCE_TENANT_OVERRIDE,
        "source_ref": override_id,
        "target": target,
        "qualified_code": target,
        "level": level,
        "context": context,
        "reason_code": f"tenant_override_add:{target}",
        "override_kind": OVERRIDE_KIND_ADD,
    }


def apply_tenant_overrides(
    base_rules: list[dict[str, Any]],
    tenant_overrides: list[dict[str, Any]],
    *,
    canonical_field_targets: set[str],
    context: str,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Apply tenant relax/add/severity after platform rule merge."""
    tenant_overrides = filter_out_document_required_overrides(tenant_overrides)
    rules_by_key = {_rule_dedup_key(rule): dict(rule) for rule in base_rules}
    order = [_rule_dedup_key(rule) for rule in base_rules]

    relax_rows = [row for row in tenant_overrides if _norm(row.get("override_kind")) == OVERRIDE_KIND_RELAX]
    severity_rows = [row for row in tenant_overrides if _norm(row.get("override_kind")) == OVERRIDE_KIND_SEVERITY]
    add_rows = [row for row in tenant_overrides if _norm(row.get("override_kind")) == OVERRIDE_KIND_ADD]

    applied_sources: list[dict[str, str]] = []

    for override in relax_rows:
        key = _override_target_key(override)
        dedup_key = (key[0], key[1]) if key[0] == "field" else ("document", key[1])
        existing = rules_by_key.get(dedup_key)
        try:
            validate_tenant_override_policy(
                override,
                canonical_field_targets=canonical_field_targets,
                existing_rule=existing,
            )
        except TenantOverridePolicyError:
            continue
        if dedup_key in rules_by_key:
            del rules_by_key[dedup_key]
            order = [k for k in order if k != dedup_key]
            applied_sources.append(
                {"source": SOURCE_TENANT_OVERRIDE, "ref": str(override.get("id") or override.get("target_code"))}
            )

    for override in severity_rows:
        dedup_key = _override_target_key(override)
        if dedup_key[0] == "document":
            dedup_key = ("document", dedup_key[1])
        else:
            dedup_key = ("field", dedup_key[1])
        existing = rules_by_key.get(dedup_key)
        if existing is None:
            continue
        try:
            validate_tenant_override_policy(
                override,
                canonical_field_targets=canonical_field_targets,
                existing_rule=existing,
            )
        except TenantOverridePolicyError:
            continue
        new_level = _norm(override.get("level")) or existing.get("level")
        existing["level"] = new_level
        rules_by_key[dedup_key] = existing
        applied_sources.append(
            {"source": SOURCE_TENANT_OVERRIDE, "ref": str(override.get("id") or override.get("target_code"))}
        )

    for override in add_rows:
        dedup_key = _override_target_key(override)
        if dedup_key[0] == "document":
            dedup_key = ("document", dedup_key[1])
        else:
            dedup_key = ("field", dedup_key[1])
        if dedup_key in rules_by_key:
            continue
        rules_by_key[dedup_key] = _compile_add_rule(override, context=context)
        order.append(dedup_key)
        applied_sources.append(
            {"source": SOURCE_TENANT_OVERRIDE, "ref": str(override.get("id") or override.get("target_code"))}
        )

    final_rules = [rules_by_key[key] for key in order if key in rules_by_key]
    return final_rules, applied_sources


def tenant_override_row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "id": str(getattr(row, "id", "") or ""),
        "tenant_id": str(getattr(row, "tenant_id", "") or ""),
        "entity_profile_code": getattr(row, "entity_profile_code", None),
        "context": getattr(row, "context", None),
        "stage_code": getattr(row, "stage_code", None),
        "override_kind": str(getattr(row, "override_kind", "") or ""),
        "rule_type": str(getattr(row, "rule_type", "") or ""),
        "target_code": str(getattr(row, "target_code", "") or ""),
        "level": getattr(row, "level", None),
        "status": str(getattr(row, "status", "") or ""),
        "reason": str(getattr(row, "reason", "") or ""),
    }
