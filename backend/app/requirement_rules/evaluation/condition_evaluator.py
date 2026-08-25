"""Policy condition evaluation (ADR-018 PR 2B-2).

Reads only normalized facts from DocumentDataContract and PersonContext — no schema
validation, alias normalization, or meta access.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Optional

from backend.app.document_hub.document_data_contract import DocumentDataContract
from backend.app.requirement_rules.citizenship import citizenship_segment, normalize_country_code
from backend.app.requirement_rules.evaluation.result_contract import (
    EvaluationReason,
    EvaluationReasonCode,
    EvaluationReasonSeverity,
    EvaluationReasonSourceType,
    RequirementEvaluationStatus,
)
from backend.app.requirement_rules.requirement_rule_contract import CitizenshipSegment, PersonContext


def _norm(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def _parse_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


@dataclass(frozen=True)
class ConditionEvaluationResult:
    satisfied: bool
    status_hint: Optional[RequirementEvaluationStatus] = None
    missing_fields: tuple[str, ...] = ()
    reasons: tuple[EvaluationReason, ...] = ()


def _reason(
    code: EvaluationReasonCode,
    *,
    message_key: str,
    source_type: EvaluationReasonSourceType,
    source_ref: str,
    severity: EvaluationReasonSeverity = EvaluationReasonSeverity.error,
    details: Optional[dict[str, Any]] = None,
) -> EvaluationReason:
    return EvaluationReason(
        code=code,
        message_key=message_key,
        severity=severity,
        source_type=source_type,
        source_ref=source_ref,
        details=dict(details or {}),
    )


def _citizenship_groups(groups: list[str]) -> set[str]:
    expanded: set[str] = set()
    for group in groups:
        key = _norm(group)
        if key == "pl":
            expanded.add("pl")
        elif key in {"eu", "eea", "ch"}:
            expanded.update({"eu", "eea", "ch"})
        else:
            expanded.add(key)
    return expanded


def _citizenship_matches_groups(citizenship: Optional[str], groups: list[str]) -> bool:
    code = normalize_country_code(citizenship)
    if not code:
        return False
    group_keys = _citizenship_groups(groups)
    segment = citizenship_segment(citizenship)
    if "pl" in group_keys and segment == CitizenshipSegment.poland:
        return True
    if group_keys.intersection({"eu", "eea", "ch"}) and segment == CitizenshipSegment.eu_eea_swiss:
        return True
    return code in group_keys


def _field_value(document_data: dict[str, Any], field: str) -> Any:
    return document_data.get(field) if isinstance(document_data, dict) else None


def _document_field_expired(
    document_data: dict[str, Any],
    field: str,
    *,
    evaluation_date: date,
    document_type_code: str,
) -> tuple[bool, Optional[RequirementEvaluationStatus], tuple[str, ...]]:
    """Return (is_valid, status_hint, missing_fields)."""
    raw = _field_value(document_data, field)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return False, RequirementEvaluationStatus.missing, (field,)

    expiry = _parse_date(raw)
    if expiry is None:
        return False, RequirementEvaluationStatus.invalid, (field,)

    if expiry < evaluation_date:
        return False, RequirementEvaluationStatus.expired, ()
    return True, None, ()


def evaluate_condition(
    condition: dict[str, Any],
    *,
    document: Optional[DocumentDataContract],
    person: PersonContext,
    process_state: Optional[str],
    evaluation_date: date,
) -> ConditionEvaluationResult:
    kind = _norm(condition.get("kind"))
    if kind == "document_review":
        expected = _norm(condition.get("status") or "approved")
        actual = _norm(document.review_status if document else "")
        if actual == expected:
            return ConditionEvaluationResult(satisfied=True)
        if actual in {"pending_review", "submitted", "in_progress", "uploaded"}:
            return ConditionEvaluationResult(
                satisfied=False,
                status_hint=RequirementEvaluationStatus.pending_review,
                reasons=(
                    _reason(
                        EvaluationReasonCode.document_pending_review,
                        message_key="requirement.document.pending_review",
                        source_type=EvaluationReasonSourceType.document,
                        source_ref=document.document_id if document else "",
                        severity=EvaluationReasonSeverity.warning,
                    ),
                ),
            )
        return ConditionEvaluationResult(
            satisfied=False,
            status_hint=RequirementEvaluationStatus.missing,
            reasons=(
                _reason(
                    EvaluationReasonCode.document_missing,
                    message_key="requirement.document.review_not_approved",
                    source_type=EvaluationReasonSourceType.document,
                    source_ref=document.document_id if document else "",
                ),
            ),
        )

    if kind == "document_schema_valid":
        if document and document.schema_valid:
            return ConditionEvaluationResult(satisfied=True)
        return ConditionEvaluationResult(
            satisfied=False,
            status_hint=RequirementEvaluationStatus.invalid,
            reasons=(
                _reason(
                    EvaluationReasonCode.schema_invalid,
                    message_key="requirement.document.schema_invalid",
                    source_type=EvaluationReasonSourceType.document,
                    source_ref=document.document_id if document else "",
                ),
            ),
        )

    if kind == "document_not_expired":
        field = str(condition.get("field") or "expiry_date")
        if not document:
            return ConditionEvaluationResult(
                satisfied=False,
                status_hint=RequirementEvaluationStatus.missing,
                reasons=(
                    _reason(
                        EvaluationReasonCode.document_missing,
                        message_key="requirement.document.missing",
                        source_type=EvaluationReasonSourceType.document,
                        source_ref="",
                    ),
                ),
            )
        if field in {"expiry_date", "valid_to"} and document.valid_to is not None:
            if document.valid_to < evaluation_date:
                return ConditionEvaluationResult(
                    satisfied=False,
                    status_hint=RequirementEvaluationStatus.expired,
                    reasons=(
                        _reason(
                            EvaluationReasonCode.document_expired,
                            message_key="requirement.document.expired",
                            source_type=EvaluationReasonSourceType.document,
                            source_ref=document.document_id,
                            details={"field": field, "valid_to": document.valid_to.isoformat()},
                        ),
                    ),
                )
            return ConditionEvaluationResult(satisfied=True)

        ok, hint, missing = _document_field_expired(
            document.document_data,
            field,
            evaluation_date=evaluation_date,
            document_type_code=document.document_type_code,
        )
        if ok:
            return ConditionEvaluationResult(satisfied=True)
        return ConditionEvaluationResult(
            satisfied=False,
            status_hint=hint,
            missing_fields=missing,
            reasons=(
                _reason(
                    EvaluationReasonCode.document_expired
                    if hint == RequirementEvaluationStatus.expired
                    else EvaluationReasonCode.required_field_missing,
                    message_key="requirement.document.field_expired"
                    if hint == RequirementEvaluationStatus.expired
                    else "requirement.document.field_missing",
                    source_type=EvaluationReasonSourceType.document,
                    source_ref=document.document_id,
                    details={"field": field},
                ),
            ),
        )

    if kind == "field_in":
        field = str(condition.get("field") or "")
        allowed = {_norm(v) for v in (condition.get("values") or [])}
        if not document:
            return ConditionEvaluationResult(satisfied=False, status_hint=RequirementEvaluationStatus.missing)
        raw = _field_value(document.document_data, field)
        if raw is None or (isinstance(raw, str) and not str(raw).strip()):
            return ConditionEvaluationResult(
                satisfied=False,
                status_hint=RequirementEvaluationStatus.unresolved,
                missing_fields=(field,),
                reasons=(
                    _reason(
                        EvaluationReasonCode.required_field_missing,
                        message_key="requirement.document.field_missing",
                        source_type=EvaluationReasonSourceType.document,
                        source_ref=document.document_id,
                        details={"field": field},
                    ),
                ),
            )
        if _norm(raw) in allowed:
            return ConditionEvaluationResult(satisfied=True)
        return ConditionEvaluationResult(
            satisfied=False,
            status_hint=RequirementEvaluationStatus.unresolved,
            reasons=(
                _reason(
                    EvaluationReasonCode.policy_condition_not_met,
                    message_key="requirement.document.field_not_in_allowed_values",
                    source_type=EvaluationReasonSourceType.policy,
                    source_ref=field,
                    details={"field": field, "value": str(raw), "allowed": sorted(allowed)},
                ),
            ),
        )

    if kind == "field_contains_any":
        field = str(condition.get("field") or "")
        required = {str(v).upper() for v in (condition.get("values") or [])}
        if not document:
            return ConditionEvaluationResult(satisfied=False, status_hint=RequirementEvaluationStatus.missing)
        raw = _field_value(document.document_data, field)
        values: set[str] = set()
        if isinstance(raw, list):
            values = {str(v).upper() for v in raw}
        elif raw is not None:
            values = {str(raw).upper()}
        if values.intersection(required):
            return ConditionEvaluationResult(satisfied=True)
        return ConditionEvaluationResult(
            satisfied=False,
            status_hint=RequirementEvaluationStatus.missing,
            missing_fields=(field,),
            reasons=(
                _reason(
                    EvaluationReasonCode.policy_condition_not_met,
                    message_key="requirement.document.categories_not_met",
                    source_type=EvaluationReasonSourceType.policy,
                    source_ref=field,
                ),
            ),
        )

    if kind == "person_citizenship_in":
        groups = condition.get("groups") or []
        if not isinstance(groups, list):
            groups = []
        if not normalize_country_code(person.citizenship):
            return ConditionEvaluationResult(
                satisfied=False,
                status_hint=RequirementEvaluationStatus.unresolved,
                reasons=(
                    _reason(
                        EvaluationReasonCode.citizenship_unknown,
                        message_key="requirement.person.citizenship_unknown",
                        source_type=EvaluationReasonSourceType.person,
                        source_ref="platform.identity.citizenship",
                        severity=EvaluationReasonSeverity.blocker,
                    ),
                ),
            )
        if _citizenship_matches_groups(person.citizenship, groups):
            return ConditionEvaluationResult(satisfied=True)
        return ConditionEvaluationResult(
            satisfied=False,
            reasons=(
                _reason(
                    EvaluationReasonCode.policy_condition_not_met,
                    message_key="requirement.person.citizenship_not_in_group",
                    source_type=EvaluationReasonSourceType.person,
                    source_ref="platform.identity.citizenship",
                ),
            ),
        )

    if kind == "process_state_in":
        allowed = {_norm(v) for v in (condition.get("states") or [])}
        actual = _norm(process_state)
        if actual and actual in allowed:
            return ConditionEvaluationResult(satisfied=True)
        return ConditionEvaluationResult(
            satisfied=False,
            status_hint=RequirementEvaluationStatus.process_pending
            if actual
            else RequirementEvaluationStatus.missing,
            reasons=(
                _reason(
                    EvaluationReasonCode.process_not_started
                    if not actual
                    else EvaluationReasonCode.process_pending,
                    message_key="requirement.process.not_started"
                    if not actual
                    else "requirement.process.pending",
                    source_type=EvaluationReasonSourceType.process,
                    source_ref=actual or "process",
                ),
            ),
        )

    return ConditionEvaluationResult(
        satisfied=False,
        reasons=(
            _reason(
                EvaluationReasonCode.policy_condition_not_met,
                message_key="requirement.condition.unknown_kind",
                source_type=EvaluationReasonSourceType.policy,
                source_ref=kind,
            ),
        ),
    )


def evaluate_all_conditions(
    conditions: list[dict[str, Any]],
    *,
    document: Optional[DocumentDataContract],
    person: PersonContext,
    process_state: Optional[str],
    evaluation_date: date,
) -> ConditionEvaluationResult:
    missing_fields: list[str] = []
    reasons: list[EvaluationReason] = []
    status_hints: list[RequirementEvaluationStatus] = []

    for condition in conditions:
        if not isinstance(condition, dict):
            continue
        result = evaluate_condition(
            condition,
            document=document,
            person=person,
            process_state=process_state,
            evaluation_date=evaluation_date,
        )
        if result.satisfied:
            continue
        missing_fields.extend(result.missing_fields)
        reasons.extend(result.reasons)
        if result.status_hint:
            status_hints.append(result.status_hint)

    if not reasons:
        return ConditionEvaluationResult(satisfied=True)

    status_priority = [
        RequirementEvaluationStatus.expired,
        RequirementEvaluationStatus.unresolved,
        RequirementEvaluationStatus.pending_review,
        RequirementEvaluationStatus.process_pending,
        RequirementEvaluationStatus.invalid,
        RequirementEvaluationStatus.missing,
    ]
    hint = next((s for s in status_priority if s in status_hints), RequirementEvaluationStatus.missing)
    return ConditionEvaluationResult(
        satisfied=False,
        status_hint=hint,
        missing_fields=tuple(dict.fromkeys(missing_fields)),
        reasons=tuple(reasons),
    )


__all__ = [
    "ConditionEvaluationResult",
    "evaluate_all_conditions",
    "evaluate_condition",
]
