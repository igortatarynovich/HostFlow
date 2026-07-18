"""Forms Sprint 1 — public contract E2E.

publish → endpoint → submission → result (compose Acquisition)

Uses Forms Adapter + Acquisition services. Does not insert Outcome/KPI by Forms.
Builder remains locked.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import inspect, select

from backend.app.acquisition.result_attribution import (
    RESULT_TYPE_INTAKE_LEAD,
    record_result_attribution_from_routing,
)
from backend.app.acquisition.submission_routing import (
    resolve_universal_submission_routing,
    stamp_acquisition_routing_on_lead,
)
from backend.app.db.session import async_session_maker
from backend.app.forms_platform.adapter import (
    ENDPOINT_TYPE_HOSTFLOW_PUBLIC_FORM,
    FORMS_ADAPTER_ID,
    FORMS_PUBLIC_CONTRACT_ID,
    adapter_identity,
    endpoint_from_publication,
    publish,
    result_handoff,
    submission_entry,
)
from backend.app.forms_platform.manifest import builder_is_locked_by_manifest
from backend.app.intake_platform.schemas import EffectivePolicy, SubmissionPolicy
from backend.app.intake_platform.submission_store import append_submission, list_submissions
from backend.app.models.campaign import (
    Campaign,
    CampaignOutcome,
    CampaignResultAttribution,
    CampaignRun,
)
from backend.app.models.lead import Lead
from backend.app.models.own_company import OwnCompany
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.app.models.vacancy import Vacancy
from backend.tests.conftest import _init_data


async def _allow_gate(*_a, **_k):
    return None


async def _default_own_company_id(tenant_id: str) -> str:
    async with async_session_maker() as session:
        row = await session.execute(
            select(OwnCompany.id)
            .where(OwnCompany.tenant_id == tenant_id, OwnCompany.is_archived.is_(False))
            .limit(1)
        )
        oc = row.scalar_one_or_none()
        assert oc
        return str(oc)


def _company_headers(auth_headers: dict, own_company_id: str) -> dict:
    return {**auth_headers, "X-Own-Company-Id": own_company_id}


@pytest.mark.asyncio
async def test_forms_sprint1_publish_endpoint_submission_result(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    monkeypatch.setattr("backend.app.acquisition.campaign_service.enforce_module_gate", _allow_gate)
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _default_own_company_id(tenant_id)

    identity = adapter_identity()
    assert identity["adapter_id"] == FORMS_ADAPTER_ID
    assert identity["contract_id"] == FORMS_PUBLIC_CONTRACT_ID
    assert identity["builder_locked"] is True
    assert builder_is_locked_by_manifest() is True
    assert set(identity["ops"]) == {"publish", "endpoint", "submission", "result"}

    vac_id = str(uuid4())
    form_id = str(uuid4())
    slug = f"fs1-{form_id[:8]}"
    async with async_session_maker() as session:
        session.add(
            Vacancy(
                id=vac_id,
                tenant_id=tenant_id,
                own_company_id=oc,
                company_id=data["company_id"],
                title="Forms Sprint 1",
                status="open",
                is_active=True,
                is_archived=False,
            )
        )
        session.add(
            TenantLeadForm(
                id=form_id,
                tenant_id=tenant_id,
                title="Sprint 1 Form",
                public_slug=slug,
                is_active=True,
                lifecycle_status="active",
                purpose="inquiry",
            )
        )
        await session.commit()

    # --- publish (Forms Adapter) ---
    async with async_session_maker() as session:
        publication = await publish(session, tenant_id=tenant_id, form_id=form_id)
        assert publication is not None
        assert publication["publication_id"] == form_id
        assert publication["public_slug"] == slug
        assert publication["is_active"] is True

        # --- endpoint ---
        endpoint = endpoint_from_publication(publication)
        assert endpoint.endpoint_type == ENDPOINT_TYPE_HOSTFLOW_PUBLIC_FORM
        assert endpoint.form_id == form_id
        assert endpoint.public_intake_path == "/api/v1/public/intake"

        # --- submission entry ---
        sub_entry = submission_entry(publication)
        assert sub_entry["forms_role"] == "submission_surface"
        assert sub_entry["builder_locked"] is True
        assert sub_entry["public_intake_path"] == endpoint.public_intake_path
        assert sub_entry["submission_handler"]["handler_id"]

    # --- Campaign + bind Form as Endpoint specialization (Acquisition compose) ---
    resp = await client.post(
        "/api/v1/platform/campaigns",
        headers=_company_headers(auth_headers, oc),
        json={
            "name": "Forms Sprint 1 compose",
            "goal_type": "hiring",
            "primary_kpi": "applications",
            "targets": [
                {
                    "target_type": "vacancy",
                    "target_id": vac_id,
                    "route_intent": "candidate_application",
                    "role": "primary",
                }
            ],
        },
    )
    assert resp.status_code == 201, resp.text
    campaign = resp.json()
    campaign_id = campaign["id"]
    flight_id = campaign["flights"][0]["id"]

    async with async_session_maker() as session:
        camp = await session.get(Campaign, campaign_id)
        flight = await session.get(CampaignRun, flight_id)
        assert camp and flight
        camp.status = "active"
        flight.status = "active"
        await session.commit()

    bind = await client.post(
        f"/api/v1/platform/campaigns/{campaign_id}/forms",
        headers=_company_headers(auth_headers, oc),
        json={"form_id": form_id, "role": "primary"},
    )
    assert bind.status_code == 201, bind.text

    # --- submission → result attribution via Acquisition (not Forms insert) ---
    lead_id = str(uuid4())
    async with async_session_maker() as session:
        decision = await resolve_universal_submission_routing(
            session,
            tenant_id=tenant_id,
            form_id=form_id,
            intake_source_profile_id=None,
        )
        assert decision.status == "routed"
        assert decision.form_id == form_id

        lead = Lead(
            id=lead_id,
            tenant_id=tenant_id,
            status="new",
            stage="questionnaire_submitted",
            normalized={},
            payload={},
        )
        stamp_acquisition_routing_on_lead(lead, decision)
        session.add(lead)
        await session.flush()

        policy = EffectivePolicy(
            purpose="inquiry",
            target_entity_profile_code="candidate",
            submission_policy=SubmissionPolicy(mode="create"),
            form_id=form_id,
            published_version=1,
            source={"endpoint_type": ENDPOINT_TYPE_HOSTFLOW_PUBLIC_FORM},
        )
        submission = await append_submission(
            session,
            tenant_id=tenant_id,
            lead_id=lead_id,
            effective_policy=policy,
            normalized_values={"email": "forms-sprint1@example.com"},
            entry_context={"acquisition_routing_v1": decision.to_dict()},
            idempotency_key=f"fs1-{lead_id}",
        )
        submission_id = str(submission["submission_id"])
        assert list_submissions(lead)

        attribution = await record_result_attribution_from_routing(
            session,
            tenant_id=tenant_id,
            lead=lead,
            submission_id=submission_id,
            result_type=RESULT_TYPE_INTAKE_LEAD,
            result_id=lead_id,
        )
        assert attribution.endpoint_form_id == form_id
        assert attribution.submission_id == submission_id
        await session.commit()

    handoff = result_handoff(submission_id=submission_id)
    assert handoff["result_owner"] == "destination_module_via_decision"
    assert "forms_owned_outcome" in handoff["forbidden"]
    assert "forms_builder" in handoff["forbidden"]
    assert FORMS_ADAPTER_ID == handoff["adapter_id"]

    # Forms does not own Outcome / Operations FKs on attribution model
    attr_cols = {c.key for c in inspect(CampaignResultAttribution).columns}
    assert "application_id" not in attr_cols
    assert "inquiry_id" not in attr_cols
    outcome_cols = {c.key for c in inspect(CampaignOutcome).columns}
    assert "forms_outcome_id" not in outcome_cols


@pytest.mark.asyncio
async def test_forms_sprint1_publish_via_platform_api(
    client: AsyncClient, auth_headers: dict, monkeypatch
):
    """HTTP resolve remains the read surface for publish."""
    monkeypatch.setattr(
        "backend.app.services.intake_form_write_service.ensure_lead_source_limit",
        _allow_gate,
    )

    async def _zero(*_a, **_k):
        return 0

    monkeypatch.setattr(
        "backend.app.services.intake_form_write_service.count_tenant_lead_sources",
        _zero,
    )
    monkeypatch.setattr(
        "backend.app.services.intake_form_write_service.ensure_tenant_lead_form_active_count_allows_transition",
        _allow_gate,
    )

    data = await _init_data()
    tenant_id = data["tenant_id"]
    from backend.tests.api.test_intake_forms_settings import _admin_headers
    from backend.tests.api.test_intake_forms_settings_p8 import _seed_entity_profiles
    from backend.app.entity_profile.constants import WAREHOUSE_WORKER_PROFILE_CODE

    await _seed_entity_profiles(tenant_id)
    headers = await _admin_headers(tenant_id)
    slug = f"fs1-api-{uuid4().hex[:8]}"
    created = await client.post(
        "/api/v1/settings/intake-forms",
        headers=headers,
        json={
            "title": "Sprint 1 API Form",
            "public_slug": slug,
            "entity_profile_code": WAREHOUSE_WORKER_PROFILE_CODE,
            "fields": [
                {"qualified_code": "recruitment.candidate.first_name", "intake_level": "required"},
                {"qualified_code": "recruitment.candidate.last_name", "intake_level": "required"},
                {"qualified_code": "recruitment.candidate.contacts.phone", "intake_level": "required"},
            ],
        },
    )
    assert created.status_code == 200, created.text
    form_id = created.json()["form"]["id"]

    resp = await client.get(
        "/api/v1/platform/forms/publications/resolve",
        headers=headers,
        params={"form_id": form_id},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    endpoint = endpoint_from_publication(body)
    assert endpoint.endpoint_type == ENDPOINT_TYPE_HOSTFLOW_PUBLIC_FORM
    assert submission_entry(body)["builder_locked"] is True
