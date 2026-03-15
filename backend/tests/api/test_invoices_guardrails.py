from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

import pytest
import sqlalchemy as sa
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.company import Company
from backend.app.models.user import User


TENANT_ID = "11111111-1111-1111-1111-111111111111"
ADMIN_EMAIL = "biuro@work-host.com"


def _operating_extra() -> dict:
    return {
        "company_role": "operating",
        "company_type": "services",
        "billing": {
            "billing_address": {
                "country": "PL",
                "city": "Warsaw",
                "street": "Main 1",
                "zip": "00-001",
            },
            "bank_accounts": [
                {
                    "id": "primary",
                    "label": "Primary",
                    "is_primary": True,
                    "iban": "PL10105000997603123456789123",
                    "bank_name": "PKO BP",
                    "swift_bic": "PKOPPLPW",
                    "country": "PL",
                }
            ],
        },
    }


def _client_extra() -> dict:
    return {
        "company_role": "client",
        "billing": {
            "billing_address": {
                "country": "PL",
                "city": "Gdansk",
                "street": "Client 10",
                "zip": "80-001",
            }
        },
    }


def _invoice_payload(*, client_id: str, issuer_id: str, status: str) -> dict:
    issue_date = date.today()
    return {
        "company_id": client_id,
        "issue_date": issue_date.isoformat(),
        "due_date": (issue_date + timedelta(days=14)).isoformat(),
        "currency": "PLN",
        "status": status,
        "items": [
            {
                "description": "Service fee",
                "qty": 1,
                "unit_price": 1000,
                "vat_rate": 23,
            }
        ],
        "billing_details": {
            "company_name": "Client Sp. z o.o.",
            "email": "billing@client.example",
            "tax_id": "PL9988776655",
            "address": "PL, Gdansk, Client 10, 80-001",
            "invoice_kind": "vat",
            "tax_mode": "standard_vat",
            "payment_terms_days": 14,
            "issuer_company_id": issuer_id,
            "issuer_name": "Issuer Sp. z o.o.",
            "issuer_tax_id": "PL1234567890",
            "issuer_address": {"country": "PL", "city": "Warsaw", "street": "Main 1", "zip": "00-001"},
            "issuer_bank_account": {
                "bank_name": "PKO BP",
                "iban": "PL10105000997603123456789123",
                "swift_bic": "PKOPPLPW",
                "country": "PL",
                "label": "Primary",
            },
        },
    }


@pytest.mark.anyio
async def test_cancel_guardrails_block_sent_overdue_and_paid(
    client: AsyncClient,
    db: AsyncSession,
    manager_headers: dict[str, str],
) -> None:
    admin_stmt = sa.select(User).where(sa.func.lower(User.email) == ADMIN_EMAIL.lower()).limit(1)
    admin = (await db.execute(admin_stmt)).scalar_one()

    issuer = Company(
        id=str(uuid4()),
        tenant_id=TENANT_ID,
        owner_user_id=str(admin.id),
        manager_user_id=str(admin.id),
        name="Issuer Sp. z o.o.",
        legal_name="Issuer Sp. z o.o.",
        tax_id="PL1234567890",
        country="PL",
        city="Warsaw",
        address="Main 1",
        extra=_operating_extra(),
    )
    client_company = Company(
        id=str(uuid4()),
        tenant_id=TENANT_ID,
        name="Client Sp. z o.o.",
        legal_name="Client Sp. z o.o.",
        tax_id="PL9988776655",
        country="PL",
        city="Gdansk",
        address="Client 10",
        extra=_client_extra(),
    )
    db.add(issuer)
    db.add(client_company)
    await db.commit()

    for status in ("sent", "overdue", "paid"):
        create_resp = await client.post(
            "/api/v1/invoices",
            headers=manager_headers,
            json=_invoice_payload(client_id=str(client_company.id), issuer_id=str(issuer.id), status=status),
        )
        assert create_resp.status_code == 201, create_resp.text
        invoice_id = str(create_resp.json()["id"])

        cancel_resp = await client.post(f"/api/v1/invoices/{invoice_id}/cancel", headers=manager_headers)
        assert cancel_resp.status_code == 400, cancel_resp.text
        assert "Create a correction invoice instead" in str(cancel_resp.text)


@pytest.mark.anyio
async def test_update_guardrails_block_non_draft_invoices(
    client: AsyncClient,
    db: AsyncSession,
    manager_headers: dict[str, str],
) -> None:
    admin_stmt = sa.select(User).where(sa.func.lower(User.email) == ADMIN_EMAIL.lower()).limit(1)
    admin = (await db.execute(admin_stmt)).scalar_one()

    issuer = Company(
        id=str(uuid4()),
        tenant_id=TENANT_ID,
        owner_user_id=str(admin.id),
        manager_user_id=str(admin.id),
        name="Issuer Update Guardrail Sp. z o.o.",
        legal_name="Issuer Update Guardrail Sp. z o.o.",
        tax_id="PL1122334455",
        country="PL",
        city="Warsaw",
        address="Main 11",
        extra=_operating_extra(),
    )
    client_company = Company(
        id=str(uuid4()),
        tenant_id=TENANT_ID,
        name="Client Update Guardrail Sp. z o.o.",
        legal_name="Client Update Guardrail Sp. z o.o.",
        tax_id="PL5544332211",
        country="PL",
        city="Gdansk",
        address="Client 11",
        extra=_client_extra(),
    )
    db.add(issuer)
    db.add(client_company)
    await db.commit()

    for status in ("issued", "sent", "overdue", "paid"):
        create_resp = await client.post(
            "/api/v1/invoices",
            headers=manager_headers,
            json=_invoice_payload(client_id=str(client_company.id), issuer_id=str(issuer.id), status=status),
        )
        assert create_resp.status_code == 201, create_resp.text
        invoice_id = str(create_resp.json()["id"])

        patch_resp = await client.patch(
            f"/api/v1/invoices/{invoice_id}",
            headers=manager_headers,
            json={"notes": f"updated for status={status}"},
        )
        assert patch_resp.status_code == 400, patch_resp.text
        assert "Only draft invoices can be edited" in str(patch_resp.text)


@pytest.mark.anyio
async def test_create_guardrails_block_operating_company_as_recipient(
    client: AsyncClient,
    db: AsyncSession,
    manager_headers: dict[str, str],
) -> None:
    admin_stmt = sa.select(User).where(sa.func.lower(User.email) == ADMIN_EMAIL.lower()).limit(1)
    admin = (await db.execute(admin_stmt)).scalar_one()

    issuer = Company(
        id=str(uuid4()),
        tenant_id=TENANT_ID,
        owner_user_id=str(admin.id),
        manager_user_id=str(admin.id),
        name="Issuer Recipient Guardrail Sp. z o.o.",
        legal_name="Issuer Recipient Guardrail Sp. z o.o.",
        tax_id="PL6677889900",
        country="PL",
        city="Warsaw",
        address="Main 99",
        extra=_operating_extra(),
    )
    db.add(issuer)
    await db.commit()

    create_resp = await client.post(
        "/api/v1/invoices",
        headers=manager_headers,
        json=_invoice_payload(client_id=str(issuer.id), issuer_id=str(issuer.id), status="draft"),
    )
    assert create_resp.status_code == 400, create_resp.text
    assert "client company" in str(create_resp.text).lower()
