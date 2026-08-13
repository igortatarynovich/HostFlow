"""B2B appeal call-result disposition + note (normalized.call_result_v1)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from sqlalchemy import select, text

from backend.app.db.session import async_session_maker
from backend.app.models import Lead, OwnCompany
from backend.app.modules.leads import crud as leads_crud
from backend.app.modules.leads.schemas import LeadCallResultIn
from backend.app.modules.leads.service.call_result import apply_lead_call_result


def test_lead_call_result_schema_accepts_callback_and_note() -> None:
    payload = LeadCallResultIn(
        result="callback_requested",
        note="Перезвонить завтра после 15:00, спрашивает про ставку",
    )
    assert payload.result == "callback_requested"
    assert "перезвонить" in payload.note.lower()


def test_lead_call_result_schema_rejects_unknown() -> None:
    with pytest.raises(ValidationError):
        LeadCallResultIn(result="maybe_later")  # type: ignore[arg-type]


def test_apply_lead_call_result_appends_history() -> None:
    lead = SimpleNamespace(normalized={})
    first = apply_lead_call_result(
        lead,  # type: ignore[arg-type]
        result="no_answer",
        note=None,
        actor_sub="u1",
    )
    assert first["result"] == "no_answer"
    assert lead.normalized["call_result_v1"]["result"] == "no_answer"

    second = apply_lead_call_result(
        lead,  # type: ignore[arg-type]
        result="callback_requested",
        note="Думает, перезвонить в пятницу",
        actor_sub="u1",
    )
    assert second["note"] == "Думает, перезвонить в пятницу"
    history = lead.normalized["call_results_v1"]
    assert len(history) == 2
    assert history[-1]["result"] == "callback_requested"
    assert lead.normalized["call_result_v1"]["result"] == "callback_requested"


@pytest.mark.anyio
async def test_post_call_result_on_client_lead(client, manager_headers, tenant_id, monkeypatch):
    async with async_session_maker() as db:
        await db.execute(
            text("SELECT set_config('app.tenant_id', :tenant_id, false)"),
            {"tenant_id": str(tenant_id)},
        )
        own_company_id = await db.scalar(
            select(OwnCompany.id)
            .where(OwnCompany.tenant_id == str(tenant_id), OwnCompany.is_archived.is_(False))
            .order_by(OwnCompany.created_at.asc())
            .limit(1)
        )
        assert own_company_id is not None
        lead = await leads_crud.create_lead(
            db,
            tenant_id=str(tenant_id),
            own_company_id=str(own_company_id),
            company_id=None,
            vacancy_id=None,
            payload={"company": {"name": "B2B Call Co"}},
            normalized={
                "company_profile": {"name": "B2B Call Co"},
                "contact_person": {"full_name": "Anna", "phone": "+48111111111"},
                "rodo": {"sent": True},
            },
            source="company_intake_form",
            lead_type="client",
            lead_target_type="client_lead",
        )
        lead.status = "processed"
        lead.stage = "new"
        lead_id = str(lead.id)
        await db.commit()

    async def _rodo_ok(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "backend.app.services.lead_rodo.ensure_lead_rodo_allows_action",
        _rodo_ok,
    )

    note = "Перезвонить завтра 15:00, интересует ставка"
    r = await client.post(
        f"/api/v1/leads/{lead_id}/call-result",
        headers=manager_headers,
        json={"result": "callback_requested", "note": note},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["stage"] == "contacted"
    norm = body.get("normalized") or {}
    assert norm.get("call_result_v1", {}).get("result") == "callback_requested"
    assert norm.get("call_result_v1", {}).get("note") == note
    assert isinstance(norm.get("call_results_v1"), list)
    assert len(norm["call_results_v1"]) >= 1

    async with async_session_maker() as db:
        await db.execute(
            text("SELECT set_config('app.tenant_id', :tenant_id, false)"),
            {"tenant_id": str(tenant_id)},
        )
        row = (await db.execute(select(Lead).where(Lead.id == lead_id))).scalar_one()
        stored = row.normalized or {}
        assert stored.get("call_result_v1", {}).get("note") == note


@pytest.mark.anyio
async def test_post_call_result_on_terminal_client_lead_keeps_stage(
    client, manager_headers, tenant_id, monkeypatch
):
    """Rejected/lost client leads may still receive call comments (no stage revive)."""
    async with async_session_maker() as db:
        await db.execute(
            text("SELECT set_config('app.tenant_id', :tenant_id, false)"),
            {"tenant_id": str(tenant_id)},
        )
        own_company_id = await db.scalar(
            select(OwnCompany.id)
            .where(OwnCompany.tenant_id == str(tenant_id), OwnCompany.is_archived.is_(False))
            .order_by(OwnCompany.created_at.asc())
            .limit(1)
        )
        assert own_company_id is not None
        lead = await leads_crud.create_lead(
            db,
            tenant_id=str(tenant_id),
            own_company_id=str(own_company_id),
            company_id=None,
            vacancy_id=None,
            payload={"company": {"name": "Closed B2B Co"}},
            normalized={
                "company_profile": {"name": "Closed B2B Co"},
                "contact_person": {"full_name": "Ola", "phone": "+48222222222"},
                "rodo": {"sent": True},
            },
            source="company_intake_form",
            lead_type="client",
            lead_target_type="client_lead",
        )
        lead.status = "rejected"
        lead.stage = "lost"
        lead_id = str(lead.id)
        await db.commit()

    async def _rodo_ok(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "backend.app.services.lead_rodo.ensure_lead_rodo_allows_action",
        _rodo_ok,
    )

    note = "Повторный звонок — всё ещё не интересно"
    r = await client.post(
        f"/api/v1/leads/{lead_id}/call-result",
        headers=manager_headers,
        json={"result": "not_interested", "note": note},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["stage"] == "lost"
    norm = body.get("normalized") or {}
    assert norm.get("call_result_v1", {}).get("result") == "not_interested"
    assert norm.get("call_result_v1", {}).get("note") == note
