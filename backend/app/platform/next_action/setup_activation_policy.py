"""Load setup activation reachability policy (shared/setup_activation_reachability.json)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_POLICY_FILENAME = "setup_activation_reachability.json"


def _resolve_policy_path() -> Path:
    here = Path(__file__).resolve()
    candidates = (
        Path("/opt/HostFlow/shared") / _POLICY_FILENAME,
        here.parents[4] / "shared" / _POLICY_FILENAME,
        here.parents[3].parent / "shared" / _POLICY_FILENAME,
        here.parent / "data" / _POLICY_FILENAME,
    )
    for path in candidates:
        if path.is_file():
            return path
    tried = ", ".join(str(p) for p in candidates)
    raise FileNotFoundError(f"setup activation reachability policy not found; tried: {tried}")


@dataclass(frozen=True)
class SetupActivationReachabilityPolicy:
    allowed_exact: frozenset[str]
    allowed_prefixes: tuple[str, ...]
    onboarding_allowed_prefix: str
    onboarding_denied_exact: frozenset[str]
    onboarding_denied_prefix: str
    settings_allowed_prefix: str
    trial_tenant_status: str
    trial_allowed_settings_exact: frozenset[str]


@lru_cache(maxsize=1)
def load_setup_activation_reachability_policy() -> SetupActivationReachabilityPolicy:
    raw = json.loads(_resolve_policy_path().read_text(encoding="utf-8"))
    lock = raw["setup_activation_lock"]
    trial = raw["guided_trial_workspace"]
    return SetupActivationReachabilityPolicy(
        allowed_exact=frozenset(lock["allowed_exact"]),
        allowed_prefixes=tuple(lock["allowed_prefixes"]),
        onboarding_allowed_prefix=str(lock["onboarding_allowed_prefix"]),
        onboarding_denied_exact=frozenset(lock["onboarding_denied_exact"]),
        onboarding_denied_prefix=str(lock["onboarding_denied_prefix"]),
        settings_allowed_prefix=str(lock["settings_allowed_prefix"]),
        trial_tenant_status=str(trial["tenant_status"]).strip().lower(),
        trial_allowed_settings_exact=frozenset(trial["allowed_settings_exact"]),
    )


def is_handler_allowed_during_setup_activation_lock(
    handler_ref: str,
    *,
    policy: SetupActivationReachabilityPolicy | None = None,
) -> bool:
    """PI-1A path check while setup activation is locked (mirrors activationRoutes.ts)."""
    path = str(handler_ref or "").strip()
    if not path.startswith("/app"):
        return False
    pol = policy or load_setup_activation_reachability_policy()

    if path in pol.allowed_exact:
        return True

    if path.startswith(pol.onboarding_allowed_prefix):
        if path in pol.onboarding_denied_exact:
            return False
        if path.startswith(pol.onboarding_denied_prefix):
            return False
        return True

    if path.startswith(pol.settings_allowed_prefix):
        return True

    for prefix in pol.allowed_prefixes:
        if path.startswith(prefix):
            return True

    return False


def is_handler_blocked_for_guided_trial(
    handler_ref: str,
    *,
    tenant_status: str | None,
    policy: SetupActivationReachabilityPolicy | None = None,
) -> bool:
    """Trial is full product access (SSOT: Team/Business for the trial window).

    Settings must not be locked for self-serve employers. The JSON policy is
    retained for documentation; it is not enforced at runtime.
    """
    del handler_ref, tenant_status, policy
    return False
