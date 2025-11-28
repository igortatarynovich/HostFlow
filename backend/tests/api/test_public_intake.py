from __future__ import annotations

from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Dict
from uuid import uuid4

import pytest
from httpx import AsyncClient
from PIL import Image, ImageDraw
from sqlalchemy import select, update

from backend.app.db.session import async_session_maker
from backend.app.models.candidate import Candidate
from backend.app.models.candidate_consent import CandidateConsent
from backend.app.models.candidate_employment import CandidateEmployment
from backend.app.models.magic_link import MagicLink


pytestmark = pytest.mark.anyio


def _headers(tenant_id: str) -> Dict[str, str]:
    return {"X-Tenant-Id": tenant_id}


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


def _mock_photo_bytes(width: int = 1800, height: int = 1200) -> bytes:
    image = Image.new("RGB", (width, height), color=(35, 50, 80))
    draw = ImageDraw.Draw(image)
    draw.rectangle((220, 180, width - 220, height - 180), fill=(240, 240, 240))
    draw.rectangle((260, 220, width - 260, 260), fill=(180, 180, 180))
    draw.text((280, 320), "HostFlow Scanner", fill=(0, 0, 0))
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_public_intake_full_flow(client: AsyncClient, tenant_id: str) -> None:
    create_resp = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={
            "contacts": {"phone_country_code": "+48", "phone": "555123456"},
            "source": "landing-page",
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    created = create_resp.json()
    token = created["token"]
    candidate_id = created["candidate_id"]

    get_resp = await client.get(f"/api/v1/public/apply/{token}", headers=_headers(tenant_id))
    assert get_resp.status_code == 200, get_resp.text
    draft = get_resp.json()
    assert draft["status"] == "draft"
    assert draft["data"]["contacts"]["phone"] == "555123456"
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
                "phone": "555123456",
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

    candidate = await _fetch_candidate(candidate_id)
    assert candidate is not None
    assert candidate.email == "driver@example.com"
    assert candidate.first_name == "Jan"

    employments = await _list_employments(candidate_id)
    assert len(employments) == 1
    assert employments[0].employer_name == "Trans Co"

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
    candidate = await _fetch_candidate(candidate_id)
    assert candidate is not None
    assert candidate.intake_submitted_at is not None
    consents = await _list_consents(candidate_id)
    assert len(consents) == 4
    assert {row.consent_code for row in consents} == {"general", "employer_share", "terms_acceptance", "cookies"}


@pytest.mark.asyncio
async def test_public_intake_requires_contact(client: AsyncClient, tenant_id: str) -> None:
    resp = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={"contacts": {}},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_public_intake_token_expired(client: AsyncClient, tenant_id: str) -> None:
    create_resp = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={"contacts": {"email": "draft@example.com"}},
    )
    token = create_resp.json()["token"]
    candidate_id = create_resp.json()["candidate_id"]

    async with async_session_maker() as session:
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
    create_resp = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={"contacts": {"email": "upload@example.com"}},
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
    first_resp = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={"contacts": {"phone_country_code": "+48", "phone": "555123456"}},
    )
    assert first_resp.status_code == 200, first_resp.text
    first_data = first_resp.json()

    second_resp = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={
            "contacts": {"phone_country_code": "+48", "phone": "555123456", "email": "second@example.com"},
            "source": "retarget",
        },
    )
    assert second_resp.status_code == 200, second_resp.text
    second_data = second_resp.json()

    assert second_data["candidate_id"] == first_data["candidate_id"]
    assert second_data["token"] == first_data["token"]


@pytest.mark.asyncio
async def test_public_scanner_flow(client: AsyncClient, tenant_id: str) -> None:
    create_resp = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={"contacts": {"phone_country_code": "+48", "phone": "555009900"}},
    )
    assert create_resp.status_code == 200, create_resp.text
    token = create_resp.json()["token"]

    session_resp = await client.post(
        "/api/v1/public/scan-sessions",
        headers=_headers(tenant_id),
        json={"token": token, "document_type": "id_card"},
    )
    assert session_resp.status_code == 200, session_resp.text
    session_id = session_resp.json()["id"]

    photo_bytes = _mock_photo_bytes()
    files = {"file": ("front.jpg", photo_bytes, "image/jpeg")}
    data = {"page_code": "front", "rotation": "0"}
    upload_resp = await client.post(
        f"/api/v1/public/scan-sessions/{session_id}/pages",
        headers=_headers(tenant_id),
        data=data,
        files=files,
    )
    assert upload_resp.status_code == 200, upload_resp.text
    upload_state = upload_resp.json()
    assert upload_state["status"] == "in_progress"
    assert any(page["page_code"] == "front" for page in upload_state["pages"])

    process_resp = await client.post(
        f"/api/v1/public/scan-sessions/{session_id}/process",
        headers=_headers(tenant_id),
    )
    assert process_resp.status_code == 200, process_resp.text
    processed = process_resp.json()
    assert processed["status"] == "done"
    assert processed["pages"][0]["status"] in {"ok", "needs_review", "rejected"}


@pytest.mark.asyncio
async def test_public_intake_matches_phone_digits_without_country_code(client: AsyncClient, tenant_id: str) -> None:
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
        json={"contacts": {"phone_country_code": "+48", "phone": "700200300"}},
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["candidate_id"] == candidate_id
    assert payload["token"]

    candidate = await _fetch_candidate(candidate_id)
    assert candidate is not None
    assert candidate.intake_token == payload["token"]

    presign_resp = await client.post(
        f"/api/v1/public/apply/{token}/documents/presign",
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
    create_resp = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={"contacts": {"email": "status@example.com"}},
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
async def test_public_magic_link_flow(client: AsyncClient, tenant_id: str) -> None:
    email = "magic@example.com"
    create_resp = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={"contacts": {"email": email}},
    )
    assert create_resp.status_code == 200

    req_resp = await client.post(
        "/api/v1/public/magic-link/request",
        headers=_headers(tenant_id),
        json={"email": email},
    )
    assert req_resp.status_code == 200

    async with async_session_maker() as session:
        stmt = select(MagicLink).where(MagicLink.contact_value == email.lower())
        magic_link = await session.scalar(stmt)
        assert magic_link is not None
        token = magic_link.token

    redeem_resp = await client.get(f"/api/v1/public/magic-link/{token}", headers=_headers(tenant_id))
    assert redeem_resp.status_code == 200, redeem_resp.text
    payload = redeem_resp.json()
    assert payload["token"]
    assert payload["apply_url"].endswith(payload["token"])

    complete_resp = await client.post(
        f"/api/v1/public/apply/{token}/documents/upload",
        headers=_headers(tenant_id),
        data={"doc_type": "visa", "storage_key": presign["key"]},
    )
    assert complete_resp.status_code == 200, complete_resp.text
    completed_state = complete_resp.json()
    visa_entry = next((doc for doc in completed_state["documents"]["documents"] if doc.get("doc_type") == "visa"), None)
    assert visa_entry is not None
    assert visa_entry["has_files"] is True
