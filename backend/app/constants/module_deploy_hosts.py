# Canonical module deploy hosts — loaded from shared/module_deploy_hosts.json (ADR-023 §3.7).
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Final
from urllib.parse import urlparse

def _registry_path_candidates() -> tuple[Path, ...]:
    """Resolve SSOT path for both monorepo checkout and Docker (/app mount)."""
    here = Path(__file__).resolve()
    # Host: .../HostFlow/backend/app/constants → parents[3]=HostFlow
    # Docker: /app/app/constants (backend mounted at /app) → parents[3]=/, parents[2]=/app
    return (
        here.parents[3] / "shared" / "module_deploy_hosts.json",
        here.parents[2] / "shared" / "module_deploy_hosts.json",
        Path("/shared/module_deploy_hosts.json"),
        Path("/opt/HostFlow/shared/module_deploy_hosts.json"),
    )


def resolve_module_deploy_registry_path() -> Path:
    for candidate in _registry_path_candidates():
        if candidate.is_file():
            return candidate
    tried = ", ".join(str(p) for p in _registry_path_candidates())
    raise FileNotFoundError(f"shared/module_deploy_hosts.json not found (tried: {tried})")


# Kept for tests / diagnostics; may point at a missing path until resolve() runs.
_REPO_SHARED = _registry_path_candidates()[0]


@lru_cache(maxsize=1)
def load_module_deploy_registry() -> dict[str, Any]:
    return json.loads(resolve_module_deploy_registry_path().read_text(encoding="utf-8"))


def deployment_hosts() -> dict[str, str]:
    return dict(load_module_deploy_registry()["hosts"])


def business_modules() -> tuple[str, ...]:
    return tuple(load_module_deploy_registry()["business_modules"])


def allowed_redirect_hostnames(*, allow_localhost: bool = False) -> frozenset[str]:
    hosts = set(deployment_hosts().values())
    hosts.add("www.hostflow.cc")
    if allow_localhost:
        hosts.update({"localhost", "127.0.0.1"})
    return frozenset(h.lower() for h in hosts)


def _query_nested_urls_allowed(query: str, *, allow_localhost: bool) -> bool:
    if not query:
        return True
    from urllib.parse import parse_qs

    for values in parse_qs(query, keep_blank_values=True).values():
        for value in values:
            v = (value or "").strip()
            if not v:
                continue
            if v.startswith("//") or v.lower().startswith("http://") or v.lower().startswith("https://"):
                if not is_allowed_auth_next(v, allow_localhost=allow_localhost):
                    return False
    return True


def is_allowed_auth_next(next_url: str, *, allow_localhost: bool = False) -> bool:
    """
    Strict open-redirect guard for login `next`.
    Allows only registry hosts (and optional localhost for dev).
    Rejects protocol-relative URLs, credentials, unexpected ports,
    and nested absolute URLs in query that point outside the allowlist.
    """
    raw = (next_url or "").strip()
    if not raw:
        return False
    if raw.startswith("//") or "\\" in raw:
        return False
    if raw.startswith("/") and not raw.startswith("//"):
        if "://" in raw or raw.startswith("/\\"):
            return False
        try:
            parsed = urlparse(f"https://hostflow.cc{raw}")
        except Exception:
            return False
        return _query_nested_urls_allowed(parsed.query, allow_localhost=allow_localhost)

    try:
        parsed = urlparse(raw)
    except Exception:
        return False

    if parsed.scheme not in ("http", "https"):
        return False
    if parsed.username or parsed.password:
        return False

    host = (parsed.hostname or "").lower()
    if not host:
        return False

    allowed = allowed_redirect_hostnames(allow_localhost=allow_localhost)
    if host not in allowed:
        return False

    if host not in {"localhost", "127.0.0.1"} and parsed.port not in (None, 80, 443):
        return False

    return _query_nested_urls_allowed(parsed.query, allow_localhost=allow_localhost)


def owner_to_deploy_host() -> dict[str, str]:
    return dict(load_module_deploy_registry()["owner_to_deploy_host"])


def entity_deep_link(entity: str, entity_id: str) -> tuple[str, str] | None:
    """Return (deploy_host_key, path) for an entity deep link (Stage 6C)."""
    from backend.app.services.entity_deep_links import resolve_entity_deep_link

    resolved = resolve_entity_deep_link(entity, entity_id)
    if not resolved:
        return None
    return resolved["host"], resolved["path"]


DEPLOYMENT_HOSTS: Final[dict[str, str]] = deployment_hosts()
OWNER_TO_DEPLOY_HOST: Final[dict[str, str]] = owner_to_deploy_host()
