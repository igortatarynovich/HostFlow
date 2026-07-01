"""Shared helpers: baseline document ruleset JSON for the default dev tenant."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

DEFAULT_TENANT_ID = "11111111-1111-1111-1111-111111111111"
BASELINE_RULESET_COMMENT = "Baseline required-documents matrix (default-tenant backfill)"


def _backend_root() -> Path:
    # backend/app/services/<this> -> parents[2] == backend/
    return Path(__file__).resolve().parents[2]


def load_baseline_ruleset_dict() -> dict[str, Any]:
    path = _backend_root() / "app" / "modules" / "documents" / "data" / "sample_ruleset.json"
    return json.loads(path.read_text(encoding="utf-8"))


def ruleset_required_matrix_empty(json_data: Any) -> bool:
    """True when ruleset JSON has no required document types (advanced or simple schema)."""
    if json_data is None:
        return True
    if isinstance(json_data, str):
        try:
            json_data = json.loads(json_data)
        except Exception:
            return True
    if not isinstance(json_data, Mapping):
        return True
    req = json_data.get("required")
    if isinstance(req, list) and len(req) > 0:
        return False
    cand = json_data.get("candidate") or {}
    defaults = cand.get("defaults") or {}
    rt = defaults.get("requiredTypes") or []
    return len(rt) == 0
