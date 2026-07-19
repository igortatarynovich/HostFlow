"""Intake Runtime Split V1 — Destination Registry (R2).

Contract id: intake.destination_registry.v1

Closed map: route_intent → destination module → owned handler.
Rejects unknown intents, duplicate registration, and incompatible
promotion targets. Does not implement Application/SalesInquiry creation (R4+).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.app.constants.campaign_registries import (
    allowed_route_intents_for_target,
    promotion_targets_by_type,
)
from backend.app.forms_platform.constants import (
    HANDLER_RECRUITMENT_LEAD_DRAFT,
    HANDLER_SALES_INQUIRY_DRAFT,
)
from backend.app.models.intake_routing_enums import RouteIntent
from backend.app.modules.intake_routing.reference import normalize_route_intent

DESTINATION_REGISTRY_CONTRACT = "intake.destination_registry.v1"

DESTINATION_RECRUITMENT = "recruitment"
DESTINATION_SALES = "sales"


class DestinationRegistryError(Exception):
    """Typed destination registry failure."""

    code: str = "intake_destination_registry_error"

    def __init__(
        self,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class DestinationUnknownIntentError(DestinationRegistryError):
    code = "intake_destination_unknown_intent"


class DestinationIncompatibleTargetError(DestinationRegistryError):
    code = "intake_destination_incompatible_target"


class DestinationIncompatibleSourceProfileError(DestinationRegistryError):
    code = "intake_destination_incompatible_source_profile"


class DestinationDuplicateRegistrationError(DestinationRegistryError):
    code = "intake_destination_duplicate_registration"


class DestinationMissingHandlerError(DestinationRegistryError):
    code = "intake_destination_missing_handler"


@dataclass(frozen=True, slots=True)
class DestinationEntry:
    route_intent: str
    destination: str
    handler_id: str
    module_owner: str
    allowed_promotion_targets: frozenset[str]

    def to_handler_dict(self) -> dict[str, Any]:
        return {
            "handler_id": self.handler_id,
            "module_owner": self.module_owner,
            "destination": self.destination,
            "route_intent": self.route_intent,
            "creates": ["application"]
            if self.destination == DESTINATION_RECRUITMENT
            else ["sales_inquiry"],
            "creates_on_create": {
                "lead_draft": False,
                "candidate": False,
                "application": self.destination == DESTINATION_RECRUITMENT,
                "sales_inquiry": self.destination == DESTINATION_SALES,
            },
            "registry_contract": DESTINATION_REGISTRY_CONTRACT,
        }


class DestinationRegistry:
    """Closed destination registry — one entry per routable route_intent."""

    def __init__(self) -> None:
        self._by_intent: dict[str, DestinationEntry] = {}

    def register(
        self,
        *,
        route_intent: str,
        destination: str,
        handler_id: str,
        module_owner: str | None = None,
        allowed_promotion_targets: frozenset[str] | None = None,
    ) -> DestinationEntry:
        intent = normalize_route_intent(route_intent)
        if intent in {RouteIntent.unknown.value, ""}:
            raise DestinationUnknownIntentError(
                "unknown route_intent cannot be registered",
                details={"route_intent": route_intent},
            )
        if intent not in {
            RouteIntent.candidate_application.value,
            RouteIntent.sales_inquiry.value,
        }:
            # V1 closed set — extend only via explicit registry change
            raise DestinationUnknownIntentError(
                "route_intent is not in V1 destination registry set",
                details={"route_intent": intent},
            )
        dest = str(destination or "").strip().lower()
        if dest not in {DESTINATION_RECRUITMENT, DESTINATION_SALES}:
            raise DestinationRegistryError(
                "unsupported destination",
                details={"destination": destination},
            )
        hid = str(handler_id or "").strip()
        if not hid:
            raise DestinationMissingHandlerError(
                "handler_id is required",
                details={"route_intent": intent},
            )
        owner = str(module_owner or dest).strip().lower()
        if owner != dest:
            raise DestinationRegistryError(
                "module_owner must match destination",
                details={"module_owner": owner, "destination": dest},
            )
        # Cross-module ownership forbidden
        if dest == DESTINATION_RECRUITMENT and not hid.startswith("recruitment."):
            raise DestinationRegistryError(
                "recruitment destination requires recruitment-owned handler_id",
                details={"handler_id": hid},
            )
        if dest == DESTINATION_SALES and not hid.startswith("sales."):
            raise DestinationRegistryError(
                "sales destination requires sales-owned handler_id",
                details={"handler_id": hid},
            )
        if intent in self._by_intent:
            raise DestinationDuplicateRegistrationError(
                "route_intent already registered",
                details={"route_intent": intent},
            )

        if allowed_promotion_targets is None:
            targets = frozenset(
                tt
                for tt, row in promotion_targets_by_type().items()
                if intent in frozenset(str(x) for x in (row.get("allowed_route_intents") or []))
            )
        else:
            targets = frozenset(str(t).strip() for t in allowed_promotion_targets if str(t).strip())

        entry = DestinationEntry(
            route_intent=intent,
            destination=dest,
            handler_id=hid,
            module_owner=owner,
            allowed_promotion_targets=targets,
        )
        self._by_intent[intent] = entry
        return entry

    def resolve(self, route_intent: str | None) -> DestinationEntry:
        raw = str(route_intent or "").strip()
        if not raw:
            raise DestinationUnknownIntentError(
                "route_intent is required (fail-closed)",
                details={"reason": "missing_route_intent"},
            )
        intent = normalize_route_intent(raw)
        if intent == RouteIntent.unknown.value:
            raise DestinationUnknownIntentError(
                "unknown route_intent",
                details={"route_intent": raw, "normalized": intent},
            )
        entry = self._by_intent.get(intent)
        if entry is None:
            raise DestinationUnknownIntentError(
                "route_intent has no destination",
                details={"route_intent": intent},
            )
        return entry

    def assert_compatible_promotion_target(
        self,
        route_intent: str,
        target_type: str,
    ) -> None:
        entry = self.resolve(route_intent)
        tt = str(target_type or "").strip().lower()
        if not tt:
            raise DestinationIncompatibleTargetError(
                "promotion target_type is required",
                details={"route_intent": entry.route_intent},
            )
        allowed = allowed_route_intents_for_target(tt)
        if entry.route_intent not in allowed:
            raise DestinationIncompatibleTargetError(
                "route_intent incompatible with promotion target",
                details={
                    "route_intent": entry.route_intent,
                    "target_type": tt,
                    "allowed_route_intents": sorted(allowed),
                },
            )
        if entry.allowed_promotion_targets and tt not in entry.allowed_promotion_targets:
            raise DestinationIncompatibleTargetError(
                "promotion target not allowed for destination entry",
                details={
                    "route_intent": entry.route_intent,
                    "target_type": tt,
                    "allowed_promotion_targets": sorted(entry.allowed_promotion_targets),
                },
            )

    def assert_compatible_source_profile(
        self,
        route_intent: str,
        *,
        profile_route_intent: str | None,
    ) -> None:
        """Pinned profile route_intent must equal the resolved intent (fail-closed)."""
        entry = self.resolve(route_intent)
        pinned_raw = str(profile_route_intent or "").strip()
        if not pinned_raw:
            raise DestinationIncompatibleSourceProfileError(
                "source profile route_intent is required",
                details={
                    "route_intent": entry.route_intent,
                    "reason": "missing_profile_route_intent",
                },
            )
        pinned = normalize_route_intent(pinned_raw)
        if pinned in {RouteIntent.unknown.value, ""}:
            raise DestinationIncompatibleSourceProfileError(
                "source profile route_intent is unknown",
                details={
                    "route_intent": entry.route_intent,
                    "profile_route_intent": pinned_raw,
                },
            )
        if pinned != entry.route_intent:
            raise DestinationIncompatibleSourceProfileError(
                "source profile route_intent incompatible with destination intent",
                details={
                    "route_intent": entry.route_intent,
                    "profile_route_intent": pinned,
                },
            )

    def list_entries(self) -> list[DestinationEntry]:
        return [self._by_intent[k] for k in sorted(self._by_intent.keys())]


def build_default_destination_registry() -> DestinationRegistry:
    """V1 closed bootstrap — candidate_application ↔ Recruitment, sales_inquiry ↔ Sales."""
    registry = DestinationRegistry()
    registry.register(
        route_intent=RouteIntent.candidate_application.value,
        destination=DESTINATION_RECRUITMENT,
        handler_id=HANDLER_RECRUITMENT_LEAD_DRAFT,
        module_owner=DESTINATION_RECRUITMENT,
    )
    registry.register(
        route_intent=RouteIntent.sales_inquiry.value,
        destination=DESTINATION_SALES,
        handler_id=HANDLER_SALES_INQUIRY_DRAFT,
        module_owner=DESTINATION_SALES,
    )
    return registry


_PLATFORM_DESTINATION_REGISTRY = build_default_destination_registry()


def platform_destination_registry() -> DestinationRegistry:
    return _PLATFORM_DESTINATION_REGISTRY


def reset_platform_destination_registry_for_tests() -> DestinationRegistry:
    """Test helper — rebuild default closed registry."""
    global _PLATFORM_DESTINATION_REGISTRY
    _PLATFORM_DESTINATION_REGISTRY = build_default_destination_registry()
    return _PLATFORM_DESTINATION_REGISTRY
