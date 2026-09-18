"""Recruitment Ready process-policy + pluggable composition (ADR-042).

Policy id: ``transfer_policy_v1`` / Ready composition authority.

Pipeline:

  public context / policy selection
    → resolve_ready_composition_v1  (separate authority)
    → private composition (may be [])
    → applicable evaluators + aggregate
    → canonical Ready verdict
    → transfer_allowed = (verdict == allowed)

Empty composition ``[]`` is a registered policy composition on the same path —
not a kernel_mode / skip_requirements bypass.

Composition **contents** (capability lists) stay private to Recruitment.
Public input is a stable selector / context only (``ready_composition_id``).

LLM-OFF.
"""

from __future__ import annotations

from typing import Any, Final, Mapping, Sequence

POLICY_ID: Final[str] = "transfer_policy_v1"
POLICY_VERSION: Final[str] = "transfer_policy_v1"

DECISION_ALLOWED: Final[str] = "allowed"
DECISION_MISSING: Final[str] = "missing"
DECISION_BLOCKED: Final[str] = "blocked"
DECISION_UNSUPPORTED: Final[str] = "unsupported_context"

DECISION_VALUES: Final[tuple[str, ...]] = (
    DECISION_ALLOWED,
    DECISION_MISSING,
    DECISION_BLOCKED,
    DECISION_UNSUPPORTED,
)

# Stable external selector key (public vocabulary — not a capability list).
READY_COMPOSITION_ID_KEY: Final[str] = "ready_composition_id"

COMPOSITION_EMPTY: Final[str] = "empty"
COMPOSITION_DRIVER: Final[str] = "driver"

# Private capability codes — never accept these as public Kernel input.
CAP_DOCUMENT_PACKS: Final[str] = "document_packs"
CAP_RECRUITMENT_PACKAGE: Final[str] = "recruitment_package"
CAP_FIELD_REQUIREMENTS: Final[str] = "field_requirements"
CAP_REQUIREMENT_ENGINE: Final[str] = "requirement_engine"
CAP_OPERATIONAL_REQUIREMENTS: Final[str] = "operational_requirements"
CAP_RECRUITER_CONFIRMATION: Final[str] = "recruiter_confirmation"

_DRIVER_CAPABILITIES: Final[tuple[str, ...]] = (
    CAP_DOCUMENT_PACKS,
    CAP_RECRUITMENT_PACKAGE,
    CAP_FIELD_REQUIREMENTS,
    CAP_REQUIREMENT_ENGINE,
    CAP_OPERATIONAL_REQUIREMENTS,
    CAP_RECRUITER_CONFIRMATION,
)

RESOLVE_API: Final[str] = "resolve_ready_composition_v1"
AGGREGATE_API: Final[str] = "aggregate_ready_verdict_v1"
SEPARATION_REL: Final[str] = (
    "docs/specs/tasks/recruitment-ready-policy-composition-separation.md"
)

# Codes treated as missing (actionable) vs hard blocked.
_MISSING_REASON_CODES: Final[frozenset[str]] = frozenset(
    {
        "missing_required_document",
        "pending_document_verification",
        "expired_required_document",
        "missing_data_field",
        "package_block_incomplete",
        "unconfirmed_block",
        "operational_requirement_open",
    }
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _norm(value: Any) -> str:
    return _text(value).lower().replace("-", "_").replace(" ", "_")


def _record(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _normalize_composition_id(value: Any) -> str | None:
    raw = _norm(value)
    if not raw:
        return None
    if raw in {"empty", "zero", "zero_requirement", "none", "[]"}:
        return COMPOSITION_EMPTY
    if raw in {"driver", "default", "production", "driver_default"}:
        return COMPOSITION_DRIVER
    return _text(value) or None


def _capabilities_for_composition(composition_id: str) -> tuple[str, ...]:
    """Private: map composition id → applicable Ready capabilities."""
    if composition_id == COMPOSITION_EMPTY:
        return ()
    if composition_id == COMPOSITION_DRIVER:
        return _DRIVER_CAPABILITIES
    return ()


def resolve_ready_composition_v1(
    ready_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Separate authority: select Ready composition from stable public context.

    Does not evaluate evidence. Does not AND capabilities unconditionally.
    Explicit ``ready_composition_id=empty`` → registered empty composition.
    Absent selector → production driver composition (today's Ready surface).
    Unknown explicit id → unresolved (unsupported_context upstream).
    """
    ctx = _record(ready_context)
    explicit = _normalize_composition_id(
        ctx.get(READY_COMPOSITION_ID_KEY) or ctx.get("ready_composition")
    )
    if explicit == COMPOSITION_EMPTY:
        return {
            "resolved": True,
            "composition_id": COMPOSITION_EMPTY,
            "context_policy": COMPOSITION_EMPTY,
            "capabilities": [],
        }
    if explicit == COMPOSITION_DRIVER:
        return {
            "resolved": True,
            "composition_id": COMPOSITION_DRIVER,
            "context_policy": COMPOSITION_DRIVER,
            "capabilities": list(_capabilities_for_composition(COMPOSITION_DRIVER)),
        }
    if explicit is not None:
        # Explicit but unknown — cannot determine applicable Ready policy.
        return {
            "resolved": False,
            "composition_id": None,
            "context_policy": None,
            "capabilities": [],
            "reason": "unknown_ready_composition_id",
            "requested_composition_id": _text(
                ctx.get(READY_COMPOSITION_ID_KEY) or ctx.get("ready_composition")
            ),
        }
    # Default production: driver composition (preserves today's Ready requirements).
    return {
        "resolved": True,
        "composition_id": COMPOSITION_DRIVER,
        "context_policy": COMPOSITION_DRIVER,
        "capabilities": list(_capabilities_for_composition(COMPOSITION_DRIVER)),
        "reason": "default_driver",
    }


def aggregate_ready_verdict_v1(
    *,
    composition_id: str | None,
    capabilities: Sequence[str],
    blocking_reasons: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Aggregate applicable-layer evidence into one canonical Ready verdict.

    ``transfer_allowed`` is derived only: decision == allowed.
    """
    reasons = [dict(r) for r in (blocking_reasons or []) if isinstance(r, Mapping)]
    caps = [str(c) for c in capabilities]

    if not reasons:
        return {
            "decision": DECISION_ALLOWED,
            "transfer_allowed": True,
            "composition_id": composition_id,
            "next_action": None,
            "primary_item": {
                "code": DECISION_ALLOWED,
                "kind": "threshold",
                "message": "Ready / transfer allowed under active Ready composition",
            },
            "active_missing": [],
            "blockers": [],
            "applicable_capabilities": caps,
        }

    missing = [
        r
        for r in reasons
        if _norm(r.get("code")) in _MISSING_REASON_CODES
        or str(r.get("source_layer") or "")
        in {
            CAP_RECRUITMENT_PACKAGE,
            CAP_FIELD_REQUIREMENTS,
            CAP_RECRUITER_CONFIRMATION,
            CAP_OPERATIONAL_REQUIREMENTS,
            CAP_DOCUMENT_PACKS,
            CAP_REQUIREMENT_ENGINE,
        }
    ]
    if missing:
        primary = missing[0]
        return {
            "decision": DECISION_MISSING,
            "transfer_allowed": False,
            "composition_id": composition_id,
            "next_action": {
                "code": str(primary.get("code") or "ready_requirement_missing"),
                "message": str(primary.get("message") or primary.get("code") or "missing"),
                "source_layer": primary.get("source_layer"),
            },
            "primary_item": {
                "code": str(primary.get("code") or "ready_requirement_missing"),
                "kind": "formal_action",
                "message": str(primary.get("message") or primary.get("code") or "missing"),
            },
            "active_missing": missing,
            "blockers": [],
            "applicable_capabilities": caps,
        }

    primary = reasons[0]
    return {
        "decision": DECISION_BLOCKED,
        "transfer_allowed": False,
        "composition_id": composition_id,
        "next_action": {
            "code": str(primary.get("code") or "ready_blocked"),
            "message": str(primary.get("message") or "blocked"),
            "source_layer": primary.get("source_layer"),
        },
        "primary_item": {
            "code": str(primary.get("code") or "ready_blocked"),
            "kind": "blocker",
            "message": str(primary.get("message") or "blocked"),
        },
        "active_missing": [],
        "blockers": reasons,
        "applicable_capabilities": caps,
    }


def unsupported_ready_verdict_v1(*, reason: str | None = None) -> dict[str, Any]:
    return {
        "decision": DECISION_UNSUPPORTED,
        "transfer_allowed": False,
        "composition_id": None,
        "next_action": {
            "code": "unsupported_context",
            "message": "Ready composition resolver could not determine an applicable Ready policy",
        },
        "primary_item": {
            "code": "unsupported_context",
            "kind": "policy_routing",
            "message": "Ready composition resolver could not determine an applicable Ready policy",
        },
        "active_missing": [],
        "blockers": [],
        "applicable_capabilities": [],
        "resolve_reason": reason,
    }


__all__ = [
    "POLICY_ID",
    "POLICY_VERSION",
    "DECISION_ALLOWED",
    "DECISION_MISSING",
    "DECISION_BLOCKED",
    "DECISION_UNSUPPORTED",
    "DECISION_VALUES",
    "READY_COMPOSITION_ID_KEY",
    "COMPOSITION_EMPTY",
    "COMPOSITION_DRIVER",
    "RESOLVE_API",
    "AGGREGATE_API",
    "SEPARATION_REL",
    "resolve_ready_composition_v1",
    "aggregate_ready_verdict_v1",
    "unsupported_ready_verdict_v1",
]
