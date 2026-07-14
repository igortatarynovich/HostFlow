"""Requirement Rule Graph planner — applicability, dependencies, stage ownership (ADR-018 PR 2A.1).

This module resolves policy structure only. Document matching and stage blocking
are implemented in RequirementEvaluationService (PR 2B).
"""

from __future__ import annotations

from typing import Any, Optional

from backend.app.requirement_rules.citizenship import citizenship_segment, is_free_movement_citizen
from backend.app.requirement_rules.requirement_definition_registry import (
    get_requirement_definition_v1,
)
from backend.app.requirement_rules.requirement_policy_registry import get_requirement_policy
from backend.app.requirement_rules.requirement_rule_contract import (
    AlternativeDisposition,
    AlternativePlan,
    CitizenshipSegment,
    MatchedAlternative,
    PersonContext,
    RequirementApplicability,
    RequirementPlan,
    RuleGraphPlanningInput,
    RuleGraphPlanningResult,
    StageOwnership,
)


def _norm(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def _parse_stage_ownership(raw: dict[str, Any]) -> StageOwnership:
    return StageOwnership(
        source_responsibility=str(raw.get("source_responsibility") or ""),
        operational_owner=str(raw.get("operational_owner") or ""),
        verification_role=str(raw.get("verification_role") or ""),
        acquisition_mode=str(raw.get("acquisition_mode") or ""),
        required_by_stage=str(raw.get("required_by_stage") or ""),
        blocks_stage=str(raw.get("blocks_stage") or ""),
        completion_event=str(raw.get("completion_event") or ""),
        document_role=str(raw.get("document_role") or "input"),
    )


def _when_matches(when: dict[str, Any], *, inp: RuleGraphPlanningInput, segment: CitizenshipSegment) -> bool:
    if not when:
        return True
    if "citizenship_segment" in when:
        allowed = {_norm(x) for x in (when["citizenship_segment"] if isinstance(when["citizenship_segment"], list) else [when["citizenship_segment"]])}
        if segment.value not in allowed:
            return False
    if when.get("citizenship_segment_not_in"):
        blocked = {_norm(x) for x in when["citizenship_segment_not_in"]}
        if segment.value in blocked:
            return False
    if "international_haulage" in when and bool(when["international_haulage"]) != bool(inp.person.international_haulage):
        return False
    if "community_licence_carrier" in when and bool(when["community_licence_carrier"]) != bool(inp.person.community_licence_carrier):
        return False
    if matched := when.get("matched_alternative"):
        if not isinstance(matched, dict):
            return False
        req = _norm(matched.get("requirement_code"))
        alt = _norm(matched.get("alternative_code"))
        if not any(m.requirement_code == req and m.alternative_code == alt for m in inp.matched_alternatives):
            return False
    if when.get("free_movement") is True and not is_free_movement_citizen(inp.person.citizenship):
        return False
    if when.get("third_country") is True and segment != CitizenshipSegment.third_country:
        return False
    not_matched = _norm(when.get("requirement_not_matched") or "")
    if not_matched:
        if any(m.requirement_code == not_matched for m in inp.matched_alternatives):
            return False
    return True


def _init_plans(policy: dict[str, Any]) -> dict[str, RequirementPlan]:
    plans: dict[str, RequirementPlan] = {}
    bindings = policy.get("requirement_bindings") or policy.get("requirements") or []
    for row in bindings:
        if not isinstance(row, dict):
            continue
        code = _norm(row.get("requirement_code"))
        if not code:
            continue
        ownership_raw = row.get("stage_ownership") or row
        plans[code] = RequirementPlan(
            requirement_code=code,
            stage_ownership=_parse_stage_ownership(ownership_raw),
        )
        definition = get_requirement_definition_v1(code)
        if definition:
            for alt in definition.get("alternatives") or []:
                if isinstance(alt, dict) and alt.get("alternative_code"):
                    plans[code].alternatives.append(
                        AlternativePlan(alternative_code=str(alt["alternative_code"]))
                    )
    return plans


def _apply_applicability_rules(
    policy: dict[str, Any],
    plans: dict[str, RequirementPlan],
    *,
    inp: RuleGraphPlanningInput,
    segment: CitizenshipSegment,
    trace: list[str],
) -> None:
    for rule in policy.get("applicability_rules") or []:
        if not isinstance(rule, dict):
            continue
        when = rule.get("when") if isinstance(rule.get("when"), dict) else {}
        if not _when_matches(when, inp=inp, segment=segment):
            continue
        effect = _norm(rule.get("effect") or "not_applicable")
        targets = rule.get("requirements") or []
        for code in targets:
            target = _norm(code)
            plan = plans.get(target)
            if not plan:
                continue
            if effect == "not_applicable":
                plan.applicability = RequirementApplicability.not_applicable
                plan.applicability_reason = str(rule.get("reason") or rule.get("rule_id") or "applicability_rule")
                for alt in plan.alternatives:
                    alt.disposition = AlternativeDisposition.not_applicable
                trace.append(f"applicability:{rule.get('rule_id')}->{target}:not_applicable")
            elif effect == "applicable":
                plan.applicability = RequirementApplicability.applicable
                plan.applicability_reason = str(rule.get("reason") or rule.get("rule_id") or "applicability_rule")
                trace.append(f"applicability:{rule.get('rule_id')}->{target}:applicable")


def _apply_dependency_rules(
    policy: dict[str, Any],
    plans: dict[str, RequirementPlan],
    *,
    inp: RuleGraphPlanningInput,
    segment: CitizenshipSegment,
    trace: list[str],
) -> None:
    matches = {(m.requirement_code, m.alternative_code) for m in inp.matched_alternatives}

    for rule in policy.get("dependency_rules") or []:
        if not isinstance(rule, dict):
            continue
        when = rule.get("when") if isinstance(rule.get("when"), dict) else {}
        if not _when_matches(when, inp=inp, segment=segment):
            continue
        kind = _norm(rule.get("kind"))
        rule_id = str(rule.get("rule_id") or kind)

        if kind == "excludes":
            reqs = rule.get("requirements") or []
            effect = _norm(rule.get("effect") or "not_applicable")
            for code in reqs:
                plan = plans.get(_norm(code))
                if not plan:
                    continue
                if effect == "not_applicable":
                    plan.applicability = RequirementApplicability.not_applicable
                    plan.excluded_by = rule_id
                    for alt in plan.alternatives:
                        alt.disposition = AlternativeDisposition.not_applicable
                trace.append(f"{kind}:{rule_id}->{code}:{effect}")

            for alt_row in rule.get("exclude_alternatives") or []:
                if not isinstance(alt_row, dict):
                    continue
                req = _norm(alt_row.get("requirement_code"))
                plan = plans.get(req)
                if not plan:
                    continue
                alt_codes = alt_row.get("alternative_codes") or []
                for alt in plan.alternatives:
                    if alt.alternative_code in {_norm(a) for a in alt_codes}:
                        alt.disposition = AlternativeDisposition.excluded
                        alt.reason = rule_id
                trace.append(f"{kind}:{rule_id}->alternatives:{req}")

        elif kind == "activates":
            for code in rule.get("requirements") or []:
                plan = plans.get(_norm(code))
                if not plan or plan.applicability == RequirementApplicability.not_applicable:
                    continue
                plan.applicability = RequirementApplicability.applicable
                plan.activated_by = rule_id
                trace.append(f"{kind}:{rule_id}->{code}")

        elif kind == "satisfies":
            for code in rule.get("requirements") or []:
                plan = plans.get(_norm(code))
                if not plan:
                    continue
                alt_code = str(rule.get("alternative_code") or "")
                for alt in plan.alternatives:
                    if alt_code and alt.alternative_code != alt_code:
                        alt.disposition = AlternativeDisposition.not_selected
                    elif alt_code and alt.alternative_code == alt_code:
                        alt.disposition = AlternativeDisposition.matched
                        alt.reason = rule_id
                trace.append(f"{kind}:{rule_id}->{code}:{alt_code}")

            for alt_row in rule.get("exclude_alternatives") or []:
                if not isinstance(alt_row, dict):
                    continue
                req = _norm(alt_row.get("requirement_code"))
                plan = plans.get(req)
                if not plan:
                    continue
                alt_codes = alt_row.get("alternative_codes") or []
                for alt in plan.alternatives:
                    if alt.alternative_code in {_norm(a) for a in alt_codes}:
                        alt.disposition = AlternativeDisposition.excluded
                        alt.reason = rule_id
                trace.append(f"{kind}:{rule_id}->exclude_alternatives:{req}")

            for code in rule.get("also_satisfies") or []:
                src = plans.get(_norm(rule.get("requirement_code") or ""))
                tgt = plans.get(_norm(code))
                if src and tgt:
                    tgt.satisfies_also.append(rule_id)
                    trace.append(f"{kind}:{rule_id}->also:{code}")

        elif kind == "requires":
            for code in rule.get("requirements") or []:
                plan = plans.get(_norm(code))
                if plan:
                    plan.applicability = RequirementApplicability.applicable
                    plan.activated_by = rule_id
                    trace.append(f"{kind}:{rule_id}->{code}")

    for req_code, alt_code in matches:
        plan = plans.get(req_code)
        if not plan:
            continue
        for alt in plan.alternatives:
            if alt.alternative_code == alt_code:
                alt.disposition = AlternativeDisposition.matched
            elif alt.disposition == AlternativeDisposition.available:
                alt.disposition = AlternativeDisposition.not_selected


def _build_decision_path(segment: CitizenshipSegment, inp: RuleGraphPlanningInput) -> list[str]:
    path = [f"citizenship_segment:{segment.value}"]
    if segment == CitizenshipSegment.third_country:
        path.append("assess:legal_stay")
        path.append("assess:labor_market_access")
    if inp.person.international_haulage and segment == CitizenshipSegment.third_country:
        path.append("assess:driver_attestation")
    path.append("assess:driver_qualification")
    return path


def plan_requirement_rule_graph(inp: RuleGraphPlanningInput) -> RuleGraphPlanningResult:
    policy = get_requirement_policy(inp.policy_ref)
    if not policy:
        raise ValueError(f"unknown policy_ref: {inp.policy_ref}")

    segment = citizenship_segment(inp.person.citizenship)
    trace: list[str] = []
    plans = _init_plans(policy)
    _apply_applicability_rules(policy, plans, inp=inp, segment=segment, trace=trace)
    _apply_dependency_rules(policy, plans, inp=inp, segment=segment, trace=trace)

    return RuleGraphPlanningResult(
        policy_ref=inp.policy_ref,
        citizenship_segment=segment,
        decision_path=_build_decision_path(segment, inp),
        requirements=plans,
        dependency_trace=trace,
    )


def requirement_is_applicable(result: RuleGraphPlanningResult, requirement_code: str) -> bool:
    plan = result.requirements.get(_norm(requirement_code))
    return bool(plan and plan.applicability == RequirementApplicability.applicable)


def alternative_disposition(
    result: RuleGraphPlanningResult,
    requirement_code: str,
    alternative_code: str,
) -> Optional[AlternativeDisposition]:
    plan = result.requirements.get(_norm(requirement_code))
    if not plan:
        return None
    for alt in plan.alternatives:
        if alt.alternative_code == _norm(alternative_code):
            return alt.disposition
    return None


__all__ = [
    "alternative_disposition",
    "plan_requirement_rule_graph",
    "requirement_is_applicable",
]
