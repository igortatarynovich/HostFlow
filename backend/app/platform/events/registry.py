"""Event Contract Registry — static platform catalog (ADR-019 PR 3A-1)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional


class EventSensitivity(str, Enum):
    internal = "internal"
    operational = "operational"
    pii = "pii"


PayloadValidator = Callable[[dict[str, Any]], None]


@dataclass(frozen=True)
class EventContract:
    event_type: str
    current_version: str
    aggregate_type: str
    owner_module: str
    sensitivity: EventSensitivity
    retention_days: int
    audit_required: bool
    validate_payload: PayloadValidator

    def validate(self, *, event_version: str, payload: dict[str, Any]) -> None:
        if event_version != self.current_version:
            raise ValueError(
                f"unsupported event version for {self.event_type}: {event_version!r}; "
                f"expected {self.current_version!r}"
            )
        self.validate_payload(payload)


def _require_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if value is None or not str(value).strip():
        raise ValueError(f"payload.{key} is required")
    return str(value).strip()


def _require_bool(payload: dict[str, Any], key: str) -> bool:
    if key not in payload:
        raise ValueError(f"payload.{key} is required")
    return bool(payload[key])


def _require_list_str(payload: dict[str, Any], key: str) -> list[str]:
    raw = payload.get(key)
    if raw is None:
        raise ValueError(f"payload.{key} is required")
    if not isinstance(raw, list):
        raise ValueError(f"payload.{key} must be a list")
    return [str(x) for x in raw]


def _parse_iso_datetime(value: Any, field: str) -> None:
    if value is None:
        raise ValueError(f"payload.{field} is required")
    text = str(value).strip()
    if not text:
        raise ValueError(f"payload.{field} is required")
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"payload.{field} must be ISO-8601 datetime") from exc


def _validate_candidate_requirements_evaluated_v1(payload: dict[str, Any]) -> None:
    _require_str(payload, "candidate_id")
    _require_str(payload, "evaluation_result_id")
    _require_str(payload, "entity_revision")
    if not _require_str(payload, "policy_ref"):
        raise ValueError("payload.policy_ref is required")
    _require_bool(payload, "can_transition")
    _require_str(payload, "target_stage")
    _require_list_str(payload, "blocker_codes")
    _parse_iso_datetime(payload.get("evaluated_at"), "evaluated_at")
    forbidden = {"documents", "personal_data", "requirements", "requirement_evaluation_v2"}
    overlap = forbidden.intersection(payload.keys())
    if overlap:
        raise ValueError(f"payload must not include internal evaluator fields: {sorted(overlap)}")


class EventContractRegistry:
    """Static registry — no tenant-defined event types."""

    def __init__(self) -> None:
        self._contracts: dict[str, EventContract] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register(
            EventContract(
                event_type="candidate.requirements_evaluated",
                current_version="v1",
                aggregate_type="candidate",
                owner_module="recruitment",
                sensitivity=EventSensitivity.operational,
                retention_days=365,
                audit_required=True,
                validate_payload=_validate_candidate_requirements_evaluated_v1,
            )
        )

    def register(self, contract: EventContract) -> None:
        self._contracts[contract.event_type] = contract

    def get(self, event_type: str) -> Optional[EventContract]:
        return self._contracts.get(event_type)

    def require(self, event_type: str) -> EventContract:
        contract = self.get(event_type)
        if contract is None:
            raise ValueError(f"unknown event type: {event_type}")
        return contract

    def validate_envelope(
        self,
        *,
        event_type: str,
        event_version: str,
        payload: dict[str, Any],
    ) -> EventContract:
        contract = self.require(event_type)
        contract.validate(event_version=event_version, payload=payload)
        return contract


_REGISTRY: Optional[EventContractRegistry] = None


def get_event_contract_registry() -> EventContractRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = EventContractRegistry()
    return _REGISTRY
