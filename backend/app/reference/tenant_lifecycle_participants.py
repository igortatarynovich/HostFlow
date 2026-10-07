"""ADR-039 lifecycle participant registry (claim declarations).

OL-6 owns runtime export/erase. New tenant-owned tables must register here
so coverage guards can see them before the lifecycle adapter exists.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Final

_SPECS_ROOT = Path(__file__).resolve().parents[3] / "docs" / "specs" / "platform"
PARTICIPANTS_PATH: Final[Path] = _SPECS_ROOT / "tenant-lifecycle-participants-v1.json"
OVERLAY_TABLE: Final[str] = "document_policy_tenant_overlays"
OVERLAY_PARTICIPANT_CODE: Final[str] = "requirement_policy_tenant_overlay"


@lru_cache(maxsize=1)
def load_lifecycle_participants_payload() -> dict[str, Any]:
    with PARTICIPANTS_PATH.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("tenant lifecycle participants JSON must be an object")
    return payload


def claimed_tenant_tables() -> frozenset[str]:
    payload = load_lifecycle_participants_payload()
    out: set[str] = set()
    for row in payload.get("participants") or []:
        if not isinstance(row, dict):
            continue
        for name in row.get("tables") or []:
            code = str(name or "").strip()
            if code:
                out.add(code)
    return frozenset(out)


def participant_claims_table(table: str) -> bool:
    return str(table or "").strip() in claimed_tenant_tables()
