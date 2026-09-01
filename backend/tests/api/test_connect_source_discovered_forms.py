"""Connect Source — discovered Meta forms in picker + ensure-on-attach."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.acquisition.connect_source_picker import (
    discovered_option_id,
    parse_discovered_form_id,
)
from backend.app.db.session import async_session_maker
from backend.app.models.intake_routing import IntakeSourceBinding, IntakeSourceProfile
from backend.app.models.lead import Lead, MetaLeadFormMapping
from backend.app.models.own_company import OwnCompany
from backend.tests.conftest import _init_data, _set_tenant


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


async def _create_campaign(client: AsyncClient, headers: dict) -> dict:
    resp = await client.post(
        "/api/v1/platform/campaigns",
        headers=headers,
        json={
            "name": f"CS discover {uuid4().hex[:6]}",
            "goal_type": "hiring",
            "primary_kpi": "applications",
            "targets": [],
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _meta_payload(*, form_id: str, ad_id: str, page_id: str = "259905353877064") -> dict:
    return {
        "object": "page",
        "entry": [
            {
                "id": page_id,
                "changes": [
                    {
                        "field": "leadgen",
                        "value": {
                            "ad_id": ad_id,
                            "form_id": form_id,
                            "page_id": page_id,
                            "leadgen_id": str(uuid4().int)[:15],
                            "field_data": [
                                {"name": "full_name", "values": ["Test Person"]},
                                {"name": "phone", "values": ["+48111111111"]},
                            ],
                        },
                    }
                ],
            }
        ],
    }


def test_discovered_option_id_roundtrip() -> None:
    assert parse_discovered_form_id(discovered_option_id("1568360074968045")) == "1568360074968045"
    assert parse_discovered_form_id("uuid-profile") is None


@pytest.mark.asyncio
async def test_intake_source_options_includes_discovered_meta_forms(
    client: AsyncClient, auth_headers: dict, tenant_id: str
) -> None:
    await _init_data()
    own_company_id = await _default_own_company_id(tenant_id)
    headers = {**auth_headers, "X-Own-Company-Id": own_company_id}
    form_id = f"9{uuid4().int % 10**15:015d}"
    ad_id = 120253341522390547
    existing_form = f"1{uuid4().int % 10**15:015d}"

    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        profile_id = str(uuid4())
        session.add(
            IntakeSourceProfile(
                id=profile_id,
                tenant_id=tenant_id,
                code=f"meta-form-{existing_form}",
                name=f"Meta form {existing_form}",
                provider="meta",
                channel="paid",
                own_company_id=own_company_id,
                route_intent="candidate_application",
                is_active=True,
            )
        )
        await session.flush()
        session.add(
            IntakeSourceBinding(
                id=str(uuid4()),
                tenant_id=tenant_id,
                intake_source_profile_id=profile_id,
                provider="meta",
                external_key=f"form_id:{existing_form}",
                external_key_secondary="",
                label=f"Meta form {existing_form}",
                is_active=True,
            )
        )
        session.add(
            Lead(
                id=str(uuid4()),
                tenant_id=tenant_id,
                source="meta",
                status="processed",
                lead_type="candidate",
                lead_target_type="candidate",
                external_id=f"meta-{uuid4().hex[:10]}",
                ad_id=ad_id,
                payload=_meta_payload(form_id=form_id, ad_id=str(ad_id)),
                normalized={"form_id": form_id, "full_name": "Test Person"},
            )
        )
        # Lead for already-profiled form — must not duplicate as discovered
        session.add(
            Lead(
                id=str(uuid4()),
                tenant_id=tenant_id,
                source="meta",
                status="processed",
                lead_type="candidate",
                lead_target_type="candidate",
                external_id=f"meta-{uuid4().hex[:10]}",
                ad_id=ad_id + 1,
                payload=_meta_payload(form_id=existing_form, ad_id=str(ad_id + 1)),
                normalized={"form_id": existing_form},
            )
        )
        await session.commit()

    resp = await client.get(
        "/api/v1/platform/campaigns/intake-source-options",
        headers=headers,
        params={"provider": "meta"},
    )
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    by_form = {str(r.get("meta_form_id") or ""): r for r in rows}
    assert existing_form in by_form
    assert by_form[existing_form]["needs_create"] is False
    assert by_form[existing_form]["id"] == profile_id

    assert form_id in by_form
    discovered = by_form[form_id]
    assert discovered["needs_create"] is True
    assert discovered["id"] == discovered_option_id(form_id)
    assert discovered["provider"] == "meta"
    assert str(ad_id) in (discovered.get("sample_ad_ids") or [])


@pytest.mark.asyncio
async def test_intake_source_options_includes_saved_meta_form_mappings(
    client: AsyncClient, auth_headers: dict, tenant_id: str
) -> None:
    await _init_data()
    own_company_id = await _default_own_company_id(tenant_id)
    headers = {**auth_headers, "X-Own-Company-Id": own_company_id}
    form_id = f"7{uuid4().int % 10**15:015d}"
    page_id = "259905353877064"

    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        session.add(
            MetaLeadFormMapping(
                id=str(uuid4()),
                tenant_id=tenant_id,
                source="meta",
                form_id=form_id,
                page_id=page_id,
                form_name="CE Drivers mapping",
                mapping_rules=[],
            )
        )
        await session.commit()

    resp = await client.get(
        "/api/v1/platform/campaigns/intake-source-options",
        headers=headers,
        params={"provider": "meta"},
    )
    assert resp.status_code == 200, resp.text
    by_form = {str(r.get("meta_form_id") or ""): r for r in resp.json()}
    assert form_id in by_form
    row = by_form[form_id]
    assert row["needs_create"] is True
    assert row["lead_form_name"] == "CE Drivers mapping"
    assert row["page_id"] == page_id


@pytest.mark.asyncio
async def test_intake_source_options_includes_graph_page_forms(
    client: AsyncClient, auth_headers: dict, tenant_id: str, monkeypatch
) -> None:
    await _init_data()
    own_company_id = await _default_own_company_id(tenant_id)
    headers = {**auth_headers, "X-Own-Company-Id": own_company_id}
    form_id = f"6{uuid4().int % 10**15:015d}"

    async def _fake_graph(_db, *, tenant_id: str):  # noqa: ARG001
        return [
            {
                "form_id": form_id,
                "page_id": "111222333",
                "form_name": "Graph CE form",
                "source": "meta",
            }
        ]

    monkeypatch.setattr(
        "backend.app.acquisition.connect_source_picker.discover_leadgen_forms_from_connected_pages",
        _fake_graph,
    )

    resp = await client.get(
        "/api/v1/platform/campaigns/intake-source-options",
        headers=headers,
        params={"provider": "meta"},
    )
    assert resp.status_code == 200, resp.text
    by_form = {str(r.get("meta_form_id") or ""): r for r in resp.json()}
    assert form_id in by_form
    row = by_form[form_id]
    assert row["needs_create"] is True
    assert row["lead_form_name"] == "Graph CE form"
    assert row["page_id"] == "111222333"


@pytest.mark.asyncio
async def test_attach_discovered_meta_form_creates_profile_and_links_flight(
    client: AsyncClient, auth_headers: dict, tenant_id: str
) -> None:
    await _init_data()
    own_company_id = await _default_own_company_id(tenant_id)
    headers = {**auth_headers, "X-Own-Company-Id": own_company_id}
    form_id = f"8{uuid4().int % 10**15:015d}"
    page_id = "259905353877064"
    ad_id = 120253343010880547

    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        session.add(
            Lead(
                id=str(uuid4()),
                tenant_id=tenant_id,
                source="meta",
                status="needs_routing",
                lead_type="candidate",
                lead_target_type="candidate",
                external_id=f"meta-{uuid4().hex[:10]}",
                ad_id=ad_id,
                payload=_meta_payload(form_id=form_id, ad_id=str(ad_id), page_id=page_id),
                normalized={"form_id": form_id},
            )
        )
        await session.commit()

    camp = await _create_campaign(client, headers)
    campaign_id = camp["id"]

    attach = await client.post(
        f"/api/v1/platform/campaigns/{campaign_id}/intake-sources",
        headers=headers,
        json={"meta_form_id": form_id, "page_id": page_id, "role": "primary"},
    )
    assert attach.status_code == 201, attach.text
    body = attach.json()
    flight = next(f for f in body["flights"] if f.get("is_current"))
    links = flight.get("intake_sources") or []
    assert len(links) == 1
    assert links[0].get("meta_form_id") == form_id
    assert links[0].get("provider") == "meta"
    assert links[0].get("code") == f"meta-form-{form_id}"

    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        profile = (
            await session.execute(
                select(IntakeSourceProfile).where(
                    IntakeSourceProfile.tenant_id == tenant_id,
                    IntakeSourceProfile.code == f"meta-form-{form_id}",
                )
            )
        ).scalar_one()
        assert profile.is_active is True
        assert str(profile.own_company_id) == own_company_id
        binding = (
            await session.execute(
                select(IntakeSourceBinding).where(
                    IntakeSourceBinding.tenant_id == tenant_id,
                    IntakeSourceBinding.intake_source_profile_id == profile.id,
                    IntakeSourceBinding.external_key == f"form_id:{form_id}",
                )
            )
        ).scalar_one()
        assert binding.is_active is True

    # Idempotent ensure: second attach with same form should 422 already linked
    again = await client.post(
        f"/api/v1/platform/campaigns/{campaign_id}/intake-sources",
        headers=headers,
        json={"meta_form_id": form_id, "page_id": page_id, "role": "primary"},
    )
    assert again.status_code == 422, again.text

    # Discovered sentinel id also works as input alias
    camp2 = await _create_campaign(client, headers)
    via_sentinel = await client.post(
        f"/api/v1/platform/campaigns/{camp2['id']}/intake-sources",
        headers=headers,
        json={"intake_source_profile_id": discovered_option_id(form_id), "role": "primary"},
    )
    assert via_sentinel.status_code == 201, via_sentinel.text
