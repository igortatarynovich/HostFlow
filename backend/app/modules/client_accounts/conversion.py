from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import ClientAccount, Company, Lead
from backend.app.modules.client_accounts import crud as account_crud
from backend.app.modules.companies import schemas as company_schemas
from backend.app.modules.companies.service import create_company_service
from backend.app.services.audit import log_activity
from backend.app.services.tenant_links import ensure_client_company_tenant_link


@dataclass(frozen=True)
class ClientLeadConversionResult:
    client_account: ClientAccount
    company: Optional[Company]
    idempotent_replay: bool


def _record(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _trim(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    return text or None


def _ensure_session_tenant_id(db: AsyncSession, tenant_id: str) -> None:
    tid = str(tenant_id)
    if isinstance(getattr(db, "info", None), dict):
        db.info["tenant_id"] = uuid.UUID(tid) if len(tid) == 36 else tid


def extract_lead_conversion_context(lead: Lead) -> dict[str, Any]:
    """Parse normalized/payload fields used for ClientAccount + Company creation."""
    normalized = _record(getattr(lead, "normalized", None))
    payload = _record(getattr(lead, "payload", None))
    company_profile = _record(normalized.get("company_profile")) or _record(payload.get("company"))
    contact_person = _record(normalized.get("contact_person")) or _record(payload.get("contact"))
    need = _record(normalized.get("need")) or _record(payload.get("need"))
    marketing = _record(normalized.get("marketing"))
    meta = _record(normalized.get("meta"))

    flat_full_name = (
        _trim(normalized.get("full_name"))
        or " ".join(
            p
            for p in [
                _trim(normalized.get("first_name")),
                _trim(normalized.get("last_name")),
            ]
            if p
        )
        or None
    )
    contact_full_name = _trim(contact_person.get("full_name")) or flat_full_name
    contact_email = (
        _trim(contact_person.get("email"))
        or _trim(normalized.get("email"))
        or _trim(payload.get("email"))
    )
    contact_phone = (
        _trim(contact_person.get("phone"))
        or _trim(normalized.get("phone"))
        or _trim(payload.get("phone"))
    )
    company_name = (
        _trim(company_profile.get("name"))
        or _trim(normalized.get("company_name"))
        or _trim(normalized.get("company_name_hint"))
        or _trim(payload.get("company_name"))
    )
    display_name = company_name or contact_full_name or "Клиент"

    contacts_payload: Dict[str, Any] = {}
    primary_contact = {
        "full_name": contact_full_name,
        "role": _trim(contact_person.get("role")),
        "email": contact_email,
        "phone": contact_phone,
        "whatsapp": bool(contact_person.get("whatsapp")) if contact_person.get("whatsapp") is not None else None,
        "source": "client_lead",
        "source_lead_id": str(lead.id),
        "is_primary": True,
    }
    primary_contact = {k: v for k, v in primary_contact.items() if v is not None and v != ""}
    if primary_contact:
        contacts_payload = {str(uuid.uuid4()): primary_contact}

    assigned_manager_id = _trim(meta.get("assigned_manager_id"))
    converting_manager_uuid: uuid.UUID | None = None
    if assigned_manager_id:
        try:
            converting_manager_uuid = uuid.UUID(assigned_manager_id)
        except ValueError:
            converting_manager_uuid = None

    return {
        "normalized": normalized,
        "company_profile": company_profile,
        "contact_person": contact_person,
        "need": need,
        "marketing": marketing,
        "meta": meta,
        "company_name": company_name,
        "display_name": display_name,
        "contact_full_name": contact_full_name,
        "contact_email": contact_email,
        "contact_phone": contact_phone,
        "contacts_payload": contacts_payload,
        "converting_manager_uuid": converting_manager_uuid,
    }


def build_company_create_from_lead(
    lead: Lead,
    ctx: dict[str, Any],
    *,
    actor_id: Optional[str],
) -> Optional[company_schemas.CompanyCreate]:
    company_name = ctx.get("company_name")
    if not company_name:
        return None
    company_profile = _record(ctx.get("company_profile"))
    need = _record(ctx.get("need"))
    marketing = _record(ctx.get("marketing"))
    meta = _record(ctx.get("meta"))
    contacts_payload = ctx.get("contacts_payload") or {}
    manager_uuid = ctx.get("converting_manager_uuid")
    if manager_uuid is None and actor_id:
        try:
            manager_uuid = uuid.UUID(actor_id)
        except ValueError:
            manager_uuid = None

    return company_schemas.CompanyCreate(
        name=company_name,
        legal_name=_trim(company_profile.get("legal_name")) or company_name,
        tax_id=_trim(company_profile.get("tax_id"))
        or _trim(company_profile.get("nip"))
        or _trim(company_profile.get("vat")),
        phone=ctx.get("contact_phone"),
        email=ctx.get("contact_email"),
        website=_trim(company_profile.get("website")),
        country_code=_trim(company_profile.get("country_code")),
        country=_trim(company_profile.get("country")),
        city=_trim(company_profile.get("city")),
        address=_trim(company_profile.get("address")),
        company_role="client",
        party_business_roles="service_client",
        client_stage="lead_converted",
        client_source=_trim(getattr(lead, "source", None)),
        manager_user_id=manager_uuid,
        contacts=contacts_payload or None,
        extra={
            "company_role": "client",
            "company_kind": "client",
            "source": lead.source,
            "source_lead_id": str(lead.id),
            "source_profile": meta.get("source_profile"),
            "intake": {
                "company_profile": company_profile,
                "contact_person": ctx.get("contact_person"),
                "need": need,
                "marketing": marketing,
                "meta": meta,
            },
            "needs": [need] if need else [],
        },
    )


async def _resolve_existing_account(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
) -> Optional[ClientAccount]:
    linked_account_id = _trim(getattr(lead, "client_account_id", None))
    if linked_account_id:
        account = await account_crud.get_client_account(db, tenant_id=tenant_id, account_id=linked_account_id)
        if account is not None:
            return account
    return await account_crud.get_client_account_by_source_lead(
        db,
        tenant_id=tenant_id,
        source_lead_id=str(lead.id),
    )


async def _resolve_existing_company(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    account: ClientAccount,
) -> Optional[Company]:
    converted_id = _trim(getattr(lead, "converted_client_id", None))
    if converted_id:
        result = await db.execute(
            select(Company).where(Company.id == converted_id, Company.tenant_id == tenant_id)
        )
        company = result.scalar_one_or_none()
        if company is not None:
            return company
    primary_id = _trim(getattr(account, "primary_company_id", None))
    if primary_id:
        result = await db.execute(
            select(Company).where(Company.id == primary_id, Company.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()
    return None


async def _link_company_to_account(
    db: AsyncSession,
    *,
    tenant_id: str,
    company_id: str,
    account_id: str,
) -> None:
    company_row = await db.get(Company, company_id)
    if company_row is not None:
        company_row.client_account_id = account_id
    primary_result = await db.execute(
        select(ClientAccount.primary_company_id).where(
            ClientAccount.id == account_id,
            ClientAccount.tenant_id == tenant_id,
        )
    )
    if not _trim(primary_result.scalar_one_or_none()):
        account_row = await db.get(ClientAccount, account_id)
        if account_row is not None:
            account_row.primary_company_id = company_id


async def _finalize_lead_after_conversion(
    lead: Lead,
    *,
    account: ClientAccount,
    company: Optional[Company],
    actor_id: Optional[str],
    conversion_reason: str,
    normalized: dict[str, Any],
    account_id: Optional[str] = None,
    company_id: Optional[str] = None,
) -> None:
    resolved_account_id = account_id or str(getattr(account, "id", ""))
    resolved_company_id = company_id or (str(getattr(company, "id", "")) if company is not None else None)
    lead.client_account_id = resolved_account_id
    if resolved_company_id:
        lead.converted_client_id = resolved_company_id
    lead.status = "processed"
    lead.stage = "converted"
    lead.error = None

    normalized_updated = dict(normalized)
    normalized_updated["client_account_id"] = resolved_account_id
    if resolved_company_id:
        normalized_updated["converted_client_id"] = resolved_company_id
        normalized_updated.setdefault("converted_client_at", datetime.now(timezone.utc).isoformat())
        normalized_updated.setdefault("converted_client_by", actor_id)
    normalized_updated["outcome_client_conversion_reason"] = conversion_reason
    lead.normalized = normalized_updated


async def _emit_conversion_audit(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    account_id: str,
    company_id: Optional[str],
    display_name: str,
    actor_id: Optional[str],
) -> None:
    company_name: Optional[str] = None
    if company_id:
        company_name = await db.scalar(select(Company.name).where(Company.id == company_id))
    try:
        await log_activity(
            db,
            tenant_id=tenant_id,
            actor_id=actor_id,
            action="client_lead.converted_to_client_account",
            target_type="lead",
            target_id=str(lead.id),
            payload={
                "client_account_id": account_id,
                "client_id": company_id,
                "company_name": company_name,
                "display_name": display_name,
                "source": lead.source,
                "own_company_id": str(getattr(lead, "own_company_id", "") or ""),
            },
        )
    except Exception:
        pass


async def convert_client_lead(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    actor_id: Optional[str] = None,
    conversion_reason: str = "manual_convert_client",
    company_in: Optional[company_schemas.CompanyCreate] = None,
) -> ClientLeadConversionResult:
    """Idempotent Lead → ClientAccount (+ optional Company) conversion."""
    ctx = extract_lead_conversion_context(lead)
    normalized = _record(ctx.get("normalized"))

    existing_account = await _resolve_existing_account(db, tenant_id=tenant_id, lead=lead)
    if existing_account is not None:
        existing_account_id = str(existing_account.id)
        company = await _resolve_existing_company(db, tenant_id=tenant_id, lead=lead, account=existing_account)
        company_id = str(company.id) if company is not None else None
        if company_id is not None:
            await _link_company_to_account(
                db,
                tenant_id=tenant_id,
                company_id=company_id,
                account_id=existing_account_id,
            )
        await _finalize_lead_after_conversion(
            lead,
            account=existing_account,
            company=company,
            actor_id=actor_id,
            conversion_reason=conversion_reason,
            normalized=normalized,
            account_id=existing_account_id,
            company_id=company_id,
        )
        await db.flush()
        return ClientLeadConversionResult(
            client_account=existing_account,
            company=company,
            idempotent_replay=True,
        )

    display_name = _trim(ctx.get("display_name")) or "Клиент"
    manager_uuid = ctx.get("converting_manager_uuid")
    if manager_uuid is None and actor_id:
        try:
            manager_uuid = uuid.UUID(actor_id)
        except ValueError:
            manager_uuid = None

    account = ClientAccount(
        id=account_crud.new_client_account_id(),
        tenant_id=tenant_id,
        own_company_id=_trim(getattr(lead, "own_company_id", None)),
        display_name=display_name,
        status="prospect",
        owner_user_id=str(manager_uuid) if manager_uuid else (actor_id or None),
        source_lead_id=str(lead.id),
    )
    account_id = str(account.id)

    company: Optional[Company] = None
    company_id: Optional[str] = None
    try:
        db.add(account)
        await db.flush()

        create_payload = company_in or build_company_create_from_lead(lead, ctx, actor_id=actor_id)
        if create_payload is not None:
            company = await _resolve_existing_company(db, tenant_id=tenant_id, lead=lead, account=account)
            if company is not None:
                company_id = str(company.id)
                await _link_company_to_account(
                    db,
                    tenant_id=tenant_id,
                    company_id=company_id,
                    account_id=account_id,
                )
            else:
                _ensure_session_tenant_id(db, tenant_id)
                company = await create_company_service(
                    db=db,
                    data=create_payload,
                    actor_user_id=actor_id,
                    commit=False,
                )
                company_id = str(company.id)
                await ensure_client_company_tenant_link(
                    db,
                    agency_tenant_id=tenant_id,
                    client_company_id=company_id,
                    handoff_enabled=True,
                )
                await _link_company_to_account(
                    db,
                    tenant_id=tenant_id,
                    company_id=company_id,
                    account_id=account_id,
                )

        await _finalize_lead_after_conversion(
            lead,
            account=account,
            company=company,
            actor_id=actor_id,
            conversion_reason=conversion_reason,
            normalized=normalized,
            account_id=account_id,
            company_id=company_id,
        )
        await db.flush()
    except IntegrityError:
        await db.rollback()
        replay_lead = await account_crud.get_lead_for_update(db, tenant_id=tenant_id, lead_id=str(lead.id))
        if replay_lead is None:
            raise
        replay_account = await _resolve_existing_account(db, tenant_id=tenant_id, lead=replay_lead)
        if replay_account is None:
            replay_account = await account_crud.get_client_account_by_source_lead(
                db,
                tenant_id=tenant_id,
                source_lead_id=str(lead.id),
            )
        if replay_account is None:
            raise
        company = await _resolve_existing_company(db, tenant_id=tenant_id, lead=replay_lead, account=replay_account)
        replay_account_id = str(replay_account.id)
        company_id = str(company.id) if company is not None else None
        if company_id is not None:
            await _link_company_to_account(
                db,
                tenant_id=tenant_id,
                company_id=company_id,
                account_id=replay_account_id,
            )
        await _finalize_lead_after_conversion(
            replay_lead,
            account=replay_account,
            company=company,
            actor_id=actor_id,
            conversion_reason=conversion_reason,
            normalized=normalized,
            account_id=replay_account_id,
            company_id=company_id,
        )
        await db.flush()
        replay_display_name = await db.scalar(
            select(ClientAccount.display_name).where(ClientAccount.id == replay_account_id)
        )
        await _emit_conversion_audit(
            db,
            tenant_id=tenant_id,
            lead=replay_lead,
            account_id=replay_account_id,
            company_id=company_id,
            display_name=_trim(replay_display_name) or "Клиент",
            actor_id=actor_id,
        )
        return ClientLeadConversionResult(
            client_account=replay_account,
            company=company,
            idempotent_replay=True,
        )

    await _emit_conversion_audit(
        db,
        tenant_id=tenant_id,
        lead=lead,
        account_id=account_id,
        company_id=company_id,
        display_name=display_name,
        actor_id=actor_id,
    )
    return ClientLeadConversionResult(
        client_account=account,
        company=company,
        idempotent_replay=False,
    )
