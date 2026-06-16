from __future__ import annotations

from backend.app.reference.reference_rule_pack_foundation import (
    CATALOG_VERSION,
    list_rule_pack_domain_targets,
    list_rule_pack_metadata,
    list_rule_pack_types,
    list_rule_pack_version_markers,
)


def test_rule_pack_foundation_baseline_shape() -> None:
    assert CATALOG_VERSION.startswith("ref4-phase1c-rule-pack-foundation-")
    assert len(list_rule_pack_types()) >= 1
    assert len(list_rule_pack_metadata()) >= 1
    assert len(list_rule_pack_domain_targets()) >= 1
    assert len(list_rule_pack_version_markers()) >= 1


def test_rule_pack_foundation_compatibility_markers_are_skeleton_only() -> None:
    markers = list_rule_pack_version_markers()
    assert all(item.compatibility_marker == "skeleton-only" for item in markers)
