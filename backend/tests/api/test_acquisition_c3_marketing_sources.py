"""Acquisition UI Cutover C-3 — Marketing Sources read API."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.acquisition.endpoint_activity import intake_source_endpoint_id
from backend.app.acquisition.sources_read import (
    HEALTH_BROKEN,
    HEALTH_NEEDS_REVIEW,
    HEALTH_READY,
    ROUTING_ISSUE_MISSING_CAMPAIGN_FLIGHT,
    compute_connection_status,
    compute_mapping_health,
    list_marketing_source_summaries,
)
from backend.app.constants.spa_paths import (
    MARKETING_NEW,
    MARKETING_SOURCES,
    SETTINGS_INTEGRATIONS_META,
    SETTINGS_LEAD_FORMS,
)
from backend.app.db.session import async_session_maker
from backend.app.models.acquisition_activity_event import AcquisitionActivityEvent
from backend.app.models.campaign import Campaign, CampaignRun, CampaignRunIntakeSource
from backend.app.models.intake_routing import IntakeSourceBinding, IntakeSourceProfile
from backend.app.models.lead import Lead, MetaLeadCredential, MetaLeadSettings
from backend.app.models.own_company import OwnCompany
from backend.app.models.tenant import Tenant

DEFAULT_TENANT_ID = "11111111-1111-1111-1111-111111111111"
OTHER_TENANT_ID = "22222222-2222-2222-2222-222222222222"


def _headers(base: Dict[str, str], *, tenant_id: str = DEFAULT_TENANT_ID) -> Dict[str, str]:
    merged = dict(base)
    merged["X-Tenant-Id"] = tenant_id
    merged.setdefault("Content-Type", "application/json")
    return merged


async def _ensure_tenant(db, tenant_id: str) -> None:
    exists = (
        await db.execute(select(Tenant.id).where(Tenant.id == tenant_id))
    ).scalar_one_or_none()
    if exists is not None:
        return
    suffix = tenant_id.replace("-", "")[:8]
    db.add(
        Tenant(
            id=tenant_id,
            name=f"Tenant {suffix}",
            slug=f"t-{suffix}",
            api_key=f"api-{suffix}-{uuid4().hex[:8]}",
            is_active=True,
        )
    )
    await db.flush()


async def _own_company_id(db, tenant_id: str) -> str:
    row = await db.execute(
        select(OwnCompany.id)
        .where(OwnCompany.tenant_id == tenant_id, OwnCompany.is_archived.is_(False))
        .order_by(OwnCompany.created_at.asc())
        .limit(1)
    )
    oc = row.scalar_one_or_none()
    if oc is None:
        oc = str(uuid4())
        db.add(OwnCompany(id=oc, tenant_id=tenant_id, name=f"OC {uuid4().hex[:6]}"))
        await db.flush()
    return str(oc)


def test_mapping_health_projection_matrix() -> None:
    assert (
        compute_mapping_health(
            connection_status="connected",
            mapping_rules_count=2,
            last_error_code=None,
        )
        == HEALTH_READY
    )
    assert (
        compute_mapping_health(
            connection_status="connected",
            mapping_rules_count=0,
            last_error_code=None,
        )
        == HEALTH_NEEDS_REVIEW
    )
    assert (
        compute_mapping_health(
            connection_status="attention",
            mapping_rules_count=2,
            last_error_code=None,
        )
        == HEALTH_NEEDS_REVIEW
    )
    assert (
        compute_mapping_health(
            connection_status="disconnected",
            mapping_rules_count=2,
            last_error_code=None,
        )
        == HEALTH_BROKEN
    )
    assert (
        compute_mapping_health(
            connection_status="connected",
            mapping_rules_count=2,
            last_error_code="routing_failed",
        )
        == HEALTH_BROKEN
    )


def test_connection_status_meta_rules() -> None:
    assert (
        compute_connection_status(
            is_active=False,
            provider="meta",
            active_binding_count=1,
            last_signature_status="ok",
            has_meta_credential=True,
        )
        == "disconnected"
    )
    assert (
        compute_connection_status(
            is_active=True,
            provider="meta",
            active_binding_count=1,
            last_signature_status="failed",
            has_meta_credential=True,
        )
        == "disconnected"
    )
    assert (
        compute_connection_status(
            is_active=True,
            provider="meta",
            active_binding_count=0,
            last_signature_status="ok",
            has_meta_credential=True,
        )
        == "attention"
    )
    assert (
        compute_connection_status(
            is_active=True,
            provider="meta",
            active_binding_count=1,
            last_signature_status="ok",
            has_meta_credential=True,
        )
        == "connected"
    )


@pytest.mark.anyio
async def test_list_sources_aggregates_bindings_and_flights(
    client: AsyncClient, manager_headers: Dict[str, str]
) -> None:
    headers = _headers(manager_headers)
    tid = DEFAULT_TENANT_ID
    async with async_session_maker() as db:
        await _ensure_tenant(db, tid)
        oc = await _own_company_id(db, tid)
        profile = IntakeSourceProfile(
            id=str(uuid4()),
            tenant_id=tid,
            code=f"c3-src-{uuid4().hex[:8]}",
            name="C3 Meta Source",
            provider="meta",
            channel="paid",
            own_company_id=oc,
            route_intent="candidate_application",
            mapping_rules=[{"source": "email", "target": "email"}],
            is_active=True,
        )
        db.add(profile)
        await db.flush()
        db.add(
            IntakeSourceBinding(
                id=str(uuid4()),
                tenant_id=tid,
                intake_source_profile_id=profile.id,
                provider="meta",
                external_key=f"form_id:form-c3-{uuid4().hex[:8]}",
                external_key_secondary=f"page_id:page-{uuid4().hex[:6]}",
                is_active=True,
                priority=10,
            )
        )
        # Source without Flight must still appear — create second profile with no links
        lonely = IntakeSourceProfile(
            id=str(uuid4()),
            tenant_id=tid,
            code=f"c3-lonely-{uuid4().hex[:8]}",
            name="C3 Lonely Source",
            provider="public_intake",
            channel="organic",
            own_company_id=oc,
            route_intent="candidate_application",
            mapping_rules=[],
            is_active=True,
        )
        db.add(lonely)
        campaign = Campaign(
            id=str(uuid4()),
            tenant_id=tid,
            own_company_id=oc,
            name="C3 Camp",
            status="draft",
            goal_type="hiring",
            primary_kpi="applications",
        )
        db.add(campaign)
        await db.flush()
        flight = CampaignRun(
            id=str(uuid4()),
            tenant_id=tid,
            campaign_id=campaign.id,
            name="Flight 1",
            status="draft",
        )
        db.add(flight)
        await db.flush()
        db.add(
            CampaignRunIntakeSource(
                id=str(uuid4()),
                tenant_id=tid,
                campaign_run_id=flight.id,
                intake_source_profile_id=profile.id,
                role="primary",
                is_active=True,
            )
        )
        existing_settings = (
            await db.execute(select(MetaLeadSettings).where(MetaLeadSettings.tenant_id == tid))
        ).scalar_one_or_none()
        if existing_settings is None:
            db.add(
                MetaLeadSettings(
                    tenant_id=tid,
                    last_signature_status="ok",
                    field_mapping=[],
                )
            )
        else:
            existing_settings.last_signature_status = "ok"

        existing_cred = (
            await db.execute(
                select(MetaLeadCredential.id)
                .where(MetaLeadCredential.tenant_id == tid)
                .limit(1)
            )
        ).scalar_one_or_none()
        if existing_cred is None:
            db.add(
                MetaLeadCredential(
                    id=str(uuid4()),
                    tenant_id=tid,
                    label="c3-cred",
                    status="active",
                )
            )
        now = datetime.now(timezone.utc)
        db.add(
            AcquisitionActivityEvent(
                id=str(uuid4()),
                tenant_id=tid,
                campaign_id=campaign.id,
                flight_id=flight.id,
                endpoint_id=intake_source_endpoint_id(profile.id),
                event_type="SubmissionReceived",
                event_version="1",
                occurred_at=now,
                recorded_at=now,
                actor_type="system",
                payload={},
            )
        )
        err_at = datetime.now(timezone.utc)
        db.add(
            AcquisitionActivityEvent(
                id=str(uuid4()),
                tenant_id=tid,
                campaign_id=campaign.id,
                flight_id=flight.id,
                endpoint_id=intake_source_endpoint_id(profile.id),
                event_type="RoutingFailed",
                event_version="1",
                occurred_at=err_at,
                recorded_at=err_at,
                actor_type="system",
                payload={"error_code": "routing_failed"},
            )
        )
        await db.commit()
        profile_id = str(profile.id)
        lonely_id = str(lonely.id)

    resp = await client.get("/api/v1/platform/marketing/sources", headers=headers)
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    by_id = {row["source_id"]: row for row in items}
    assert profile_id in by_id
    assert lonely_id in by_id

    linked = by_id[profile_id]
    assert linked["provider"] == "meta"
    assert linked["display_name"] == "C3 Meta Source"
    assert linked["connection_status"] == "connected"
    # routing_failed → Broken even with mapping rules
    assert linked["mapping_health"] == HEALTH_BROKEN
    assert linked["campaign_count"] >= 1
    assert linked["flight_count"] >= 1
    assert linked["last_submission_at"] is not None
    assert linked["last_error_at"] is not None
    assert linked["last_error_code"] == "routing_failed"
    assert linked["mapping_path"].startswith(SETTINGS_INTEGRATIONS_META)
    assert "tab=field_mapping" in linked["mapping_path"]
    assert linked["test_lead_path"].startswith(MARKETING_SOURCES)
    assert linked["test_lead_path"].endswith(f"/{linked['source_id']}/test-lead")
    assert linked["settings_path"] == SETTINGS_INTEGRATIONS_META

    lonely_row = by_id[lonely_id]
    assert lonely_row["campaign_count"] == 0
    assert lonely_row["flight_count"] == 0
    assert lonely_row["mapping_health"] == HEALTH_NEEDS_REVIEW


@pytest.mark.anyio
async def test_list_sources_tenant_isolation(
    client: AsyncClient, manager_headers: Dict[str, str]
) -> None:
    headers = _headers(manager_headers)
    async with async_session_maker() as db:
        await _ensure_tenant(db, OTHER_TENANT_ID)
        oc = await _own_company_id(db, OTHER_TENANT_ID)
        foreign = IntakeSourceProfile(
            id=str(uuid4()),
            tenant_id=OTHER_TENANT_ID,
            code=f"foreign-{uuid4().hex[:8]}",
            name="Foreign Source",
            provider="meta",
            channel="paid",
            own_company_id=oc,
            route_intent="candidate_application",
            mapping_rules=[{"source": "phone", "target": "phone"}],
            is_active=True,
        )
        db.add(foreign)
        await db.commit()
        foreign_id = str(foreign.id)

    resp = await client.get("/api/v1/platform/marketing/sources", headers=headers)
    assert resp.status_code == 200, resp.text
    ids = {row["source_id"] for row in resp.json()["items"]}
    assert foreign_id not in ids


@pytest.mark.anyio
async def test_ready_health_when_mapped_and_connected() -> None:
    tid = DEFAULT_TENANT_ID
    async with async_session_maker() as db:
        await _ensure_tenant(db, tid)
        oc = await _own_company_id(db, tid)
        profile = IntakeSourceProfile(
            id=str(uuid4()),
            tenant_id=tid,
            code=f"ready-{uuid4().hex[:8]}",
            name="Ready Source",
            provider="public_intake",
            channel="organic",
            own_company_id=oc,
            route_intent="candidate_application",
            mapping_rules=[{"source": "email", "target": "email"}],
            is_active=True,
            public_slug=f"ready-{uuid4().hex[:6]}",
        )
        db.add(profile)
        await db.commit()
        pid = str(profile.id)

        rows = await list_marketing_source_summaries(db, tenant_id=tid)
    by_id = {r.source_id: r for r in rows}
    assert pid in by_id
    assert by_id[pid].mapping_health == HEALTH_READY
    assert by_id[pid].connection_status == "connected"


def test_c3_list_router_still_exposes_get() -> None:
    from backend.app.api.v1.platform import marketing_sources as mod

    list_methods: set[str] = set()
    for route in mod.router.routes:
        if getattr(route, "path", "") in {"", "/"} or str(getattr(route, "path", "")).endswith(
            "/platform/marketing/sources"
        ):
            list_methods |= set(getattr(route, "methods", set()) or set())
    # List remains GET; C-4 adds POST under /{source_id}/sample/*
    assert "GET" in list_methods
    assert SETTINGS_LEAD_FORMS.startswith("/app/settings/lead-forms")
    assert MARKETING_SOURCES == "/app/marketing/sources"


@pytest.mark.anyio
async def test_waiting_submissions_project_ad_id_and_setup_cta(
    client: AsyncClient, manager_headers: Dict[str, str]
) -> None:
    """C-3 visibility: needs_routing leads → waiting count, Ad ID, concrete reason, setup CTA."""
    headers = _headers(manager_headers)
    tid = DEFAULT_TENANT_ID
    form_id = f"form-wait-{uuid4().hex[:8]}"
    ad_id = 99887766
    async with async_session_maker() as db:
        await _ensure_tenant(db, tid)
        oc = await _own_company_id(db, tid)
        profile = IntakeSourceProfile(
            id=str(uuid4()),
            tenant_id=tid,
            code=f"c3-wait-{uuid4().hex[:8]}",
            name="C3 Waiting Source",
            provider="meta",
            channel="paid",
            own_company_id=oc,
            route_intent="candidate_application",
            mapping_rules=[{"source": "email", "target": "email"}],
            is_active=True,
        )
        db.add(profile)
        await db.flush()
        db.add(
            IntakeSourceBinding(
                id=str(uuid4()),
                tenant_id=tid,
                intake_source_profile_id=profile.id,
                provider="meta",
                external_key=f"form_id:{form_id}",
                is_active=True,
                priority=10,
            )
        )
        now = datetime.now(timezone.utc)
        db.add(
            Lead(
                id=str(uuid4()),
                tenant_id=tid,
                own_company_id=oc,
                source="meta",
                status="needs_routing",
                ad_id=ad_id,
                payload={"form_id": form_id, "ad_id": ad_id},
                normalized={
                    "form_id": form_id,
                    "ad_id": ad_id,
                    "acquisition_routing_v1": {
                        "status": "unresolved",
                        "intake_source_profile_id": str(profile.id),
                        "form_id": form_id,
                        "unresolved_reason": "missing_campaign_flight",
                    },
                },
                created_at=now,
            )
        )
        # Older waiting lead — must not win last_problematic_ad_id
        db.add(
            Lead(
                id=str(uuid4()),
                tenant_id=tid,
                own_company_id=oc,
                source="meta",
                status="needs_routing",
                ad_id=111,
                payload={"form_id": form_id, "ad_id": 111},
                normalized={
                    "form_id": form_id,
                    "ad_id": 111,
                    "acquisition_routing_v1": {
                        "status": "unresolved",
                        "intake_source_profile_id": str(profile.id),
                    },
                },
                created_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
            )
        )
        # Processed lead must not count as waiting
        db.add(
            Lead(
                id=str(uuid4()),
                tenant_id=tid,
                own_company_id=oc,
                source="meta",
                status="processed",
                ad_id=222,
                payload={"form_id": form_id},
                normalized={"form_id": form_id, "ad_id": 222},
            )
        )
        await db.commit()
        profile_id = str(profile.id)

    resp = await client.get("/api/v1/platform/marketing/sources", headers=headers)
    assert resp.status_code == 200, resp.text
    by_id = {row["source_id"]: row for row in resp.json()["items"]}
    assert profile_id in by_id
    row = by_id[profile_id]
    assert row["waiting_submissions"] == 2
    assert row["last_problematic_ad_id"] == str(ad_id)
    assert row["routing_issue_code"] == ROUTING_ISSUE_MISSING_CAMPAIGN_FLIGHT
    assert "Campaign/Flight" in (row["routing_issue_message"] or "")
    assert row["setup_campaign_flight_path"]
    assert row["setup_campaign_flight_path"].startswith(MARKETING_NEW)
    assert f"intake_source_profile_id={profile_id}" in row["setup_campaign_flight_path"]
    assert f"ad_id={ad_id}" in row["setup_campaign_flight_path"]
    assert row["mapping_health"] in {HEALTH_NEEDS_REVIEW, HEALTH_BROKEN}
    assert row["last_submission_at"] is not None
