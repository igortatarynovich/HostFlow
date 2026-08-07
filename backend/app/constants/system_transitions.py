"""ADR-035 platform system transition catalog.

Operational pipeline stages are board positions. System transitions are exit /
cross-module events — never the object's current position.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

# Catalog keys (stable; do not invent company-local keys).
HANDOFF_TO_HR = "handoff_to_hr"
HANDOFF_TO_FLEET = "handoff_to_fleet"
HANDOFF_TO_CLIENT = "handoff_to_client"
CLOSE_SUCCESS = "close_success"
CLOSE_DECLINED = "close_declined"

ALL_CATALOG_KEYS: frozenset[str] = frozenset(
    {
        HANDOFF_TO_HR,
        HANDOFF_TO_FLEET,
        HANDOFF_TO_CLIENT,
        CLOSE_SUCCESS,
        CLOSE_DECLINED,
    }
)

# Must not be used as Candidate (or other source) operational board position.
FORBIDDEN_AS_OPERATIONAL_STAGE_CODES: frozenset[str] = frozenset(
    {
        "ready_for_hr",
        "processing_by_hr",
        "ready_for_fleet",
        # Legacy pseudo-handoff columns on Candidate boards
        "processing_by_client",
    }
)

# Legacy stage codes that map to catalog transitions during strangler (Phase C).
LEGACY_STAGE_TO_TRANSITION: dict[str, str] = {
    "ready_for_hr": HANDOFF_TO_HR,
    "processing_by_hr": HANDOFF_TO_HR,
    "ready_for_handoff": HANDOFF_TO_CLIENT,
    "processing_by_client": HANDOFF_TO_CLIENT,
    "ready_for_fleet": HANDOFF_TO_FLEET,
}


@dataclass(frozen=True)
class SystemTransitionDef:
    key: str
    label: str
    source_module: str
    source_object_type: str
    target_module: str | None
    target_object_type: str | None
    requires_enabled_module: str | None
    locks_semantics: bool = True


CATALOG: tuple[SystemTransitionDef, ...] = (
    SystemTransitionDef(
        key=HANDOFF_TO_HR,
        label="Handoff to HR",
        source_module="recruitment",
        source_object_type="candidate",
        target_module="hr",
        target_object_type="employee",
        requires_enabled_module="hr",
    ),
    SystemTransitionDef(
        key=HANDOFF_TO_CLIENT,
        label="Handoff to Client",
        source_module="recruitment",
        source_object_type="candidate",
        target_module=None,
        target_object_type=None,
        requires_enabled_module=None,
    ),
    SystemTransitionDef(
        key=HANDOFF_TO_FLEET,
        label="Handoff to Fleet",
        source_module="hr",
        source_object_type="employee",
        target_module="fleet",
        target_object_type="driver_assignment",
        requires_enabled_module="fleet",
    ),
    SystemTransitionDef(
        key=CLOSE_SUCCESS,
        label="Close successfully",
        source_module="*",
        source_object_type="*",
        target_module=None,
        target_object_type=None,
        requires_enabled_module=None,
    ),
    SystemTransitionDef(
        key=CLOSE_DECLINED,
        label="Close declined",
        source_module="*",
        source_object_type="*",
        target_module=None,
        target_object_type=None,
        requires_enabled_module=None,
    ),
)

_BY_KEY: dict[str, SystemTransitionDef] = {t.key: t for t in CATALOG}


def get_transition(key: str) -> SystemTransitionDef | None:
    return _BY_KEY.get(str(key or "").strip())


def available_transitions(
    *,
    source_module: str,
    source_object_type: str,
    enabled_modules: Iterable[str] | None = None,
) -> list[SystemTransitionDef]:
    """Filter platform catalog by source + company enabled modules (ADR-035 A2)."""
    enabled = {str(m).strip().lower() for m in (enabled_modules or []) if m}
    sm = str(source_module or "").strip().lower()
    so = str(source_object_type or "").strip().lower()
    out: list[SystemTransitionDef] = []
    for t in CATALOG:
        if t.source_module not in ("*", sm):
            continue
        if t.source_object_type not in ("*", so):
            continue
        req = t.requires_enabled_module
        if req and req not in enabled:
            continue
        out.append(t)
    return out


def is_forbidden_operational_stage(code: str | None) -> bool:
    if not code:
        return False
    return str(code).strip().lower() in FORBIDDEN_AS_OPERATIONAL_STAGE_CODES


# Lifecycle statuses (orthogonal to board stage) — ADR-035 §6
LIFECYCLE_ACTIVE = "active"
LIFECYCLE_CLOSED = "closed"
LIFECYCLE_ARCHIVED = "archived"
LIFECYCLE_STATUSES: frozenset[str] = frozenset(
    {LIFECYCLE_ACTIVE, LIFECYCLE_CLOSED, LIFECYCLE_ARCHIVED}
)
