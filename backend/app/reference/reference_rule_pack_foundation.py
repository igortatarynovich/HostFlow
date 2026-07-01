from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class RulePackType:
    code: str
    label: str


@dataclass(frozen=True)
class RulePackMetadata:
    pack_code: str
    pack_type: str
    title: str
    description: str
    lifecycle_state: str


@dataclass(frozen=True)
class RulePackDomainTarget:
    pack_code: str
    target_domain: str


@dataclass(frozen=True)
class RulePackVersionMarker:
    pack_code: str
    schema_version: str
    compatibility_marker: str


CATALOG_VERSION: Final[str] = "ref4-phase1c-rule-pack-foundation-v1"


RULE_PACK_TYPES_CANONICAL: Final[tuple[RulePackType, ...]] = (
    RulePackType("document_reference_pack", "Document Reference Pack"),
    RulePackType("workforce_reference_pack", "Workforce Reference Pack"),
    RulePackType("transport_reference_pack", "Transport Reference Pack"),
)

RULE_PACK_METADATA_CANONICAL: Final[tuple[RulePackMetadata, ...]] = (
    RulePackMetadata(
        pack_code="doc_minimum_reference_pack",
        pack_type="document_reference_pack",
        title="Document Minimum Reference Pack",
        description="Reference-only metadata skeleton for document-related rule packs.",
        lifecycle_state="draft",
    ),
    RulePackMetadata(
        pack_code="workforce_baseline_reference_pack",
        pack_type="workforce_reference_pack",
        title="Workforce Baseline Reference Pack",
        description="Reference-only metadata skeleton for workforce domains.",
        lifecycle_state="draft",
    ),
)

RULE_PACK_DOMAIN_TARGETS_CANONICAL: Final[tuple[RulePackDomainTarget, ...]] = (
    RulePackDomainTarget("doc_minimum_reference_pack", "document_types"),
    RulePackDomainTarget("doc_minimum_reference_pack", "document_categories"),
    RulePackDomainTarget("workforce_baseline_reference_pack", "workforce_categories"),
    RulePackDomainTarget("workforce_baseline_reference_pack", "employment_types"),
    RulePackDomainTarget("workforce_baseline_reference_pack", "transport_modes"),
)

RULE_PACK_VERSION_MARKERS_CANONICAL: Final[tuple[RulePackVersionMarker, ...]] = (
    RulePackVersionMarker("doc_minimum_reference_pack", "1.0.0", "skeleton-only"),
    RulePackVersionMarker("workforce_baseline_reference_pack", "1.0.0", "skeleton-only"),
)


def list_rule_pack_types() -> tuple[RulePackType, ...]:
    return RULE_PACK_TYPES_CANONICAL


def list_rule_pack_metadata() -> tuple[RulePackMetadata, ...]:
    return RULE_PACK_METADATA_CANONICAL


def list_rule_pack_domain_targets() -> tuple[RulePackDomainTarget, ...]:
    return RULE_PACK_DOMAIN_TARGETS_CANONICAL


def list_rule_pack_version_markers() -> tuple[RulePackVersionMarker, ...]:
    return RULE_PACK_VERSION_MARKERS_CANONICAL


def _assert_unique_rule_pack_codes() -> None:
    pack_codes = [item.pack_code for item in RULE_PACK_METADATA_CANONICAL]
    assert len(pack_codes) == len(set(pack_codes)), "Duplicate rule pack code"


_assert_unique_rule_pack_codes()


__all__ = [
    "CATALOG_VERSION",
    "RulePackType",
    "RulePackMetadata",
    "RulePackDomainTarget",
    "RulePackVersionMarker",
    "RULE_PACK_TYPES_CANONICAL",
    "RULE_PACK_METADATA_CANONICAL",
    "RULE_PACK_DOMAIN_TARGETS_CANONICAL",
    "RULE_PACK_VERSION_MARKERS_CANONICAL",
    "list_rule_pack_types",
    "list_rule_pack_metadata",
    "list_rule_pack_domain_targets",
    "list_rule_pack_version_markers",
]
