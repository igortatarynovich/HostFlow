"""Requirement rule registry — Entity Profile + Document Pack sources only (P1)."""

from __future__ import annotations

from typing import Any, Optional

from backend.app.entity_profile.constants import REQUIREMENT_REQUIRED
from backend.app.requirement_rules.constants import (
    CONTEXT_TO_FIELD_LEVEL,
    DOCUMENT_EVALUATION_CONTEXTS,
    REQUIREMENT_RULES_V1,
    RULE_TYPE_DOCUMENT_REQUIRED,
    RULE_TYPE_FIELD_REQUIRED,
    SOURCE_DOCUMENT_PACK,
    SOURCE_ENTITY_PROFILE,
    VALID_CONTEXTS,
)
from backend.app.requirement_rules.manifests import DOCUMENT_PACK_MANIFESTS


class RequirementRulesNotFoundError(LookupError):
    def __init__(self, *, entity_profile_code: str) -> None:
        self.entity_profile_code = str(entity_profile_code or "").strip()
        super().__init__(f"Requirement rules not found for entity profile: {self.entity_profile_code}")


def get_document_pack_manifest(pack_code: str) -> Optional[dict[str, Any]]:
    code = str(pack_code or "").strip()
    if not code:
        return None
    return DOCUMENT_PACK_MANIFESTS.get(code)


def _field_level_for_context(field_row: dict[str, Any], context: str) -> str:
    level_key = CONTEXT_TO_FIELD_LEVEL.get(context, "card_save_level")
    level = str(field_row.get(level_key) or field_row.get("intake_level") or "optional").strip().lower()
    return level


def build_field_required_rules(
    profile_view: dict[str, Any],
    *,
    context: str,
) -> list[dict[str, Any]]:
    ctx = str(context or "readiness").strip().lower()
    if ctx not in VALID_CONTEXTS:
        ctx = "readiness"
    rules: list[dict[str, Any]] = []
    profile_code = str(
        profile_view.get("profile_code")
        or profile_view.get("entity_profile_code")
        or (profile_view.get("profile") or {}).get("profile_code")
        or ""
    ).strip()
    for row in profile_view.get("fields") or []:
        if not isinstance(row, dict):
            continue
        qualified_code = str(row.get("qualified_code") or "").strip()
        if not qualified_code:
            continue
        if _field_level_for_context(row, ctx) != REQUIREMENT_REQUIRED:
            continue
        rules.append(
            {
                "rule_type": RULE_TYPE_FIELD_REQUIRED,
                "source": SOURCE_ENTITY_PROFILE,
                "source_ref": profile_code,
                "target": qualified_code,
                "qualified_code": qualified_code,
                "level": "blocking",
                "context": ctx,
                "reason_code": f"entity_profile_field_required:{qualified_code}",
            }
        )
    return rules


def build_document_required_rules(
    *,
    pack_code: str,
    entity_profile_code: str,
    context: str,
) -> list[dict[str, Any]]:
    ctx = str(context or "readiness").strip().lower()
    if ctx not in DOCUMENT_EVALUATION_CONTEXTS:
        return []
    pack = get_document_pack_manifest(pack_code)
    if pack is None:
        return []
    rules: list[dict[str, Any]] = []
    for item in pack.get("required_documents") or []:
        if not isinstance(item, dict):
            continue
        doc_code = str(item.get("document_type_code") or "").strip()
        if not doc_code:
            continue
        rules.append(
            {
                "rule_type": RULE_TYPE_DOCUMENT_REQUIRED,
                "source": SOURCE_DOCUMENT_PACK,
                "source_ref": pack_code,
                "target": doc_code,
                "document_type_code": doc_code,
                "pack_code": pack_code,
                "level": str(item.get("level") or "blocking").strip().lower(),
                "verification": str(item.get("verification") or "optional").strip().lower(),
                "context": ctx,
                "reason_code": str(item.get("reason_code") or f"document_pack_required:{doc_code}"),
                "entity_profile_code": entity_profile_code,
            }
        )
    return rules


def build_requirement_rule_set(
    profile_view: dict[str, Any],
    *,
    context: str = "readiness",
) -> dict[str, Any]:
    """Compile deterministic rules from Entity Profile + Document Pack (P1 sources only)."""
    profile_meta = profile_view.get("profile") if isinstance(profile_view.get("profile"), dict) else profile_view
    entity_profile_code = str(
        profile_view.get("profile_code")
        or profile_view.get("entity_profile_code")
        or profile_meta.get("profile_code")
        or ""
    ).strip()
    if not entity_profile_code:
        raise RequirementRulesNotFoundError(entity_profile_code="?")

    ctx = str(context or "readiness").strip().lower()
    if ctx not in VALID_CONTEXTS:
        ctx = "readiness"

    field_rules = build_field_required_rules(profile_view, context=ctx)
    pack_code = str(profile_meta.get("document_pack_code") or profile_view.get("document_pack_code") or "").strip()
    document_rules = build_document_required_rules(
        pack_code=pack_code,
        entity_profile_code=entity_profile_code,
        context=ctx,
    )

    rule_sources_applied: list[dict[str, str]] = [{"source": SOURCE_ENTITY_PROFILE, "ref": entity_profile_code}]
    if pack_code and document_rules:
        rule_sources_applied.append({"source": SOURCE_DOCUMENT_PACK, "ref": pack_code})

    return {
        "contract_version": REQUIREMENT_RULES_V1,
        "entity_profile_code": entity_profile_code,
        "entity_type": str(profile_meta.get("entity_type") or profile_view.get("entity_type") or "").strip() or None,
        "context": ctx,
        "document_pack_code": pack_code or None,
        "process_profile_code": str(profile_meta.get("process_profile_code") or "").strip() or None,
        "rule_sources_applied": rule_sources_applied,
        "rules": field_rules + document_rules,
        "p1_sources_only": True,
        "excluded_sources": ["process_profile", "tenant_override"],
    }
