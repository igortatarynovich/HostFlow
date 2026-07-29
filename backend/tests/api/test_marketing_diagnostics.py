"""Source Diagnostics — Marketing diagnostics list + case (+ PR2 filters)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.acquisition.submission_routing import ACQUISITION_ROUTING_V1_KEY
from backend.app.db.session import async_session_maker
from backend.app.models.lead import Lead
from backend.app.models.tenant import Tenant

DEFAULT_TENANT_ID = "11111111-1111-1111-1111-111111111111"


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


def _stamped_lead(
    *,
    lead_id: str,
    source: str,
    status: str,
    flight_id: str,
    routing_status: str = "routed",
    error: str | None = None,
) -> Lead:
    return Lead(
        id=lead_id,
        tenant_id=DEFAULT_TENANT_ID,
        source=source,
        status=status,
        lead_type="candidate",
        lead_target_type="candidate",
        external_id=f"meta-lead-{uuid4().hex[:10]}",
        error=error,
        normalized={
            "full_name": f"Person {lead_id[:8]}",
            "phone": "+48111111111",
            ACQUISITION_ROUTING_V1_KEY: {
                "status": routing_status,
                "campaign_id": str(uuid4()),
                "campaign_run_id": flight_id,
                "route_intent": "candidate_application",
            },
            "submissions_v1": [
                {
                    "submission_id": str(uuid4()),
                    "submitted_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
        },
        payload={"ad_id": "120249011467340547"},
    )


@pytest.mark.asyncio
async def test_diagnostics_list_and_case(client: AsyncClient, auth_headers: Dict[str, str]):
    lead_id = str(uuid4())
    async with async_session_maker() as db:
        await _ensure_tenant(db, DEFAULT_TENANT_ID)
        db.add(
            Lead(
                id=lead_id,
                tenant_id=DEFAULT_TENANT_ID,
                source="meta",
                status="needs_routing",
                lead_type="candidate",
                lead_target_type="candidate",
                external_id=f"meta-lead-{uuid4().hex[:10]}",
                normalized={
                    "full_name": "Diag Person",
                    "phone": "+48111111111",
                    ACQUISITION_ROUTING_V1_KEY: {
                        "status": "unresolved",
                        "unresolved_reason": "missing_campaign_flight",
                        "campaign_id": str(uuid4()),
                        "campaign_run_id": str(uuid4()),
                        "route_intent": "candidate_application",
                    },
                    "submissions_v1": [
                        {
                            "submission_id": str(uuid4()),
                            "submitted_at": datetime.now(timezone.utc).isoformat(),
                        }
                    ],
                },
                payload={"ad_id": "120249011467340547"},
            )
        )
        await db.commit()

    list_resp = await client.get(
        "/api/v1/platform/marketing/diagnostics/submissions",
        headers=_headers(auth_headers),
    )
    assert list_resp.status_code == 200, list_resp.text
    items = list_resp.json()["items"]
    assert any(row["lead_id"] == lead_id for row in items)
    match = next(row for row in items if row["lead_id"] == lead_id)
    assert match["full_name"] == "Diag Person"
    assert match["routing_status"] == "unresolved"

    case_resp = await client.get(
        f"/api/v1/platform/marketing/diagnostics/submissions/{lead_id}",
        headers=_headers(auth_headers),
    )
    assert case_resp.status_code == 200, case_resp.text
    body = case_resp.json()
    assert body["lead_id"] == lead_id
    assert body["routing"]["unresolved_reason"] == "missing_campaign_flight"
    assert body["payload"]["ad_id"] == "120249011467340547"
    assert isinstance(body["timeline"], list)


@pytest.mark.asyncio
async def test_diagnostics_list_filters(client: AsyncClient, auth_headers: Dict[str, str]):
    flight_a = str(uuid4())
    flight_b = str(uuid4())
    meta_ok = str(uuid4())
    meta_fail = str(uuid4())
    form_ok = str(uuid4())
    async with async_session_maker() as db:
        await _ensure_tenant(db, DEFAULT_TENANT_ID)
        db.add_all(
            [
                _stamped_lead(
                    lead_id=meta_ok,
                    source="meta",
                    status="processed",
                    flight_id=flight_a,
                    routing_status="routed",
                ),
                _stamped_lead(
                    lead_id=meta_fail,
                    source="meta",
                    status="failed",
                    flight_id=flight_a,
                    routing_status="unresolved",
                    error="mapping_error",
                ),
                _stamped_lead(
                    lead_id=form_ok,
                    source="form",
                    status="processed",
                    flight_id=flight_b,
                    routing_status="routed",
                ),
            ]
        )
        await db.commit()

    by_source = await client.get(
        "/api/v1/platform/marketing/diagnostics/submissions",
        headers=_headers(auth_headers),
        params={"source": "form", "limit": 50},
    )
    assert by_source.status_code == 200, by_source.text
    source_ids = {row["lead_id"] for row in by_source.json()["items"]}
    assert form_ok in source_ids
    assert meta_ok not in source_ids
    assert meta_fail not in source_ids

    by_flight = await client.get(
        "/api/v1/platform/marketing/diagnostics/submissions",
        headers=_headers(auth_headers),
        params={"flight_id": flight_a, "limit": 50},
    )
    assert by_flight.status_code == 200, by_flight.text
    flight_ids = {row["lead_id"] for row in by_flight.json()["items"]}
    assert meta_ok in flight_ids
    assert meta_fail in flight_ids
    assert form_ok not in flight_ids

    failed = await client.get(
        "/api/v1/platform/marketing/diagnostics/submissions",
        headers=_headers(auth_headers),
        params={"failed_only": True, "limit": 50},
    )
    assert failed.status_code == 200, failed.text
    failed_ids = {row["lead_id"] for row in failed.json()["items"]}
    assert meta_fail in failed_ids
    assert meta_ok not in failed_ids
    assert form_ok not in failed_ids

    bad_flight = await client.get(
        "/api/v1/platform/marketing/diagnostics/submissions",
        headers=_headers(auth_headers),
        params={"flight_id": "not-a-uuid"},
    )
    assert bad_flight.status_code == 422


@pytest.mark.asyncio
async def test_diagnostics_case_404(client: AsyncClient, auth_headers: Dict[str, str]):
    resp = await client.get(
        f"/api/v1/platform/marketing/diagnostics/submissions/{uuid4()}",
        headers=_headers(auth_headers),
    )
    assert resp.status_code == 404
