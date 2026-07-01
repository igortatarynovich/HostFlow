from __future__ import annotations

from backend.app.reference.reference_tenant_override_foundation import (
    CATALOG_VERSION,
    TENANT_OVERLAY_SCHEMA_CONTRACT,
    is_tenant_override_allowed,
    list_tenant_override_domains,
    list_tenant_override_rules,
    list_tenant_override_types,
)


def test_tenant_override_foundation_baseline_shape() -> None:
    assert CATALOG_VERSION.startswith("ref4-phase1c-tenant-override-foundation-")
    assert len(list_tenant_override_types()) >= 1
    assert len(list_tenant_override_domains()) >= 1
    assert len(list_tenant_override_rules()) >= 1
    assert set(TENANT_OVERLAY_SCHEMA_CONTRACT.keys()) == {
        "tenant_id",
        "domain",
        "override_type",
        "target_code",
        "value",
    }


def test_tenant_override_foundation_allowance_resolution() -> None:
    assert is_tenant_override_allowed(domain="document_types", override_type="label_override") is True
    assert is_tenant_override_allowed(domain="driver_capability_classes", override_type="label_override") is False
    assert is_tenant_override_allowed(domain="unknown_domain", override_type="label_override") is False
