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
from backend.app.models.intake_routing import IntakeSourceProfile
from backend.app.models.lead import Lead
from backend.app.models.own_company import OwnCompany
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
    assert body["duplicate"]["active"] is False


@pytest.mark.asyncio
async def test_diagnostics_case_duplicate_surface(
    client: AsyncClient, auth_headers: Dict[str, str]
):
    lead_id = str(uuid4())
    candidate_id = str(uuid4())
    async with async_session_maker() as db:
        await _ensure_tenant(db, DEFAULT_TENANT_ID)
        db.add(
            Lead(
                id=lead_id,
                tenant_id=DEFAULT_TENANT_ID,
                source="meta",
                status="duplicate_review",
                lead_type="candidate",
                lead_target_type="candidate",
                external_id=f"meta-lead-{uuid4().hex[:10]}",
                normalized={
                    "full_name": "Dup Person",
                    ACQUISITION_ROUTING_V1_KEY: {
                        "status": "routed",
                        "campaign_id": str(uuid4()),
                        "campaign_run_id": str(uuid4()),
                        "route_intent": "candidate_application",
                    },
                    "decision_result_v1": {
                        "disposition": "blocked_duplicate",
                        "attach_candidate_id": candidate_id,
                        "duplicate_match": {
                            "level": "probable",
                            "candidate_id": candidate_id,
                            "reasons": ["phone_match"],
                            "hr_blockers": ["workforce_active"],
                            "needs_duplicate_review": True,
                        },
                        "blocking_reasons": ["duplicate_review"],
                        "warnings": [],
                    },
                    "duplicate_match_v1": {
                        "level": "probable",
                        "suggested_candidate_id": candidate_id,
                        "reasons": ["phone_match"],
                        "hr_blockers": ["workforce_active"],
                        "error_code": "DUPLICATE_REVIEW_PROBABLE",
                        "stamped_at": datetime.now(timezone.utc).isoformat(),
                    },
                },
                payload={},
            )
        )
        await db.commit()

    case_resp = await client.get(
        f"/api/v1/platform/marketing/diagnostics/submissions/{lead_id}",
        headers=_headers(auth_headers),
    )
    assert case_resp.status_code == 200, case_resp.text
    dup = case_resp.json()["duplicate"]
    assert dup["active"] is True
    assert dup["lead_status"] == "duplicate_review"
    assert dup["disposition"] == "blocked_duplicate"
    assert dup["match_level"] == "probable"
    assert dup["suggested_candidate_id"] == candidate_id
    assert dup["error_code"] == "DUPLICATE_REVIEW_PROBABLE"
    assert dup["needs_duplicate_review"] is True
    assert "phone_match" in dup["reasons"]
    assert "workforce_active" in dup["hr_blockers"]


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


@pytest.mark.asyncio
async def test_diagnostics_case_mapping_context(client: AsyncClient, auth_headers: Dict[str, str]):
    lead_id = str(uuid4())
    profile_id = str(uuid4())
    async with async_session_maker() as db:
        await _ensure_tenant(db, DEFAULT_TENANT_ID)
        oc = (
            await db.execute(
                select(OwnCompany.id)
                .where(OwnCompany.tenant_id == DEFAULT_TENANT_ID)
                .limit(1)
            )
        ).scalar_one_or_none()
        if oc is None:
            oc = str(uuid4())
            db.add(OwnCompany(id=oc, tenant_id=DEFAULT_TENANT_ID, name="Diag OC"))
            await db.flush()
        db.add(
            IntakeSourceProfile(
                id=profile_id,
                tenant_id=DEFAULT_TENANT_ID,
                code=f"diag-src-{uuid4().hex[:8]}",
                name="Diag Mapping Source",
                provider="meta",
                channel="paid",
                own_company_id=str(oc),
                route_intent="candidate_application",
                mapping_rules=[{"source": "email", "target": "email"}],
                is_active=True,
            )
        )
        db.add(
            Lead(
                id=lead_id,
                tenant_id=DEFAULT_TENANT_ID,
                source="meta",
                status="processed",
                lead_type="candidate",
                lead_target_type="candidate",
                external_id=f"meta-lead-{uuid4().hex[:10]}",
                normalized={
                    "full_name": "Mapped Person",
                    ACQUISITION_ROUTING_V1_KEY: {
                        "status": "routed",
                        "campaign_id": str(uuid4()),
                        "campaign_run_id": str(uuid4()),
                        "route_intent": "candidate_application",
                        "intake_source_profile_id": profile_id,
                    },
                },
                payload={},
            )
        )
        await db.commit()

    case_resp = await client.get(
        f"/api/v1/platform/marketing/diagnostics/submissions/{lead_id}",
        headers=_headers(auth_headers),
    )
    assert case_resp.status_code == 200, case_resp.text
    mapping = case_resp.json()["mapping"]
    assert mapping["active"] is True
    assert mapping["source_id"] == profile_id
    assert mapping["display_name"] == "Diag Mapping Source"
    assert mapping["mapping_health"] in {"ready", "needs_review"}
    assert mapping["mapping_rules_count"] >= 1
    assert mapping["historical_version_available"] is False
    assert mapping["profile_missing"] is False
    assert "/app/marketing/sources/" in (mapping["mapping_path"] or "")
    assert profile_id in (mapping["mapping_path"] or "")


@pytest.mark.asyncio
async def test_diagnostics_case_mapping_drift_from_applied_stamp(
    client: AsyncClient, auth_headers: Dict[str, str]
):
    lead_id = str(uuid4())
    profile_id = str(uuid4())
    from backend.app.acquisition.mapping_applied_stamp import fingerprint_mapping_rules

    applied_rules = [{"source": "email", "target": "email"}]
    current_rules = [
        {"source": "email", "target": "email"},
        {"source": "phone", "target": "phone"},
    ]
    async with async_session_maker() as db:
        await _ensure_tenant(db, DEFAULT_TENANT_ID)
        oc = (
            await db.execute(
                select(OwnCompany.id)
                .where(OwnCompany.tenant_id == DEFAULT_TENANT_ID)
                .limit(1)
            )
        ).scalar_one_or_none()
        if oc is None:
            oc = str(uuid4())
            db.add(OwnCompany(id=oc, tenant_id=DEFAULT_TENANT_ID, name="Diag OC2"))
            await db.flush()
        db.add(
            IntakeSourceProfile(
                id=profile_id,
                tenant_id=DEFAULT_TENANT_ID,
                code=f"diag-drift-{uuid4().hex[:8]}",
                name="Diag Drift Source",
                provider="meta",
                channel="paid",
                own_company_id=str(oc),
                route_intent="candidate_application",
                mapping_rules=current_rules,
                is_active=True,
            )
        )
        db.add(
            Lead(
                id=lead_id,
                tenant_id=DEFAULT_TENANT_ID,
                source="meta",
                status="processed",
                lead_type="candidate",
                lead_target_type="candidate",
                external_id=f"meta-lead-{uuid4().hex[:10]}",
                normalized={
                    "full_name": "Drift Person",
                    ACQUISITION_ROUTING_V1_KEY: {
                        "status": "routed",
                        "campaign_id": str(uuid4()),
                        "campaign_run_id": str(uuid4()),
                        "route_intent": "candidate_application",
                        "intake_source_profile_id": profile_id,
                    },
                    "mapping_applied_v1": {
                        "source_id": profile_id,
                        "rules_source": "profile",
                        "rules_count": 1,
                        "rules_fingerprint": fingerprint_mapping_rules(applied_rules),
                        "stamped_at": datetime.now(timezone.utc).isoformat(),
                    },
                },
                payload={},
            )
        )
        await db.commit()

    case_resp = await client.get(
        f"/api/v1/platform/marketing/diagnostics/submissions/{lead_id}",
        headers=_headers(auth_headers),
    )
    assert case_resp.status_code == 200, case_resp.text
    mapping = case_resp.json()["mapping"]
    assert mapping["historical_version_available"] is True
    assert mapping["drift"] is True
    assert mapping["applied_rules_count"] == 1
    assert mapping["mapping_rules_count"] >= 2


@pytest.mark.asyncio
async def test_diagnostics_list_drift_only_filter(
    client: AsyncClient, auth_headers: Dict[str, str]
):
    from backend.app.acquisition.mapping_applied_stamp import fingerprint_mapping_rules

    drifted_id = str(uuid4())
    stable_id = str(uuid4())
    profile_id = str(uuid4())
    applied_rules = [{"source": "email", "target": "email"}]
    current_rules = [
        {"source": "email", "target": "email"},
        {"source": "phone", "target": "phone"},
    ]
    flight_id = str(uuid4())
    async with async_session_maker() as db:
        await _ensure_tenant(db, DEFAULT_TENANT_ID)
        oc = (
            await db.execute(
                select(OwnCompany.id)
                .where(OwnCompany.tenant_id == DEFAULT_TENANT_ID)
                .limit(1)
            )
        ).scalar_one_or_none()
        if oc is None:
            oc = str(uuid4())
            db.add(OwnCompany(id=oc, tenant_id=DEFAULT_TENANT_ID, name="Diag OC Drift List"))
            await db.flush()
        db.add(
            IntakeSourceProfile(
                id=profile_id,
                tenant_id=DEFAULT_TENANT_ID,
                code=f"diag-drift-list-{uuid4().hex[:8]}",
                name="Diag Drift List Source",
                provider="meta",
                channel="paid",
                own_company_id=str(oc),
                route_intent="candidate_application",
                mapping_rules=current_rules,
                is_active=True,
            )
        )
        stamp_old = {
            "source_id": profile_id,
            "rules_source": "profile",
            "rules_count": 1,
            "rules_fingerprint": fingerprint_mapping_rules(applied_rules),
            "stamped_at": datetime.now(timezone.utc).isoformat(),
        }
        stamp_match = {
            "source_id": profile_id,
            "rules_source": "profile",
            "rules_count": 2,
            "rules_fingerprint": fingerprint_mapping_rules(current_rules),
            "stamped_at": datetime.now(timezone.utc).isoformat(),
        }
        for lead_id, stamp in ((drifted_id, stamp_old), (stable_id, stamp_match)):
            db.add(
                Lead(
                    id=lead_id,
                    tenant_id=DEFAULT_TENANT_ID,
                    source="meta",
                    status="processed",
                    lead_type="candidate",
                    lead_target_type="candidate",
                    external_id=f"meta-lead-{uuid4().hex[:10]}",
                    normalized={
                        "full_name": f"Person {lead_id[:8]}",
                        ACQUISITION_ROUTING_V1_KEY: {
                            "status": "routed",
                            "campaign_id": str(uuid4()),
                            "campaign_run_id": flight_id,
                            "route_intent": "candidate_application",
                            "intake_source_profile_id": profile_id,
                        },
                        "mapping_applied_v1": stamp,
                        "submissions_v1": [
                            {
                                "submission_id": str(uuid4()),
                                "submitted_at": datetime.now(timezone.utc).isoformat(),
                            }
                        ],
                    },
                    payload={},
                )
            )
        await db.commit()

    drifted = await client.get(
        "/api/v1/platform/marketing/diagnostics/submissions",
        headers=_headers(auth_headers),
        params={"drift_only": True, "limit": 50},
    )
    assert drifted.status_code == 200, drifted.text
    body = drifted.json()
    ids = {row["lead_id"] for row in body["items"]}
    assert drifted_id in ids
    assert stable_id not in ids
    for row in body["items"]:
        if row["lead_id"] == drifted_id:
            assert row["mapping_drift"] is True
    assert body["drift_alert_count"] >= 1

    unfiltered = await client.get(
        "/api/v1/platform/marketing/diagnostics/submissions",
        headers=_headers(auth_headers),
        params={"flight_id": flight_id, "limit": 50},
    )
    assert unfiltered.status_code == 200, unfiltered.text
    by_id = {row["lead_id"]: row for row in unfiltered.json()["items"]}
    assert by_id[drifted_id]["mapping_drift"] is True
    assert by_id[stable_id]["mapping_drift"] is False


@pytest.mark.asyncio
async def test_diagnostics_drift_summary_window(
    client: AsyncClient, auth_headers: Dict[str, str]
):
    from backend.app.acquisition.mapping_applied_stamp import fingerprint_mapping_rules

    drifted_id = str(uuid4())
    stable_id = str(uuid4())
    profile_id = str(uuid4())
    applied_rules = [{"source": "email", "target": "email"}]
    current_rules = [
        {"source": "email", "target": "email"},
        {"source": "phone", "target": "phone"},
    ]
    async with async_session_maker() as db:
        await _ensure_tenant(db, DEFAULT_TENANT_ID)
        oc = (
            await db.execute(
                select(OwnCompany.id)
                .where(OwnCompany.tenant_id == DEFAULT_TENANT_ID)
                .limit(1)
            )
        ).scalar_one_or_none()
        if oc is None:
            oc = str(uuid4())
            db.add(OwnCompany(id=oc, tenant_id=DEFAULT_TENANT_ID, name="Diag OC Drift Summary"))
            await db.flush()
        db.add(
            IntakeSourceProfile(
                id=profile_id,
                tenant_id=DEFAULT_TENANT_ID,
                code=f"diag-drift-sum-{uuid4().hex[:8]}",
                name="Diag Drift Summary Source",
                provider="meta",
                channel="paid",
                own_company_id=str(oc),
                route_intent="candidate_application",
                mapping_rules=current_rules,
                is_active=True,
            )
        )
        stamp_old = {
            "source_id": profile_id,
            "rules_source": "profile",
            "rules_count": 1,
            "rules_fingerprint": fingerprint_mapping_rules(applied_rules),
            "stamped_at": datetime.now(timezone.utc).isoformat(),
        }
        stamp_match = {
            "source_id": profile_id,
            "rules_source": "profile",
            "rules_count": 2,
            "rules_fingerprint": fingerprint_mapping_rules(current_rules),
            "stamped_at": datetime.now(timezone.utc).isoformat(),
        }
        for lead_id, stamp in ((drifted_id, stamp_old), (stable_id, stamp_match)):
            db.add(
                Lead(
                    id=lead_id,
                    tenant_id=DEFAULT_TENANT_ID,
                    source="meta",
                    status="processed",
                    lead_type="candidate",
                    lead_target_type="candidate",
                    external_id=f"meta-lead-{uuid4().hex[:10]}",
                    normalized={
                        "full_name": f"Person {lead_id[:8]}",
                        ACQUISITION_ROUTING_V1_KEY: {
                            "status": "routed",
                            "campaign_id": str(uuid4()),
                            "campaign_run_id": str(uuid4()),
                            "route_intent": "candidate_application",
                            "intake_source_profile_id": profile_id,
                        },
                        "mapping_applied_v1": stamp,
                        "submissions_v1": [
                            {
                                "submission_id": str(uuid4()),
                                "submitted_at": datetime.now(timezone.utc).isoformat(),
                            }
                        ],
                    },
                    payload={},
                )
            )
        await db.commit()

    resp = await client.get(
        "/api/v1/platform/marketing/diagnostics/drift-summary",
        headers=_headers(auth_headers),
        params={"window_hours": 168},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["window_hours"] == 168
    assert body["drift_count"] >= 1
    assert body["scanned"] >= 1
    assert "drift_only=1" in body["diagnostics_href"]
    assert isinstance(body["scan_capped"], bool)


@pytest.mark.asyncio
async def test_diagnostics_case_export_json(client: AsyncClient, auth_headers: Dict[str, str]):
    lead_id = str(uuid4())
    flight_id = str(uuid4())
    async with async_session_maker() as db:
        await _ensure_tenant(db, DEFAULT_TENANT_ID)
        db.add(
            _stamped_lead(
                lead_id=lead_id,
                source="meta",
                status="processed",
                flight_id=flight_id,
            )
        )
        await db.commit()

    resp = await client.get(
        f"/api/v1/platform/marketing/diagnostics/submissions/{lead_id}/export",
        headers=_headers(auth_headers),
    )
    assert resp.status_code == 200, resp.text
    assert "attachment" in (resp.headers.get("content-disposition") or "")
    assert f"diagnostics-case-{lead_id}.json" in (resp.headers.get("content-disposition") or "")
    body = resp.json()
    assert body["schema"] == "hostflow.marketing_diagnostics_export"
    assert body["schema_version"] == 1
    assert body["lead_id"] == lead_id
    assert body["flight_id"] == flight_id
    assert "payload" in body
    assert "normalized" in body
    assert "mapping" in body
    assert "duplicate" in body
    assert isinstance(body["timeline"], list)


@pytest.mark.asyncio
async def test_diagnostics_case_export_404(client: AsyncClient, auth_headers: Dict[str, str]):
    missing = str(uuid4())
    resp = await client.get(
        f"/api/v1/platform/marketing/diagnostics/submissions/{missing}/export",
        headers=_headers(auth_headers),
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "submission_not_found"
