"""ADR-035: fire_candidate_system_transition wires real Employee / client handoff."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from backend.app.constants import system_transitions as st
from backend.app.services.system_transition_runtime import fire_candidate_system_transition


def _candidate(**kwargs):
    base = {
        "id": "cand-1",
        "tenant_id": "ten-1",
        "company_id": "co-1",
        "stage": "accepted",
        "lifecycle_status": "active",
        "extra": "{}",
        "note": None,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_handoff_to_hr_calls_handoff_from_candidate():
    cand = _candidate()
    emp = SimpleNamespace(id="emp-1")
    db = MagicMock()

    with patch(
        "backend.app.services.workforce_employees.handoff_from_candidate",
        new_callable=AsyncMock,
        return_value=emp,
    ) as mock_ho:
        result = await fire_candidate_system_transition(
            db,
            candidate=cand,
            catalog_key=st.HANDOFF_TO_HR,
            tenant_id="ten-1",
            actor_user_id="user-1",
            enabled_modules={"recruitment", "hr"},
        )

    mock_ho.assert_awaited_once()
    assert result["employee_id"] == "emp-1"
    assert cand.lifecycle_status == st.LIFECYCLE_CLOSED


@pytest.mark.asyncio
async def test_handoff_to_hr_requires_hr_module():
    cand = _candidate()
    with pytest.raises(HTTPException) as ei:
        await fire_candidate_system_transition(
            MagicMock(),
            candidate=cand,
            catalog_key=st.HANDOFF_TO_HR,
            tenant_id="ten-1",
            actor_user_id="user-1",
            enabled_modules={"recruitment"},
        )
    assert ei.value.status_code == 422


@pytest.mark.asyncio
async def test_handoff_to_client_does_not_create_employee():
    cand = _candidate()
    handoff = SimpleNamespace(id="ho-1")
    db = MagicMock()

    with patch(
        "backend.app.services.handoff.create_handoff",
        new_callable=AsyncMock,
        return_value=(handoff, None),
    ) as mock_ch:
        with patch(
            "backend.app.services.workforce_employees.handoff_from_candidate",
            new_callable=AsyncMock,
        ) as mock_emp:
            result = await fire_candidate_system_transition(
                db,
                candidate=cand,
                catalog_key=st.HANDOFF_TO_CLIENT,
                tenant_id="ten-1",
                actor_user_id="user-1",
                enabled_modules={"recruitment"},
            )

    mock_emp.assert_not_called()
    mock_ch.assert_awaited_once()
    assert result["employee_id"] is None
    assert result["handoff_id"] == "ho-1"
    assert cand.lifecycle_status == st.LIFECYCLE_CLOSED


@pytest.mark.asyncio
async def test_close_declined_sets_rejected_stage():
    cand = _candidate(stage="accepted")
    result = await fire_candidate_system_transition(
        MagicMock(),
        candidate=cand,
        catalog_key=st.CLOSE_DECLINED,
        tenant_id="ten-1",
        actor_user_id="user-1",
        enabled_modules={"recruitment"},
    )
    assert cand.stage == "rejected"
    assert cand.lifecycle_status == st.LIFECYCLE_CLOSED
    assert result["employee_id"] is None


@pytest.mark.asyncio
async def test_closed_candidate_cannot_fire_again():
    cand = _candidate(lifecycle_status="closed")
    with pytest.raises(HTTPException) as ei:
        await fire_candidate_system_transition(
            MagicMock(),
            candidate=cand,
            catalog_key=st.CLOSE_SUCCESS,
            tenant_id="ten-1",
            actor_user_id="user-1",
            enabled_modules={"recruitment"},
        )
    assert ei.value.status_code == 409
