"""Mapping revision stamp applied at Lead ingest (Diagnostics PR5).

Stores a compact fingerprint of the rules used when normalizing a submission.
Not a parallel mapping engine — read-only evidence for ops / drift.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

MAPPING_APPLIED_V1_KEY = "mapping_applied_v1"


def fingerprint_mapping_rules(rules: Sequence[Mapping[str, Any]] | None) -> str:
    """Stable short fingerprint of mapping rules (order-insensitive)."""
    cleaned: list[dict[str, Any]] = []
    for raw in rules or []:
        if not isinstance(raw, Mapping):
            continue
        cleaned.append({str(k): raw[k] for k in sorted(raw.keys())})
    cleaned.sort(key=lambda r: json.dumps(r, sort_keys=True, default=str))
    blob = json.dumps(cleaned, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def build_mapping_applied_stamp(
    *,
    rules: Sequence[Mapping[str, Any]] | None,
    source_id: str | None,
    rules_source: str | None,
    profile_updated_at: str | None = None,
) -> dict[str, Any]:
    rule_list = [dict(r) for r in (rules or []) if isinstance(r, Mapping)]
    from backend.app.modules.leads.conversion_mapping import compact_executable_rules

    stamp: dict[str, Any] = {
        "source_id": str(source_id).strip() if source_id else None,
        "rules_source": str(rules_source or "").strip() or None,
        "rules_count": len(rule_list),
        "rules_fingerprint": fingerprint_mapping_rules(rule_list),
        "profile_updated_at": profile_updated_at,
        "stamped_at": datetime.now(timezone.utc).isoformat(),
    }
    executable = compact_executable_rules(rule_list)
    if executable:
        stamp["executable_rules"] = executable
    return stamp


def stamp_mapping_applied_v1(
    normalized: dict[str, Any],
    *,
    rules: Sequence[Mapping[str, Any]] | None,
    source_id: str | None,
    rules_source: str | None,
    profile_updated_at: str | None = None,
) -> dict[str, Any]:
    """Write ``mapping_applied_v1`` onto ``normalized`` (in-place). Returns the stamp."""
    stamp = build_mapping_applied_stamp(
        rules=rules,
        source_id=source_id,
        rules_source=rules_source,
        profile_updated_at=profile_updated_at,
    )
    normalized[MAPPING_APPLIED_V1_KEY] = stamp
    return stamp


def read_mapping_applied_stamp(normalized: Mapping[str, Any] | None) -> dict[str, Any]:
    raw = (normalized or {}).get(MAPPING_APPLIED_V1_KEY)
    return dict(raw) if isinstance(raw, Mapping) else {}


def empty_applied_evidence() -> dict[str, Any]:
    return {
        "present": False,
        "lead_id": None,
        "stamped_at": None,
        "rules_fingerprint": None,
        "rules_count": 0,
        "rules_source": None,
        "drift": False,
        "sentences": [],
    }


def _scalar_at(normalized: Mapping[str, Any], key: str) -> str | None:
    if not key:
        return None
    if key in normalized:
        val = normalized[key]
        if isinstance(val, (dict, list)) or val is None:
            return None
        text = str(val).strip()
        return text or None
    cur: Any = normalized
    for part in key.split("."):
        if not isinstance(cur, Mapping) or part not in cur:
            return None
        cur = cur[part]
    if isinstance(cur, (dict, list)) or cur is None:
        return None
    text = str(cur).strip()
    return text or None


def _index_destinations(
    destinations: Sequence[Mapping[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    by_code: dict[str, dict[str, Any]] = {}
    for raw in destinations or []:
        if not isinstance(raw, Mapping):
            continue
        entry = dict(raw)
        code = str(entry.get("code") or "").strip()
        if code:
            by_code[code.lower()] = entry
        for alias in entry.get("aliases") or []:
            name = str(alias).strip()
            if name:
                by_code[name.lower()] = entry
    return by_code


def _option_label(entry: Mapping[str, Any] | None, value: str) -> str:
    if not entry:
        return value
    needle = value.strip().lower()
    for opt in entry.get("options") or []:
        if not isinstance(opt, Mapping):
            continue
        opt_value = str(opt.get("value") or "").strip()
        opt_label = str(opt.get("label") or "").strip()
        if opt_value.lower() == needle or opt_label.lower() == needle:
            return opt_label or opt_value or value
    return value


def compose_applied_evidence(
    *,
    lead_id: str | None,
    normalized: Mapping[str, Any] | None,
    current_rules: Sequence[Mapping[str, Any]] | None,
    destinations: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Operator-facing applied-rule evidence from ``mapping_applied_v1``.

    Not contract health. Empty when no ingest stamp is present.
    """
    stamp = read_mapping_applied_stamp(normalized)
    applied_fp = str(stamp.get("rules_fingerprint") or "").strip() or None
    if not lead_id or not applied_fp:
        return empty_applied_evidence()
    current_fp = fingerprint_mapping_rules(current_rules)
    dest_index = _index_destinations(destinations)
    sentences: list[dict[str, Any]] = []
    executable = stamp.get("executable_rules")
    rules = executable if isinstance(executable, list) else []
    for raw in rules:
        if not isinstance(raw, Mapping):
            continue
        source = str(raw.get("source") or "").strip()
        dest_code = str(
            raw.get("qualified_field_code") or raw.get("normalized_target") or ""
        ).strip()
        entry = dest_index.get(dest_code.lower()) if dest_code else None
        dest_label = str((entry or {}).get("label") or dest_code or source).strip()
        value = (
            _scalar_at(normalized or {}, str(raw.get("normalized_target") or "").strip())
            or _scalar_at(normalized or {}, dest_code)
            or _scalar_at(normalized or {}, dest_code.split(".")[-1] if dest_code else "")
            or _scalar_at(normalized or {}, source)
        )
        shown = _option_label(entry, value) if value else ""
        if dest_label and shown:
            sentence = f"Last application wrote {dest_label} = {shown}"
        elif dest_label:
            sentence = f"Last application wrote {dest_label}"
        else:
            continue
        sentences.append(
            {
                "source": source or None,
                "destination_label": dest_label,
                "value": shown or None,
                "sentence": sentence,
            }
        )
    return {
        "present": True,
        "lead_id": str(lead_id),
        "stamped_at": str(stamp.get("stamped_at") or "").strip() or None,
        "rules_fingerprint": applied_fp,
        "rules_count": int(stamp.get("rules_count") or 0),
        "rules_source": str(stamp.get("rules_source") or "").strip() or None,
        "drift": bool(current_fp and applied_fp != current_fp),
        "sentences": sentences,
    }


__all__ = [
    "MAPPING_APPLIED_V1_KEY",
    "build_mapping_applied_stamp",
    "compose_applied_evidence",
    "empty_applied_evidence",
    "fingerprint_mapping_rules",
    "read_mapping_applied_stamp",
    "stamp_mapping_applied_v1",
]
