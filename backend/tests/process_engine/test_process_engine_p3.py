"""Process Engine P3 — vacancy profile binding and resolution order."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend.app.models.process_engine import PLATFORM_TENANT_SCOPE, REGISTRY_STATUS_ACTIVE
from backend.app.process_engine.constants import RECRUITMENT_MODULE
from backend.app.process_engine.evaluator_adapter import TransitionEvaluatorAdapter
from backend.app.process_engine.manifests.recruitment import DEFAULT_PROFILE_CODE
from backend.app.process_engine.profile_resolver import (
    EffectiveProcessProfile,
    resolve_effective_process_profile,
    resolve_effective_process_profile_for_candidate,
)
from backend.app.process_engine import profile_resolver as resolver_module


def _profile(
    profile_id: str,
    *,
    code: str,
    tenant_id: str = "tenant-1",
    is_default: bool = False,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=profile_id,
        code=code,
        tenant_id=tenant_id,
        module=RECRUITMENT_MODULE,
        status=REGISTRY_STATUS_ACTIVE,
        is_default=is_default,
    )


@pytest.mark.anyio
async def test_p3_vacancy_explicit_profile_wins_over_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    vacancy_profile = _profile("pe-vacancy", code="vacancy_custom")
    tenant_default = _profile("pe-tenant", code=DEFAULT_PROFILE_CODE, is_default=True)
    system_default = _profile("pe-system", code=DEFAULT_PROFILE_CODE, tenant_id=PLATFORM_TENANT_SCOPE)

    monkeypatch.setattr(
        resolver_module,
        "_load_active_process_profile",
        AsyncMock(return_value=vacancy_profile),
    )
    monkeypatch.setattr(
        resolver_module,
        "resolve_process_profile_for_candidate_profile",
        AsyncMock(return_value=tenant_default),
    )
    monkeypatch.setattr(
        resolver_module.ProcessEngineRegistry,
        "get_default_process_profile",
        AsyncMock(return_value=tenant_default),
    )
    monkeypatch.setattr(
        resolver_module,
        "_resolve_system_default_process_profile",
        AsyncMock(return_value=system_default),
    )

    vacancy = SimpleNamespace(
        pe_process_profile_id="pe-vacancy",
        candidate_profile_id=None,
    )
    resolved = await resolve_effective_process_profile(
        db=None,  # type: ignore[arg-type]
        tenant_id="tenant-1",
        vacancy=vacancy,
    )

    assert resolved is not None
    assert resolved.source == "vacancy"
    assert resolved.profile_id == "pe-vacancy"


@pytest.mark.anyio
async def test_p3_legacy_candidate_profile_bridge_before_tenant_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    legacy_profile = _profile("pe-legacy", code="driver_ce_default")
    tenant_default = _profile("pe-tenant", code=DEFAULT_PROFILE_CODE, is_default=True)

    monkeypatch.setattr(
        resolver_module,
        "_load_active_process_profile",
        AsyncMock(return_value=None),
    )
    legacy_mock = AsyncMock(return_value=legacy_profile)
    monkeypatch.setattr(resolver_module, "resolve_process_profile_for_candidate_profile", legacy_mock)
    tenant_mock = AsyncMock(return_value=tenant_default)
    monkeypatch.setattr(resolver_module.ProcessEngineRegistry, "get_default_process_profile", tenant_mock)

    vacancy = SimpleNamespace(
        pe_process_profile_id=None,
        candidate_profile_id="cp-legacy",
    )
    resolved = await resolve_effective_process_profile(
        db=None,  # type: ignore[arg-type]
        tenant_id="tenant-1",
        vacancy=vacancy,
    )

    assert resolved is not None
    assert resolved.source == "legacy_candidate_profile"
    assert resolved.profile_id == "pe-legacy"
    legacy_mock.assert_awaited_once()
    tenant_mock.assert_not_awaited()


@pytest.mark.anyio
async def test_p3_tenant_default_before_system_default(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_default = _profile("pe-tenant", code=DEFAULT_PROFILE_CODE, is_default=True)
    system_default = _profile("pe-system", code=DEFAULT_PROFILE_CODE, tenant_id=PLATFORM_TENANT_SCOPE)

    monkeypatch.setattr(
        resolver_module,
        "_load_active_process_profile",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        resolver_module,
        "resolve_process_profile_for_candidate_profile",
        AsyncMock(return_value=None),
    )
    tenant_mock = AsyncMock(return_value=tenant_default)
    monkeypatch.setattr(resolver_module.ProcessEngineRegistry, "get_default_process_profile", tenant_mock)
    system_mock = AsyncMock(return_value=system_default)
    monkeypatch.setattr(resolver_module, "_resolve_system_default_process_profile", system_mock)

    resolved = await resolve_effective_process_profile(
        db=None,  # type: ignore[arg-type]
        tenant_id="tenant-1",
        vacancy=None,
    )

    assert resolved is not None
    assert resolved.source == "tenant_default"
    assert resolved.profile_id == "pe-tenant"
    system_mock.assert_not_awaited()


@pytest.mark.anyio
async def test_p3_system_default_when_tenant_default_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    system_default = _profile("pe-system", code=DEFAULT_PROFILE_CODE, tenant_id=PLATFORM_TENANT_SCOPE)

    monkeypatch.setattr(
        resolver_module,
        "_load_active_process_profile",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        resolver_module,
        "resolve_process_profile_for_candidate_profile",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        resolver_module.ProcessEngineRegistry,
        "get_default_process_profile",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        resolver_module,
        "_resolve_system_default_process_profile",
        AsyncMock(return_value=system_default),
    )

    resolved = await resolve_effective_process_profile(
        db=None,  # type: ignore[arg-type]
        tenant_id="tenant-1",
        vacancy=None,
    )

    assert resolved is not None
    assert resolved.source == "system_default"
    assert resolved.profile_code == DEFAULT_PROFILE_CODE


@pytest.mark.anyio
async def test_p3_candidate_inherits_vacancy_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    vacancy_profile = _profile("pe-vacancy", code="vacancy_custom")
    expected = EffectiveProcessProfile(profile=vacancy_profile, source="vacancy")  # type: ignore[arg-type]

    class _Result:
        def scalar_one_or_none(self):
            return SimpleNamespace(
                id="vac-1",
                tenant_id="tenant-1",
                pe_process_profile_id="pe-vacancy",
                candidate_profile_id=None,
            )

    db = SimpleNamespace(execute=AsyncMock(return_value=_Result()))
    resolve_mock = AsyncMock(return_value=expected)
    monkeypatch.setattr(resolver_module, "resolve_effective_process_profile", resolve_mock)

    candidate = SimpleNamespace(vacancy_id="vac-1")
    resolved = await resolve_effective_process_profile_for_candidate(
        db,  # type: ignore[arg-type]
        tenant_id="tenant-1",
        candidate=candidate,
    )

    assert resolved is expected
    resolve_mock.assert_awaited_once()
    _, kwargs = resolve_mock.await_args
    assert kwargs["vacancy"].pe_process_profile_id == "pe-vacancy"


@pytest.mark.anyio
async def test_p3_adapter_exposes_effective_profile_for_stage_logic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = _profile("pe-tenant", code=DEFAULT_PROFILE_CODE, is_default=True)
    resolved = EffectiveProcessProfile(profile=profile, source="tenant_default")  # type: ignore[arg-type]
    monkeypatch.setattr(
        "backend.app.process_engine.evaluator_adapter.resolve_effective_process_profile_for_candidate_id",
        AsyncMock(return_value=resolved),
    )

    out = await TransitionEvaluatorAdapter.resolve_effective_process_profile_for_candidate_id(
        db=None,  # type: ignore[arg-type]
        tenant_id="tenant-1",
        candidate_id="cand-1",
    )

    assert out == {
        "process_profile_id": "pe-tenant",
        "process_profile_code": DEFAULT_PROFILE_CODE,
        "process_profile_source": "tenant_default",
        "module": RECRUITMENT_MODULE,
    }


def test_p3_vacancy_model_has_process_profile_column() -> None:
    from backend.app.models.vacancy import Vacancy

    assert hasattr(Vacancy, "pe_process_profile_id")


def test_p3_candidates_service_uses_adapter_for_effective_profile() -> None:
    from pathlib import Path

    source = Path("backend/app/api/v1/candidates/service.py").read_text(encoding="utf-8")
    assert "resolve_effective_process_profile_for_candidate_id" in source
    assert "TransferPolicyResolver" not in source
