"""Shadow evaluation of professional vacancy requirements.

Reads merged Overlay predicates and a professional_profile projection.
Writes nothing. Does not read Document Hub, lead.normalized, or the legacy
years thresholds. A no_match here is an explanation, not a pipeline action.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

CONTRACT_ID = "professional_requirements_evaluation.v1"
ENFORCEMENT = "shadow"

MATCH = "match"
NO_MATCH = "no_match"
NEEDS_INFO = "needs_info"
NEEDS_REVIEW = "needs_review"

PREFERRED_MATCHED = "matched"
PREFERRED_NOT_MATCHED = "not_matched"
PREFERRED_UNKNOWN = "unknown"

_CALCULATED = "calculated"
_PRESENCE = "presence_only"
_INSUFFICIENT = "insufficient_history"
_AMBIGUOUS = "ambiguous_history"
_NONE = "no_evidence"


def evaluate_professional_requirements(
    profile: Mapping[str, Any] | None,
    requirements: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    """Explain each predicate. Legacy years criteria are not an input."""
    projection = profile if isinstance(profile, Mapping) else {}
    rows = []
    for requirement in requirements or []:
        if isinstance(requirement, Mapping):
            rows.append(_evaluate_one(projection, requirement))
    return {
        "contract_id": CONTRACT_ID,
        "enforcement": ENFORCEMENT,
        "requirements": rows,
        "shadow_eligibility": _shadow_eligibility(rows),
    }


def _shadow_eligibility(rows: Sequence[Mapping[str, Any]]) -> str:
    """Mandatory requirements only. Preferred failure stays out of this result."""
    mandatory = [row for row in rows if row.get("affects_eligibility")]
    results = {str(row.get("result") or "") for row in mandatory}
    if NO_MATCH in results:
        return NO_MATCH
    if NEEDS_REVIEW in results:
        return NEEDS_REVIEW
    if NEEDS_INFO in results:
        return NEEDS_INFO
    return MATCH


def _evaluate_one(profile: Mapping[str, Any], requirement: Mapping[str, Any]) -> dict[str, Any]:
    domain = str(requirement.get("domain") or "")
    if domain == "capability":
        result, reason, evidence, provenance = _capability(profile, requirement)
    elif domain == "experience":
        result, reason, evidence, provenance = _experience(profile, requirement)
    elif domain == "characteristic":
        result, reason, evidence, provenance = _characteristic(profile, requirement)
    elif domain == "language":
        result, reason, evidence, provenance = (
            NEEDS_INFO,
            "outside_professional_profile",
            None,
            [{"source": "professional_profile", "present": False}],
        )
    else:
        result, reason, evidence, provenance = (NEEDS_INFO, "unknown_predicate", None, [])
    strength = str(requirement.get("strength") or "")
    preferred = strength == "preferred"
    return {
        "qualified_code": requirement.get("qualified_code"),
        "strength": strength,
        "affects_eligibility": not preferred,
        "expected": _expected(requirement),
        "evidence": evidence,
        "result": result,
        "preference_result": _preference_result(result) if preferred else None,
        "reason": reason,
        "provenance": provenance,
    }


def _expected(requirement: Mapping[str, Any]) -> dict[str, Any]:
    expected: dict[str, Any] = {
        "domain": requirement.get("domain"),
        "mode": requirement.get("mode"),
        "code": requirement.get("code"),
    }
    if requirement.get("mode") == "minimum":
        expected["minimum_days"] = requirement.get("minimum_days")
    if requirement.get("subject"):
        expected["subject"] = requirement.get("subject")
    return expected


def _preference_result(result: str) -> str:
    if result == MATCH:
        return PREFERRED_MATCHED
    if result == NO_MATCH:
        return PREFERRED_NOT_MATCHED
    return PREFERRED_UNKNOWN


def _capability(
    profile: Mapping[str, Any],
    requirement: Mapping[str, Any],
) -> tuple[str, str, Any, list[dict[str, Any]]]:
    capabilities = profile.get("capabilities") if isinstance(profile.get("capabilities"), Mapping) else {}
    facet = str(requirement.get("facet") or "")
    provenance = [{"source": "capabilities", "facet": facet, "record": "operator_facts"}]
    if facet == "driving_category":
        licence = capabilities.get("licence") if isinstance(capabilities.get("licence"), Mapping) else {}
        categories = [str(code).upper() for code in licence.get("categories") or []]
        raw = [str(code) for code in licence.get("raw_unmapped") or []]
        wanted = str(requirement.get("code") or "").upper()
        evidence = {"categories": categories, "raw_unmapped": raw}
        if wanted in categories:
            return MATCH, "capability_present", evidence, provenance
        if raw:
            return NEEDS_REVIEW, "capability_unmapped", evidence, provenance
        if categories:
            return NO_MATCH, "capability_absent", evidence, provenance
        return NEEDS_INFO, "capability_not_recorded", evidence, provenance
    fact = capabilities.get(facet) if isinstance(capabilities.get(facet), Mapping) else {}
    presence = fact.get("presence") if isinstance(fact, Mapping) else None
    evidence = {"presence": presence}
    if presence is True:
        return MATCH, "capability_present", evidence, provenance
    if presence is False:
        return NO_MATCH, "capability_absent", evidence, provenance
    return NEEDS_INFO, "capability_not_recorded", evidence, provenance


def _experience(
    profile: Mapping[str, Any],
    requirement: Mapping[str, Any],
) -> tuple[str, str, Any, list[dict[str, Any]]]:
    facet = str(requirement.get("facet") or "")
    if facet == "trailer_hiring":
        return _trailer(profile, requirement)
    aggregate = _aggregate_for(profile, facet, str(requirement.get("code") or ""))
    if aggregate is None and facet == OPERATION_SCOPE_DOMESTIC_FACET:
        return _character_presence(profile, requirement, "operation_scopes")
    if aggregate is None:
        return NEEDS_INFO, "experience_not_recorded", None, [{"source": "experience.aggregates", "facet": facet}]
    return _judge_aggregate(aggregate, requirement, f"experience.aggregates.{_aggregate_path(facet, requirement)}")


OPERATION_SCOPE_DOMESTIC_FACET = "operation_scope"


def _aggregate_path(facet: str, requirement: Mapping[str, Any]) -> str:
    if facet in {"movement_pattern", "crew_mode", "operation_scope"}:
        return f"{facet}.{requirement.get('code')}"
    return {"total": "total_tenure", "CE": "ce", "EU": "eu", "international": "international"}.get(facet, facet)


def _aggregate_for(profile: Mapping[str, Any], facet: str, code: str) -> Mapping[str, Any] | None:
    experience = profile.get("experience") if isinstance(profile.get("experience"), Mapping) else {}
    aggregates = experience.get("aggregates") if isinstance(experience.get("aggregates"), Mapping) else {}
    if facet == "total":
        value = aggregates.get("total_tenure")
    elif facet == "CE":
        value = aggregates.get("ce")
    elif facet == "EU":
        value = aggregates.get("eu")
    elif facet == "international":
        value = aggregates.get("international")
    elif facet in {"movement_pattern", "crew_mode"}:
        group = aggregates.get(facet) if isinstance(aggregates.get(facet), Mapping) else {}
        value = group.get(code)
    else:
        value = None
    return value if isinstance(value, Mapping) else None


def _judge_aggregate(
    aggregate: Mapping[str, Any],
    requirement: Mapping[str, Any],
    source: str,
) -> tuple[str, str, Any, list[dict[str, Any]]]:
    status = str(aggregate.get("status") or _NONE)
    days = aggregate.get("days") if isinstance(aggregate.get("days"), int) else None
    evidence = {
        "status": status,
        "days": days,
        "years": aggregate.get("years"),
        "contributing_employment_ids": list(aggregate.get("contributing_employment_ids") or []),
    }
    provenance = [{
        "source": source,
        "status": status,
        "employment_ids": evidence["contributing_employment_ids"],
        "reasons": list(aggregate.get("reasons") or []),
    }]
    mode = requirement.get("mode")
    if mode == "minimum":
        minimum = requirement.get("minimum_days")
        if status == _CALCULATED and isinstance(days, int) and isinstance(minimum, int):
            if days >= minimum:
                return MATCH, "calculated_meets_minimum", evidence, provenance
            return NO_MATCH, "calculated_below_minimum", evidence, provenance
        if status == _PRESENCE:
            return NEEDS_INFO, "presence_only_not_duration", evidence, provenance
        if status == _AMBIGUOUS:
            return NEEDS_INFO, "experience_ambiguous", evidence, provenance
        if status == _INSUFFICIENT:
            return NEEDS_INFO, "experience_insufficient", evidence, provenance
        return NEEDS_INFO, "experience_not_recorded", evidence, provenance
    if status in {_CALCULATED, _PRESENCE}:
        return MATCH, "experience_present", evidence, provenance
    if status == _AMBIGUOUS:
        return NEEDS_INFO, "experience_ambiguous", evidence, provenance
    if status == _INSUFFICIENT:
        return NEEDS_INFO, "experience_insufficient", evidence, provenance
    return NEEDS_INFO, "experience_not_recorded", evidence, provenance


def _character_presence(
    profile: Mapping[str, Any],
    requirement: Mapping[str, Any],
    group_name: str,
) -> tuple[str, str, Any, list[dict[str, Any]]]:
    experience = profile.get("experience") if isinstance(profile.get("experience"), Mapping) else {}
    character = experience.get("work_character") if isinstance(experience.get("work_character"), Mapping) else {}
    rows = character.get(group_name) if isinstance(character.get(group_name), list) else []
    code = str(requirement.get("code") or "")
    matched = [row for row in rows if isinstance(row, Mapping) and row.get("code") == code]
    evidence = {"rows": matched}
    provenance = [{"source": f"experience.work_character.{group_name}", "code": code}]
    if requirement.get("mode") == "minimum":
        return NEEDS_INFO, "presence_only_not_duration", evidence, provenance
    if any(row.get("resolution") == "unmapped" for row in matched):
        return NEEDS_REVIEW, "experience_unmapped", evidence, provenance
    if matched:
        return MATCH, "experience_present", evidence, provenance
    if any(isinstance(row, Mapping) and row.get("resolution") == "unmapped" for row in rows):
        return NEEDS_REVIEW, "experience_unmapped", evidence, provenance
    if rows:
        return NO_MATCH, "experience_absent", evidence, provenance
    return NEEDS_INFO, "experience_not_recorded", evidence, provenance


def _trailer(
    profile: Mapping[str, Any],
    requirement: Mapping[str, Any],
) -> tuple[str, str, Any, list[dict[str, Any]]]:
    experience = profile.get("experience") if isinstance(profile.get("experience"), Mapping) else {}
    practical = experience.get("practical_experience") if isinstance(experience.get("practical_experience"), Mapping) else {}
    trailers = practical.get("trailers") if isinstance(practical.get("trailers"), Mapping) else {}
    items = [item for item in trailers.get("items") or [] if isinstance(item, Mapping)]
    code = str(requirement.get("code") or "")
    mapped = [
        item for item in items
        if item.get("mapping") == "mapped" and item.get("target_vocabulary") == "trailer_hiring" and item.get("target_code") == code
    ]
    unmapped = [item for item in items if item.get("mapping") != "mapped"]
    evidence = {
        "mapped": [item.get("target_code") for item in mapped],
        "unmapped": [item.get("code") for item in unmapped],
    }
    provenance = [{"source": "experience.practical_experience.trailers", "required_code": code}]
    if requirement.get("mode") == "minimum":
        return NEEDS_INFO, "presence_only_not_duration", evidence, provenance
    if mapped:
        return MATCH, "trailer_mapped", evidence, provenance
    if unmapped:
        return NEEDS_REVIEW, "trailer_unmapped", evidence, provenance
    if items:
        return NO_MATCH, "trailer_absent", evidence, provenance
    return NEEDS_INFO, "experience_not_recorded", evidence, provenance


def _characteristic(
    profile: Mapping[str, Any],
    requirement: Mapping[str, Any],
) -> tuple[str, str, Any, list[dict[str, Any]]]:
    subject = str(requirement.get("subject") or "")
    code = str(requirement.get("code") or "")
    constraints = [row for row in profile.get("constraints") or [] if isinstance(row, Mapping)]
    same = [row for row in constraints if row.get("subject") == subject and row.get("code") == code]
    active = [row for row in same if row.get("activity") == "active"]
    unknown = [row for row in same if row.get("activity") == "unknown"]
    evidence = {
        "active": [_constraint_ref(row) for row in active],
        "ignored_activity": [
            _constraint_ref(row) for row in same if row.get("activity") in {"expired", "scheduled"}
        ],
    }
    provenance = [{
        "source": "constraints",
        "subject": subject,
        "code": code,
        "constraint_ids": [row.get("id") for row in same],
    }]
    if any(row.get("effect") == "prohibited" for row in active):
        return NO_MATCH, "constraint_prohibited", evidence, provenance
    if any(row.get("effect") == "limited" for row in active):
        return NEEDS_REVIEW, "constraint_limited", evidence, provenance
    if unknown:
        return NEEDS_REVIEW, "constraint_activity_unknown", evidence, provenance
    return MATCH, "constraint_clear", evidence, provenance


def _constraint_ref(row: Mapping[str, Any]) -> dict[str, Any]:
    return {"id": row.get("id"), "effect": row.get("effect"), "activity": row.get("activity")}
