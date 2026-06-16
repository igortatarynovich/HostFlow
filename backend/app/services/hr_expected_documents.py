from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


def _config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "hr_expected_documents.json"


@lru_cache(maxsize=1)
def load_hr_expected_documents() -> list[dict[str, Any]]:
    p = _config_path()
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        out.append(
            {
                "document_code": str(row.get("document_code") or "").strip(),
                "label": str(row.get("label") or "").strip(),
                "group": str(row.get("group") or "").strip() or "other",
                "default_owner": str(row.get("default_owner") or "").strip() or "HR",
                "requires_expiry": bool(row.get("requires_expiry")),
                "verification_required": bool(row.get("verification_required", True)),
                "applies_to_driver": bool(row.get("applies_to_driver", True)),
                "applies_to_non_driver": bool(row.get("applies_to_non_driver", True)),
                "blocks_employment": bool(row.get("blocks_employment")),
                "renewal_window_days": int(row.get("renewal_window_days") or 30),
                "default_next_action": str(row.get("default_next_action") or "").strip(),
                "aliases": [str(x).strip().lower() for x in (row.get("aliases") or []) if str(x).strip()],
            }
        )
    return [x for x in out if x["document_code"] and x["label"]]

