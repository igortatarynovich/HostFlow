"""Mapping revision stamp applied at Lead ingest (Diagnostics PR5).

Stores a compact fingerprint of the rules used when normalizing a submission.
Not a parallel mapping engine — read-only evidence for ops / drift.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Sequence

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


__all__ = [
    "MAPPING_APPLIED_V1_KEY",
    "build_mapping_applied_stamp",
    "fingerprint_mapping_rules",
    "read_mapping_applied_stamp",
    "stamp_mapping_applied_v1",
]
