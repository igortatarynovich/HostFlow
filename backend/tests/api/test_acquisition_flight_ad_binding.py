"""Meta Ad ID → Flight binding runtime (Acquisition cutover contract)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.acquisition.flight_ad_binding import MISSING_CAMPAIGN_FLIGHT
from backend.app.acquisition.submission_routing import (
    RoutingSource,
    UnresolvedReason,
    resolve_universal_submission_routing,
)
from backend.app.db.session import async_session_maker
from backend.app.models.campaign import (
    Campaign,
    CampaignRun,
    CampaignRunForm,
    CampaignRunIntakeSource,
    CampaignTarget,
    FlightAdBinding,
)
from backend.app.models.intake_routing import IntakeSourceProfile
from backend.app.models.lead import Lead
from backend.app.models.own_company import OwnCompany
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.app.models.company import Company
from backend.app.models.vacancy import Vacancy
from backend.tests.conftest import _init_data

DEFAULT_TENANT_ID = "11111111-1111-1111-1111-111111111111"


async def _own_company_id(tenant_id: str) -> str:
    async with async_session_maker() as session:
        row = await session.execute(
            select(OwnCompany.id)
            .where(OwnCompany.tenant_id == tenant_id, OwnCompany.is_archived.is_(False))
            .limit(1)
        )
        oc = row.scalar_one_or_none()
        assert oc
        return str(oc)


async def _company_id(tenant_id: str) -> str:
    async with async_session_maker() as session:
        row = await session.execute(
            select(Company.id).where(Company.tenant_id == tenant_id).limit(1)
        )
        cid = row.scalar_one_or_none()
        assert cid
        return str(cid)


async def _seed_campaign_flight(
    *,
    tenant_id: str,
    own_company_id: str,
    vacancy_id: str | None = None,
    campaign_status: str = "active",
    flight_status: str = "active",
) -> tuple[str, str]:
    async with async_session_maker() as session:
        campaign = Campaign(
            id=str(uuid4()),
            tenant_id=tenant_id,
            own_company_id=own_company_id,
            name=f"AdBind Camp {uuid4().hex[:6]}",
            status=campaign_status,
            goal_type="hiring",
            primary_kpi="applications",
        )
        session.add(campaign)
        await session.flush()
        flight = CampaignRun(
            id=str(uuid4()),
            tenant_id=tenant_id,
            campaign_id=campaign.id,
            name="Flight Ad",
            status=flight_status,
            code=f"f-{uuid4().hex[:6]}",
        )
        session.add(flight)
        await session.flush()
        campaign.current_flight_id = flight.id
        if vacancy_id:
            session.add(
                CampaignTarget(
                    id=str(uuid4()),
                    tenant_id=tenant_id,
                    campaign_id=campaign.id,
                    target_type="vacancy",
                    target_id=str(vacancy_id),
                    target_module="recruitment",
                    route_intent="candidate_application",
                    role="primary",
                    sort_order=0,
                )
            )
        await session.commit()
        return str(campaign.id), str(flight.id)


@pytest.mark.anyio
async def test_meta_ad_without_binding_is_missing_campaign_flight_no_profile_default():
    """No Ad bind and no Connect Source Flight → unresolved; never profile_default."""
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _own_company_id(tenant_id)
    async with async_session_maker() as session:
        profile = IntakeSourceProfile(
            id=str(uuid4()),
            tenant_id=tenant_id,
            code=f"ad-prof-{uuid4().hex[:6]}",
            name="Profile",
            provider="meta",
            channel="paid",
            own_company_id=oc,
            route_intent="candidate_application",
            mapping_rules=[{"source": "email", "target": "email"}],
            is_active=True,
        )
        session.add(profile)
        await session.commit()
        pid = str(profile.id)

        decision = await resolve_universal_submission_routing(
            session,
            tenant_id=tenant_id,
            intake_source_profile_id=pid,
            form_id=None,
            provider="meta",
            provider_ad_id="998877001",
        )
    assert decision.status == "unresolved"
    assert decision.unresolved_reason == UnresolvedReason.missing_campaign_flight.value
    assert decision.source != RoutingSource.profile_default.value


@pytest.mark.anyio
async def test_meta_ad_without_binding_uses_connect_source_flight():
    """Connect Source (profile→Flight) routes Meta+ad when Ad bind is absent."""
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _own_company_id(tenant_id)
    company_id = await _company_id(tenant_id)

    async with async_session_maker() as session:
        vac = Vacancy(
            id=str(uuid4()),
            tenant_id=tenant_id,
            own_company_id=oc,
            company_id=company_id,
            title="Drivers",
            status="open",
            is_active=True,
            is_archived=False,
        )
        session.add(vac)
        await session.flush()
        camp_id, flight_id = await _seed_inner(
            session, tenant_id=tenant_id, own_company_id=oc, vacancy_id=str(vac.id)
        )
        profile = IntakeSourceProfile(
            id=str(uuid4()),
            tenant_id=tenant_id,
            code=f"cs-prof-{uuid4().hex[:6]}",
            name="POLTRAKT ENG CE Drivers PL",
            provider="meta",
            channel="paid",
            own_company_id=oc,
            route_intent="candidate_application",
            mapping_rules=[{"source": "email", "target": "email"}],
            is_active=True,
        )
        session.add(profile)
        await session.flush()
        session.add(
            CampaignRunIntakeSource(
                id=str(uuid4()),
                tenant_id=tenant_id,
                campaign_run_id=flight_id,
                intake_source_profile_id=str(profile.id),
                role="primary",
                is_active=True,
            )
        )
        await session.commit()
        pid = str(profile.id)

        decision = await resolve_universal_submission_routing(
            session,
            tenant_id=tenant_id,
            intake_source_profile_id=pid,
            form_id=None,
            provider="meta",
            provider_ad_id="120249011467340547",
        )
    assert decision.status == "routed"
    assert decision.campaign_run_id == flight_id
    assert decision.campaign_id == camp_id
    assert decision.source == RoutingSource.campaign_target.value
    assert "connect_source_flight" in decision.warnings
    assert decision.source != RoutingSource.profile_default.value


@pytest.mark.anyio
async def test_meta_ad_binding_wins_over_form_flight(
    client: AsyncClient, manager_headers: dict
):
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _own_company_id(tenant_id)
    company_id = await _company_id(tenant_id)
    ad_id = str(900_000_000 + (uuid4().int % 90_000_000))

    async with async_session_maker() as session:
        # Vacancy for CampaignTarget
        vac = Vacancy(
            id=str(uuid4()),
            tenant_id=tenant_id,
            own_company_id=oc,
            company_id=company_id,
            title="Warehouse",
            status="open",
            is_active=True,
            is_archived=False,
        )
        session.add(vac)
        await session.flush()
        form = TenantLeadForm(
            id=str(uuid4()),
            tenant_id=tenant_id,
            title="Form",
            public_slug=f"f-{uuid4().hex[:6]}",
            is_active=True,
            lifecycle_status="published",
            purpose="inquiry",
        )
        session.add(form)
        await session.flush()

        # Form-linked flight (wrong attribution if Form won)
        camp_form, flight_form = await _seed_inner(
            session, tenant_id=tenant_id, own_company_id=oc, vacancy_id=str(vac.id)
        )
        session.add(
            CampaignRunForm(
                id=str(uuid4()),
                tenant_id=tenant_id,
                campaign_run_id=flight_form,
                form_id=str(form.id),
                role="primary",
                is_active=True,
            )
        )
        # Ad-bound flight
        camp_ad, flight_ad = await _seed_inner(
            session, tenant_id=tenant_id, own_company_id=oc, vacancy_id=str(vac.id)
        )
        session.add(
            FlightAdBinding(
                id=str(uuid4()),
                tenant_id=tenant_id,
                provider="meta",
                provider_ad_id=ad_id,
                campaign_id=camp_ad,
                campaign_run_id=flight_ad,
                is_active=True,
            )
        )
        await session.commit()
        form_id = str(form.id)

        decision = await resolve_universal_submission_routing(
            session,
            tenant_id=tenant_id,
            form_id=form_id,
            provider="meta",
            provider_ad_id=ad_id,
        )
    assert decision.status == "routed"
    assert decision.campaign_run_id == flight_ad
    assert decision.campaign_run_id != flight_form
    assert decision.source == RoutingSource.flight_ad_binding.value


async def _seed_inner(session, *, tenant_id, own_company_id, vacancy_id):
    campaign = Campaign(
        id=str(uuid4()),
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        name=f"Camp {uuid4().hex[:5]}",
        status="active",
        goal_type="hiring",
        primary_kpi="applications",
    )
    session.add(campaign)
    await session.flush()
    flight = CampaignRun(
        id=str(uuid4()),
        tenant_id=tenant_id,
        campaign_id=campaign.id,
        name="F",
        status="active",
        code=f"c-{uuid4().hex[:5]}",
    )
    session.add(flight)
    await session.flush()
    campaign.current_flight_id = flight.id
    session.add(
        CampaignTarget(
            id=str(uuid4()),
            tenant_id=tenant_id,
            campaign_id=campaign.id,
            target_type="vacancy",
            target_id=str(vacancy_id),
            target_module="recruitment",
            route_intent="candidate_application",
            role="primary",
            sort_order=0,
        )
    )
    await session.flush()
    return str(campaign.id), str(flight.id)


@pytest.mark.anyio
async def test_attach_ad_binding_reprocesses_missing_campaign_flight(
    client: AsyncClient, manager_headers: dict
):
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _own_company_id(tenant_id)
    company_id = await _company_id(tenant_id)
    ad_id = str(800_000_000 + (uuid4().int % 90_000_000))

    async with async_session_maker() as session:
        vac = Vacancy(
            id=str(uuid4()),
            tenant_id=tenant_id,
            own_company_id=oc,
            company_id=company_id,
            title="Pickers",
            status="open",
            is_active=True,
            is_archived=False,
        )
        session.add(vac)
        await session.flush()
        camp_id, flight_id = await _seed_campaign_flight(
            tenant_id=tenant_id, own_company_id=oc, vacancy_id=str(vac.id)
        )
        # waiting lead
        lead = Lead(
            id=str(uuid4()),
            tenant_id=tenant_id,
            own_company_id=oc,
            source="meta",
            status="needs_routing",
            ad_id=int(ad_id),
            payload={"ad_id": ad_id, "field_data": []},
            normalized={
                "ad_id": ad_id,
                "email": f"wait-{uuid4().hex[:6]}@example.com",
                "acquisition_routing_v1": {
                    "status": "unresolved",
                    "unresolved_reason": MISSING_CAMPAIGN_FLIGHT,
                },
            },
            error=MISSING_CAMPAIGN_FLIGHT,
            external_id=f"meta-lead-{uuid4().hex[:10]}",
        )
        # other needs_routing (mapping) must not reprocess
        other = Lead(
            id=str(uuid4()),
            tenant_id=tenant_id,
            own_company_id=oc,
            source="meta",
            status="needs_routing",
            ad_id=int(ad_id),
            payload={},
            normalized={"ad_id": ad_id},
            error="MAPPING_FAILED",
            external_id=f"meta-lead-{uuid4().hex[:10]}",
        )
        session.add_all([lead, other])
        await session.commit()
        lead_id = str(lead.id)
        other_id = str(other.id)

    headers = dict(manager_headers)
    headers["X-Tenant-Id"] = tenant_id
    headers["X-Own-Company-Id"] = oc
    headers["Content-Type"] = "application/json"
    resp = await client.post(
        f"/api/v1/platform/campaigns/{camp_id}/flights/{flight_id}/ad-bindings",
        headers=headers,
        json={"provider_ad_id": ad_id, "provider": "meta"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["provider_ad_id"] == ad_id
    assert body["flight_id"] == flight_id
    assert body["reprocess"]["matched"] >= 1

    async with async_session_maker() as session:
        waiting = await session.get(Lead, lead_id)
        untouched = await session.get(Lead, other_id)
        assert waiting is not None
        assert untouched is not None
        # Reprocess attempted; either routed further or still blocked by gates,
        # but must not stay on missing_campaign_flight if Flight is active+target.
        stamp = (waiting.normalized or {}).get("acquisition_routing_v1") or {}
        assert stamp.get("unresolved_reason") != MISSING_CAMPAIGN_FLIGHT or waiting.candidate_id
        assert untouched.error == "MAPPING_FAILED"


def _waiting_lead(
    *,
    tenant_id: str,
    own_company_id: str | None,
    ad_id: str,
    source: str = "meta",
    email: str | None = None,
) -> Lead:
    return Lead(
        id=str(uuid4()),
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        source=source,
        status="needs_routing",
        ad_id=int(ad_id) if str(ad_id).isdigit() else None,
        payload={"ad_id": ad_id, "field_data": []},
        normalized={
            "ad_id": ad_id,
            "email": email or f"wait-{uuid4().hex[:8]}@example.com",
            "acquisition_routing_v1": {
                "status": "unresolved",
                "unresolved_reason": MISSING_CAMPAIGN_FLIGHT,
            },
        },
        error=MISSING_CAMPAIGN_FLIGHT,
        external_id=f"meta-lead-{uuid4().hex[:12]}",
    )


def _clear_waiting_stamp(lead: Lead) -> None:
    lead.error = None
    lead.status = "processed"
    norm = dict(lead.normalized or {})
    stamp = dict(norm.get("acquisition_routing_v1") or {})
    stamp["status"] = "routed"
    stamp.pop("unresolved_reason", None)
    norm["acquisition_routing_v1"] = stamp
    lead.normalized = norm


@pytest.mark.anyio
async def test_reprocess_batches_beyond_200_and_isolates_filters(monkeypatch):
    """201+ waiting leads are fully drained; other tenant/provider/ad_id stay waiting."""
    from backend.app.acquisition import flight_ad_binding as fab
    from backend.app.modules.leads.service import _bulk as bulk_mod

    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _own_company_id(tenant_id)
    target_ad = str(700_000_000 + (uuid4().int % 90_000_000))
    other_ad = str(int(target_ad) + 1)
    other_tenant = "22222222-2222-2222-2222-222222222222"
    conversions: list[str] = []

    async def fake_reprocess(db, *, stored_lead_id, **_kwargs):
        lead = await db.get(Lead, stored_lead_id)
        assert lead is not None
        # Idempotent convert: count only first successful conversion.
        stamp = (lead.normalized or {}).get("acquisition_routing_v1") or {}
        if stamp.get("unresolved_reason") == MISSING_CAMPAIGN_FLIGHT and not lead.candidate_id:
            conversions.append(str(lead.id))
            lead.candidate_id = None  # no FK row; stamp clear is enough for filter
            _clear_waiting_stamp(lead)
            # Synthetic application marker for idempotency asserts
            norm = dict(lead.normalized or {})
            norm["_test_application_v1"] = {"created": True, "run": 1}
            lead.normalized = norm

    monkeypatch.setattr(bulk_mod, "reprocess_stored_lead_payload", fake_reprocess)

    target_ids: list[str] = []
    async with async_session_maker() as session:
        leads = [
            _waiting_lead(tenant_id=tenant_id, own_company_id=oc, ad_id=target_ad)
            for _ in range(201)
        ]
        other_ad_lead = _waiting_lead(
            tenant_id=tenant_id, own_company_id=oc, ad_id=other_ad
        )
        other_provider_lead = _waiting_lead(
            tenant_id=tenant_id, own_company_id=oc, ad_id=target_ad, source="tiktok"
        )
        # other provider still has meta stamp but source filter excludes non-meta for meta binding
        other_tenant_lead = _waiting_lead(
            tenant_id=other_tenant, own_company_id=None, ad_id=target_ad
        )
        session.add_all(leads + [other_ad_lead, other_provider_lead, other_tenant_lead])
        await session.commit()
        target_ids = [str(x.id) for x in leads]
        other_ad_id = str(other_ad_lead.id)
        other_provider_id = str(other_provider_lead.id)
        other_tenant_id = str(other_tenant_lead.id)

    summary = await fab.reprocess_leads_for_ad_binding(
        tenant_id=tenant_id,
        provider="meta",
        provider_ad_id=target_ad,
        batch_size=50,
    )
    assert summary["matched"] == 201
    assert summary["processed"] == 201
    assert summary["batches"] >= 5  # 50 * 5 = 250 capacity; 201 needs ≥5 pages
    assert summary["errors"] == []
    assert len(conversions) == 201

    # Second run: no duplicate conversions
    summary2 = await fab.reprocess_leads_for_ad_binding(
        tenant_id=tenant_id,
        provider="meta",
        provider_ad_id=target_ad,
        batch_size=50,
    )
    assert summary2["matched"] == 0
    assert summary2["processed"] == 0
    assert len(conversions) == 201

    async with async_session_maker() as session:
        for lid in target_ids:
            row = await session.get(Lead, lid)
            assert row is not None
            stamp = (row.normalized or {}).get("acquisition_routing_v1") or {}
            assert stamp.get("unresolved_reason") != MISSING_CAMPAIGN_FLIGHT
            assert (row.normalized or {}).get("_test_application_v1", {}).get("created") is True

        for lid in (other_ad_id, other_provider_id):
            row = await session.get(Lead, lid)
            assert row is not None
            assert row.error == MISSING_CAMPAIGN_FLIGHT

        from backend.tests.conftest import _set_tenant

        await _set_tenant(session, other_tenant)
        other_tenant_row = await session.get(Lead, other_tenant_id)
        assert other_tenant_row is not None
        assert other_tenant_row.error == MISSING_CAMPAIGN_FLIGHT
        assert other_tenant_row.tenant_id == other_tenant


@pytest.mark.anyio
async def test_binding_survives_reprocess_lead_failure(
    client: AsyncClient, manager_headers: dict, monkeypatch
):
    """Binding commit is durable even when one waiting lead fails during reprocess."""
    from backend.app.modules.leads.service import _bulk as bulk_mod

    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _own_company_id(tenant_id)
    company_id = await _company_id(tenant_id)
    ad_id = str(600_000_000 + (uuid4().int % 90_000_000))

    async with async_session_maker() as session:
        vac = Vacancy(
            id=str(uuid4()),
            tenant_id=tenant_id,
            own_company_id=oc,
            company_id=company_id,
            title="Survivors",
            status="open",
            is_active=True,
            is_archived=False,
        )
        session.add(vac)
        await session.flush()
        camp_id, flight_id = await _seed_campaign_flight(
            tenant_id=tenant_id, own_company_id=oc, vacancy_id=str(vac.id)
        )
        ok_lead = _waiting_lead(tenant_id=tenant_id, own_company_id=oc, ad_id=ad_id)
        bad_lead = _waiting_lead(tenant_id=tenant_id, own_company_id=oc, ad_id=ad_id)
        session.add_all([ok_lead, bad_lead])
        await session.commit()
        ok_id = str(ok_lead.id)
        bad_id = str(bad_lead.id)

    async def flaky_reprocess(db, *, stored_lead_id, **_kwargs):
        if str(stored_lead_id) == bad_id:
            raise RuntimeError("simulated reprocess failure")
        lead = await db.get(Lead, stored_lead_id)
        assert lead is not None
        _clear_waiting_stamp(lead)

    monkeypatch.setattr(bulk_mod, "reprocess_stored_lead_payload", flaky_reprocess)

    headers = dict(manager_headers)
    headers["X-Tenant-Id"] = tenant_id
    headers["X-Own-Company-Id"] = oc
    headers["Content-Type"] = "application/json"
    resp = await client.post(
        f"/api/v1/platform/campaigns/{camp_id}/flights/{flight_id}/ad-bindings",
        headers=headers,
        json={"provider_ad_id": ad_id, "provider": "meta"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["is_active"] is True
    assert body["reprocess"]["processed"] >= 1
    assert any(e.get("lead_id") == bad_id for e in body["reprocess"].get("errors") or [])

    async with async_session_maker() as session:
        binding = (
            await session.execute(
                select(FlightAdBinding).where(
                    FlightAdBinding.tenant_id == tenant_id,
                    FlightAdBinding.provider == "meta",
                    FlightAdBinding.provider_ad_id == ad_id,
                    FlightAdBinding.is_active.is_(True),
                )
            )
        ).scalar_one()
        assert str(binding.campaign_run_id) == flight_id

        ok_row = await session.get(Lead, ok_id)
        bad_row = await session.get(Lead, bad_id)
        assert ok_row is not None and bad_row is not None
        ok_stamp = (ok_row.normalized or {}).get("acquisition_routing_v1") or {}
        assert ok_stamp.get("unresolved_reason") != MISSING_CAMPAIGN_FLIGHT
        assert bad_row.error == MISSING_CAMPAIGN_FLIGHT


@pytest.mark.anyio
async def test_list_awaiting_skips_earlier_non_matching_same_ad(monkeypatch):
    """>1000 earlier MAPPING_FAILED rows must not starve a later missing_campaign_flight lead."""
    from datetime import datetime, timedelta, timezone

    from backend.app.acquisition import flight_ad_binding as fab
    from backend.app.db.deps import bind_tenant_context_to_session
    from backend.app.modules.leads.service import _bulk as bulk_mod
    from uuid import UUID

    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _own_company_id(tenant_id)
    ad_id = str(550_000_000 + (uuid4().int % 90_000_000))
    base = datetime.now(timezone.utc) - timedelta(hours=2)
    conversions: list[str] = []

    async def fake_reprocess(db, *, stored_lead_id, **_kwargs):
        lead = await db.get(Lead, stored_lead_id)
        assert lead is not None
        conversions.append(str(lead.id))
        _clear_waiting_stamp(lead)

    monkeypatch.setattr(bulk_mod, "reprocess_stored_lead_payload", fake_reprocess)

    async with async_session_maker() as session:
        await bind_tenant_context_to_session(session, UUID(tenant_id))
        junk: list[Lead] = []
        for i in range(1001):
            lead = Lead(
                id=str(uuid4()),
                tenant_id=tenant_id,
                own_company_id=oc,
                source="meta",
                status="needs_routing",
                ad_id=int(ad_id),
                payload={"ad_id": ad_id},
                normalized={"ad_id": ad_id},
                error="MAPPING_FAILED",
                external_id=f"map-fail-{uuid4().hex[:12]}",
                created_at=base + timedelta(seconds=i),
            )
            junk.append(lead)
        waiting = _waiting_lead(tenant_id=tenant_id, own_company_id=oc, ad_id=ad_id)
        waiting.created_at = base + timedelta(seconds=2000)
        # Also cover stamp-only path (error cleared but unresolved_reason set).
        stamp_only = _waiting_lead(tenant_id=tenant_id, own_company_id=oc, ad_id=ad_id)
        stamp_only.error = None
        stamp_only.created_at = base + timedelta(seconds=2001)
        session.add_all(junk + [waiting, stamp_only])
        await session.commit()
        waiting_id = str(waiting.id)
        stamp_only_id = str(stamp_only.id)

        page = await fab.list_leads_awaiting_ad_flight(
            session,
            tenant_id=tenant_id,
            provider="meta",
            provider_ad_id=ad_id,
            limit=10,
        )
        page_ids = {str(x.id) for x in page}
        assert waiting_id in page_ids
        assert stamp_only_id in page_ids
        assert len(page) == 2

    summary = await fab.reprocess_leads_for_ad_binding(
        tenant_id=tenant_id,
        provider="meta",
        provider_ad_id=ad_id,
        batch_size=50,
    )
    assert summary["matched"] == 2
    assert summary["processed"] == 2
    assert set(conversions) == {waiting_id, stamp_only_id}


@pytest.mark.anyio
async def test_attach_rejects_non_meta_provider(
    client: AsyncClient, manager_headers: dict
):
    data = await _init_data()
    tenant_id = data["tenant_id"]
    oc = await _own_company_id(tenant_id)
    company_id = await _company_id(tenant_id)
    async with async_session_maker() as session:
        vac = Vacancy(
            id=str(uuid4()),
            tenant_id=tenant_id,
            own_company_id=oc,
            company_id=company_id,
            title="Prov Gate",
            status="open",
            is_active=True,
            is_archived=False,
        )
        session.add(vac)
        await session.flush()
        camp_id, flight_id = await _seed_campaign_flight(
            tenant_id=tenant_id, own_company_id=oc, vacancy_id=str(vac.id)
        )

    headers = dict(manager_headers)
    headers["X-Tenant-Id"] = tenant_id
    headers["X-Own-Company-Id"] = oc
    headers["Content-Type"] = "application/json"
    resp = await client.post(
        f"/api/v1/platform/campaigns/{camp_id}/flights/{flight_id}/ad-bindings",
        headers=headers,
        json={"provider_ad_id": "123456789", "provider": "tiktok"},
    )
    assert resp.status_code == 422, resp.text
