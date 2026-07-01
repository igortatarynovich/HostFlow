"""Unit tests for tenant access classification (no DB)."""

from __future__ import annotations

from dataclasses import dataclass

from backend.app.auth.deps import Role
from backend.app.security.api_tenant_context import (
    SecurityAccessKind,
    classify_api_tenant_access,
)


@dataclass
class _FakeUser:
    sub: str
    email: str
    role: str
    tenant_id: str
    raw: dict


def test_tenant_bound_when_header_matches_jwt() -> None:
    u = _FakeUser("u1", "a@b.c", Role.administrator.value, "11111111-1111-1111-1111-111111111111", {})
    k, scope = classify_api_tenant_access(
        u,
        header_tenant_id="11111111-1111-1111-1111-111111111111",
        elevated_reason=None,
        elevated_scope=None,
    )
    assert k == SecurityAccessKind.tenant_bound
    assert scope is None


def test_superadmin_cross_tenant_classifies_elevated() -> None:
    u = _FakeUser("u1", "a@b.c", Role.superadmin.value, "11111111-1111-1111-1111-111111111111", {})
    k, scope = classify_api_tenant_access(
        u,
        header_tenant_id="22222222-2222-2222-2222-222222222222",
        elevated_reason="ops",
        elevated_scope=None,
    )
    assert k == SecurityAccessKind.superadmin_elevated
    assert scope == "cross_tenant_rls"


def test_support_impersonation_claim() -> None:
    u = _FakeUser(
        "u1",
        "a@b.c",
        Role.administrator.value,
        "11111111-1111-1111-1111-111111111111",
        {"impersonating_tenant_id": "22222222-2222-2222-2222-222222222222"},
    )
    k, scope = classify_api_tenant_access(
        u,
        header_tenant_id="22222222-2222-2222-2222-222222222222",
        elevated_reason=None,
        elevated_scope=None,
    )
    assert k == SecurityAccessKind.support_impersonation
    assert scope == "support_session"


def test_recruiter_mismatch_stays_tenant_bound_classification() -> None:
    """JWT/header mismatch without superadmin impersonation stays tenant_bound at classifier level."""
    u = _FakeUser("u1", "a@b.c", Role.recruiter.value, "11111111-1111-1111-1111-111111111111", {})
    k, scope = classify_api_tenant_access(
        u,
        header_tenant_id="22222222-2222-2222-2222-222222222222",
        elevated_reason=None,
        elevated_scope=None,
    )
    assert k == SecurityAccessKind.tenant_bound
    assert scope is None
