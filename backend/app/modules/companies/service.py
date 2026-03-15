from typing import Sequence
from uuid import UUID

from backend.app.models import Company
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from . import crud, schemas
from .crud import OperatingCompanyLimitReached


async def get_company_or_404(db: AsyncSession, company_id: UUID) -> Company:
    company = await crud.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


async def list_companies_service(
    db: AsyncSession,
    q: str | None = None,
    include_archived: bool = False,
    allowed_company_ids: set[str] | None = None,
) -> Sequence[Company]:
    return await crud.list_companies(
        db,
        q=q,
        include_archived=include_archived,
        allowed_company_ids=allowed_company_ids,
    )


def _map_value_error(exc: ValueError) -> HTTPException:
    if isinstance(exc, OperatingCompanyLimitReached):
        missing_slots = max(1, exc.used - exc.effective_limit + 1) if exc.effective_limit > 0 else 1
        return HTTPException(
            status_code=402,
            detail={
                "code": "OPERATING-COMPANY-LIMIT",
                "message": "Operating company limit reached for current subscription",
                "billing_path": "/app/settings/billing",
                "recommended_extra_slots": missing_slots,
                "slots": {
                    "included_limit": exc.included_limit,
                    "extra_slots": exc.extra_slots,
                    "effective_limit": exc.effective_limit,
                    "used": exc.used,
                    "available": max(0, exc.effective_limit - exc.used) if exc.effective_limit > 0 else 0,
                    "unlimited": exc.effective_limit == 0,
                },
            },
        )
    message = str(exc)
    if "Multiple contacts marked as primary" in message:
        return HTTPException(status_code=409, detail="CONTACT-PRIMARY")
    if "Only one bank account can be marked as primary" in message:
        return HTTPException(status_code=409, detail="BANK-PRIMARY-EXISTS")
    if "Operating company limit reached" in message:
        return HTTPException(status_code=402, detail="OPERATING-COMPANY-LIMIT")
    if "IBAN" in message:
        return HTTPException(status_code=422, detail="IBAN-CHECK")
    return HTTPException(status_code=422, detail=message)


def _extra_section(company: Company, key: str) -> dict:
    extra = getattr(company, "extra", {}) or {}
    if isinstance(extra, dict):
        raw = extra.get(key) or {}
    else:
        raw = {}
    return dict(raw)


async def create_company_service(
    db: AsyncSession,
    data: schemas.CompanyCreate,
    *,
    actor_user_id: str | None = None,
) -> Company:
    try:
        return await crud.create_company(db, data, actor_user_id=actor_user_id)
    except ValueError as exc:
        raise _map_value_error(exc) from exc


async def update_company_service(
    db: AsyncSession,
    company_id: UUID,
    data: schemas.CompanyUpdate,
) -> Company:
    try:
        company = await crud.update_company(db, company_id, data)
    except ValueError as exc:
        raise _map_value_error(exc) from exc
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


async def archive_company_service(
    db: AsyncSession,
    company_id: UUID,
) -> None:
    archived = await crud.archive_company(db, company_id)
    if not archived:
        raise HTTPException(status_code=404, detail="Company not found")


async def update_company_legal_service(
    db: AsyncSession,
    company_id: UUID,
    payload: dict,
) -> dict:
    try:
        company = await crud.update_company_extra_section(db, company_id, "legal", payload)
    except ValueError as exc:
        raise _map_value_error(exc) from exc
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    legal = _extra_section(company, "legal")
    if not legal:
        return {}
    return schemas.LegalProfile.model_validate(legal).model_dump(mode="json")


async def replace_company_billing_service(
    db: AsyncSession,
    company_id: UUID,
    payload: dict,
) -> dict:
    try:
        company = await crud.update_company_extra_section(db, company_id, "billing", payload)
    except ValueError as exc:
        raise _map_value_error(exc) from exc
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    billing = _extra_section(company, "billing")
    return schemas.BillingProfile.model_validate(billing).model_dump(mode="json")


async def add_company_bank_account_service(
    db: AsyncSession,
    company_id: UUID,
    payload: dict,
) -> dict:
    try:
        account = await crud.add_company_bank_account(db, company_id, payload)
    except ValueError as exc:
        raise _map_value_error(exc) from exc
    if account is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return account


async def update_company_bank_account_service(
    db: AsyncSession,
    company_id: UUID,
    account_id: UUID,
    payload: dict,
) -> dict:
    try:
        account = await crud.update_company_bank_account(db, company_id, account_id, payload)
    except ValueError as exc:
        raise _map_value_error(exc) from exc
    if account is None:
        raise HTTPException(status_code=404, detail="Bank account not found")
    return account


async def delete_company_bank_account_service(
    db: AsyncSession,
    company_id: UUID,
    account_id: UUID,
) -> None:
    deleted = await crud.delete_company_bank_account(db, company_id, account_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Bank account not found")


async def add_company_contact_service(
    db: AsyncSession,
    company_id: UUID,
    payload: dict,
) -> dict:
    try:
        contact = await crud.add_company_contact(db, company_id, payload)
    except ValueError as exc:
        raise _map_value_error(exc) from exc
    if contact is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return contact


async def update_company_contact_service(
    db: AsyncSession,
    company_id: UUID,
    contact_id: UUID,
    payload: dict,
) -> dict:
    try:
        contact = await crud.update_company_contact(db, company_id, contact_id, payload)
    except ValueError as exc:
        raise _map_value_error(exc) from exc
    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


async def delete_company_contact_service(
    db: AsyncSession,
    company_id: UUID,
    contact_id: UUID,
) -> None:
    deleted = await crud.delete_company_contact(db, company_id, contact_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Contact not found")


async def replace_company_operations_service(
    db: AsyncSession,
    company_id: UUID,
    payload: dict,
) -> dict:
    try:
        company = await crud.update_company_extra_section(db, company_id, "operations", payload)
    except ValueError as exc:
        raise _map_value_error(exc) from exc
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    operations = _extra_section(company, "operations")
    return schemas.OperationsProfile.model_validate(operations).model_dump(mode="json")


async def update_company_compliance_service(
    db: AsyncSession,
    company_id: UUID,
    payload: dict,
) -> dict:
    try:
        company = await crud.update_company_extra_section(db, company_id, "compliance", payload)
    except ValueError as exc:
        raise _map_value_error(exc) from exc
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    compliance = _extra_section(company, "compliance")
    return schemas.ComplianceProfile.model_validate(compliance).model_dump(mode="json")


async def update_company_portal_service(
    db: AsyncSession,
    company_id: UUID,
    payload: dict,
) -> dict:
    try:
        company = await crud.update_company_extra_section(db, company_id, "client_portal", payload)
    except ValueError as exc:
        raise _map_value_error(exc) from exc
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    portal = _extra_section(company, "client_portal")
    return schemas.PortalProfile.model_validate(portal).model_dump(mode="json")


async def update_company_integrations_service(
    db: AsyncSession,
    company_id: UUID,
    payload: dict,
) -> dict:
    try:
        company = await crud.update_company_extra_section(db, company_id, "integrations", payload)
    except ValueError as exc:
        raise _map_value_error(exc) from exc
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    integrations = _extra_section(company, "integrations")
    return schemas.IntegrationsProfile.model_validate(integrations).model_dump(mode="json")


async def enable_company_portal_service(
    db: AsyncSession,
    company_id: UUID,
    enabled: bool,
    url: str | None = None,
) -> dict:
    payload: dict = {"enabled": enabled}
    if url is not None:
        payload["url"] = url
    return await update_company_portal_service(db, company_id, payload)


async def get_company_readiness_service(
    db: AsyncSession,
    company_id: UUID,
) -> schemas.CompanyReadiness:
    readiness = await crud.get_company_readiness_info(db, company_id)
    if not readiness:
        raise HTTPException(status_code=404, detail="Company not found")
    return readiness
