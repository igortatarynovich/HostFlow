import hashlib
import hmac
import json
import uuid

import pytest
import sqlalchemy as sa

from backend.app.core.settings import settings
from backend.app.core.crypto import encrypt_secret
from backend.app.db.session import async_session_maker
from backend.app.models.lead import MetaLeadCredential
from backend.app.modules.leads import pipeline, webhook


DEFAULT_TENANT_ID = "11111111-1111-1111-1111-111111111111"


async def _ensure_page_credential(page_id: str, *, tenant_id: str = DEFAULT_TENANT_ID, status: str = "active") -> None:
    async with async_session_maker() as session:
        session.add(
            MetaLeadCredential(
                tenant_id=tenant_id,
                label=f"page-{page_id}",
                status=status,
                encrypted_page_id=encrypt_secret(page_id),
            )
        )
        await session.commit()


async def _ensure_settings_row() -> None:
    async with async_session_maker() as session:
        tenant_id = "11111111-1111-1111-1111-111111111111"
        row = await session.execute(
            sa.text(
                "SELECT tenant_id FROM meta_lead_settings WHERE tenant_id = :tenant"
            ),
            {"tenant": tenant_id},
        )
        if row.scalar_one_or_none():
            await session.execute(
                sa.text(
                    """
                    UPDATE meta_lead_settings
                    SET
                        auto_create_enabled = :auto_create_enabled,
                        mask_pii_in_logs = :mask_pii_in_logs,
                        pull_field_data_from_graph = :pull_field_data_from_graph,
                        webhook_verify_token = :webhook_verify_token
                    WHERE tenant_id = :tenant_id
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "auto_create_enabled": True,
                    "mask_pii_in_logs": True,
                    "pull_field_data_from_graph": True,
                    "webhook_verify_token": "hostflow123",
                },
            )
            await session.commit()
            return
        await session.execute(
            sa.text(
                """
                INSERT INTO meta_lead_settings
                (tenant_id, auto_create_enabled, mask_pii_in_logs, pull_field_data_from_graph, webhook_verify_token)
                VALUES (:tenant_id, :auto_create_enabled, :mask_pii_in_logs, :pull_field_data_from_graph, :webhook_verify_token)
                """
            ),
            {
                "tenant_id": tenant_id,
                "auto_create_enabled": True,
                "mask_pii_in_logs": True,
                "pull_field_data_from_graph": True,
                "webhook_verify_token": "hostflow123",
            },
        )
        await session.commit()


def _signed_headers(payload: dict) -> dict[str, str]:
    secret = settings.meta_webhook_secret or ""
    body = json.dumps(payload).encode("utf-8")
    signature = "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return {"Content-Type": "application/json", "X-Hub-Signature-256": signature}


@pytest.mark.anyio
async def test_webhook_with_field_data_creates_lead(monkeypatch, client):
    await _ensure_settings_row()
    async def no_signatures(*args, **kwargs):
        return []

    monkeypatch.setattr(webhook.admin_service, "get_active_secret_candidates", no_signatures)
    suf = uuid.uuid4().hex[:12]
    page_id = f"PAGE-FIELD-{suf}"
    lead_id = f"lead-field-{suf}"
    await _ensure_page_credential(page_id)

    payload = {
        "object": "page",
        "entry": [
            {
                "id": page_id,
                "changes": [
                    {
                        "field": "leadgen",
                        "value": {
                            "leadgen_id": lead_id,
                            "page_id": page_id,
                            "form_id": "FORM-ID",
                            "field_data": [
                                {"name": "phone_number", "values": ["+48504004622"]},
                                {"name": "full_name", "values": ["Igor Tatarynowicz"]},
                                {"name": "country", "values": ["pl"]},
                            ],
                        },
                    }
                ],
            }
        ],
    }

    resp = await client.post(
        "/api/v1/leads/meta/webhook",
        params={"verify_token": "hostflow123"},
        content=json.dumps(payload),
        headers=_signed_headers(payload),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] in {"processed", "needs_routing"}

    async with async_session_maker() as session:
        row = await session.execute(
            sa.text(
                """
                SELECT status, error, normalized->>'phone' AS phone
                FROM leads
                WHERE external_id = :lead_id
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"lead_id": lead_id},
        )
        status, error, phone = row.fetchone()
        assert status in ("processed", "needs_routing")
        assert phone == "+48504004622"
        assert error in (None, "", "AUTO_CREATE_DISABLED", "VACANCY_NOT_RESOLVED")


@pytest.mark.anyio
async def test_webhook_skeleton_does_not_overwrite_field_data(monkeypatch, client):
    await _ensure_settings_row()
    async def no_signatures(*args, **kwargs):
        return []

    monkeypatch.setattr(webhook.admin_service, "get_active_secret_candidates", no_signatures)
    suf = uuid.uuid4().hex[:12]
    page_a = f"SKE-PAGE-{suf}"
    lead_id = f"lead-skeleton-{suf}"
    await _ensure_page_credential(page_a)
    payload_full = {
        "object": "page",
        "entry": [
            {
                "id": page_a,
                "changes": [
                    {
                        "field": "leadgen",
                        "value": {
                            "leadgen_id": lead_id,
                            "page_id": page_a,
                            "form_id": "FORM-A",
                            "field_data": [
                                {"name": "phone", "values": ["+14155550123"]},
                                {"name": "full_name", "values": ["Test Skeleton"]},
                            ],
                        },
                    }
                ],
            }
        ],
    }
    resp_full = await client.post(
        "/api/v1/leads/meta/webhook",
        params={"verify_token": "hostflow123"},
        content=json.dumps(payload_full),
        headers=_signed_headers(payload_full),
    )
    assert resp_full.status_code == 200

    payload_skeleton = {
        "object": "page",
        "entry": [
            {
                "id": page_a,
                "changes": [
                    {
                        "field": "leadgen",
                        "value": {
                            "leadgen_id": lead_id,
                            "page_id": page_a,
                            "form_id": "FORM-A",
                        },
                    }
                ],
            }
        ],
    }
    resp_skeleton = await client.post(
        "/api/v1/leads/meta/webhook",
        params={"verify_token": "hostflow123"},
        content=json.dumps(payload_skeleton),
        headers=_signed_headers(payload_skeleton),
    )
    assert resp_skeleton.status_code == 200
    body = resp_skeleton.json()
    assert body["status"] in {"processed", "needs_routing"}

    async with async_session_maker() as session:
        row = await session.execute(
            sa.text(
                """
                SELECT status, payload
                FROM leads
                WHERE external_id = :lead_id
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"lead_id": lead_id},
        )
        status, payload_db = row.fetchone()
        assert status in ("processed", "needs_routing")
        field_data = payload_db["entry"][0]["changes"][0]["value"]["field_data"]
        field_map = {item["name"]: item["values"] for item in field_data}
        assert field_map["phone"] == ["+14155550123"]
        assert field_map["full_name"] == ["Test Skeleton"]

    payload_update = {
        "object": "page",
        "entry": [
            {
                "id": page_a,
                "changes": [
                    {
                        "field": "leadgen",
                        "value": {
                            "leadgen_id": lead_id,
                            "page_id": page_a,
                            "form_id": "FORM-A",
                            "field_data": [
                                {"name": "phone", "values": ["+14155550199"]},
                            ],
                        },
                    }
                ],
            }
        ],
    }
    resp_update = await client.post(
        "/api/v1/leads/meta/webhook",
        params={"verify_token": "hostflow123"},
        content=json.dumps(payload_update),
        headers=_signed_headers(payload_update),
    )
    assert resp_update.status_code == 200
    body_update = resp_update.json()
    assert body_update["status"] in {"processed", "needs_routing", "duplicated"}

    async with async_session_maker() as session:
        row = await session.execute(
            sa.text(
                """
                SELECT status, payload
                FROM leads
                WHERE external_id = :lead_id
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"lead_id": lead_id},
        )
        status, payload_db = row.fetchone()
        assert status in ("processed", "needs_routing", "duplicated")
        field_data = payload_db["entry"][0]["changes"][0]["value"]["field_data"]
        field_map = {item["name"]: item["values"] for item in field_data}
        assert field_map["phone"] == ["+14155550199"]
        assert field_map["full_name"] == ["Test Skeleton"]


@pytest.mark.anyio
async def test_webhook_resurrects_failed_lead(monkeypatch, client):
    await _ensure_settings_row()

    async def no_signatures(*args, **kwargs):
        return []

    monkeypatch.setattr(webhook.admin_service, "get_active_secret_candidates", no_signatures)
    lead_id = f"lead-resurrect-{uuid.uuid4().hex[:6]}"
    page_r = f"PAGE-R-{uuid.uuid4().hex[:12]}"
    await _ensure_page_credential(page_r)

    payload_skeleton = {
        "object": "page",
        "entry": [
            {
                "id": page_r,
                "changes": [
                    {
                        "field": "leadgen",
                        "value": {
                            "leadgen_id": lead_id,
                            "page_id": page_r,
                            "ad_id": "AD-R-1",
                        },
                    }
                ],
            }
        ],
    }

    resp_failed = await client.post(
        "/api/v1/leads/meta/webhook",
        params={"verify_token": "hostflow123"},
        content=json.dumps(payload_skeleton),
        headers=_signed_headers(payload_skeleton),
    )
    assert resp_failed.status_code == 200
    failed_body = resp_failed.json()
    assert failed_body["status"] == "failed"
    failed_error = failed_body.get("error") or ""
    assert any(marker in failed_error for marker in ("NO_CONTACTS", "GRAPH_"))
    initial_lead_uuid = failed_body["lead_id"]

    async with async_session_maker() as session:
        row = await session.execute(
            sa.text(
                """
                SELECT id, status, error, normalized->>'phone' AS phone, normalized->'raw_field_names' AS raw_fields
                FROM leads
                WHERE external_id = :lead_id
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"lead_id": lead_id},
        )
        db_id, status, error, phone, raw_fields = row.fetchone()
        assert db_id == initial_lead_uuid
        assert status == "failed"
        assert error and any(marker in error for marker in ("NO_CONTACTS", "GRAPH_"))
        assert phone is None
        assert raw_fields in (None, [])
        count_row = await session.execute(
            sa.text("SELECT COUNT(*) FROM leads WHERE external_id = :lead_id"),
            {"lead_id": lead_id},
        )
        assert count_row.scalar_one() == 1

    payload_enriched = {
        "object": "page",
        "entry": [
            {
                "id": page_r,
                "changes": [
                    {
                        "field": "leadgen",
                        "value": {
                            "leadgen_id": lead_id,
                            "page_id": page_r,
                            "ad_id": "AD-R-1",
                            "field_data": [
                                {"name": "phone_number", "values": ["+48555111222"]},
                                {"name": "full_name", "values": ["Revived Lead"]},
                            ],
                        },
                    }
                ],
            }
        ],
    }

    resp_success = await client.post(
        "/api/v1/leads/meta/webhook",
        params={"verify_token": "hostflow123"},
        content=json.dumps(payload_enriched),
        headers=_signed_headers(payload_enriched),
    )
    assert resp_success.status_code == 200
    success_body = resp_success.json()
    assert success_body["lead_id"] == initial_lead_uuid
    assert success_body["status"] in {"processed", "needs_routing", "duplicated"}
    assert success_body.get("error") in (None, "", "VACANCY_NOT_RESOLVED")

    async with async_session_maker() as session:
        row = await session.execute(
            sa.text(
                """
                SELECT id, status, error, normalized->>'phone' AS phone, normalized->'raw_field_names' AS raw_fields
                FROM leads
                WHERE external_id = :lead_id
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"lead_id": lead_id},
        )
        db_id, status, error, phone, raw_fields = row.fetchone()
        assert db_id == initial_lead_uuid
        assert status in ("processed", "needs_routing", "duplicated")
        assert error in (None, "", "VACANCY_NOT_RESOLVED")
        assert phone == "+48555111222"
        assert raw_fields and "phone_number" in raw_fields
        count_row = await session.execute(
            sa.text("SELECT COUNT(*) FROM leads WHERE external_id = :lead_id"),
            {"lead_id": lead_id},
        )
        assert count_row.scalar_one() == 1


@pytest.mark.anyio
async def test_webhook_graph_fallback(monkeypatch, client):
    await _ensure_settings_row()
    suf = uuid.uuid4().hex[:12]
    page_g = f"PAGE-G-{suf}"
    lead_id = f"lead-graph-{suf}"
    await _ensure_page_credential(page_g)
    payload = {
        "object": "page",
        "entry": [
            {
                "id": page_g,
                "changes": [
                    {
                        "field": "leadgen",
                        "value": {
                            "leadgen_id": lead_id,
                            "page_id": page_g,
                        },
                    }
                ],
            }
        ],
    }

    async def no_signatures(*args, **kwargs):
        return []

    async def fake_token(*args, **kwargs):
        return "token"

    class FakeGraphResponse:
        status_code = 200

        def __init__(self, payload):
            self._payload = payload

        def json(self):
            return self._payload

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, params=None):
            return FakeGraphResponse(
                {
                    "field_data": [
                        {"name": "phone_number", "values": ["+33123456789"]},
                        {"name": "full_name", "values": ["Graph Import"]},
                    ]
                }
            )

    monkeypatch.setattr(webhook.admin_service, "get_page_access_token", fake_token)
    monkeypatch.setattr(webhook.admin_service, "get_active_secret_candidates", no_signatures)
    monkeypatch.setattr(pipeline.httpx, "AsyncClient", FakeAsyncClient)

    resp = await client.post(
        "/api/v1/leads/meta/webhook",
        params={"verify_token": "hostflow123"},
        content=json.dumps(payload),
        headers=_signed_headers(payload),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in {"processed", "needs_routing"}

    async with async_session_maker() as session:
        row = await session.execute(
            sa.text(
                """
                SELECT status, normalized->>'phone' AS phone
                FROM leads
                WHERE external_id = :lead_id
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"lead_id": lead_id},
        )
        status, phone = row.fetchone()
        assert status in ("processed", "needs_routing")
        assert phone == "+33123456789"


@pytest.mark.anyio
async def test_webhook_unknown_page_does_not_use_verify_token(monkeypatch, client):
    await _ensure_settings_row()

    async def no_signatures(*args, **kwargs):
        return []

    monkeypatch.setattr(webhook.admin_service, "get_active_secret_candidates", no_signatures)
    page_id = f"PAGE-UNKNOWN-{uuid.uuid4().hex[:12]}"
    lead_id = f"lead-unknown-{uuid.uuid4().hex[:12]}"
    payload = {
        "object": "page",
        "entry": [
            {
                "id": page_id,
                "changes": [
                    {
                        "field": "leadgen",
                        "value": {
                            "leadgen_id": lead_id,
                            "page_id": page_id,
                            "form_id": "FORM-UNKNOWN",
                        },
                    }
                ],
            }
        ],
    }

    resp = await client.post(
        "/api/v1/leads/meta/webhook",
        params={"verify_token": "hostflow123"},
        content=json.dumps(payload),
        headers=_signed_headers(payload),
    )
    assert resp.status_code == 403, resp.text
    assert "Tenant not resolved" in resp.text

    async with async_session_maker() as session:
        row = await session.execute(
            sa.text("SELECT COUNT(*) FROM leads WHERE external_id = :lead_id"),
            {"lead_id": lead_id},
        )
        assert row.scalar_one() == 0


@pytest.mark.anyio
async def test_webhook_disabled_page_credential_is_rejected(monkeypatch, client):
    await _ensure_settings_row()

    async def no_signatures(*args, **kwargs):
        return []

    monkeypatch.setattr(webhook.admin_service, "get_active_secret_candidates", no_signatures)
    page_id = f"PAGE-DISABLED-{uuid.uuid4().hex[:12]}"
    lead_id = f"lead-disabled-{uuid.uuid4().hex[:12]}"
    await _ensure_page_credential(page_id, status="disabled")
    payload = {
        "object": "page",
        "entry": [
            {
                "id": page_id,
                "changes": [
                    {
                        "field": "leadgen",
                        "value": {
                            "leadgen_id": lead_id,
                            "page_id": page_id,
                            "form_id": "FORM-DISABLED",
                        },
                    }
                ],
            }
        ],
    }

    resp = await client.post(
        "/api/v1/leads/meta/webhook",
        params={"verify_token": "hostflow123"},
        content=json.dumps(payload),
        headers=_signed_headers(payload),
    )
    assert resp.status_code == 403, resp.text
    assert "Tenant not resolved" in resp.text
