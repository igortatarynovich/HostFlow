"""Single-alternative matching dispatcher (PR 2B-2)."""

from __future__ import annotations

from datetime import date
from typing import Optional

from backend.app.document_hub.document_data_contract import DocumentDataContract
from backend.app.requirement_rules.evaluation.document_matcher import match_document_alternative
from backend.app.requirement_rules.evaluation.match_types import AlternativeMatchOutcome
from backend.app.requirement_rules.evaluation.person_fact_matcher import match_person_fact_alternative
from backend.app.requirement_rules.evaluation.process_matcher import match_process_alternative
from backend.app.requirement_rules.requirement_rule_contract import PersonContext


def _norm(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def match_alternative(
    alternative: dict,
    *,
    requirement_code: str,
    documents: tuple[DocumentDataContract, ...],
    person: PersonContext,
    process_states: dict[str, str],
    evaluation_date: date,
    entity_type: str,
    entity_id: str,
) -> AlternativeMatchOutcome:
    kind = _norm(alternative.get("kind"))
    process_state = process_states.get(requirement_code) or process_states.get(_norm(alternative.get("alternative_code")))

    if kind == "document":
        return match_document_alternative(
            alternative,
            requirement_code=requirement_code,
            documents=documents,
            person=person,
            process_state=process_state,
            evaluation_date=evaluation_date,
            entity_type=entity_type,
            entity_id=entity_id,
        )
    if kind == "person_fact":
        return match_person_fact_alternative(
            alternative,
            person=person,
            process_state=process_state,
            evaluation_date=evaluation_date,
        )
    if kind == "process_state":
        return match_process_alternative(
            alternative,
            requirement_code=requirement_code,
            person=person,
            process_state=process_state,
            evaluation_date=evaluation_date,
        )
    return AlternativeMatchOutcome(
        alternative_code=str(alternative.get("alternative_code") or ""),
        kind=kind or "unknown",
        matched=False,
        fully_satisfied=False,
    )


__all__ = ["match_alternative"]
