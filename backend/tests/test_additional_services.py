import uuid

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from backend.app.main import app

BASE_URL = "http://testserver"
TENANT_ID = "00000000-0000-0000-0000-000000000001"

ADMIN_EMAIL = "biuro@work-host.com"
ADMIN_PASS = "Host123!"


async def _login(client: AsyncClient) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        headers={"Content-Type": "application/json"},
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASS},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


async def _create_company(client: AsyncClient, headers: dict) -> str:
    response = await client.post(
        "/api/v1/companies",
        headers=headers,
        json={
            "name": "Transport X",
            "legal_name": "Transport X Sp. z o.o.",
            "tax_id": "PL1234567890",
            "email": "contact@transport-x.test",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


async def _create_vacancy(client: AsyncClient, headers: dict, company_id: str) -> str:
    response = await client.post(
        "/api/v1/vacancies",
        headers=headers,
        json={
            "company_id": company_id,
            "title": "Driver C+E",
            "target": 1,
            "status": "open",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


async def _create_candidate(client: AsyncClient, headers: dict, vacancy_id: str) -> str:
    response = await client.post(
        "/api/v1/candidates",
        headers=headers,
        json={
            "first_name": "John",
            "last_name": "Doe",
            "stage": "new",
            "vacancy_id": vacancy_id,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


@pytest.mark.asyncio
async def test_additional_services_end_to_end():
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url=BASE_URL,
        ) as client:
            token = await _login(client)

            headers = {
                "X-Tenant-Id": TENANT_ID,
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            company_id = await _create_company(client, headers)
            vacancy_id = await _create_vacancy(client, headers, company_id)
            candidate_id = await _create_candidate(client, headers, vacancy_id)

            service_code = f"svc_{uuid.uuid4().hex[:6]}"
            create_catalog_resp = await client.post(
                "/api/v1/services",
                headers=headers,
                json={
                    "code": service_code,
                    "name": "Medical clearance",
                    "description": "Pre-employment medical exam",
                    "category": "medical",
                    "unit": "person",
                    "base_price": 320.0,
                    "estimated_cost": 180.0,
                    "cost_currency": "PLN",
                    "vat_rate": 8.0,
                    "requires_schedule": True,
                    "requires_candidate": True,
                    "result_document_type": "medical",
                    "sla_hours": 48,
                },
            )
            assert create_catalog_resp.status_code == 200, create_catalog_resp.text
            service_id = create_catalog_resp.json()["id"]

            order_resp = await client.post(
                "/api/v1/service-orders",
                headers=headers,
                json={
                    "candidate_id": candidate_id,
                    "currency": "PLN",
                    "notes": "Initial onboarding package",
                    "items": [
                        {
                            "service_id": service_id,
                            "qty": 1,
                            "unit_price": 320,
                            "estimated_cost": 190,
                            "vat_rate": 8,
                        }
                    ],
                },
            )
            assert order_resp.status_code == 200, order_resp.text
            order_body = order_resp.json()
            order_id = order_body["id"]
            assert order_body["status"] == "draft"
            assert len(order_body["items"]) == 1
            item_id = order_body["items"][0]["id"]
            assert float(order_body["items"][0]["estimated_cost"]) == pytest.approx(190.0)
            assert order_body["items"][0]["cost_status"] == "estimated"

            schedule_resp = await client.post(
                f"/api/v1/service-items/{item_id}/schedule",
                headers=headers,
                json={
                    "provider": "Medicover Poznań",
                    "slot_start": "2025-01-10T09:00:00Z",
                    "slot_end": "2025-01-10T10:00:00Z",
                    "location": "Poznań, ul. Zdrowia 5",
                    "status": "confirmed",
                },
            )
            assert schedule_resp.status_code == 200, schedule_resp.text

            status_resp = await client.patch(
                f"/api/v1/service-orders/{order_id}",
                headers=headers,
                json={"status": "approved"},
            )
            assert status_resp.status_code == 200, status_resp.text
            assert status_resp.json()["status"] == "approved"

            deliver_resp = await client.post(
                f"/api/v1/service-items/{item_id}/deliver",
                headers=headers,
                json={
                    "status": "delivered",
                    "result_document": {
                        "document_type": "medical",
                        "status": "approved",
                        "issued_at": "2025-01-11",
                        "expires_at": "2026-01-11",
                        "extra": {"provider": "Medicover"},
                    },
                    "attachments": [
                        {
                            "file_id": str(uuid.uuid4()),
                            "label": "medical_report.pdf",
                        }
                    ],
                },
            )
            assert deliver_resp.status_code == 200, deliver_resp.text
            deliver_body = deliver_resp.json()
            assert deliver_body["status"] == "delivered"

            order_details = await client.get(
                f"/api/v1/service-orders/{order_id}", headers=headers
            )
            assert order_details.status_code == 200, order_details.text
            assert order_details.json()["items"][0]["status"] == "delivered"

            summary_resp = await client.get(
                f"/api/v1/service-orders/{order_id}/summary",
                headers=headers,
            )
            assert summary_resp.status_code == 200, summary_resp.text
            summary = summary_resp.json()
            assert summary["missing_documents"] == {}

            analytics_resp = await client.get(
                "/api/v1/analytics/services-overview",
                headers=headers,
            )
            assert analytics_resp.status_code == 200, analytics_resp.text
            analytics_body = analytics_resp.json()
            assert float(analytics_body["totals"]["revenue"]) >= 320.0
            assert float(analytics_body["totals"]["estimated_cost"]) >= 190.0
            assert analytics_body["data_quality"]["estimated_items"] >= 1

            docs_resp = await client.get(
                "/api/v1/documents",
                headers=headers,
                params={"candidate_id": candidate_id, "type": "medical"},
            )
            assert docs_resp.status_code == 200, docs_resp.text
            docs_body = docs_resp.json()
            medical_doc = next((doc for doc in docs_body if doc["type"] == "medical"), None)
            assert medical_doc, "expected medical document to be created"
            assert medical_doc["status"] == "approved"

            candidate_orders = await client.get(
                f"/api/v1/candidates/{candidate_id}/service-orders",
                headers=headers,
            )
            assert candidate_orders.status_code == 200, candidate_orders.text
            assert candidate_orders.json(), "Candidate orders list must not be empty"

            error_resp = await client.post(
                "/api/v1/service-orders",
                headers=headers,
                json={
                    "currency": "PLN",
                    "items": [
                        {
                            "service_id": service_id,
                            "qty": 1,
                        }
                    ],
                },
            )
            assert error_resp.status_code == 422, error_resp.text
