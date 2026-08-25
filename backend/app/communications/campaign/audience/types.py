"""Pure data contracts for C2.3 Audience Resolver (no ORM / I/O)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

# Supported audience definition types (opaque JSON on CampaignAudienceDefinition).
DEFINITION_TYPE_STATIC_LIST = "static_list"
DEFINITION_TYPE_FILTER = "filter"
DEFINITION_TYPES = frozenset(
    {
        DEFINITION_TYPE_STATIC_LIST,
        DEFINITION_TYPE_FILTER,
    }
)

SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"
SEVERITY_INFO = "info"

DIAG_INVALID_DEFINITION = "invalid_definition"
DIAG_UNKNOWN_DEFINITION_TYPE = "unknown_definition_type"
DIAG_EMPTY_AUDIENCE = "empty_audience"
DIAG_INVALID_RECIPIENT = "invalid_recipient"
DIAG_DUPLICATE_RECIPIENT = "duplicate_recipient"
DIAG_FILTER_INVALID = "filter_invalid"
DIAG_ENTITY_POOL_REQUIRED = "entity_pool_required"
DIAG_ENTITY_SKIPPED = "entity_skipped"


@dataclass(frozen=True, slots=True)
class AudienceDefinitionPayload:
    """Immutable audience *definition* (selection rule) — not a snapshot."""

    definition_type: str
    definition: Mapping[str, Any] = field(default_factory=dict)
    meta: Mapping[str, Any] = field(default_factory=dict)
    version_id: str | None = None


@dataclass(frozen=True, slots=True)
class EntityCandidate:
    """Caller-supplied entity for filter resolution (no module / DB imports)."""

    entity_type: str
    entity_id: str
    address: str | None = None
    label: str | None = None
    attributes: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ResolveContext:
    """Caller-supplied inputs — resolver never loads tenants/entities from DB."""

    # Required for definition_type=filter; ignored for static_list.
    entities: Sequence[EntityCandidate] = field(default_factory=tuple)
    # Optional extras (locale, channel hints) — reserved for later PRs.
    extras: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Diagnostic:
    code: str
    severity: str
    message: str
    path: str | None = None
    details: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "path": self.path,
            "details": dict(self.details),
        }


@dataclass(frozen=True, slots=True)
class ResolvedRecipient:
    """One snapshot member produced from a definition (+ context)."""

    entity_type: str
    entity_id: str
    address: str
    label: str | None = None
    snapshot: Mapping[str, Any] = field(default_factory=dict)

    def to_run_dict(self) -> dict[str, Any]:
        """Shape expected by create_run_with_snapshot(recipients=...)."""
        out: dict[str, Any] = {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "address": self.address,
            "snapshot": dict(self.snapshot),
        }
        if self.label is not None:
            out["label"] = self.label
        return out


@dataclass(frozen=True, slots=True)
class SkippedCandidate:
    entity_type: str
    entity_id: str
    address: str | None
    reason_codes: tuple[str, ...]
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "address": self.address,
            "reason_codes": list(self.reason_codes),
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class ResolveResult:
    """Audience *snapshot* materialization (pure) — persist via lifecycle separately."""

    ok: bool
    definition_type: str
    recipients: tuple[ResolvedRecipient, ...]
    skipped: tuple[SkippedCandidate, ...]
    diagnostics: tuple[Diagnostic, ...]
    fingerprint: Mapping[str, Any] = field(default_factory=dict)

    def recipient_run_dicts(self) -> list[dict[str, Any]]:
        return [r.to_run_dict() for r in self.recipients]

    def to_snapshot_meta(self) -> dict[str, Any]:
        return {
            "resolver": "communication.campaign.audience.v1",
            "ok": self.ok,
            "definition_type": self.definition_type,
            "recipient_count": len(self.recipients),
            "skipped_count": len(self.skipped),
            "fingerprint": dict(self.fingerprint),
            "diagnostics": [d.to_dict() for d in self.diagnostics],
            "skipped": [s.to_dict() for s in self.skipped],
        }


__all__ = [
    "DEFINITION_TYPE_STATIC_LIST",
    "DEFINITION_TYPE_FILTER",
    "DEFINITION_TYPES",
    "SEVERITY_ERROR",
    "SEVERITY_WARNING",
    "SEVERITY_INFO",
    "DIAG_INVALID_DEFINITION",
    "DIAG_UNKNOWN_DEFINITION_TYPE",
    "DIAG_EMPTY_AUDIENCE",
    "DIAG_INVALID_RECIPIENT",
    "DIAG_DUPLICATE_RECIPIENT",
    "DIAG_FILTER_INVALID",
    "DIAG_ENTITY_POOL_REQUIRED",
    "DIAG_ENTITY_SKIPPED",
    "AudienceDefinitionPayload",
    "EntityCandidate",
    "ResolveContext",
    "Diagnostic",
    "ResolvedRecipient",
    "SkippedCandidate",
    "ResolveResult",
]
