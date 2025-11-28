from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from uuid import UUID
from typing import Any, Dict, Tuple

DIFF_ENGINE_ID = "hostflow/jsondiff-v1"


def normalize_ruleset_payload(raw: Dict[str, Any] | None) -> Dict[str, Any]:
    """Return a plain mapping representation of ruleset JSON."""
    if raw is None:
        payload: Mapping[str, Any] | Dict[str, Any] | None = None
    elif isinstance(raw, Mapping):
        payload = dict(raw)
    elif isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except Exception:
            return {}
        payload = parsed if isinstance(parsed, dict) else None
    else:
        payload = None

    if not payload:
        return {}

    def _coerce(value: Any) -> Any:
        if isinstance(value, Mapping):
            return {str(k): _coerce(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set, frozenset, Sequence)) and not isinstance(value, (str, bytes, bytearray)):
            return [_coerce(item) for item in list(value)]
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, Enum):
            return value.value if hasattr(value, "value") else str(value)
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, (bytes, bytearray)):
            return value.decode("utf-8", errors="ignore")
        return value

    coerced = _coerce(payload)
    if not isinstance(coerced, dict):
        return {}
    try:
        # round-trip through JSON to guarantee JSON-compatible primitives only.
        return json.loads(json.dumps(coerced))
    except Exception:
        return coerced


def compute_ruleset_signature(
    tenant_id: str,
    version: int,
    payload: Dict[str, Any],
    comment: str | None = None,
) -> str:
    """
    Generate a stable SHA256 signature for the ruleset payload.
    """
    canonical = {
        "tenant_id": tenant_id,
        "version": version,
        "ruleset": payload,
    }
    if comment:
        canonical["comment"] = comment
    serialized = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _join_path(path: Tuple[str, ...]) -> str:
    return ".".join(filter(None, path)) or "<root>"


def _diff(
    path: Tuple[str, ...],
    left: Any,
    right: Any,
    added: Dict[str, Any],
    removed: Dict[str, Any],
    changed: Dict[str, Dict[str, Any]],
) -> None:
    if left == right:
        return
    if isinstance(left, dict) and isinstance(right, dict):
        keys = set(left.keys()) | set(right.keys())
        for key in sorted(keys):
            next_path = path + (str(key),)
            if key not in left:
                added[_join_path(next_path)] = right[key]
            elif key not in right:
                removed[_join_path(next_path)] = left[key]
            else:
                _diff(next_path, left[key], right[key], added, removed, changed)
        return

    if isinstance(left, list) and isinstance(right, list):
        if left != right:
            changed[_join_path(path)] = {"from": left, "to": right}
        return

    changed[_join_path(path)] = {"from": left, "to": right}


def compute_ruleset_diff(
    previous: Dict[str, Any] | None, current: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Produce a compact structural diff representation between two rulesets.
    """
    prev_payload = previous or {}
    added: Dict[str, Any] = {}
    removed: Dict[str, Any] = {}
    changed: Dict[str, Dict[str, Any]] = {}
    _diff((), prev_payload, current, added, removed, changed)

    summary = {
        "added": len(added),
        "removed": len(removed),
        "changed": len(changed),
    }
    result: Dict[str, Any] = {
        "engine": DIFF_ENGINE_ID,
        "summary": summary,
        "added": added,
        "removed": removed,
        "changed": changed,
    }

    if summary["added"] == 0 and summary["removed"] == 0 and summary["changed"] == 0:
        result["status"] = "identical"

    return result
