"""Person-fact alternative matching (PR 2B-2)."""

from __future__ import annotations

from datetime import date
from typing import Optional

from backend.app.requirement_rules.evaluation.condition_evaluator import evaluate_all_conditions
from backend.app.requirement_rules.evaluation.match_types import AlternativeMatchOutcome
from backend.app.requirement_rules.requirement_rule_contract import PersonContext


def match_person_fact_alternative(
    alternative: dict,
    *,
    person: PersonContext,
    process_state: Optional[str],
    evaluation_date: date,
) -> AlternativeMatchOutcome:
    alternative_code = str(alternative.get("alternative_code") or "")
    conditions = alternative.get("conditions") or []
    cond_result = evaluate_all_conditions(
        conditions,
        document=None,
        person=person,
        process_state=process_state,
        evaluation_date=evaluation_date,
    )
    person_facts = ("platform.identity.citizenship",) if cond_result.satisfied else ()
    return AlternativeMatchOutcome(
        alternative_code=alternative_code,
        kind="person_fact",
        matched=cond_result.satisfied,
        fully_satisfied=cond_result.satisfied,
        matched_person_facts=person_facts,
        failure_reasons=cond_result.reasons,
        status_hint=cond_result.status_hint,
    )


__all__ = ["match_person_fact_alternative"]
