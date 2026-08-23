from __future__ import annotations

from typing import Any, Dict, Optional

from backend.app.reference.document_policy_merge import merge_resolved_policy

_CACHE: Dict[str, Any] | None = None


def load_default_ruleset(*, tenant_delta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    global _CACHE
    if tenant_delta is None and isinstance(_CACHE, dict):
        return _CACHE
    resolved = merge_resolved_policy(tenant_delta)
    if tenant_delta is None:
        _CACHE = resolved
    return resolved
