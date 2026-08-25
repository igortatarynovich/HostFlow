"""Module Stage Registry existence — single producer for stage registration (LI-1).

JSON at ``docs/specs/platform/module-stage-registry-recruitment-candidate-v0.json``
is the v0 identity SoT for ``recruitment.candidate.*``. Legacy paths
(``constants/stages.py``, funnel presets, PE manifests) remain stranglers until LI-2+.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Final

_SPECS_ROOT = Path(__file__).resolve().parents[4] / "docs" / "specs" / "platform"
REGISTRY_PATH: Final[Path] = _SPECS_ROOT / "module-stage-registry-recruitment-candidate-v0.json"
CATALOG_VERSION: Final[str] = "lifecycle-identity-li1-recruitment-candidate-v0"


def qualified_stage_id(module_key: str, entity_kind: str, stage_key: str) -> str:
    return f"{module_key.strip()}.{entity_kind.strip()}.{stage_key.strip()}"


def _parse_qualified_stage_id(value: str) -> tuple[str, str, str] | None:
    parts = value.strip().split(".")
    if len(parts) != 3 or not all(parts):
        return None
    return parts[0], parts[1], parts[2]


@lru_cache(maxsize=1)
def _registered_qualified_ids() -> frozenset[str]:
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    module_key = str(payload["module_key"])
    entity_kind = str(payload["entity_kind"])
    keys = payload.get("stage_keys") or []
    return frozenset(qualified_stage_id(module_key, entity_kind, str(key)) for key in keys)


def list_registered_stage_keys(module_key: str, entity_kind: str) -> frozenset[str]:
    prefix = f"{module_key.strip()}.{entity_kind.strip()}."
    return frozenset(
        qualified.removeprefix(prefix)
        for qualified in _registered_qualified_ids()
        if qualified.startswith(prefix)
    )


def is_stage_registered(module_key: str, entity_kind: str, stage_key: str) -> bool:
    return qualified_stage_id(module_key, entity_kind, stage_key) in _registered_qualified_ids()


def is_stage_registered_qualified(qualified: str) -> bool:
    parsed = _parse_qualified_stage_id(qualified)
    if parsed is None:
        return False
    module_key, entity_kind, stage_key = parsed
    return is_stage_registered(module_key, entity_kind, stage_key)
