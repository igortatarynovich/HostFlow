"""Canonical module_owner × result_type → communication_domain (C2).

Deterministic, closed registry. No default domain. No cross-owned mappings.
Communications-owned — must not import Recruitment/Sales ORM.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.app.acquisition.flights.destination_contract import (
    RESULT_APPLICATION,
    RESULT_SALES_INQUIRY,
)

DOMAIN_RECRUITMENT = "recruitment"
DOMAIN_SALES = "sales"

MODULE_RECRUITMENT = "recruitment"
MODULE_SALES = "sales"

COMMUNICATION_DOMAIN_REGISTRY_CONTRACT = "communication.domain_registry.v1"


class CommunicationDomainRegistryError(Exception):
    code = "communication_domain_registry_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class CommunicationDomainUnknownOwnerError(CommunicationDomainRegistryError):
    code = "communication_domain_unknown_owner"


class CommunicationDomainUnknownTypeError(CommunicationDomainRegistryError):
    code = "communication_domain_unknown_result_type"


class CommunicationDomainIncompatibleError(CommunicationDomainRegistryError):
    code = "communication_domain_incompatible_mapping"


class CommunicationDomainDuplicateError(CommunicationDomainRegistryError):
    code = "communication_domain_duplicate_registration"


@dataclass(frozen=True, slots=True)
class DomainRegistryEntry:
    module_owner: str
    result_type: str
    communication_domain: str


class CommunicationDomainRegistry:
    """Closed map: (module_owner, result_type) → communication_domain."""

    def __init__(self) -> None:
        self._by_key: dict[tuple[str, str], DomainRegistryEntry] = {}

    def register(
        self,
        *,
        module_owner: str,
        result_type: str,
        communication_domain: str,
    ) -> DomainRegistryEntry:
        owner = str(module_owner or "").strip().lower()
        rtype = str(result_type or "").strip().lower()
        domain = str(communication_domain or "").strip().lower()
        if not owner:
            raise CommunicationDomainUnknownOwnerError(
                "module_owner is required",
                details={"reason": "unknown_module_owner"},
            )
        if not rtype:
            raise CommunicationDomainUnknownTypeError(
                "result_type is required",
                details={"reason": "unknown_result_type"},
            )
        if not domain:
            raise CommunicationDomainRegistryError(
                "communication_domain is required (no default)",
                details={"module_owner": owner, "result_type": rtype},
            )
        # V1: domain must equal module_owner — no separate guessing.
        if domain != owner:
            raise CommunicationDomainIncompatibleError(
                "communication_domain must equal module_owner (V1)",
                details={
                    "module_owner": owner,
                    "communication_domain": domain,
                    "reason": "cross_owned_or_mismatched_domain",
                },
            )
        if owner == MODULE_RECRUITMENT and domain != DOMAIN_RECRUITMENT:
            raise CommunicationDomainIncompatibleError(
                "recruitment owner cannot map to non-recruitment domain",
                details={"module_owner": owner, "communication_domain": domain},
            )
        if owner == MODULE_SALES and domain != DOMAIN_SALES:
            raise CommunicationDomainIncompatibleError(
                "sales owner cannot map to non-sales domain",
                details={"module_owner": owner, "communication_domain": domain},
            )
        key = (owner, rtype)
        if key in self._by_key:
            raise CommunicationDomainDuplicateError(
                "duplicate module_owner + result_type registration",
                details={"module_owner": owner, "result_type": rtype},
            )
        entry = DomainRegistryEntry(
            module_owner=owner,
            result_type=rtype,
            communication_domain=domain,
        )
        self._by_key[key] = entry
        return entry

    def resolve(self, *, module_owner: str, result_type: str) -> DomainRegistryEntry:
        owner = str(module_owner or "").strip().lower()
        rtype = str(result_type or "").strip().lower()
        if not owner:
            raise CommunicationDomainUnknownOwnerError(
                "module_owner is required",
                details={"reason": "unknown_module_owner"},
            )
        if owner not in {MODULE_RECRUITMENT, MODULE_SALES}:
            raise CommunicationDomainUnknownOwnerError(
                "unknown module_owner",
                details={"module_owner": owner, "reason": "unknown_module_owner"},
            )
        if not rtype:
            raise CommunicationDomainUnknownTypeError(
                "result_type is required",
                details={
                    "module_owner": owner,
                    "reason": "unknown_result_type",
                },
            )
        entry = self._by_key.get((owner, rtype))
        if entry is None:
            # Distinguish unknown type vs incompatible pair for known types.
            known_types = {k[1] for k in self._by_key}
            if rtype not in known_types:
                raise CommunicationDomainUnknownTypeError(
                    "unknown result_type",
                    details={
                        "module_owner": owner,
                        "result_type": rtype,
                        "reason": "unknown_result_type",
                    },
                )
            raise CommunicationDomainIncompatibleError(
                "incompatible module_owner + result_type",
                details={
                    "module_owner": owner,
                    "result_type": rtype,
                    "reason": "incompatible_result_type",
                },
            )
        return entry

    def list_entries(self) -> list[DomainRegistryEntry]:
        return [self._by_key[k] for k in sorted(self._by_key.keys())]


def build_default_communication_domain_registry() -> CommunicationDomainRegistry:
    registry = CommunicationDomainRegistry()
    registry.register(
        module_owner=MODULE_RECRUITMENT,
        result_type=RESULT_APPLICATION,
        communication_domain=DOMAIN_RECRUITMENT,
    )
    registry.register(
        module_owner=MODULE_SALES,
        result_type=RESULT_SALES_INQUIRY,
        communication_domain=DOMAIN_SALES,
    )
    return registry


_PLATFORM_DOMAIN_REGISTRY = build_default_communication_domain_registry()


def platform_communication_domain_registry() -> CommunicationDomainRegistry:
    return _PLATFORM_DOMAIN_REGISTRY


def reset_communication_domain_registry_for_tests() -> CommunicationDomainRegistry:
    global _PLATFORM_DOMAIN_REGISTRY
    _PLATFORM_DOMAIN_REGISTRY = build_default_communication_domain_registry()
    return _PLATFORM_DOMAIN_REGISTRY
