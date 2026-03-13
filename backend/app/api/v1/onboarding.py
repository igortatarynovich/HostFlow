"""Onboarding and activation status for self-serve CRM flow."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import UserCtx, get_current_user
from backend.app.db.deps import get_db_with_tenant
from backend.app.models import Company, Lead, Reminder, ServiceOrder, Tenant, Vacancy

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


class OnboardingStatusOut(BaseModel):
    business_type: str
    onboarding_required: bool
    activation_required: bool
    companies_count: int
    leads_count: int
    vacancies_count: int
    service_orders_count: int
    reminders_count: int
    clients_count: int
    counterparties_count: int
    steps: dict[str, bool]


def _normalize_company_role(extra: object) -> str | None:
    if not isinstance(extra, dict):
        return None
    raw = (
        extra.get("company_role")
        or extra.get("company_kind")
        or extra.get("kind")
        or extra.get("entity_type")
    )
    normalized = str(raw or "").strip().lower()
    if normalized in {"operating", "client", "counterparty"}:
        return normalized
    return None


@router.get("/status", response_model=OnboardingStatusOut)
async def get_onboarding_status(
    _user: UserCtx = Depends(get_current_user),
    db_tenant=Depends(get_db_with_tenant),
):
    """Onboarding/activation state for path `signup -> company -> first value`."""
    db, tenant_uuid = db_tenant
    tenant_id = str(tenant_uuid)
    tenant_row = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id).limit(1)
    )
    tenant = tenant_row.scalar_one_or_none()

    company_count_row = await db.execute(
        select(func.count())
        .select_from(Company)
        .where(Company.tenant_id == tenant_id, Company.is_archived.is_(False))
    )
    company_extra_rows = await db.execute(
        select(Company.extra).where(Company.tenant_id == tenant_id, Company.is_archived.is_(False))
    )
    lead_count_row = await db.execute(
        select(func.count()).select_from(Lead).where(Lead.tenant_id == tenant_id)
    )
    vacancy_count_row = await db.execute(
        select(func.count()).select_from(Vacancy).where(Vacancy.tenant_id == tenant_id)
    )
    service_order_count_row = await db.execute(
        select(func.count()).select_from(ServiceOrder).where(ServiceOrder.tenant_id == tenant_id)
    )
    reminder_count_row = await db.execute(
        select(func.count()).select_from(Reminder).where(Reminder.tenant_id == tenant_id)
    )

    total_companies_count = int(company_count_row.scalar_one() or 0)
    operating_companies_count = 0
    clients_count = 0
    counterparties_count = 0
    for extra in company_extra_rows.scalars().all():
        kind = _normalize_company_role(extra)
        if kind == "operating":
            operating_companies_count += 1
        elif kind == "client":
            clients_count += 1
        elif kind == "counterparty":
            counterparties_count += 1

    # Backward compatibility for tenants created before explicit company_role classification.
    if operating_companies_count == 0 and total_companies_count > 0:
        operating_companies_count = 1
        if clients_count == 0 and counterparties_count == 0 and total_companies_count > 1:
            clients_count = total_companies_count - 1

    leads_count = int(lead_count_row.scalar_one() or 0)
    vacancies_count = int(vacancy_count_row.scalar_one() or 0)
    service_orders_count = int(service_order_count_row.scalar_one() or 0)
    reminders_count = int(reminder_count_row.scalar_one() or 0)

    raw_business_type = (
        (tenant.settings or {}).get("business_type")
        if tenant is not None and isinstance(getattr(tenant, "settings", None), dict)
        else None
    )
    business_type = str(raw_business_type or "").strip().lower()
    if business_type not in ("agency", "employer", "services"):
        tenant_type_value = str(getattr(getattr(tenant, "type", None), "value", getattr(tenant, "type", ""))).strip().lower()
        if tenant_type_value == "company":
            business_type = "employer"
        else:
            business_type = "agency"

    onboarding_required = operating_companies_count == 0
    steps = {
        "company_created": operating_companies_count > 0,
        "first_lead_created": leads_count > 0,
        "first_vacancy_created": vacancies_count > 0,
        "first_service_order_created": service_orders_count > 0,
        "first_client_created": clients_count > 0,
        "next_action_created": reminders_count > 0,
    }
    if business_type == "employer":
        type_specific_ready = steps["first_vacancy_created"]
    elif business_type == "services":
        type_specific_ready = steps["first_client_created"]
    else:
        type_specific_ready = steps["first_lead_created"]
    activation_required = steps["company_created"] and not (
        type_specific_ready and steps["next_action_created"]
    )

    return OnboardingStatusOut(
        business_type=business_type,
        onboarding_required=onboarding_required,
        activation_required=activation_required,
        companies_count=operating_companies_count,
        leads_count=leads_count,
        vacancies_count=vacancies_count,
        service_orders_count=service_orders_count,
        reminders_count=reminders_count,
        clients_count=clients_count,
        counterparties_count=counterparties_count,
        steps=steps,
    )
