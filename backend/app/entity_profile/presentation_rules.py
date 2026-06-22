"""Presentation Rules evaluator (P10A) — form display layer only.

Rules control show/hide, required-if, and readonly-if within a form presentation.
They do **not** define business requirements (documents, process gates) — that is P10B.
"""

from __future__ import annotations

from typing import Any, Optional

VALID_OPERATORS = frozenset({"eq", "neq", "truthy", "falsy", "in"})
RULE_KEYS = frozenset({"show_if", "hide_if", "required_if", "readonly_if"})


class PresentationRulesWriteError(ValueError):
    def __init__(self, code: str, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y", "on"}:
        return True
    if text in {"false", "0", "no", "n", "off", ""}:
        return False
    return bool(text)


def _normalize_scalar(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped
    return value


def evaluate_rule_condition(condition: Any, values: dict[str, Any]) -> bool:
    """Evaluate a single presentation rule condition against current form values."""
    if not isinstance(condition, dict):
        return False
    source = str(condition.get("source_field") or condition.get("field") or "").strip()
    if not source:
        return False
    actual = values.get(source)
    operator = str(condition.get("operator") or "eq").strip().lower()
    expected = condition.get("value")

    if operator == "truthy":
        return _coerce_bool(actual)
    if operator == "falsy":
        return not _coerce_bool(actual)
    if operator == "eq":
        return _normalize_scalar(actual) == _normalize_scalar(expected)
    if operator == "neq":
        return _normalize_scalar(actual) != _normalize_scalar(expected)
    if operator == "in":
        if not isinstance(expected, list):
            return False
        normalized_actual = _normalize_scalar(actual)
        return any(_normalize_scalar(item) == normalized_actual for item in expected)
    return False


def _rules_from_field(field: dict[str, Any]) -> dict[str, Any]:
    override = field.get("presentation_overrides")
    if isinstance(override, dict):
        rules = override.get("presentation_rules")
        if isinstance(rules, dict):
            return dict(rules)
    top = field.get("presentation_rules")
    if isinstance(top, dict):
        return dict(top)
    return {}


def evaluate_presentation_field_state(
    field: dict[str, Any],
    values: dict[str, Any],
) -> dict[str, Any]:
    """Return evaluated display state for one presentation field."""
    base_level = str(field.get("intake_level") or "optional").strip().lower()
    if base_level not in ("required", "optional", "hidden"):
        base_level = "optional"

    rules = _rules_from_field(field)
    visible = base_level != "hidden"
    readonly = False
    effective_level = base_level

    show_if = rules.get("show_if")
    if show_if is not None:
        visible = evaluate_rule_condition(show_if, values)

    hide_if = rules.get("hide_if")
    if hide_if is not None and evaluate_rule_condition(hide_if, values):
        visible = False

    readonly_if = rules.get("readonly_if")
    if readonly_if is not None and evaluate_rule_condition(readonly_if, values):
        readonly = True

    required_if = rules.get("required_if")
    if visible and required_if is not None and evaluate_rule_condition(required_if, values):
        effective_level = "required"

    if not visible:
        effective_level = "hidden"
        readonly = False

    return {
        "visible": visible,
        "readonly": readonly,
        "intake_level": effective_level,
        "base_intake_level": base_level,
    }


def apply_presentation_rules_evaluation(
    presentation: dict[str, Any],
    values: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Attach ``evaluated`` state to each field; expose ``presentation_rules`` at field top level."""
    value_map = dict(values or {})
    fields_out: list[dict[str, Any]] = []
    for raw in presentation.get("fields") or []:
        if not isinstance(raw, dict):
            continue
        field = dict(raw)
        rules = _rules_from_field(field)
        if rules:
            field["presentation_rules"] = rules
        field["evaluated"] = evaluate_presentation_field_state(field, value_map)
        fields_out.append(field)
    out = dict(presentation)
    out["fields"] = fields_out
    out["presentation_rules_applied"] = bool(value_map)
    return out


def _validate_condition(
    *,
    target_field: str,
    rule_key: str,
    condition: Any,
    field_subset: frozenset[str],
) -> None:
    if not isinstance(condition, dict):
        raise PresentationRulesWriteError(
            code="presentation_rule_invalid_condition",
            message=f"{rule_key} on {target_field} must be an object",
            details={"target_field": target_field, "rule_key": rule_key},
        )
    source = str(condition.get("source_field") or condition.get("field") or "").strip()
    if not source:
        raise PresentationRulesWriteError(
            code="presentation_rule_source_required",
            message=f"{rule_key} on {target_field} requires source_field",
            details={"target_field": target_field, "rule_key": rule_key},
        )
    if source not in field_subset:
        raise PresentationRulesWriteError(
            code="presentation_rule_source_outside_subset",
            message=f"Rule source_field must belong to the same presentation subset: {source}",
            details={"target_field": target_field, "source_field": source},
        )
    if source == target_field:
        raise PresentationRulesWriteError(
            code="presentation_rule_self_reference",
            message=f"Rule source_field cannot equal target field: {target_field}",
            details={"target_field": target_field, "source_field": source},
        )
    operator = str(condition.get("operator") or "eq").strip().lower()
    if operator not in VALID_OPERATORS:
        raise PresentationRulesWriteError(
            code="presentation_rule_invalid_operator",
            message=f"Invalid operator for {target_field}.{rule_key}: {operator}",
            details={"target_field": target_field, "operator": operator},
        )


def validate_presentation_rules_for_subset(
    presentation_overrides: dict[str, Any],
    field_subset: list[str],
) -> None:
    """Validate P10A rules: target and source fields must stay inside presentation subset."""
    subset = frozenset(str(code).strip() for code in field_subset if str(code).strip())
    for target_field, override in (presentation_overrides or {}).items():
        code = str(target_field or "").strip()
        if code not in subset:
            continue
        if not isinstance(override, dict):
            continue
        rules = override.get("presentation_rules")
        if not isinstance(rules, dict):
            continue
        for rule_key, condition in rules.items():
            key = str(rule_key or "").strip()
            if key not in RULE_KEYS:
                raise PresentationRulesWriteError(
                    code="presentation_rule_unknown_key",
                    message=f"Unknown presentation rule key: {key}",
                    details={"target_field": code, "rule_key": key},
                )
            _validate_condition(
                target_field=code,
                rule_key=key,
                condition=condition,
                field_subset=subset,
            )


def missing_required_presentation_fields(
    presentation: dict[str, Any],
    values: dict[str, Any],
) -> list[str]:
    """Return qualified_codes missing for visible fields with effective required level."""
    evaluated = apply_presentation_rules_evaluation(presentation, values)
    missing: list[str] = []
    for field in evaluated.get("fields") or []:
        if not isinstance(field, dict):
            continue
        evaluated_state = field.get("evaluated") if isinstance(field.get("evaluated"), dict) else {}
        if not evaluated_state.get("visible", True):
            continue
        level = str(evaluated_state.get("intake_level") or "optional").strip().lower()
        if level != "required":
            continue
        code = str(field.get("qualified_code") or "").strip()
        if not code:
            continue
        raw = values.get(code)
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            missing.append(code)
    return missing
