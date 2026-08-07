"""Unit tests for ADR-036 trust role helpers."""

from __future__ import annotations

import pytest

from backend.app.auth.trust_roles import (
    assert_matrix_role_editable,
    expand_allowed_roles_for_trust,
    infer_access_context,
    infer_preset_id,
    normalize_trust_role,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("administrator", "administrator"),
        ("owner", "administrator"),
        ("recruiter", "employee"),
        ("supervisor", "employee"),
        ("hr_officer", "employee"),
        ("compliance_officer", "employee"),
        ("client_manager", "viewer"),
        ("client_processor", "viewer"),
        ("viewer", "viewer"),
        ("employee", "employee"),
        ("", "viewer"),
    ],
)
def test_normalize_trust_role(raw: str, expected: str) -> None:
    assert normalize_trust_role(raw) == expected


def test_infer_access_context_orthogonal() -> None:
    assert infer_access_context("viewer", "tenant") == "tenant"
    assert infer_access_context("viewer", "portal") == "portal"
    assert infer_access_context("client_manager", None) == "portal"
    assert infer_access_context("recruiter", None) == "tenant"
    assert infer_access_context("viewer", None) == "tenant"


def test_infer_preset_id() -> None:
    assert infer_preset_id("recruiter") == "recruiter"
    assert infer_preset_id("supervisor") == "team_lead"
    assert infer_preset_id("client_processor") == "portal_guest"
    assert infer_preset_id("administrator") is None


def test_expand_allowed_roles_for_trust_employee_bridge() -> None:
    allowed = expand_allowed_roles_for_trust({"recruiter", "supervisor"})
    assert "employee" in allowed
    assert "recruiter" in allowed


def test_matrix_ceiling_locks_administrator_for_tenant_admin() -> None:
    with pytest.raises(ValueError, match="trust_ceiling"):
        assert_matrix_role_editable("administrator", actor_is_superadmin=False)
    assert_matrix_role_editable("employee", actor_is_superadmin=False)
    assert_matrix_role_editable("administrator", actor_is_superadmin=True)
