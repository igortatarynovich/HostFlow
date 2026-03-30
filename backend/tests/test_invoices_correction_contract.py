from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

import pytest

from backend.app.api.v1.invoices import crud
from backend.app.models.company import Company
from backend.app.models.own_company import OwnCompany


TENANT_ID = "11111111-1111-1111-1111-111111111111"


def _company_extra(*, role: str, with_bank: bool) -> dict:
    billing: dict = {
        "billing_address": {
            "country": "PL",
            "city": "Warsaw",
            "street": "Main 1",
            "zip": "00-001",
        }
    }
    if with_bank:
        billing["bank_accounts"] = [
            {
                "label": "Primary",
                "is_primary": True,
                "iban": "PL10105000997603123456789123",
                "bank_name": "PKO BP",
                "swift_bic": "PKOPPLPW",
                "country": "PL",
            }
        ]
    return {"company_role": role, "billing": billing}


async def _create_company(db, *, role: str, with_bank: bool, name: str, tax_id: str) -> Company:
    company = Company(
        id=str(uuid4()),
        tenant_id=TENANT_ID,
        name=name,
        legal_name=name,
        tax_id=tax_id,
        country="PL",
        city="Warsaw",
        address="Main 1",
        extra=_company_extra(role=role, with_bank=with_bank),
    )
    db.add(company)
    await db.flush()
    return company


def _base_payload(*, company_id: str, issuer_company_id: str, status: str = "draft", billing_extra: dict | None = None) -> dict:
    issue_date = date.today()
    billing = {"invoice_kind": "vat", "tax_mode": "standard_vat", "issuer_company_id": issuer_company_id}
    if billing_extra:
        billing.update(billing_extra)
    return {
        "company_id": company_id,
        "issue_date": issue_date,
        "due_date": issue_date + timedelta(days=14),
        "currency": "PLN",
        "status": status,
        "items": [
            {
                "description": "Recruitment service",
                "qty": 1,
                "unit_price": "1000.00",
                "vat_rate": "23.00",
            }
        ],
        "billing_details": billing,
    }


@pytest.mark.anyio
async def test_create_invoice_uses_own_company_as_issuer_when_no_issuer_company_id(db) -> None:
    """§2.4 billing: issuer defaults from OwnCompany when payload carries own_company_id."""
    client = await _create_company(
        db, role="client", with_bank=False, name="Client Sp. z o.o.", tax_id="PL0987654321"
    )
    own = OwnCompany(
        id=str(uuid4()),
        tenant_id=TENANT_ID,
        name="Our Workspace",
        legal_name="Our Workspace Sp. z o.o.",
        tax_id="PL1234567890",
        country="PL",
        city="Warsaw",
        address="Issuer Street 1",
        bank_details={
            "bank_accounts": [
                {
                    "label": "Main",
                    "is_primary": True,
                    "iban": "PL10105000997603123456789123",
                    "bank_name": "PKO BP",
                    "swift_bic": "PKOPPLPW",
                    "country": "PL",
                }
            ]
        },
    )
    db.add(own)
    await db.flush()

    issue_date = date.today()
    payload = {
        "own_company_id": own.id,
        "company_id": client.id,
        "issue_date": issue_date,
        "due_date": issue_date + timedelta(days=14),
        "currency": "PLN",
        "status": "draft",
        "items": [
            {
                "description": "Service",
                "qty": 1,
                "unit_price": "100.00",
                "vat_rate": "23.00",
            }
        ],
        "billing_details": {"invoice_kind": "vat", "tax_mode": "standard_vat"},
    }
    invoice = await crud.create_invoice(db, TENANT_ID, payload, created_by=None)
    bd = dict(invoice.billing_details or {})
    assert bd.get("issuer_own_company_id") == own.id
    assert bd.get("issuer_name")
    assert bd.get("issuer_tax_id") == "PL1234567890"
    bank = bd.get("issuer_bank_account") or {}
    assert bank.get("iban") == "PL10105000997603123456789123"


@pytest.mark.anyio
async def test_correction_autofills_original_invoice_number(db) -> None:
    issuer = await _create_company(db, role="operating", with_bank=True, name="Issuer Sp. z o.o.", tax_id="PL1234567890")
    client = await _create_company(db, role="client", with_bank=False, name="Client Sp. z o.o.", tax_id="PL0987654321")

    original = await crud.create_invoice(
        db,
        TENANT_ID,
        _base_payload(company_id=client.id, issuer_company_id=issuer.id, status="issued"),
        created_by=None,
    )

    correction = await crud.create_invoice(
        db,
        TENANT_ID,
        _base_payload(
            company_id=client.id,
            issuer_company_id=issuer.id,
            billing_extra={
                "invoice_kind": "correction",
                "correction_of_invoice_id": original.id,
                "correction_reason": "Price adjustment",
            },
        ),
        created_by=None,
    )

    assert correction.billing_details is not None
    assert correction.billing_details.get("correction_of_invoice_number") == original.invoice_number


@pytest.mark.anyio
async def test_correction_requires_non_draft_original(db) -> None:
    issuer = await _create_company(db, role="operating", with_bank=True, name="Issuer Draft Test", tax_id="PL1111111111")
    client = await _create_company(db, role="client", with_bank=False, name="Client Draft Test", tax_id="PL2222222222")

    original = await crud.create_invoice(
        db,
        TENANT_ID,
        _base_payload(company_id=client.id, issuer_company_id=issuer.id, status="draft"),
        created_by=None,
    )

    with pytest.raises(ValueError, match="Original invoice must be confirmed before correction"):
        await crud.create_invoice(
            db,
            TENANT_ID,
            _base_payload(
                company_id=client.id,
                issuer_company_id=issuer.id,
                billing_extra={
                    "invoice_kind": "correction",
                    "correction_of_invoice_id": original.id,
                    "correction_reason": "Fix draft",
                },
            ),
            created_by=None,
        )


@pytest.mark.anyio
async def test_correction_cannot_target_another_correction(db) -> None:
    issuer = await _create_company(db, role="operating", with_bank=True, name="Issuer Corr Test", tax_id="PL3333333333")
    client = await _create_company(db, role="client", with_bank=False, name="Client Corr Test", tax_id="PL4444444444")

    original = await crud.create_invoice(
        db,
        TENANT_ID,
        _base_payload(company_id=client.id, issuer_company_id=issuer.id, status="issued"),
        created_by=None,
    )
    first_correction = await crud.create_invoice(
        db,
        TENANT_ID,
        _base_payload(
            company_id=client.id,
            issuer_company_id=issuer.id,
            billing_extra={
                "invoice_kind": "correction",
                "correction_of_invoice_id": original.id,
                "correction_reason": "First correction",
            },
        ),
        created_by=None,
    )

    with pytest.raises(ValueError, match="cannot target another correction"):
        await crud.create_invoice(
            db,
            TENANT_ID,
            _base_payload(
                company_id=client.id,
                issuer_company_id=issuer.id,
                billing_extra={
                    "invoice_kind": "correction",
                    "correction_of_invoice_id": first_correction.id,
                    "correction_reason": "Second correction",
                },
            ),
            created_by=None,
        )


@pytest.mark.anyio
async def test_get_invoice_correction_chain_returns_original_and_corrections(db) -> None:
    issuer = await _create_company(db, role="operating", with_bank=True, name="Issuer Chain Test", tax_id="PL5555555555")
    client = await _create_company(db, role="client", with_bank=False, name="Client Chain Test", tax_id="PL6666666666")

    original = await crud.create_invoice(
        db,
        TENANT_ID,
        _base_payload(company_id=client.id, issuer_company_id=issuer.id, status="issued"),
        created_by=None,
    )
    correction_1 = await crud.create_invoice(
        db,
        TENANT_ID,
        _base_payload(
            company_id=client.id,
            issuer_company_id=issuer.id,
            billing_extra={
                "invoice_kind": "correction",
                "correction_of_invoice_id": original.id,
                "correction_reason": "Correction A",
            },
        ),
        created_by=None,
    )
    correction_2 = await crud.create_invoice(
        db,
        TENANT_ID,
        _base_payload(
            company_id=client.id,
            issuer_company_id=issuer.id,
            billing_extra={
                "invoice_kind": "correction",
                "correction_of_invoice_id": original.id,
                "correction_reason": "Correction B",
            },
        ),
        created_by=None,
    )

    chain_from_original = await crud.get_invoice_correction_chain(db, TENANT_ID, original.id)
    chain_from_correction = await crud.get_invoice_correction_chain(db, TENANT_ID, correction_2.id)

    ids_original = [str(x.id) for x in chain_from_original]
    ids_correction = [str(x.id) for x in chain_from_correction]
    assert str(original.id) in ids_original
    assert str(correction_1.id) in ids_original
    assert str(correction_2.id) in ids_original
    assert ids_original == ids_correction


@pytest.mark.anyio
async def test_invoice_number_must_be_unique(db) -> None:
    issuer = await _create_company(db, role="operating", with_bank=True, name="Issuer Number Test", tax_id="PL7777777777")
    client = await _create_company(db, role="client", with_bank=False, name="Client Number Test", tax_id="PL8888888888")

    first = await crud.create_invoice(
        db,
        TENANT_ID,
        {
            **_base_payload(company_id=client.id, issuer_company_id=issuer.id, status="issued"),
            "invoice_number": "FV/2026/03/0099",
        },
        created_by=None,
    )
    assert first.invoice_number == "FV/2026/03/0099"

    with pytest.raises(ValueError, match="Invoice number already exists"):
        await crud.create_invoice(
            db,
            TENANT_ID,
            {
                **_base_payload(company_id=client.id, issuer_company_id=issuer.id, status="issued"),
                "invoice_number": "FV/2026/03/0099",
            },
            created_by=None,
        )
