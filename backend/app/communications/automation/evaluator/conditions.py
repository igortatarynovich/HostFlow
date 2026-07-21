"""Pure condition-tree evaluation for C2.2 Rule Evaluator."""

from __future__ import annotations

from typing import Any, Mapping

from backend.app.communications.automation.evaluator.types import CONDITION_OPS


class ConditionError(ValueError):
    """Raised when the condition tree itself is invalid."""

    def __init__(self, message: str, *, path: str | None = None) -> None:
        super().__init__(message)
        self.path = path
        self.message = message


def resolve_path(data: Mapping[str, Any] | None, path: str) -> Any:
    """Resolve dotted path against a nested mapping. Missing → None."""
    if not path:
        raise ConditionError("path is required", path=path)
    cur: Any = data or {}
    for part in str(path).split("."):
        if not isinstance(cur, Mapping):
            return None
        if part not in cur:
            return None
        cur = cur[part]
    return cur


def _as_mapping(node: Any, *, path: str) -> Mapping[str, Any]:
    if not isinstance(node, Mapping):
        raise ConditionError("condition node must be an object", path=path)
    return node


def evaluate_condition(node: Mapping[str, Any] | None, data: Mapping[str, Any]) -> bool:
    """Evaluate a declarative condition tree against event data.

    Empty / missing node matches everything (True).
    """
    if node is None:
        return True
    if not isinstance(node, Mapping):
        raise ConditionError("conditions must be an object", path="$")
    if not node:
        return True
    return _eval_node(node, data, path="$")


def _eval_node(node: Mapping[str, Any], data: Mapping[str, Any], *, path: str) -> bool:
    op = str(node.get("op") or "").strip().lower()
    if not op:
        # Bare filter object: all keys must eq values (shallow convenience).
        return all(resolve_path(data, str(k)) == v for k, v in node.items())

    if op not in CONDITION_OPS:
        raise ConditionError(f"unknown condition op: {op}", path=path)

    if op == "and":
        args = node.get("args")
        if not isinstance(args, (list, tuple)) or not args:
            raise ConditionError("and requires non-empty args", path=path)
        return all(
            _eval_node(_as_mapping(a, path=f"{path}.args[{i}]"), data, path=f"{path}.args[{i}]")
            for i, a in enumerate(args)
        )

    if op == "or":
        args = node.get("args")
        if not isinstance(args, (list, tuple)) or not args:
            raise ConditionError("or requires non-empty args", path=path)
        return any(
            _eval_node(_as_mapping(a, path=f"{path}.args[{i}]"), data, path=f"{path}.args[{i}]")
            for i, a in enumerate(args)
        )

    if op == "not":
        if "arg" in node:
            child = _as_mapping(node.get("arg"), path=f"{path}.arg")
            return not _eval_node(child, data, path=f"{path}.arg")
        args = node.get("args")
        if isinstance(args, (list, tuple)) and len(args) == 1:
            child = _as_mapping(args[0], path=f"{path}.args[0]")
            return not _eval_node(child, data, path=f"{path}.args[0]")
        raise ConditionError("not requires arg or single-item args", path=path)

    field_path = str(node.get("path") or "").strip()
    if not field_path:
        raise ConditionError(f"{op} requires path", path=path)
    actual = resolve_path(data, field_path)

    if op == "exists":
        return actual is not None

    expected = node.get("value")

    if op == "eq":
        return actual == expected
    if op == "neq":
        return actual != expected
    if op == "in":
        if not isinstance(expected, (list, tuple, set, frozenset)):
            raise ConditionError("in requires list value", path=path)
        return actual in expected
    if op == "not_in":
        if not isinstance(expected, (list, tuple, set, frozenset)):
            raise ConditionError("not_in requires list value", path=path)
        return actual not in expected
    if op == "contains":
        if actual is None:
            return False
        if isinstance(actual, (str, list, tuple, set)):
            return expected in actual  # type: ignore[operator]
        return False
    if op in {"gt", "gte", "lt", "lte"}:
        if actual is None or expected is None:
            return False
        try:
            if op == "gt":
                return actual > expected  # type: ignore[operator]
            if op == "gte":
                return actual >= expected  # type: ignore[operator]
            if op == "lt":
                return actual < expected  # type: ignore[operator]
            return actual <= expected  # type: ignore[operator]
        except TypeError as exc:
            raise ConditionError(f"{op} type error: {exc}", path=path) from exc

    raise ConditionError(f"unhandled op: {op}", path=path)


def match_filter(event_filter: Mapping[str, Any] | None, data: Mapping[str, Any]) -> bool:
    """Trigger filter: empty matches; otherwise treat as condition tree or shallow eq map."""
    if not event_filter:
        return True
    if "op" in event_filter:
        return evaluate_condition(event_filter, data)
    return all(resolve_path(data, str(k)) == v for k, v in event_filter.items())


def map_variables(
    mapping: Mapping[str, Any] | None,
    data: Mapping[str, Any],
) -> dict[str, Any]:
    """Map template variable name → value from event data via path or literal.

    Mapping forms:
    - ``{"contact_name": "payload.name"}`` — dotted path
    - ``{"locale": {"literal": "pl"}}`` — fixed literal
    """
    out: dict[str, Any] = {}
    if not mapping:
        return out
    for key, spec in mapping.items():
        name = str(key or "").strip()
        if not name:
            continue
        if isinstance(spec, Mapping) and "literal" in spec:
            out[name] = spec.get("literal")
        elif isinstance(spec, str):
            out[name] = resolve_path(data, spec)
        else:
            out[name] = spec
    return out


__all__ = [
    "ConditionError",
    "resolve_path",
    "evaluate_condition",
    "match_filter",
    "map_variables",
]
