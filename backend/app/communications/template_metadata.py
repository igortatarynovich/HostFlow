"""Immutable communication template metadata (C4 SoT).

Metadata — not template name, catalog path, or UI — is the source of truth
for whether a template may be used in a CommunicationContext.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

LIFECYCLE_ACTIVE = "active"
LIFECYCLE_DISABLED = "disabled"
LIFECYCLE_ARCHIVED = "archived"

ACTIVE_LIFECYCLES = frozenset({LIFECYCLE_ACTIVE})

TEMPLATE_METADATA_CONTRACT = "communication.template_metadata.v1"


@dataclass(frozen=True, slots=True)
class CommunicationTemplateMetadata:
    """Immutable template identity + eligibility dimensions."""

    template_id: str
    template_version: str
    module_owner: str
    communication_domain: str
    communication_purpose: str
    supported_channels: frozenset[str]
    supported_locales: frozenset[str]
    lifecycle_status: str
    policy_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "template_version": self.template_version,
            "module_owner": self.module_owner,
            "communication_domain": self.communication_domain,
            "communication_purpose": self.communication_purpose,
            "supported_channels": sorted(self.supported_channels),
            "supported_locales": sorted(self.supported_locales),
            "lifecycle_status": self.lifecycle_status,
            "policy_version": self.policy_version,
            "contract": TEMPLATE_METADATA_CONTRACT,
        }


def build_template_metadata(
    *,
    template_id: str,
    template_version: str,
    module_owner: str,
    communication_domain: str,
    communication_purpose: str,
    supported_channels: set[str] | frozenset[str] | list[str],
    supported_locales: set[str] | frozenset[str] | list[str],
    lifecycle_status: str = LIFECYCLE_ACTIVE,
    policy_version: str,
) -> CommunicationTemplateMetadata:
    return CommunicationTemplateMetadata(
        template_id=str(template_id or "").strip(),
        template_version=str(template_version or "").strip(),
        module_owner=str(module_owner or "").strip().lower(),
        communication_domain=str(communication_domain or "").strip().lower(),
        communication_purpose=str(communication_purpose or "").strip(),
        supported_channels=frozenset(
            str(c).strip().lower() for c in supported_channels if str(c).strip()
        ),
        supported_locales=frozenset(
            str(loc).strip().lower() for loc in supported_locales if str(loc).strip()
        ),
        lifecycle_status=str(lifecycle_status or "").strip().lower(),
        policy_version=str(policy_version or "").strip(),
    )


def assert_metadata_complete(
    meta: CommunicationTemplateMetadata | None,
) -> CommunicationTemplateMetadata:
    if meta is None:
        raise ValueError("missing_template_metadata")
    if not meta.template_id or not meta.template_version:
        raise ValueError("incomplete_template_metadata")
    if not meta.module_owner or not meta.communication_domain:
        raise ValueError("incomplete_template_metadata")
    if not meta.communication_purpose:
        raise ValueError("incomplete_template_metadata")
    if not meta.supported_channels:
        raise ValueError("incomplete_template_metadata")
    if not meta.lifecycle_status or not meta.policy_version:
        raise ValueError("incomplete_template_metadata")
    return meta
