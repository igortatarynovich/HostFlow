from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

_BASE_DIR = Path(__file__).resolve().parents[1]  # backend/app
_DEFAULT_RULESET_PATH = _BASE_DIR / "modules" / "documents" / "data" / "sample_ruleset.json"
_CACHE: Dict[str, Any] | None = None


def load_default_ruleset() -> Dict[str, Any]:
    global _CACHE
    if isinstance(_CACHE, dict):
        return _CACHE
    if _DEFAULT_RULESET_PATH.is_file():
        try:
            data = json.loads(_DEFAULT_RULESET_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                _CACHE = data
                return data
        except Exception:
            pass
    _CACHE = {"requiredTypes": [], "optionalTypes": []}
    return _CACHE
