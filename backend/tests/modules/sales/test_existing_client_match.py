"""Existing client name match for Sales inquiries (legal-suffix tolerant)."""

from __future__ import annotations

import uuid

import pytest

from backend.app.models import Company
from backend.app.models.client_account import ClientAccount
from backend.app.modules.client_accounts import crud as account_crud
from backend.app.modules.sales.services.existing_client_match import (
    find_unique_existing_client,
    normalize_company_match_key,
)


def test_normalize_strips_polish_legal_suffix() -> None:
    assert normalize_company_match_key("Synergia Kadry") == "synergia kadry"
    assert normalize_company_match_key("SYNERGIA KADRY sp. z o.o.") == "synergia kadry"
    assert (
        normalize_company_match_key("SYNERGIA KADRY SPÓŁKA Z OGRANICZONĄ ODPOWIEDZIALNOŚCIĄ")
        == "synergia kadry"
    )


@pytest.mark.asyncio
async def test_find_unique_matches_suffix_variant(db, tenant_id: str) -> None:
    company = Company(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        name="SYNERGIA KADRY sp. z o.o.",
        legal_name="SYNERGIA KADRY SPÓŁKA Z OGRANICZONĄ ODPOWIEDZIALNOŚCIĄ",
        extra={"company_role": "client", "company_kind": "client"},
        party_business_roles="employer",
    )
    account = ClientAccount(
        id=account_crud.new_client_account_id(),
        tenant_id=tenant_id,
        display_name="WORK SPECTRUM sp. z o.o.",
        status="active",
        primary_company_id=company.id,
    )
    company.client_account_id = account.id
    db.add_all([company, account])
    await db.flush()

    hit = await find_unique_existing_client(
        db,
        tenant_id=tenant_id,
        company_name="Synergia Kadry",
    )
    assert hit is not None
    assert hit.company_id == company.id
    assert hit.client_account_id == account.id
