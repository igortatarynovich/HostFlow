"""ADR-036: communications feature gates must accept canonical employee."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.app.auth.deps import UserCtx
from backend.app.services.communications_access import assert_comm_feature_access


def _user(
    *,
    role: str,
    jwt_role: str | None = None,
    preset_id: str | None = None,
) -> UserCtx:
    jwt = jwt_role if jwt_role is not None else role
    return UserCtx(
        sub="u1",
        email="recruiter@example.test",
        role=role,
        tenant_id="t1",
        supervisor_id=None,
        raw={"role": jwt, "user_id": "u1"},
        preset_id=preset_id,
    )


def _tenant() -> SimpleNamespace:
    return SimpleNamespace(settings={})


def test_canonical_employee_can_use_messages() -> None:
    assert_comm_feature_access(
        tenant=_tenant(),
        current_user=_user(role="employee", jwt_role="employee", preset_id="recruiter"),
        tenant_id="t1",
        feature="messages",
    )


def test_legacy_recruiter_jwt_remapped_to_employee_can_use_messages() -> None:
    assert_comm_feature_access(
        tenant=_tenant(),
        current_user=_user(role="employee", jwt_role="recruiter", preset_id="recruiter"),
        tenant_id="t1",
        feature="messages",
    )


def test_canonical_employee_cannot_use_communications_admin() -> None:
    with pytest.raises(HTTPException) as exc:
        assert_comm_feature_access(
            tenant=_tenant(),
            current_user=_user(role="employee", jwt_role="employee", preset_id="recruiter"),
            tenant_id="t1",
            feature="communicationsAdmin",
        )
    assert exc.value.status_code == 403


def test_team_lead_employee_can_use_communications_admin() -> None:
    assert_comm_feature_access(
        tenant=_tenant(),
        current_user=_user(role="employee", jwt_role="employee", preset_id="team_lead"),
        tenant_id="t1",
        feature="communicationsAdmin",
    )


def test_legacy_supervisor_jwt_can_use_communications_admin() -> None:
    assert_comm_feature_access(
        tenant=_tenant(),
        current_user=_user(role="employee", jwt_role="supervisor", preset_id="team_lead"),
        tenant_id="t1",
        feature="communicationsAdmin",
    )
