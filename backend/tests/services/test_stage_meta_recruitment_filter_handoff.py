"""Agency handoff stage-change gate respects vacancy funnel SoT + kill-switch."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from backend.app.constants.stages import RECRUITMENT_HANDOFF_HIDDEN_STAGE_CODES
from backend.app.services import stage_meta_recruitment_filter as mod
from backend.app.services.hiring_pipeline_gates import merge_hiring_pipeline_gates


@pytest.mark.anyio
async def test_recruitment_blocked_on_hidden_stage_when_enforcement_on(monkeypatch: pytest.MonkeyPatch) -> None:
    gates = merge_hiring_pipeline_gates({"enforce_requirement_stage_blocks": True})
    monkeypatch.setattr(mod, "is_client_tenant", AsyncMock(return_value=False))
    monkeypatch.setattr(mod, "list_links_for_agency", AsyncMock(return_value=[SimpleNamespace(get_handoff_enabled=lambda: True)]))
    monkeypatch.setattr(
        "backend.app.services.hiring_pipeline_gates.resolve_hiring_pipeline_gates",
        AsyncMock(return_value=gates),
    )

    user = SimpleNamespace(tenant_id="t1", role="employee")
    with pytest.raises(HTTPException) as ei:
        await mod.enforce_agency_handoff_stage_change_allowed(
            MagicMock(),
            tenant_id="t1",
            user=user,  # type: ignore[arg-type]
            new_stage_code="permit_ordered",
        )
    assert ei.value.status_code == 403


@pytest.mark.anyio
async def test_recruitment_allowed_when_stage_on_vacancy_funnel(monkeypatch: pytest.MonkeyPatch) -> None:
    gates = merge_hiring_pipeline_gates({"enforce_requirement_stage_blocks": True})
    monkeypatch.setattr(mod, "is_client_tenant", AsyncMock(return_value=False))
    monkeypatch.setattr(mod, "list_links_for_agency", AsyncMock(return_value=[SimpleNamespace(get_handoff_enabled=lambda: True)]))
    monkeypatch.setattr(
        "backend.app.services.hiring_pipeline_gates.resolve_hiring_pipeline_gates",
        AsyncMock(return_value=gates),
    )

    assert "permit_ordered" in RECRUITMENT_HANDOFF_HIDDEN_STAGE_CODES
    user = SimpleNamespace(tenant_id="t1", role="employee")
    await mod.enforce_agency_handoff_stage_change_allowed(
        MagicMock(),
        tenant_id="t1",
        user=user,  # type: ignore[arg-type]
        new_stage_code="permit_ordered",
        funnel_stage_codes={"docs_got", "permit_ordered", "employed"},
    )


@pytest.mark.anyio
async def test_recruitment_allowed_when_kill_switch_off(monkeypatch: pytest.MonkeyPatch) -> None:
    gates = merge_hiring_pipeline_gates({"enforce_requirement_stage_blocks": False})
    monkeypatch.setattr(mod, "is_client_tenant", AsyncMock(return_value=False))
    monkeypatch.setattr(
        "backend.app.services.hiring_pipeline_gates.resolve_hiring_pipeline_gates",
        AsyncMock(return_value=gates),
    )
    # Would fail if links were consulted; kill-switch returns before.
    monkeypatch.setattr(mod, "list_links_for_agency", AsyncMock(side_effect=AssertionError("should not list links")))

    user = SimpleNamespace(tenant_id="t1", role="employee")
    await mod.enforce_agency_handoff_stage_change_allowed(
        MagicMock(),
        tenant_id="t1",
        user=user,  # type: ignore[arg-type]
        new_stage_code="employed",
    )
