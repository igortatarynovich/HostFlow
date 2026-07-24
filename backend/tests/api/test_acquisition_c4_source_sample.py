"""Acquisition UI Cutover C-4 — Marketing Sources sample / preview API."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from backend.app.acquisition.sources_sample import mask_sample_value
from backend.app.db.session import async_session_maker
from backend.app.models.candidate import Candidate
from backend.app.models.intake_routing import IntakeSourceBinding, IntakeSourceProfile
from backend.app.models.lead import Lead
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


async def _make_meta_source(db, *, tenant_id: str, form_id: str) -> IntakeSourceProfile:
    await _ensure_tenant(db, tenant_id)
    oc = await _own_company_id(db, tenant_id)
    profile = IntakeSourceProfile(
        id=str(uuid4()),
        tenant_id=tenant_id,
        code=f"c4-src-{uuid4().hex[:8]}",
        name="C4 Meta Source",
        provider="meta",
        channel="paid",
        own_company_id=oc,
        route_intent="candidate_application",
        mapping_rules=[
            {"source": "email", "target": "email"},
            {"source": "full_name", "target": "full_name"},
        ],
        is_active=True,
    )
    db.add(profile)
    await db.flush()
    db.add(
        IntakeSourceBinding(
            id=str(uuid4()),
            tenant_id=tenant_id,
            intake_source_profile_id=profile.id,
            provider="meta",
            external_key=f"form_id:{form_id}",
            external_key_secondary=f"page_id:page-{uuid4().hex[:6]}",
            is_active=True,
            priority=10,
        )
    )
    await db.flush()
    return profile


def _meta_payload(*, form_id: str, email: str = "anna@example.com", phone: str = "+48111222333") -> dict[str, Any]:
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "form_id": form_id,
                            "leadgen_id": f"lg-{uuid4().hex[:10]}",
                            "field_data": [
                                {"name": "full_name", "values": ["Anna Kowalska"]},
                                {"name": "email", "values": [email]},
                                {"name": "phone_number", "values": [phone]},
                                {"name": "which_licence", "values": ["CE"]},
                            ],
                        }
                    }
                ]
            }
        ]
    }


def test_mask_sample_value_email_phone_name() -> None:
    assert mask_sample_value("email", "anna@example.com") == "a***@example.com"
    assert mask_sample_value("phone_number", "+48111222333").startswith("***")
    assert mask_sample_value("full_name", "Anna Kowalska") == "A***"


@pytest.mark.anyio
async def test_sample_tenant_isolation(
    client: AsyncClient, manager_headers: Dict[str, str]
) -> None:
    form_id = f"form-c4-iso-{uuid4().hex[:8]}"
    async with async_session_maker() as db:
        foreign = await _make_meta_source(db, tenant_id=OTHER_TENANT_ID, form_id=form_id)
        await db.commit()
        foreign_id = str(foreign.id)

    headers = _headers(manager_headers, tenant_id=DEFAULT_TENANT_ID)
    resp = await client.get(
        f"/api/v1/platform/marketing/sources/{foreign_id}/sample",
        headers=headers,
    )
    assert resp.status_code == 404, resp.text


@pytest.mark.anyio
async def test_from_payload_discovers_masked_fields(
    client: AsyncClient, manager_headers: Dict[str, str]
) -> None:
    form_id = f"form-c4-paste-{uuid4().hex[:8]}"
    async with async_session_maker() as db:
        profile = await _make_meta_source(db, tenant_id=DEFAULT_TENANT_ID, form_id=form_id)
        await db.commit()
        source_id = str(profile.id)

    headers = _headers(manager_headers)
    sample = _meta_payload(form_id=form_id)
    resp = await client.post(
        f"/api/v1/platform/marketing/sources/{source_id}/sample/from-payload",
        headers=headers,
        json={"sample_payload": sample},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["has_sample"] is True
    assert body["sample_source"] == "paste"
    by_source = {f["source"]: f for f in body["fields"]}
    assert "email" in by_source
    assert by_source["email"]["sample_value_masked"] == "a***@example.com"
    assert by_source["email"]["status"] == "mapped"
    assert by_source["email"]["proposed_target"] == "email"
    assert "which_licence" in by_source
    assert by_source["which_licence"]["status"] == "unmapped"
    # Masked raw must not echo full email / full name plaintext samples.
    dumped = str(body["raw_payload_masked"])
    assert "anna@example.com" not in dumped.lower()
    assert "Anna Kowalska" not in dumped
    assert "a***@example.com" in dumped or "A***" in dumped


@pytest.mark.anyio
async def test_preview_does_not_create_candidate_or_lead(
    client: AsyncClient, manager_headers: Dict[str, str]
) -> None:
    form_id = f"form-c4-prev-{uuid4().hex[:8]}"
    async with async_session_maker() as db:
        profile = await _make_meta_source(db, tenant_id=DEFAULT_TENANT_ID, form_id=form_id)
        await db.commit()
        source_id = str(profile.id)
        leads_before = (
            await db.execute(select(func.count()).select_from(Lead).where(Lead.tenant_id == DEFAULT_TENANT_ID))
        ).scalar_one()
        candidates_before = (
            await db.execute(
                select(func.count()).select_from(Candidate).where(Candidate.tenant_id == DEFAULT_TENANT_ID)
            )
        ).scalar_one()

    headers = _headers(manager_headers)
    sample = _meta_payload(form_id=form_id, email=f"c4-preview-{uuid4().hex[:6]}@example.com")
    resp = await client.post(
        f"/api/v1/platform/marketing/sources/{source_id}/sample/preview",
        headers=headers,
        json={"sample_payload": sample},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["creates_entities"] is False
    assert "normalized_payload" in body
    assert isinstance(body["normalized_payload"], dict)

    async with async_session_maker() as db:
        leads_after = (
            await db.execute(select(func.count()).select_from(Lead).where(Lead.tenant_id == DEFAULT_TENANT_ID))
        ).scalar_one()
        candidates_after = (
            await db.execute(
                select(func.count()).select_from(Candidate).where(Candidate.tenant_id == DEFAULT_TENANT_ID)
            )
        ).scalar_one()
    assert leads_after == leads_before
    assert candidates_after == candidates_before


@pytest.mark.anyio
async def test_get_sample_from_existing_lead(
    client: AsyncClient, manager_headers: Dict[str, str]
) -> None:
    form_id = f"form-c4-lead-{uuid4().hex[:8]}"
    async with async_session_maker() as db:
        profile = await _make_meta_source(db, tenant_id=DEFAULT_TENANT_ID, form_id=form_id)
        lead = Lead(
            id=str(uuid4()),
            tenant_id=DEFAULT_TENANT_ID,
            source="meta",
            payload=_meta_payload(form_id=form_id, email="lead-sample@example.com"),
            normalized={
                "form_id": form_id,
                "acquisition_routing_v1": {"intake_source_profile_id": str(profile.id)},
            },
            status="new",
            created_at=datetime.now(timezone.utc),
        )
        db.add(lead)
        await db.commit()
        source_id = str(profile.id)
        lead_id = str(lead.id)

    headers = _headers(manager_headers)
    resp = await client.get(
        f"/api/v1/platform/marketing/sources/{source_id}/sample",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["has_sample"] is True
    assert body["sample_source"] == "lead"
    assert body["lead_id"] == lead_id
    emails = [f for f in body["fields"] if f["source"] == "email"]
    assert emails
    assert emails[0]["sample_value_masked"] == "l***@example.com"


@pytest.mark.anyio
async def test_capture_next_arms_and_lazy_captures_on_get(
    client: AsyncClient, manager_headers: Dict[str, str]
) -> None:
    form_id = f"form-c4-cap-{uuid4().hex[:8]}"
    async with async_session_maker() as db:
        profile = await _make_meta_source(db, tenant_id=DEFAULT_TENANT_ID, form_id=form_id)
        await db.commit()
        source_id = str(profile.id)

    headers = _headers(manager_headers)
    arm = await client.post(
        f"/api/v1/platform/marketing/sources/{source_id}/sample/capture-next",
        headers=headers,
    )
    assert arm.status_code == 200, arm.text
    assert arm.json()["capture_next_until"]

    async with async_session_maker() as db:
        lead = Lead(
            id=str(uuid4()),
            tenant_id=DEFAULT_TENANT_ID,
            source="meta",
            payload=_meta_payload(form_id=form_id, email="capture-next@example.com"),
            normalized={
                "form_id": form_id,
                "acquisition_routing_v1": {"intake_source_profile_id": source_id},
            },
            status="new",
            created_at=datetime.now(timezone.utc),
        )
        db.add(lead)
        await db.commit()
        lead_id = str(lead.id)

    resp = await client.get(
        f"/api/v1/platform/marketing/sources/{source_id}/sample",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["sample_source"] == "capture_next"
    assert body["lead_id"] == lead_id
    assert body["capture_next_until"] is None


def test_c4_router_exposes_sample_routes() -> None:
    from backend.app.api.v1.platform import marketing_sources as mod

    paths = {getattr(route, "path", "") for route in mod.router.routes}
    assert any(p.endswith("/{source_id}/sample") for p in paths)
    assert any(p.endswith("/{source_id}/sample/preview") for p in paths)
    assert any(p.endswith("/{source_id}/sample/from-payload") for p in paths)
    assert any(p.endswith("/{source_id}/sample/capture-next") for p in paths)
