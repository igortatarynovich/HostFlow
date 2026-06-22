from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import func, select, text, update

from backend.app.db.session import async_session_maker
from backend.app.models.candidate import Candidate
from backend.app.models.candidate_consent import CandidateConsent
from backend.app.models.candidate_employment import CandidateEmployment
from backend.app.models.company import Company
from backend.app.models.own_company import OwnCompany
from backend.app.models.audit import ActivityLog
from backend.app.models.intake_routing import IntakeSourceProfile
from backend.app.models.lead import Lead
from backend.app.models.user_notification import UserNotification
from backend.app.models.tenant import TenantLicense
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.app.modules.leads import crud as leads_crud
from backend.tests.api.test_leads_meta import _ensure_company, _ensure_vacancy


pytestmark = pytest.mark.anyio


@pytest_asyncio.fixture(autouse=True)
async def _bump_max_candidates_for_public_intake_tests(tenant_id: str) -> None:
    """Default tenant DB often exceeds license cap; public intake creates new candidates."""
    async with async_session_maker() as session:
        lic = (
            await session.execute(select(TenantLicense).where(TenantLicense.tenant_id == tenant_id).limit(1))
        ).scalar_one_or_none()
        if lic is not None:
            lic.max_candidates_active = 500_000
            await session.commit()


def _headers(tenant_id: str) -> Dict[str, str]:
    return {"X-Tenant-Id": tenant_id}


async def _seed_active_lead_form(tenant_id: str, *, prefix: str = "intake") -> str:
    slug = f"{prefix}-{uuid4().hex[:10]}"
    async with async_session_maker() as session:
        session.add(
            TenantLeadForm(
                id=str(uuid4()),
                tenant_id=tenant_id,
                title="Public intake test form",
                public_slug=slug,
                is_active=True,
            )
        )
        await session.commit()
    return slug


async def _seed_company_intake_source_profile(tenant_id: str, *, prefix: str = "company-source") -> tuple[str, str]:
    slug = f"{prefix}-{uuid4().hex[:10]}"
    async with async_session_maker() as session:
        own_company_id = await session.scalar(
            select(OwnCompany.id)
            .where(OwnCompany.tenant_id == tenant_id, OwnCompany.is_archived.is_(False))
            .order_by(OwnCompany.created_at.asc())
            .limit(1)
        )
        assert own_company_id is not None
        session.add(
            IntakeSourceProfile(
                id=str(uuid4()),
                tenant_id=tenant_id,
                code=f"b2b-{slug}",
                name="Work Host Business — B2B Transport Companies",
                provider="public_intake",
                channel="paid_social",
                own_company_id=str(own_company_id),
                route_intent="sales_inquiry",
                public_slug=slug,
                form_type="company_intake",
                lead_type="client",
                lead_target_type="client_lead",
                source="meta_ads",
                default_language="pl",
                supported_languages="pl,en,ru",
                is_active=True,
            )
        )
        await session.commit()
    return slug, str(own_company_id)


async def _fetch_candidate(candidate_id: str) -> Candidate | None:
    async with async_session_maker() as session:
        stmt = select(Candidate).where(Candidate.id == candidate_id)
        return await session.scalar(stmt)


async def _list_employments(candidate_id: str) -> list[CandidateEmployment]:
    async with async_session_maker() as session:
        stmt = select(CandidateEmployment).where(CandidateEmployment.candidate_id == candidate_id)
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def _list_consents(candidate_id: str) -> list[CandidateConsent]:
    async with async_session_maker() as session:
        stmt = select(CandidateConsent).where(CandidateConsent.candidate_id == candidate_id)
        result = await session.execute(stmt)
        return list(result.scalars().all())


@pytest.mark.asyncio
async def test_public_intake_full_flow(client: AsyncClient, tenant_id: str) -> None:
    slug = await _seed_active_lead_form(tenant_id, prefix="full")
    phone_suffix = uuid4().hex[:9]
    phone = f"555{phone_suffix}"
    create_resp = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={
            "contacts": {"phone_country_code": "+48", "phone": phone},
            "source": "landing-page",
            "lead_form_slug": slug,
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    created = create_resp.json()
    token = created["token"]
    lead_id = created.get("lead_id")
    assert lead_id
    assert not created.get("candidate_id")

    get_resp = await client.get(f"/api/v1/public/apply/{token}", headers=_headers(tenant_id))
    assert get_resp.status_code == 200, get_resp.text
    draft = get_resp.json()
    assert draft["status"] == "draft"
    assert draft.get("lead_id") == lead_id
    assert draft["data"]["contacts"]["phone"] == phone
    doc_types = draft["documents"].get("doc_types") or {}
    driver_license_meta = doc_types.get("driver_license")
    assert driver_license_meta is not None
    assert "required_files" in driver_license_meta
    assert "metadata_schema" in driver_license_meta
    assert draft.get("stage")
    assert draft.get("created_at")
    assert isinstance(draft.get("timeline"), list)
    assert draft["timeline"][0]["key"] == "intake_created"
    assert draft.get("status_share_token")

    update_payload = {
        "data": {
            "contacts": {
                "phone_country_code": "+48",
                "phone": phone,
                "email": "driver@example.com",
                "preferred_messenger": "whatsapp",
            },
            "personal": {
                "full_name": "Jan Kowalski",
                "citizenship": "PL",
                "residency_status": "card",
            },
            "experience": {
                "years_ce": 5,
                "intl_experience": True,
                "trailer_types": ["tautliner"],
                "route_types": ["PL-DE"],
            },
            "employments": [
                {
                    "employer_name": "Trans Co",
                    "country": "PL",
                    "position": "Driver CE",
                    "start_date": "2023-01-01",
                    "end_date": "2023-12-01",
                    "trailer_types": ["tautliner"],
                    "route_types": ["PL-DE"],
                    "reason_for_leaving": "Relocation",
                }
            ],
            "agreements": {"general": False, "employer_share": True, "terms_acceptance": True},
        }
    }

    put_resp = await client.put(
        f"/api/v1/public/apply/{token}",
        headers=_headers(tenant_id),
        json=update_payload,
    )
    assert put_resp.status_code == 200, put_resp.text
    payload = put_resp.json()
    assert payload["data"]["personal"]["full_name"] == "Jan Kowalski"
    assert payload["data"]["experience"]["years_ce"] == 5
    assert payload["data"]["employments"][0]["employer_name"] == "Trans Co"
    assert payload["data"]["contacts"]["email"] == "driver@example.com"

    async with async_session_maker() as session:
        lead = await session.get(Lead, lead_id)
        assert lead is not None
        assert lead.stage == "intake_draft"
        assert not lead.candidate_id

    submit_resp = await client.post(
        f"/api/v1/public/apply/{token}/submit",
        headers=_headers(tenant_id),
        json={
            "consents": {"general": True, "employer_share": True, "terms_acceptance": True},
            "documents_version": {
                "privacy": "2025-02-01",
                "terms": "2025-02-01",
                "cookies": "2025-02-01",
            },
            "cookies_accepted": True,
        },
    )
    assert submit_resp.status_code == 200, submit_resp.text
    submitted = submit_resp.json()
    assert submitted["status"] == "submitted"
    assert submitted.get("lead_id") == lead_id

    async with async_session_maker() as session:
        lead = await session.get(Lead, lead_id)
        assert lead is not None
        assert (lead.normalized or {}).get("decision_result_v1") is not None
        candidate_id = lead.candidate_id or submitted.get("candidate_id")
        if candidate_id:
            candidate = await _fetch_candidate(candidate_id)
            assert candidate is not None
            consents = await _list_consents(candidate_id)
            assert len(consents) == 4
            assert {row.consent_code for row in consents} == {"general", "employer_share", "terms_acceptance", "cookies"}
            employments = await _list_employments(candidate_id)
            assert len(employments) == 1
            assert employments[0].employer_name == "Trans Co"


@pytest.mark.asyncio
async def test_public_intake_requires_contact(client: AsyncClient, tenant_id: str) -> None:
    slug = await _seed_active_lead_form(tenant_id, prefix="nocontact")
    resp = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={"contacts": {}, "lead_form_slug": slug},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_public_intake_token_expired(client: AsyncClient, tenant_id: str) -> None:
    slug = await _seed_active_lead_form(tenant_id, prefix="exp")
    create_resp = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={"contacts": {"email": "draft@example.com"}, "lead_form_slug": slug},
    )
    token = create_resp.json()["token"]
    lead_id = create_resp.json().get("lead_id")

    async with async_session_maker() as session:
        if lead_id:
            lead = await session.get(Lead, lead_id)
            assert lead is not None
            norm = dict(lead.normalized or {})
            block = dict(norm.get("public_intake_draft_v1") or {})
            block["intake_token_expires_at"] = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
            norm["public_intake_draft_v1"] = block
            lead.normalized = norm
        else:
            candidate_id = create_resp.json()["candidate_id"]
            await session.execute(
                update(Candidate)
                .where(Candidate.id == candidate_id)
                .values(intake_token_expires_at=datetime.now(timezone.utc) - timedelta(days=1))
            )
        await session.commit()

    resp = await client.get(f"/api/v1/public/apply/{token}", headers=_headers(tenant_id))
    assert resp.status_code == 410


@pytest.mark.asyncio
async def test_public_intake_document_upload_and_download(client: AsyncClient, tenant_id: str) -> None:
    slug = await _seed_active_lead_form(tenant_id, prefix="doc")
    create_resp = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={"contacts": {"email": "upload@example.com"}, "lead_form_slug": slug},
    )
    assert create_resp.status_code == 200
    token = create_resp.json()["token"]

    files = {"file": ("passport.pdf", b"%PDF-1.4 test content", "application/pdf")}
    data = {"doc_type": "passport"}
    upload_resp = await client.post(
        f"/api/v1/public/apply/{token}/documents/upload",
        headers=_headers(tenant_id),
        data=data,
        files=files,
    )
    assert upload_resp.status_code == 200, upload_resp.text
    uploaded_state = upload_resp.json()
    documents = uploaded_state["documents"]["documents"]
    passport_entry = next((doc for doc in documents if doc.get("doc_type") == "passport"), None)
    assert passport_entry is not None
    assert passport_entry["has_files"] is True
    assert passport_entry["download_url"]
    doc_types = uploaded_state["documents"].get("doc_types") or {}
    passport_meta = doc_types.get("passport")
    assert passport_meta is not None
    assert passport_meta.get("title", {}).get("ru")
    timeline = uploaded_state.get("timeline") or []
    assert any(entry.get("key") == "documents_upload" for entry in timeline)

    download_resp = await client.get(passport_entry["download_url"], headers=_headers(tenant_id))
    assert download_resp.status_code == 200
    assert download_resp.headers["content-type"].startswith("application/pdf")


@pytest.mark.asyncio
async def test_public_intake_reuses_existing_candidate(client: AsyncClient, tenant_id: str) -> None:
    slug = await _seed_active_lead_form(tenant_id, prefix="reuse")
    first_resp = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={
            "contacts": {"phone_country_code": "+48", "phone": "555123456"},
            "lead_form_slug": slug,
        },
    )
    assert first_resp.status_code == 200, first_resp.text
    first_data = first_resp.json()

    second_resp = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={
            "contacts": {"phone_country_code": "+48", "phone": "555123456", "email": "second@example.com"},
            "source": "retarget",
            "lead_form_slug": slug,
        },
    )
    assert second_resp.status_code == 200, second_resp.text
    second_data = second_resp.json()

    assert second_data["lead_id"] == first_data["lead_id"]
    assert second_data["token"] == first_data["token"]


@pytest.mark.asyncio
async def test_public_intake_matches_phone_digits_without_country_code(client: AsyncClient, tenant_id: str) -> None:
    slug = await _seed_active_lead_form(tenant_id, prefix="phone")
    candidate_id = str(uuid4())
    async with async_session_maker() as session:
        existing = Candidate(
            id=candidate_id,
            tenant_id=tenant_id,
            first_name="Lead",
            last_name="Driver",
            phone="+48 700 200 300",
            phone_country_code=None,
            intake_status="draft",
            stage="docs_wait",
        )
        session.add(existing)
        await session.commit()

    resp = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={"contacts": {"phone_country_code": "+48", "phone": "700200300"}, "lead_form_slug": slug},
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["candidate_id"] == candidate_id
    assert payload["token"]

    candidate = await _fetch_candidate(candidate_id)
    assert candidate is not None
    assert candidate.intake_token == payload["token"]

    presign_resp = await client.post(
        f"/api/v1/public/apply/{payload['token']}/documents/presign",
        headers=_headers(tenant_id),
        json={"doc_type": "visa", "filename": "visa.pdf"},
    )
    assert presign_resp.status_code == 200, presign_resp.text
    presign = presign_resp.json()
    assert presign["key"].endswith(".pdf")

    upload_url = presign["url"]
    put_resp = await client.put(
        upload_url,
        headers=_headers(tenant_id),
        content=b"PDF binary data",
    )
    assert put_resp.status_code == 204, put_resp.text


@pytest.mark.asyncio
async def test_public_status_endpoint(client: AsyncClient, tenant_id: str) -> None:
    slug = await _seed_active_lead_form(tenant_id, prefix="status")
    create_resp = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={"contacts": {"email": "status@example.com"}, "lead_form_slug": slug},
    )
    assert create_resp.status_code == 200
    token = create_resp.json()["token"]

    get_resp = await client.get(f"/api/v1/public/apply/{token}", headers=_headers(tenant_id))
    assert get_resp.status_code == 200
    draft = get_resp.json()
    share_token = draft["status_share_token"]
    assert share_token

    status_resp = await client.get(f"/api/v1/public/status/{share_token}", headers=_headers(tenant_id))
    assert status_resp.status_code == 200, status_resp.text
    status_payload = status_resp.json()
    assert status_payload["candidate_id"] == draft["candidate_id"]
    assert status_payload["timeline"]
    assert status_payload["documents"]


@pytest.mark.asyncio
async def test_public_status_tolerates_invalid_stored_email(client: AsyncClient, tenant_id: str) -> None:
    """Garbage emails on the candidate row must not break /public/status (used by documents upload link)."""
    share_token = f"st_{uuid4().hex}"
    candidate_id = str(uuid4())
    async with async_session_maker() as session:
        session.add(
            Candidate(
                id=candidate_id,
                tenant_id=tenant_id,
                first_name="X",
                last_name="Y",
                email="not-a-valid-email",
                status_share_token=share_token,
                status_share_token_expires_at=datetime.now(timezone.utc) + timedelta(days=30),
                intake_status="draft",
            )
        )
        await session.commit()

    status_resp = await client.get(f"/api/v1/public/status/{share_token}", headers=_headers(tenant_id))
    assert status_resp.status_code == 200, status_resp.text
    body = status_resp.json()
    assert body["candidate_id"] == candidate_id
    assert body["contacts"]["email"] is None


@pytest.mark.asyncio
async def test_public_magic_link_flow(client: AsyncClient, tenant_id: str) -> None:
    slug = f"magic-flow-{uuid4().hex[:10]}"
    async with async_session_maker() as session:
        session.add(
            TenantLeadForm(
                id=str(uuid4()),
                tenant_id=tenant_id,
                title="Magic test form",
                public_slug=slug,
                is_active=True,
            )
        )
        await session.commit()

    email = f"magic-{uuid4().hex[:10]}@example.com"
    create_resp = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={"contacts": {"email": email}, "lead_form_slug": slug},
    )
    assert create_resp.status_code == 200, create_resp.text
    intake_token = create_resp.json()["token"]

    req_resp = await client.post(
        "/api/v1/public/magic-link/request",
        headers=_headers(tenant_id),
        json={"email": email, "intake_token": intake_token},
    )
    assert req_resp.status_code == 200

    async with async_session_maker() as session:
        r = await session.execute(
            text("SELECT token FROM magic_links WHERE contact_value = :cv LIMIT 1"),
            {"cv": email.lower()},
        )
        row = r.first()
        assert row is not None
        token = row[0]

    redeem_resp = await client.get(f"/api/v1/public/magic-link/{token}", headers=_headers(tenant_id))
    assert redeem_resp.status_code == 200, redeem_resp.text
    payload = redeem_resp.json()
    assert payload["token"]
    assert payload["apply_url"].endswith(payload["token"])

    apply_token = payload["token"]
    presign_resp = await client.post(
        f"/api/v1/public/apply/{apply_token}/documents/presign",
        headers=_headers(tenant_id),
        json={"doc_type": "visa", "filename": "visa.pdf"},
    )
    assert presign_resp.status_code == 200, presign_resp.text
    presign = presign_resp.json()
    put_magic = await client.put(
        presign["url"],
        headers=_headers(tenant_id),
        content=b"PDF binary data",
    )
    assert put_magic.status_code == 204, put_magic.text

    complete_resp = await client.post(
        f"/api/v1/public/apply/{apply_token}/documents/upload",
        headers=_headers(tenant_id),
        data={"doc_type": "visa", "storage_key": presign["key"]},
    )
    assert complete_resp.status_code == 200, complete_resp.text
    completed_state = complete_resp.json()
    visa_entry = next((doc for doc in completed_state["documents"]["documents"] if doc.get("doc_type") == "visa"), None)
    assert visa_entry is not None
    assert visa_entry["has_files"] is True


@pytest.mark.asyncio
async def test_public_intake_create_with_vacancy_id(client: AsyncClient, tenant_id: str) -> None:
    slug = f"vac-intake-{uuid4().hex[:10]}"
    async with async_session_maker() as session:
        from backend.app.entity_profile.seed import ensure_tenant_entity_profile_defaults
        from backend.app.seed_candidate_profiles import ensure_driver_ce_default_profile

        await ensure_tenant_entity_profile_defaults(session, tenant_id)
        await ensure_driver_ce_default_profile(session, tenant_id)
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)
        session.add(
            TenantLeadForm(
                id=str(uuid4()),
                tenant_id=tenant_id,
                title="Vacancy intake form",
                public_slug=slug,
                is_active=True,
            )
        )
        await session.commit()

    create_resp = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={
            "contacts": {"phone_country_code": "+48", "phone": f"555{uuid4().int % 10**6:06d}"},
            "source": "test-vacancy-intake",
            "lead_form_slug": slug,
            "vacancy_id": vacancy_id,
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    body = create_resp.json()
    assert body.get("lead_id")
    assert not body.get("candidate_id")
    token = body["token"]

    async with async_session_maker() as session:
        lead = await session.get(Lead, body["lead_id"])
        assert lead is not None
        assert lead.vacancy_id == vacancy_id

    submit_resp = await client.post(
        f"/api/v1/public/apply/{token}/submit",
        headers=_headers(tenant_id),
        json={
            "consents": {"general": True, "employer_share": True, "terms_acceptance": True},
            "documents_version": {"privacy": "2025-02-01", "terms": "2025-02-01", "cookies": "2025-02-01"},
            "cookies_accepted": True,
        },
    )
    assert submit_resp.status_code == 200, submit_resp.text
    submitted = submit_resp.json()
    candidate_id = submitted.get("candidate_id")
    if candidate_id:
        row = await _fetch_candidate(candidate_id)
        assert row is not None
        assert row.vacancy_id == vacancy_id


@pytest.mark.asyncio
async def test_public_intake_create_unknown_vacancy_id_404(client: AsyncClient, tenant_id: str) -> None:
    slug = f"vac-unknown-{uuid4().hex[:10]}"
    async with async_session_maker() as session:
        session.add(
            TenantLeadForm(
                id=str(uuid4()),
                tenant_id=tenant_id,
                title="Unknown vacancy form",
                public_slug=slug,
                is_active=True,
            )
        )
        await session.commit()

    missing = str(uuid4())
    create_resp = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={
            "contacts": {"phone_country_code": "+48", "phone": "555000222"},
            "source": "test-unknown-vacancy",
            "lead_form_slug": slug,
            "vacancy_id": missing,
        },
    )
    assert create_resp.status_code == 404, create_resp.text
    detail = create_resp.json().get("detail")
    assert isinstance(detail, dict)
    assert detail.get("code") == "intake_vacancy_not_found"


@pytest.mark.asyncio
async def test_public_intake_create_vacancy_wrong_tenant_404(client: AsyncClient, tenant_id: str) -> None:
    slug = f"vac-wrong-{uuid4().hex[:10]}"
    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        vacancy_id = await _ensure_vacancy(session, tenant_id, company_id)
        other_tenant = str(uuid4())
        await session.execute(
            text("UPDATE vacancies SET tenant_id = :tid WHERE id = :vid"),
            {"tid": other_tenant, "vid": vacancy_id},
        )
        session.add(
            TenantLeadForm(
                id=str(uuid4()),
                tenant_id=tenant_id,
                title="Wrong-tenant vacancy form",
                public_slug=slug,
                is_active=True,
            )
        )
        await session.commit()

    create_resp = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={
            "contacts": {"phone_country_code": "+48", "phone": "555000333"},
            "source": "test-wrong-tenant-vacancy",
            "lead_form_slug": slug,
            "vacancy_id": vacancy_id,
        },
    )
    assert create_resp.status_code == 404, create_resp.text
    detail = create_resp.json().get("detail")
    assert isinstance(detail, dict)
    assert detail.get("code") == "intake_vacancy_not_found"


@pytest.mark.asyncio
async def test_public_intake_client_application_creates_lead_on_submit(client: AsyncClient, tenant_id: str) -> None:
    slug = await _seed_active_lead_form(tenant_id, prefix="client-app")
    suffix = uuid4().hex[:10]
    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        row = await leads_crud.get_meta_settings(session, tenant_id=tenant_id)
        if row is None:
            await leads_crud.create_meta_settings(session, tenant_id=tenant_id, default_company_id=company_id)
        else:
            await leads_crud.update_meta_settings(session, row, default_company_id=company_id)
        await session.commit()

    create_resp = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={
            "contacts": {"phone_country_code": "+48", "phone": f"557{suffix}"},
            "lead_form_slug": slug,
            "application_kind": "client",
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    token = create_resp.json()["token"]
    lead_id = create_resp.json()["lead_id"]
    assert lead_id
    assert not create_resp.json().get("candidate_id")

    get_resp = await client.get(f"/api/v1/public/apply/{token}", headers=_headers(tenant_id))
    assert get_resp.status_code == 200, get_resp.text
    assert get_resp.json().get("data", {}).get("application_kind") == "client"

    submit_resp = await client.post(
        f"/api/v1/public/apply/{token}/submit",
        headers=_headers(tenant_id),
        json={
            "consents": {"general": True, "employer_share": True, "terms_acceptance": True},
            "documents_version": {"privacy": "2025-02-01", "terms": "2025-02-01", "cookies": "2025-02-01"},
            "cookies_accepted": True,
        },
    )
    assert submit_resp.status_code == 200, submit_resp.text

    async with async_session_maker() as session:
        lead = await session.get(Lead, lead_id)
        assert lead is not None
        assert lead.lead_type == "client"
        assert lead.lead_target_type == "client_lead"
        assert lead.candidate_id is None
        assert lead.own_company_id is not None
        assert lead.company_id is None
        assert lead.vacancy_id is None
        assert lead.converted_client_id is None

        notif_n = (
            await session.execute(
                select(func.count())
                .select_from(UserNotification)
                .where(
                    UserNotification.tenant_id == tenant_id,
                    UserNotification.event_type == "lead_public_intake_client",
                )
            )
        ).scalar_one()
        assert int(notif_n or 0) >= 1


@pytest.mark.asyncio
async def test_public_intake_client_creates_company_lead_without_company(
    client: AsyncClient, tenant_id: str
) -> None:
    slug = await _seed_active_lead_form(tenant_id, prefix="client-skip")
    suffix = uuid4().hex[:10]
    async with async_session_maker() as session:
        row = await leads_crud.get_meta_settings(session, tenant_id=tenant_id)
        if row is None:
            await leads_crud.create_meta_settings(session, tenant_id=tenant_id, default_company_id=None)
        else:
            await leads_crud.update_meta_settings(session, row, default_company_id=None)
        await session.commit()

    create_resp = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={
            "contacts": {"phone_country_code": "+48", "phone": f"558{suffix}"},
            "lead_form_slug": slug,
            "application_kind": "client",
            "client_company": {
                "name": f"Transport Client {suffix}",
                "tax_id": f"VAT{suffix}",
                "country_code": "PL",
                "city": "Warsaw",
            },
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    token = create_resp.json()["token"]
    lead_id = create_resp.json()["lead_id"]
    assert lead_id

    submit_resp = await client.post(
        f"/api/v1/public/apply/{token}/submit",
        headers=_headers(tenant_id),
        json={
            "consents": {"general": True, "employer_share": True, "terms_acceptance": True},
            "documents_version": {"privacy": "2025-02-01", "terms": "2025-02-01", "cookies": "2025-02-01"},
            "cookies_accepted": True,
        },
    )
    assert submit_resp.status_code == 200, submit_resp.text

    async with async_session_maker() as session:
        lead = await session.get(Lead, lead_id)
        assert lead is not None
        assert lead.lead_type == "client"
        assert lead.lead_target_type == "client_lead"
        assert lead.stage == "questionnaire_submitted"
        assert lead.status == "new"
        assert lead.own_company_id is not None
        assert lead.candidate_id is None
        assert lead.company_id is None
        assert lead.vacancy_id is None
        assert lead.converted_client_id is None
        assert (lead.normalized or {}).get("company_name") == f"Transport Client {suffix}"

        lead_n = (
            await session.execute(
                select(func.count())
                .select_from(UserNotification)
                .where(
                    UserNotification.tenant_id == tenant_id,
                    UserNotification.event_type == "lead_public_intake_client",
                )
            )
        ).scalar_one()
        assert int(lead_n or 0) >= 1


@pytest.mark.asyncio
async def test_public_company_intake_creates_b2b_lead(client: AsyncClient, tenant_id: str) -> None:
    slug, expected_own_company_id = await _seed_company_intake_source_profile(
        tenant_id,
        prefix="company-intake",
    )
    suffix = uuid4().hex[:10]
    payload = {
        "company": {
            "name": f"ABC Transport {suffix}",
            "legal_name": f"ABC Transport {suffix} Sp. z o.o.",
            "tax_id": f"PL{suffix}",
            "country": "Poland",
            "country_code": "PL",
            "city": "Poznan",
            "website": "abc-transport.pl",
            "fleet_size": 25,
            "transport_type": "mixed",
        },
        "contact": {
            "full_name": "Tomasz Kowalski",
            "role": "Fleet Manager",
            "email": f"tomasz-{suffix}@abc.pl",
            "phone": f"+48555{suffix[:6]}",
            "whatsapp": True,
        },
        "need": {
            "what_needed": "drivers C+E",
            "people_count": 5,
            "needed_when": "ASAP",
            "cooperation_type": "recruitment",
            "candidate_countries": ["Ukraine", "India", "Georgia"],
            "requirements": "ADR, code 95, English",
        },
        "terms": {
            "rate": "100 EUR/day",
            "schedule": "4/1",
            "base_location": "Poznan",
            "truck_brands": ["MAN", "Mercedes"],
            "body_type": "curtain",
            "additional": "no pallets",
        },
        "service_intent": "driver_recruitment",
        "language": "pl",
        "consent": {
            "terms_accepted": True,
            "privacy_accepted": True,
            "data_processing_accepted": True,
            "accuracy_confirmed": True,
        },
        "source_context": {
            "utm_source": "meta",
            "utm_campaign": "b2b_transport_clients_pl",
            "utm_adset": "poznan_transport_companies",
            "utm_ad": "need_drivers_creative_01",
            "fbclid": f"fb{suffix}",
            "landing_page": f"https://example.test/forms/company-intake/{slug}",
            "referrer": "https://facebook.com/",
        },
    }

    resp = await client.post(f"/api/v1/public/company-intake/{slug}/submit", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["stage"] == "questionnaire_submitted"
    assert body["status"] == "new"
    assert body["duplicate"] is False
    assert body["own_company_id"] == str(expected_own_company_id)
    assert body["company_id"] is None

    async with async_session_maker() as session:
        lead = await session.get(Lead, body["lead_id"])
        assert lead is not None
        assert lead.tenant_id == tenant_id
        assert lead.source == "meta_ads"
        assert lead.lead_type == "client"
        assert lead.lead_target_type == "client_lead"
        assert lead.stage == "questionnaire_submitted"
        assert lead.status == "new"
        assert str(lead.own_company_id) == str(expected_own_company_id)
        assert lead.company_id is None
        assert lead.vacancy_id is None
        assert lead.converted_client_id is None
        assert (lead.normalized or {}).get("company_tax_id") == f"PL{suffix}"
        assert (lead.normalized or {}).get("contact_email") == f"tomasz-{suffix}@abc.pl"
        assert (lead.normalized or {}).get("need_summary") == "5 drivers C+E"
        assert (lead.normalized or {}).get("lead_source") == "meta_ads"
        assert (lead.normalized or {}).get("company_profile", {}).get("tax_id") == f"PL{suffix}"
        assert (lead.normalized or {}).get("contact_person", {}).get("email") == f"tomasz-{suffix}@abc.pl"
        assert (lead.normalized or {}).get("need", {}).get("summary") == "5 drivers C+E"
        assert (lead.normalized or {}).get("marketing", {}).get("source") == "meta_ads"
        assert (lead.normalized or {}).get("meta", {}).get("language") == "pl"
        assert (lead.normalized or {}).get("meta", {}).get("source_profile", {}).get("public_slug") == slug
        assert (lead.normalized or {}).get("utm_campaign") == "b2b_transport_clients_pl"
        assert (lead.normalized or {}).get("fbclid") == f"fb{suffix}"
        assert (lead.payload or {}).get("intake_flow") == "client_company"
        assert (lead.payload or {}).get("source_profile", {}).get("public_slug") == slug

        activity = (
            await session.execute(
                select(ActivityLog).where(
                    ActivityLog.tenant_id == tenant_id,
                    ActivityLog.action == "company_intake_form_submitted",
                    ActivityLog.target_id == body["lead_id"],
                )
            )
        ).scalar_one_or_none()
        assert activity is not None


@pytest.mark.asyncio
async def test_client_lead_creation_contract_requires_owner_and_no_client_links(tenant_id: str) -> None:
    suffix = uuid4().hex[:10]
    async with async_session_maker() as session:
        own_company_id = await session.scalar(
            select(OwnCompany.id)
            .where(OwnCompany.tenant_id == tenant_id, OwnCompany.is_archived.is_(False))
            .order_by(OwnCompany.created_at.asc())
            .limit(1)
        )
        assert own_company_id is not None
        company_id = await _ensure_company(session, tenant_id)

        with pytest.raises(ValueError, match="own_company_id is required"):
            await leads_crud.create_lead(
                session,
                tenant_id=tenant_id,
                own_company_id=None,
                company_id=None,
                vacancy_id=None,
                payload={"test": True},
                normalized={"company_name": f"No Owner {suffix}"},
                source="company_intake_form",
                lead_type="client",
                lead_target_type="client_lead",
            )

        with pytest.raises(ValueError, match="company_id must be empty"):
            await leads_crud.create_lead(
                session,
                tenant_id=tenant_id,
                own_company_id=str(own_company_id),
                company_id=company_id,
                vacancy_id=None,
                payload={"test": True},
                normalized={"company_name": f"Linked Client {suffix}"},
                source="company_intake_form",
                lead_type="client",
                lead_target_type="client_lead",
            )

        lead = await leads_crud.create_lead(
            session,
            tenant_id=tenant_id,
            own_company_id=str(own_company_id),
            company_id=None,
            vacancy_id=None,
            payload={"test": True},
            normalized={"company_name": f"Valid Client Lead {suffix}"},
            source="company_intake_form",
            lead_type="candidate",
            lead_target_type="client_lead",
        )
        assert lead.lead_type == "client"
        assert lead.lead_target_type == "client_lead"
        assert str(lead.own_company_id) == str(own_company_id)
        assert lead.company_id is None
        assert lead.vacancy_id is None
        await session.rollback()


@pytest.mark.asyncio
async def test_public_company_intake_duplicate_scope_ignores_candidate_leads(
    client: AsyncClient,
    tenant_id: str,
) -> None:
    slug, own_company_id = await _seed_company_intake_source_profile(
        tenant_id,
        prefix="company-scope",
    )
    suffix = uuid4().hex[:10]
    email = f"scope-{suffix}@abc.pl"
    tax_id = f"PLSCOPE{suffix}"
    async with async_session_maker() as session:
        company_id = await _ensure_company(session, tenant_id)
        await leads_crud.create_lead(
            session,
            tenant_id=tenant_id,
            own_company_id=own_company_id,
            company_id=company_id,
            vacancy_id=None,
            payload={"test": "candidate lead with same probes"},
            normalized={
                "company_name": f"ABC Transport Scope {suffix}",
                "company_tax_id": tax_id,
                "contact_email": email,
            },
            source="meta",
            lead_type="candidate",
            lead_target_type="candidate",
        )
        await session.commit()

    payload = {
        "company": {
            "name": f"ABC Transport Scope {suffix}",
            "tax_id": tax_id,
            "country": "Poland",
            "country_code": "PL",
        },
        "contact": {
            "full_name": "Tomasz Kowalski",
            "email": email,
        },
        "need": {
            "what_needed": "drivers C+E",
            "people_count": 5,
        },
        "language": "en",
        "consent": {
            "terms_accepted": True,
            "privacy_accepted": True,
            "data_processing_accepted": True,
            "accuracy_confirmed": True,
        },
    }
    resp = await client.post(f"/api/v1/public/company-intake/{slug}/submit", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["duplicate"] is False

    async with async_session_maker() as session:
        leads = (
            await session.execute(
                select(Lead).where(
                    Lead.tenant_id == tenant_id,
                    Lead.own_company_id == own_company_id,
                    Lead.normalized["contact_email"].as_string() == email,
                )
            )
        ).scalars().all()
        assert {lead.lead_target_type for lead in leads} >= {"candidate", "client_lead"}


@pytest.mark.skip(reason="P5C: client public intake is lead-first; no transitional candidate dossier")
@pytest.mark.asyncio
async def test_public_intake_client_surfaces_intake_application_kind_on_candidate_detail(
    client: AsyncClient,
    tenant_id: str,
    manager_headers: Dict[str, str],
) -> None:
    slug = await _seed_active_lead_form(tenant_id, prefix="client-ak")
    suffix = uuid4().hex[:10]
    create_resp = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={
            "contacts": {"phone_country_code": "+48", "phone": f"559{suffix}"},
            "lead_form_slug": slug,
            "application_kind": "client",
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    candidate_id = create_resp.json()["candidate_id"]

    detail = await client.get(f"/api/v1/candidates/{candidate_id}", headers=manager_headers)
    assert detail.status_code == 200, detail.text
    assert detail.json().get("intake_application_kind") == "client"

    nna = await client.get(
        "/api/v1/candidates/no-next-action",
        headers=manager_headers,
        params={"intake_application_kind": "client", "limit": 100},
    )
    assert nna.status_code == 200, nna.text
    nna_body = nna.json()
    items = nna_body.get("items") or []
    match = next((x for x in items if str(x.get("id")) == candidate_id), None)
    assert match is not None
    assert match.get("intake_application_kind") == "client"
