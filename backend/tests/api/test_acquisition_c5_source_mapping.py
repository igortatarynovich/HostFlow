"""Acquisition UI Cutover C-5 — Marketing Sources mapping + routing preview API."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any, Dict
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.acquisition.mapping_applied_stamp import stamp_mapping_applied_v1
from backend.app.acquisition.submission_routing import ACQUISITION_ROUTING_V1_KEY
from backend.app.core.settings import settings
from backend.app.db.session import async_session_maker
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


def _meta_ingest_headers(base: Dict[str, str], payload: dict[str, Any]) -> Dict[str, str]:
    secret = str(settings.meta_webhook_secret or "").encode("utf-8")
    body = json.dumps(payload).encode("utf-8")
    digest = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return {**_headers(base), "X-Hub-Signature-256": f"sha256={digest}"}


def _meta_lead_payload(
    *,
    form_id: str,
    email: str,
    color: str,
    leadgen_id: str,
    page_id: str | None = None,
    vacancy_id: str | None = None,
) -> dict[str, Any]:
    field_data = [
        {"name": "email", "values": [email]},
        {"name": "favourite_color", "values": [color]},
    ]
    if vacancy_id:
        field_data.append({"name": "vacancy_id", "values": [vacancy_id]})
    value: dict[str, Any] = {
        "leadgen_id": leadgen_id,
        "form_id": form_id,
        "field_data": field_data,
    }
    if page_id:
        value["page_id"] = page_id
    entry: dict[str, Any] = {"changes": [{"value": value}]}
    if page_id:
        entry["id"] = page_id
    return {"entry": [entry]}


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


async def _make_meta_source(
    db,
    *,
    tenant_id: str,
    form_id: str,
    mapping_rules: list[dict[str, Any]] | None = None,
    page_id: str | None = None,
) -> IntakeSourceProfile:
    await _ensure_tenant(db, tenant_id)
    oc = await _own_company_id(db, tenant_id)
    page_key = str(page_id or f"page-{uuid4().hex[:6]}").strip()
    profile = IntakeSourceProfile(
        id=str(uuid4()),
        tenant_id=tenant_id,
        code=f"c5-src-{uuid4().hex[:8]}",
        name="C5 Meta Source",
        provider="meta",
        channel="paid",
        own_company_id=oc,
        route_intent="candidate_application",
        mapping_rules=list(mapping_rules or []),
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
            external_key_secondary=f"page_id:{page_key}",
            is_active=True,
            priority=10,
        )
    )
    await db.flush()
    return profile


@pytest.mark.anyio
async def test_get_put_mapping_persists_profile_rules(
    client: AsyncClient, manager_headers: Dict[str, str]
) -> None:
    form_id = f"form-c5-{uuid4().hex[:8]}"
    async with async_session_maker() as db:
        profile = await _make_meta_source(
            db,
            tenant_id=DEFAULT_TENANT_ID,
            form_id=form_id,
            mapping_rules=[{"source": "email", "target": "email"}],
        )
        await db.commit()
        source_id = str(profile.id)

    headers = _headers(manager_headers)
    got = await client.get(
        f"/api/v1/platform/marketing/sources/{source_id}/mapping",
        headers=headers,
    )
    assert got.status_code == 200, got.text
    body = got.json()
    assert body["source_id"] == source_id
    assert body["rules_source"] == "profile"
    assert body["destination"] == "candidate_application"
    assert body["mapping_rules_count"] >= 1
    assert body["applied_evidence"]["present"] is False

    put = await client.put(
        f"/api/v1/platform/marketing/sources/{source_id}/mapping",
        headers=headers,
        json={
            "mapping_rules": [
                {"source": "email", "target": "email"},
                {"source": "full_name", "target": "full_name"},
                {"source": "which_licence", "action": "ignore"},
            ]
        },
    )
    assert put.status_code == 200, put.text
    put_body = put.json()
    assert put_body["mapping_rules_count"] == 3
    assert put_body["rules_source"] == "profile"
    assert put_body["mapping_health"] in {"valid", "needs_review", "invalid"}
    assert put_body["mapping_health"] not in {"ready", "broken"}
    assert put_body["mapping_human"]

    async with async_session_maker() as db:
        row = (
            await db.execute(
                select(IntakeSourceProfile).where(IntakeSourceProfile.id == source_id)
            )
        ).scalar_one()
        rules = list(row.mapping_rules or [])
        sources = {str(r.get("source")) for r in rules if isinstance(r, dict)}
        assert sources == {"email", "full_name", "which_licence"}


@pytest.mark.anyio
async def test_mapping_workspace_returns_applied_evidence_from_last_submission(
    client: AsyncClient, manager_headers: Dict[str, str]
) -> None:
    form_id = f"form-c5-applied-{uuid4().hex[:8]}"
    rules = [
        {
            "source": "email",
            "target": "email",
            "qualified_field_code": "recruitment.candidate.contacts.email",
        }
    ]
    lead_id = str(uuid4())
    async with async_session_maker() as db:
        profile = await _make_meta_source(
            db,
            tenant_id=DEFAULT_TENANT_ID,
            form_id=form_id,
            mapping_rules=rules,
        )
        source_id = str(profile.id)
        normalized: dict[str, Any] = {
            "email": "anna@example.com",
            ACQUISITION_ROUTING_V1_KEY: {
                "status": "routed",
                "route_intent": "candidate_application",
                "intake_source_profile_id": source_id,
            },
        }
        stamp_mapping_applied_v1(
            normalized,
            rules=rules,
            source_id=source_id,
            rules_source="authority",
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
                normalized=normalized,
                payload={},
            )
        )
        await db.commit()

    headers = _headers(manager_headers)
    got = await client.get(
        f"/api/v1/platform/marketing/sources/{source_id}/mapping",
        headers=headers,
    )
    assert got.status_code == 200, got.text
    evidence = got.json()["applied_evidence"]
    assert evidence["present"] is True
    assert evidence["lead_id"] == lead_id
    assert evidence["drift"] is False
    assert evidence["rules_fingerprint"]
    sentences = " ".join(row["sentence"] for row in evidence["sentences"])
    assert "anna@example.com" in sentences
    assert "Last application wrote" in sentences


@pytest.mark.anyio
async def test_mapping_close_path_ready_projection_then_real_ingest_applied_evidence(
    client: AsyncClient, manager_headers: Dict[str, str]
) -> None:
    """Close path through ingest — not a hand-stamped Lead. Does not mark Operator Gate PASS."""
    form_id = f"form-c5-close-{uuid4().hex[:8]}"
    page_id = f"page-c5-close-{uuid4().hex[:6]}"
    async with async_session_maker() as db:
        from backend.tests.api.test_leads_meta import _ensure_company, _ensure_vacancy

        profile = await _make_meta_source(
            db,
            tenant_id=DEFAULT_TENANT_ID,
            form_id=form_id,
            page_id=page_id,
            mapping_rules=[],
        )
        company_id = await _ensure_company(db, DEFAULT_TENANT_ID)
        vacancy_id = await _ensure_vacancy(db, DEFAULT_TENANT_ID, company_id)
        await db.commit()
        source_id = str(profile.id)

    headers = _headers(manager_headers)
    saved = await client.put(
        f"/api/v1/platform/marketing/sources/{source_id}/mapping",
        headers=headers,
        json={
            "schema_snapshot": {
                "fields": [
                    {"source": "email", "label": "Email"},
                    {"source": "favourite_color", "label": "Favourite color"},
                ]
            },
            "mapping_rules": [
                {
                    "source": "email",
                    "target": "email",
                    "qualified_field_code": "recruitment.candidate.contacts.email",
                },
                {"source": "favourite_color", "action": "ignore"},
            ],
        },
    )
    assert saved.status_code == 200, saved.text
    workspace = saved.json()
    assert workspace["has_schema"] is True
    assert workspace["summary"]["headline"] == "all_set"
    assert workspace["summary"]["contract_health"] == "valid"
    assert workspace["applied_evidence"]["present"] is False
    projection_text = " ".join(item["sentence"] for item in workspace["projection"])
    assert "The next application will write" in projection_text
    by_source = {row["source"]: row for row in workspace["schema_fields"]}
    assert by_source["email"]["binding"] == "mapped"
    assert by_source["favourite_color"]["binding"] == "ignored"

    suffix = uuid4().hex[:8]
    email = f"close-{suffix}@example.com"
    payload = _meta_lead_payload(
        form_id=form_id,
        email=email,
        color="blue",
        leadgen_id=f"lg-close-{suffix}",
        page_id=page_id,
        vacancy_id=vacancy_id,
    )
    ingest = await client.post(
        "/api/v1/leads/meta",
        headers=_meta_ingest_headers(manager_headers, payload),
        content=json.dumps(payload),
    )
    assert ingest.status_code == 200, ingest.text
    ingest_body = ingest.json()
    lead_id = ingest_body.get("lead_id")
    assert lead_id

    after = await client.get(
        f"/api/v1/platform/marketing/sources/{source_id}/mapping",
        headers=headers,
    )
    assert after.status_code == 200, after.text
    evidence = after.json()["applied_evidence"]
    assert evidence["present"] is True
    assert evidence["lead_id"] == lead_id
    assert evidence["drift"] is False
    sentences = " ".join(row["sentence"] for row in evidence["sentences"])
    assert email in sentences
    assert "Last application wrote" in sentences
    assert "blue" not in sentences


@pytest.mark.anyio
async def test_routing_preview_flags_unmapped_without_creating_entities(
    client: AsyncClient, manager_headers: Dict[str, str]
) -> None:
    form_id = f"form-c5-prev-{uuid4().hex[:8]}"
    async with async_session_maker() as db:
        profile = await _make_meta_source(
            db,
            tenant_id=DEFAULT_TENANT_ID,
            form_id=form_id,
            mapping_rules=[{"source": "email", "target": "email"}],
        )
        await db.commit()
        source_id = str(profile.id)

    headers = _headers(manager_headers)
    sample_payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "form_id": form_id,
                            "leadgen_id": f"lg-{uuid4().hex[:10]}",
                            "field_data": [
                                {"name": "email", "values": ["anna@example.com"]},
                                {"name": "which_licence", "values": ["CE"]},
                            ],
                        }
                    }
                ]
            }
        ]
    }
    resp = await client.post(
        f"/api/v1/platform/marketing/sources/{source_id}/mapping/routing-preview",
        headers=headers,
        json={"sample_payload": sample_payload},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["creates_entities"] is False
    assert body["needs_review"] is True
    assert "which_licence" in body["unmapped_fields"]
    assert body["destination"] == "candidate_application"


@pytest.mark.anyio
async def test_mapping_tenant_isolation(
    client: AsyncClient, manager_headers: Dict[str, str]
) -> None:
    form_id = f"form-c5-iso-{uuid4().hex[:8]}"
    async with async_session_maker() as db:
        foreign = await _make_meta_source(
            db, tenant_id=OTHER_TENANT_ID, form_id=form_id
        )
        await db.commit()
        foreign_id = str(foreign.id)

    headers = _headers(manager_headers, tenant_id=DEFAULT_TENANT_ID)
    resp = await client.get(
        f"/api/v1/platform/marketing/sources/{foreign_id}/mapping",
        headers=headers,
    )
    assert resp.status_code == 404


def test_c5_router_exposes_mapping_routes() -> None:
    from backend.app.api.v1.platform import marketing_sources as mod

    paths = {getattr(route, "path", "") for route in mod.router.routes}
    assert any(p.endswith("/{source_id}/mapping") for p in paths)
    assert any(p.endswith("/{source_id}/mapping/routing-preview") for p in paths)


def test_build_source_paths_mapping_is_marketing_native() -> None:
    from backend.app.acquisition.sources_read import build_source_paths
    from backend.app.constants.spa_paths import MARKETING_SOURCES, SETTINGS_INTEGRATIONS_META

    mapping, test_lead, settings = build_source_paths(
        source_id="src-1",
        provider="meta",
        meta_form_id="form-1",
        lead_form_id=None,
    )
    assert mapping == f"{MARKETING_SOURCES}/src-1/mapping"
    assert test_lead == f"{MARKETING_SOURCES}/src-1/test-lead"
    assert settings == SETTINGS_INTEGRATIONS_META


@pytest.mark.anyio
async def test_mapping_workspace_schema_without_sample(
    client: AsyncClient, manager_headers: Dict[str, str]
) -> None:
    form_id = f"form-ma3-{uuid4().hex[:8]}"
    async with async_session_maker() as db:
        profile = await _make_meta_source(
            db,
            tenant_id=DEFAULT_TENANT_ID,
            form_id=form_id,
            mapping_rules=[],
        )
        await db.commit()
        source_id = str(profile.id)

    headers = _headers(manager_headers)
    put = await client.put(
        f"/api/v1/platform/marketing/sources/{source_id}/mapping",
        headers=headers,
        json={
            "schema_snapshot": {
                "fields": [
                    {
                        "source": "document_validity",
                        "label": "Срок действия документов",
                        "options": ["Менее 3 месяцев", "Более 8 месяцев"],
                    },
                    {"source": "favourite_color", "label": "Любимый цвет"},
                    {"source": "eu_experience", "label": "Стаж в ЕС"},
                ]
            },
            "mapping_rules": [
                {
                    "source": "document_validity",
                    "target": "document_validity",
                    "option_map": {"Более 8 месяцев": "GT_8_MONTHS"},
                },
                {"source": "favourite_color", "action": "ignore"},
            ],
        },
    )
    assert put.status_code == 200, put.text
    body = put.json()
    assert body["has_schema"] is True
    assert body["has_sample"] is False
    sources = [row["source"] for row in body["schema_fields"]]
    assert sources == ["document_validity", "favourite_color", "eu_experience"]
    by_source = {row["source"]: row for row in body["schema_fields"]}
    assert by_source["document_validity"]["binding"] == "mapped"
    assert by_source["favourite_color"]["binding"] == "ignored"
    assert by_source["eu_experience"]["binding"] == "unmapped"
    assert by_source["eu_experience"]["drift"] == "field_added"
    assert by_source["eu_experience"]["drift_human"]
    assert by_source["document_validity"]["drift"] in {"option_added", "destination_invalid"}
    assert body["summary"]["headline"] in {"option_drift", "destination_invalid"}
    assert body["summary"]["unmapped_count"] == 1
    assert body["projection"]
    assert "document_validity" in body["projection"][0]["sentence"]
    assert "Менее 3 месяцев" not in body["projection"][0]["sentence"]
    assert "Более 8 месяцев" not in body["projection"][0]["sentence"]

    got = await client.get(
        f"/api/v1/platform/marketing/sources/{source_id}/mapping",
        headers=headers,
    )
    assert got.status_code == 200, got.text
    again = got.json()
    assert again["has_sample"] is False
    assert len(again["schema_fields"]) == 3
    assert again["schema_fields"][0]["option_map"]["Более 8 месяцев"] == "GT_8_MONTHS"


def test_workspace_rows_do_not_require_sample() -> None:
    from backend.app.acquisition.mapping_workspace import build_workspace_rows

    rows, summary = build_workspace_rows(
        schema_fields=[
            {"source": "q1", "label": "Question 1", "options": []},
            {"source": "q2", "label": "Question 2", "options": []},
        ],
        mapping_rules=[],
        sample_by_source={},
        destinations=[],
        has_schema=True,
    )
    assert [r["source"] for r in rows] == ["q1", "q2"]
    assert all(r["binding"] == "unmapped" for r in rows)
    assert summary["headline"] == "needs_check"
    assert summary["total_count"] == 2


def test_incomplete_option_map_is_not_ready() -> None:
    from backend.app.acquisition.mapping_workspace import build_workspace_rows

    rows, summary = build_workspace_rows(
        schema_fields=[
            {
                "source": "document_validity",
                "label": "Document validity",
                "options": ["Under 3 months", "Over 8 months"],
            }
        ],
        mapping_rules=[
            {
                "source": "document_validity",
                "qualified_field_code": "candidate.document_validity",
                "option_map": {},
            }
        ],
        sample_by_source={},
        destinations=[
            {
                "code": "candidate.document_validity",
                "label": "Document validity",
                "field_type": "select",
                "choice": True,
                "aliases": [],
                "options": [
                    {"value": "LT_3_MONTHS", "label": "Under 3 months"},
                    {"value": "GT_8_MONTHS", "label": "Over 8 months"},
                ],
            }
        ],
        has_schema=True,
    )
    assert rows[0]["drift"] is None
    assert rows[0]["incomplete_options"] is True
    assert summary["headline"] == "needs_check"
    assert summary["contract_health"] == "needs_review"


def test_option_added_is_named_taxonomy_not_ready() -> None:
    from backend.app.acquisition.mapping_workspace import build_workspace_rows

    rows, summary = build_workspace_rows(
        schema_fields=[
            {
                "source": "document_validity",
                "label": "Document validity",
                "options": ["Under 3 months", "Over 8 months"],
            }
        ],
        mapping_rules=[
            {
                "source": "document_validity",
                "qualified_field_code": "candidate.document_validity",
                "option_map": {"Over 8 months": "GT_8_MONTHS"},
            }
        ],
        sample_by_source={},
        destinations=[
            {
                "code": "candidate.document_validity",
                "label": "Document validity",
                "field_type": "select",
                "choice": True,
                "aliases": [],
                "options": [
                    {"value": "LT_3_MONTHS", "label": "Under 3 months"},
                    {"value": "GT_8_MONTHS", "label": "Over 8 months"},
                ],
            }
        ],
        has_schema=True,
    )
    assert rows[0]["drift"] == "option_added"
    assert summary["headline"] == "option_drift"
    assert summary["contract_health"] == "needs_review"


def test_complete_option_decisions_are_ready() -> None:
    from backend.app.acquisition.mapping_workspace import (
        OPTION_IGNORE_VALUE,
        build_workspace_rows,
    )

    rows, summary = build_workspace_rows(
        schema_fields=[
            {
                "source": "document_validity",
                "label": "Document validity",
                "options": ["Under 3 months", "Over 8 months"],
            }
        ],
        mapping_rules=[
            {
                "source": "document_validity",
                "qualified_field_code": "candidate.document_validity",
                "option_map": {
                    "Under 3 months": OPTION_IGNORE_VALUE,
                    "Over 8 months": "GT_8_MONTHS",
                },
            }
        ],
        sample_by_source={},
        destinations=[
            {
                "code": "candidate.document_validity",
                "label": "Document validity",
                "field_type": "select",
                "choice": True,
                "aliases": [],
                "options": [{"value": "GT_8_MONTHS", "label": "Over 8 months"}],
            }
        ],
        has_schema=True,
    )
    assert rows[0]["drift"] is None
    assert summary["headline"] == "all_set"
    assert summary["contract_health"] == "valid"


def test_projection_does_not_pass_through_raw_option() -> None:
    from backend.app.acquisition.mapping_workspace import build_projection, build_workspace_rows

    rows, _summary = build_workspace_rows(
        schema_fields=[
            {
                "source": "document_validity",
                "label": "Document validity",
                "options": ["Более 8 месяцев"],
            }
        ],
        mapping_rules=[
            {
                "source": "document_validity",
                "qualified_field_code": "candidate.document_validity",
                "option_map": {"Более 8 месяцев": "GT_8_MONTHS"},
            }
        ],
        sample_by_source={"document_validity": "Более 8 месяцев"},
        destinations=[
            {
                "code": "candidate.document_validity",
                "label": "Document validity",
                "field_type": "select",
                "choice": True,
                "aliases": [],
                "options": [{"value": "GT_8_MONTHS", "label": "Over 8 months"}],
            }
        ],
        has_schema=True,
    )
    projection = build_projection(rows)
    assert projection
    assert projection[0]["example_out"] == "Over 8 months"
    assert "Более 8 месяцев" not in projection[0]["sentence"]
    assert "Over 8 months" in projection[0]["sentence"]


def test_drift_taxonomy_names_all_six_classes() -> None:
    from backend.app.acquisition.mapping_workspace import (
        DRIFT_DESTINATION_INVALID,
        DRIFT_FIELD_ADDED,
        DRIFT_FIELD_REMOVED,
        DRIFT_HUMAN,
        DRIFT_OPTION_ADDED,
        DRIFT_OPTION_REMOVED,
        DRIFT_TYPE_CHANGED,
        TAXONOMY_DRIFT,
        build_workspace_rows,
    )

    assert TAXONOMY_DRIFT == {
        DRIFT_FIELD_ADDED,
        DRIFT_FIELD_REMOVED,
        DRIFT_OPTION_ADDED,
        DRIFT_OPTION_REMOVED,
        DRIFT_TYPE_CHANGED,
        DRIFT_DESTINATION_INVALID,
    }
    dests = [
        {
            "code": "candidate.email",
            "label": "Email",
            "field_type": "string",
            "choice": False,
            "aliases": [],
            "options": [],
        }
    ]
    rows, summary = build_workspace_rows(
        schema_fields=[
            {
                "source": "color",
                "label": "Color",
                "options": ["red", "blue"],
                "field_type": "choice",
            },
            {"source": "gone_dest", "label": "Gone dest", "options": []},
        ],
        mapping_rules=[
            {"source": "color", "qualified_field_code": "candidate.email"},
            {"source": "gone_dest", "qualified_field_code": "candidate.missing"},
            {"source": "removed_q", "qualified_field_code": "candidate.email"},
        ],
        sample_by_source={},
        destinations=dests,
        has_schema=True,
    )
    by_source = {r["source"]: r for r in rows}
    assert by_source["color"]["drift"] == DRIFT_TYPE_CHANGED
    assert by_source["gone_dest"]["drift"] == DRIFT_DESTINATION_INVALID
    assert by_source["removed_q"]["drift"] == DRIFT_FIELD_REMOVED
    assert by_source["removed_q"]["historical"] is True
    assert by_source["color"]["drift_human"] == DRIFT_HUMAN[DRIFT_TYPE_CHANGED]
    assert summary["contract_health"] == "invalid"
    assert summary["headline"] == DRIFT_DESTINATION_INVALID


def test_option_removed_and_field_added_are_named() -> None:
    from backend.app.acquisition.mapping_workspace import build_workspace_rows

    rows, summary = build_workspace_rows(
        schema_fields=[
            {
                "source": "validity",
                "label": "Validity",
                "options": ["a"],
                "field_type": "choice",
            },
            {"source": "new_q", "label": "New", "options": []},
        ],
        mapping_rules=[
            {
                "source": "validity",
                "qualified_field_code": "candidate.document_validity",
                "option_map": {"a": "A", "old": "B"},
            }
        ],
        sample_by_source={},
        destinations=[
            {
                "code": "candidate.document_validity",
                "label": "Validity",
                "field_type": "select",
                "choice": True,
                "aliases": [],
                "options": [{"value": "A", "label": "A"}],
            }
        ],
        has_schema=True,
    )
    by_source = {r["source"]: r for r in rows}
    assert by_source["validity"]["drift"] == "option_removed"
    assert by_source["new_q"]["drift"] == "field_added"
    assert "new question" in summary["human"].lower() or "form changed" in summary["human"].lower()
    assert summary["headline"] in {"option_drift", "option_removed"}
