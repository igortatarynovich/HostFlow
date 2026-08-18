"""Ensure a Sales ClientAccount exists for an operator-created client company.

Add Client (tenant link / company_role=client) is the product path for
«our client without their own tenant». Campaigns target ClientAccount, not Company.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import ClientAccount, Company
from backend.app.modules.sales.services.create_client_account_manually import (
    DUPLICATE_ACTION_CREATE_NEW,
    ManualClientAccountDuplicateError,
    create_client_account_manually,
)

_ACTIVE_STAGES = frozenset({"active", "contract_signed"})
_INACTIVE_STAGES = frozenset({"lost"})


def is_local_client_company(company: Company) -> bool:
    extra = company.extra if isinstance(company.extra, dict) else {}
    role = str(extra.get("company_role") or "client").strip().lower()
    return role != "operating"


def _account_status_for_company(company: Company) -> str:
    stage = str(getattr(company, "client_stage", "") or "").strip().lower()
    if stage in _ACTIVE_STAGES:
        return "active"
    if stage in _INACTIVE_STAGES:
        return "inactive"
    return "prospect"


def _idempotency_key(*, tenant_id: str, company_id: str) -> str:
    return f"manual-company:{tenant_id}:{company_id}"


async def _load_account(
    db: AsyncSession,
    *,
    tenant_id: str,
    account_id: Optional[str],
) -> Optional[ClientAccount]:
    aid = str(account_id or "").strip()
    if not aid:
        return None
    return await db.scalar(
        select(ClientAccount).where(
            ClientAccount.id == aid,
            ClientAccount.tenant_id == tenant_id,
        )
    )


async def _link_company_to_account(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
    account_id: str,
) -> None:
    company_row = await db.get(Company, company_id)
    if company_row is not None and str(company_row.tenant_id) == tenant_id:
        company_row.client_account_id = account_id
    account_row = await db.get(ClientAccount, account_id)
    if account_row is not None and not str(getattr(account_row, "primary_company_id", "") or "").strip():
        account_row.primary_company_id = company_id


async def _account_for_primary_company(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
) -> Optional[ClientAccount]:
    return await db.scalar(
        select(ClientAccount)
        .where(
            ClientAccount.tenant_id == tenant_id,
            ClientAccount.primary_company_id == company_id,
        )
        .limit(1)
    )


async def ensure_manual_client_account_for_company(
    db: AsyncSession,
    *,
    tenant_id: str,
    actor_user_id: str,
    company: Company,
    own_company_id: Optional[str] = None,
    reason: str = "operator_add_client",
    link_primary_company: bool = True,
) -> ClientAccount:
    """Create or reuse ClientAccount with origin_type=manual_creation for this company.

    When ``link_primary_company`` is false (linked employer lives in another tenant),
    the account is still created in the agency tenant so campaigns can target it.
    """
    company_id = str(company.id)
    display_name = str(company.name or "").strip() or "Client"
    owner_id = str(getattr(company, "owner_user_id", "") or "").strip() or None

    existing = None
    if link_primary_company:
        existing = await _load_account(
            db,
            tenant_id=tenant_id,
            account_id=str(getattr(company, "client_account_id", "") or ""),
        )
        if existing is None:
            existing = await _account_for_primary_company(
                db, tenant_id=tenant_id, company_id=company_id
            )
    if existing is not None:
        if link_primary_company:
            await _link_company_to_account(
                db,
                tenant_id=tenant_id,
                company_id=company_id,
                account_id=str(existing.id),
            )
        return existing

    primary_id = company_id if link_primary_company else None
    try:
        result = await create_client_account_manually(
            db,
            tenant_id=tenant_id,
            own_company_id=own_company_id,
            actor_user_id=actor_user_id,
            display_name=display_name,
            status=_account_status_for_company(company),
            owner_user_id=owner_id,
            primary_company_id=primary_id,
            idempotency_key=_idempotency_key(tenant_id=tenant_id, company_id=company_id),
            reason=reason,
            source_note="add_client",
        )
    except ManualClientAccountDuplicateError as exc:
        candidate_id = ""
        if exc.candidates:
            candidate_id = str(exc.candidates[0].get("client_account_id") or "").strip()
        reused = await _load_account(db, tenant_id=tenant_id, account_id=candidate_id)
        if reused is not None and len(exc.candidates) == 1:
            primary = str(getattr(reused, "primary_company_id", "") or "").strip()
            if (not primary) or primary == company_id:
                if link_primary_company:
                    await _link_company_to_account(
                        db,
                        tenant_id=tenant_id,
                        company_id=company_id,
                        account_id=str(reused.id),
                    )
                return reused
        result = await create_client_account_manually(
            db,
            tenant_id=tenant_id,
            own_company_id=own_company_id,
            actor_user_id=actor_user_id,
            display_name=display_name,
            status=_account_status_for_company(company),
            owner_user_id=owner_id,
            primary_company_id=primary_id,
            idempotency_key=_idempotency_key(tenant_id=tenant_id, company_id=company_id),
            reason=reason,
            source_note="add_client",
            force_create=True,
            duplicate_decision={"action": DUPLICATE_ACTION_CREATE_NEW},
        )

    account = result.account
    if link_primary_company:
        await _link_company_to_account(
            db,
            tenant_id=tenant_id,
            company_id=company_id,
            account_id=str(account.id),
        )
    return account


async def ensure_manual_client_accounts_for_local_client_companies(
    db: AsyncSession,
    *,
    tenant_id: str,
    actor_user_id: str,
) -> list[ClientAccount]:
    """Backfill ClientAccount for agency-owned client companies (no operating profiles)."""
    rows = (
        await db.execute(
            select(Company).where(
                Company.tenant_id == tenant_id,
                Company.is_archived.is_(False),
            )
        )
    ).scalars().all()
    created_or_reused: list[ClientAccount] = []
    for company in rows:
        if not is_local_client_company(company):
            continue
        account = await ensure_manual_client_account_for_company(
            db,
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            company=company,
            reason="ensure_from_client_companies",
        )
        created_or_reused.append(account)
    return created_or_reused
