"""Tests for tenant status normalization in setup readiness."""

from __future__ import annotations

from backend.app.services.recruitment_setup_readiness import _normalize_tenant_status


class _EnumLike:
    value = "trial"


def test_normalize_tenant_status_from_enum_value() -> None:
    assert _normalize_tenant_status(_EnumLike()) == "trial"


def test_normalize_tenant_status_from_repr() -> None:
    assert _normalize_tenant_status("TenantStatus.trial") == "trial"
