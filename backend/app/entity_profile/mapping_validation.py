"""Validate ingest field mapping rules against Entity Profile allowed fields (P3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.app.field_registry.intake_mapping import (
    qualified_code_from_legacy_target,
    resolve_intake_mapping_target,
)


@dataclass(frozen=True)
class MappingValidationResult:
    accepted_rules: list[dict[str, Any]] = field(default_factory=list)
    rejected_rules: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted_count": len(self.accepted_rules),
            "rejected_count": len(self.rejected_rules),
            "accepted_rules": self.accepted_rules,
            "rejected_rules": self.rejected_rules,
            "warnings": self.warnings,
        }


def rule_qualified_code(rule: dict[str, Any]) -> str | None:
    explicit = str(rule.get("qualified_field_code") or rule.get("qualified_code") or "").strip()
    if explicit:
        return explicit
    target = str(rule.get("target") or "").strip()
    if not target:
        return None
    if "." in target:
        return target
    return qualified_code_from_legacy_target(target)


def allowed_qualified_codes_from_profile_view(profile_view: dict[str, Any]) -> set[str]:
    codes: set[str] = set()
    for row in profile_view.get("fields") or []:
        if not isinstance(row, dict):
            continue
        code = str(row.get("qualified_code") or "").strip()
        if code:
            codes.add(code)
    return codes


def validate_mapping_rules_for_profile(
    rules: list[dict[str, Any]],
    *,
    allowed_qualified_codes: set[str],
    entity_profile_code: str | None,
    resolution_source: str,
) -> MappingValidationResult:
    """Accept only rules whose qualified_code belongs to the resolved Entity Profile."""
    if not rules:
        return MappingValidationResult()

    if not allowed_qualified_codes:
        if resolution_source in {"legacy_candidate_profile", "not_specified"}:
            return MappingValidationResult(
                accepted_rules=[dict(r) for r in rules if isinstance(r, dict)],
                warnings=["entity_profile_unscoped_mapping_legacy_allowed"],
            )
        return MappingValidationResult(
            rejected_rules=[dict(r) for r in rules if isinstance(r, dict)],
            warnings=["entity_profile_empty_no_mapping_allowed"],
        )

    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    warnings: list[str] = []

    for rule in rules:
        if not isinstance(rule, dict):
            continue
        qualified = rule_qualified_code(rule)
        if not qualified:
            rejected.append(dict(rule))
            warnings.append(f"mapping_target_unresolved:{rule.get('source')}")
            continue
        if qualified not in allowed_qualified_codes:
            rejected.append({**dict(rule), "qualified_field_code": qualified})
            warnings.append(f"mapping_target_rejected:{qualified}")
            continue
        enriched = dict(rule)
        enriched.setdefault("qualified_field_code", qualified)
        accepted.append(enriched)

    if entity_profile_code and rejected:
        warnings.insert(0, f"mapping_scoped_to_profile:{entity_profile_code}")

    return MappingValidationResult(
        accepted_rules=accepted,
        rejected_rules=rejected,
        warnings=warnings,
    )
