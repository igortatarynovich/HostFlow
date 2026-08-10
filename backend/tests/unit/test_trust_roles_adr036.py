"""Unit tests for ADR-036 trust role helpers."""

from __future__ import annotations

import pytest

from backend.app.auth.trust_roles import (
    actor_satisfies_role_allowlist,
    assert_matrix_role_editable,
    expand_allowed_roles_for_trust,
    infer_access_context,
    infer_preset_id,
    is_hr_workspace_actor,
    is_team_lead_org_actor,
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


def test_resolve_preset_id_prefers_preferences() -> None:
    from backend.app.auth.trust_roles import resolve_preset_id

    assert resolve_preset_id("employee", preferences={"preset_id": "hr"}) == "hr"
    assert resolve_preset_id("recruiter") == "recruiter"
    assert resolve_preset_id("employee", explicit="team_lead") == "team_lead"


def test_is_hr_workspace_actor_with_preset() -> None:
    assert is_hr_workspace_actor("employee", preferences={"preset_id": "hr"})
    assert not is_hr_workspace_actor("employee", preferences={"preset_id": "recruiter"})
    assert is_hr_workspace_actor("hr_officer")


def test_expand_allowed_roles_for_trust_employee_bridge() -> None:
    allowed = expand_allowed_roles_for_trust({"recruiter", "supervisor"})
    assert "employee" in allowed
    assert "recruiter" in allowed


def test_actor_satisfies_employee_on_job_proxy_allowlist() -> None:
    assert actor_satisfies_role_allowlist(
        role="employee",
        allowed={"recruiter", "supervisor"},
    )
    assert actor_satisfies_role_allowlist(
        role="recruiter",
        allowed={"recruiter"},
    )
    assert not actor_satisfies_role_allowlist(
        role="viewer",
        allowed={"recruiter"},
        access_context="tenant",
    )


def test_actor_satisfies_portal_viewer_bridge() -> None:
    assert actor_satisfies_role_allowlist(
        role="viewer",
        allowed={"client_manager", "client_processor"},
        access_context="portal",
    )
    assert not actor_satisfies_role_allowlist(
        role="viewer",
        allowed={"client_manager"},
        access_context="tenant",
    )
    assert actor_satisfies_role_allowlist(
        role="client_manager",
        allowed={"client_manager"},
        access_context=None,
    )
    # Explicit viewer allowlist accepts legacy portal roles via trust normalize
    assert actor_satisfies_role_allowlist(
        role="client_manager",
        allowed={"administrator", "employee", "viewer"},
        access_context=None,
    )


def test_hr_and_team_lead_helpers() -> None:
    assert is_hr_workspace_actor("hr_officer")
    assert not is_hr_workspace_actor("employee")
    assert is_team_lead_org_actor("supervisor")
    assert not is_team_lead_org_actor("recruiter")


def test_permission_preset_helpers() -> None:
    from backend.app.auth.trust_roles import (
        get_permission_preset,
        list_permission_preset_ids,
        trust_role_for_preset,
    )

    assert "recruiter" in list_permission_preset_ids()
    assert trust_role_for_preset("recruiter") == "employee"
    assert trust_role_for_preset("portal_guest") == "viewer"
    assert get_permission_preset("hr")["hr"]["editable"] is True


def test_normalize_assignable_role_coerces_legacy() -> None:
    from backend.app.services.users import _normalize_assignable_role

    assert _normalize_assignable_role("recruiter") == ("employee", "recruiter")
    assert _normalize_assignable_role("employee", preset_id="hr") == ("employee", "hr")
    assert _normalize_assignable_role("client_processor")[0] == "viewer"


def test_matrix_ceiling_locks_administrator_for_tenant_admin() -> None:
    with pytest.raises(ValueError, match="trust_ceiling"):
        assert_matrix_role_editable("administrator", actor_is_superadmin=False)
    assert_matrix_role_editable("employee", actor_is_superadmin=False)
    assert_matrix_role_editable("administrator", actor_is_superadmin=True)


def test_billable_seat_buckets_and_portal_non_billable() -> None:
    from backend.app.auth.trust_roles import (
        billable_seat_bucket,
        seat_quota_attr_for_role,
    )

    assert billable_seat_bucket("administrator") == "administrator"
    assert billable_seat_bucket("recruiter") == "employee"
    assert billable_seat_bucket("employee") == "employee"
    assert billable_seat_bucket("viewer") == "viewer"
    assert billable_seat_bucket("client_manager") is None
    assert billable_seat_bucket("viewer", access_context="portal") is None
    assert billable_seat_bucket("viewer", preset_id="portal_guest") is None
    assert seat_quota_attr_for_role("employee") == "max_recruiters"
    assert seat_quota_attr_for_role("administrator") == "max_supervisors"
    assert seat_quota_attr_for_role("viewer") == "max_viewers"
    assert seat_quota_attr_for_role("client_processor") is None
