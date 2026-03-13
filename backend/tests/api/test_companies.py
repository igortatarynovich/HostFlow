from __future__ import annotations

from datetime import date, timedelta
from typing import Dict
from uuid import UUID

import pytest
from httpx import AsyncClient

COMPANY_BASE_URL = "/api/v1/companies"


def _assert_uuid(value: str) -> UUID:
    return UUID(str(value))


@pytest.mark.anyio
async def test_company_profile_workflow(
    client: AsyncClient,
    manager_headers: Dict[str, str],
) -> None:
    # Create draft company
    create_resp = await client.post(
        f"{COMPANY_BASE_URL}/",
        headers=manager_headers,
        json={"name": "Atlas Logistics"},
    )
    assert create_resp.status_code == 200, create_resp.text
    company = create_resp.json()
    company_id = _assert_uuid(company["id"])

    # Update legal section
    legal_payload = {
        "reg_no": "REG-123456",
        "vat_eu": "PL1234567890",
        "established_at": "2012-06-01",
        "registered_address": {
            "country": "PL",
            "city": "Poznań",
            "street": "Polna 1",
            "zip": "60-101",
        },
        "authorized_representatives": [
            {"full_name": "Jan Kowalski", "role": "CEO", "email": "jan@example.com"}
        ],
    }
    legal_resp = await client.patch(
        f"{COMPANY_BASE_URL}/{company_id}/legal",
        headers=manager_headers,
        json=legal_payload,
    )
    assert legal_resp.status_code == 200, legal_resp.text
    legal_data = legal_resp.json()
    assert legal_data["reg_no"] == "REG-123456"
    assert legal_data["registered_address"]["city"] == "Poznań"

    # Configure billing with primary bank account
    billing_payload = {
        "default_currency": "PLN",
        "payment_terms_days": 30,
        "invoice_email": "billing@atlas.example",
        "bank_accounts": [
            {
                "bank_name": "mBank",
                "iban": "PL61109010140000071219812874",
                "swift_bic": "WBKPPLPP",
                "label": "Primary",
                "is_primary": True,
            }
        ],
    }
    billing_resp = await client.put(
        f"{COMPANY_BASE_URL}/{company_id}/billing",
        headers=manager_headers,
        json=billing_payload,
    )
    assert billing_resp.status_code == 200, billing_resp.text
    billing_data = billing_resp.json()
    assert billing_data["payment_terms_days"] == 30
    assert billing_data["bank_accounts"][0]["label"] == "Primary"

    # Adding another primary bank account should conflict
    conflict_resp = await client.post(
        f"{COMPANY_BASE_URL}/{company_id}/bank-accounts",
        headers=manager_headers,
        json={
            "iban": "PL02105000997603123456789123",
            "bank_name": "PKO BP",
            "swift_bic": "BPKOPLPW",
            "is_primary": True,
        },
    )
    assert conflict_resp.status_code == 409
    assert conflict_resp.json()["detail"] == "BANK-PRIMARY-EXISTS"

    # Add secondary account without primary flag
    add_account_resp = await client.post(
        f"{COMPANY_BASE_URL}/{company_id}/bank-accounts",
        headers=manager_headers,
        json={
            "iban": "PL02105000997603123456789123",
            "bank_name": "PKO BP",
            "swift_bic": "BPKOPLPW",
            "is_primary": False,
        },
    )
    assert add_account_resp.status_code == 200, add_account_resp.text
    secondary_account = add_account_resp.json()
    secondary_account_id = secondary_account["id"]
    assert secondary_account["is_primary"] is False

    # Promote secondary account to primary
    promote_resp = await client.patch(
        f"{COMPANY_BASE_URL}/{company_id}/bank-accounts/{secondary_account_id}",
        headers=manager_headers,
        json={"is_primary": True},
    )
    assert promote_resp.status_code == 200, promote_resp.text
    promoted = promote_resp.json()
    assert promoted["is_primary"] is True

    # Add primary contact
    contact_resp = await client.post(
        f"{COMPANY_BASE_URL}/{company_id}/contacts",
        headers=manager_headers,
        json={
            "full_name": "Anna Nowak",
            "role": "OWNER",
            "email": "anna@atlas.example",
            "phone": "+48 600 100 200",
            "is_primary": True,
        },
    )
    assert contact_resp.status_code == 200, contact_resp.text
    contact = contact_resp.json()
    contact_id = contact["id"]

    # Attempt to add second primary contact -> conflict
    contact_conflict = await client.post(
        f"{COMPANY_BASE_URL}/{company_id}/contacts",
        headers=manager_headers,
        json={
            "full_name": "Piotr Zawadzki",
            "role": "ACC",
            "email": "piotr@atlas.example",
            "is_primary": True,
        },
    )
    assert contact_conflict.status_code == 409
    assert contact_conflict.json()["detail"] == "CONTACT-PRIMARY"

    # Update compliance data
    compliance_resp = await client.patch(
        f"{COMPANY_BASE_URL}/{company_id}/compliance",
        headers=manager_headers,
        json={
            "fin_check_status": "manual_review",
            "aml_required": True,
            "doc_valid_until": (date.today() + timedelta(days=90)).isoformat(),
        },
    )
    assert compliance_resp.status_code == 200, compliance_resp.text
    assert compliance_resp.json()["aml_required"] is True

    # Enable client portal
    portal_resp = await client.post(
        f"{COMPANY_BASE_URL}/{company_id}/enable-portal",
        headers=manager_headers,
        json={"enabled": True, "url": "https://portal.atlas.example"},
    )
    assert portal_resp.status_code == 200, portal_resp.text
    assert portal_resp.json()["enabled"] is True

    # Check readiness
    readiness_resp = await client.get(
        f"{COMPANY_BASE_URL}/{company_id}/readiness",
        headers=manager_headers,
    )
    assert readiness_resp.status_code == 200, readiness_resp.text
    readiness = readiness_resp.json()
    assert readiness["has_legal"] is True
    assert readiness["has_primary_contact"] is True
    assert readiness["has_primary_bank"] is True
    assert readiness["billing_ready"] is True
    assert readiness["client_portal_enabled"] is True

    # Removing primary contact should reassign automatically
    delete_contact_resp = await client.delete(
        f"{COMPANY_BASE_URL}/{company_id}/contacts/{contact_id}",
        headers=manager_headers,
    )
    assert delete_contact_resp.status_code == 204


@pytest.mark.anyio
async def test_company_bootstrap_assigns_owner_and_manager(
    client: AsyncClient,
    manager_headers: Dict[str, str],
) -> None:
    me_resp = await client.get("/api/v1/users/me", headers=manager_headers)
    assert me_resp.status_code == 200, me_resp.text
    me = me_resp.json()

    create_resp = await client.post(
        f"{COMPANY_BASE_URL}/",
        headers=manager_headers,
        json={"name": "Ownership Bootstrap Co"},
    )
    assert create_resp.status_code == 200, create_resp.text
    company = create_resp.json()
    assert company["owner_user_id"] == me["user_id"]
    assert company["manager_user_id"] == me["user_id"]


@pytest.mark.anyio
async def test_company_limit_applies_only_to_operating_profiles(
    client: AsyncClient,
    manager_headers: Dict[str, str],
) -> None:
    operating_resp = await client.post(
        f"{COMPANY_BASE_URL}/",
        headers=manager_headers,
        json={"name": "Primary Operating Co", "company_type": "services", "company_role": "operating"},
    )
    assert operating_resp.status_code == 200, operating_resp.text
    operating_company = operating_resp.json()
    assert operating_company["extra"]["company_role"] == "operating"

    second_operating_resp = await client.post(
        f"{COMPANY_BASE_URL}/",
        headers=manager_headers,
        json={"name": "Second Operating Co", "company_type": "services", "company_role": "operating"},
    )
    assert second_operating_resp.status_code == 402, second_operating_resp.text
    assert second_operating_resp.json()["detail"] == "OPERATING-COMPANY-LIMIT"

    client_resp = await client.post(
        f"{COMPANY_BASE_URL}/",
        headers=manager_headers,
        json={"name": "Client Counterparty", "company_role": "client"},
    )
    assert client_resp.status_code == 200, client_resp.text
    client_company = client_resp.json()
    assert client_company["extra"]["company_role"] == "client"
