from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.workforce_eligibility_resolver import (
    WorkforceEligibilityContext as ResolverWorkforceEligibilityContext,
    WorkforceEligibilityResolver,
)


@dataclass
class WorkforceEligibilityContext:
    tenant_id: str
    candidate_id: str | None = None
    employee_id: str | None = None
    citizenship: str | None = None
    work_country: str | None = None
    residence_status: str | None = None
    position_category: str | None = None
    employment_type: str | None = None
    stage: str | None = None
    client_id: str | None = None
    vacancy_id: str | None = None


async def resolve_workforce_eligibility_via_contract(
    db: AsyncSession,
    *,
    context: WorkforceEligibilityContext,
) -> dict[str, Any]:
    """Delivery-contract adapter for workforce eligibility reads."""
    return await WorkforceEligibilityResolver.resolve(
        db,
        context=ResolverWorkforceEligibilityContext(
            tenant_id=context.tenant_id,
            candidate_id=context.candidate_id,
            employee_id=context.employee_id,
            citizenship=context.citizenship,
            work_country=context.work_country,
            residence_status=context.residence_status,
            position_category=context.position_category,
            employment_type=context.employment_type,
            stage=context.stage,
            client_id=context.client_id,
            vacancy_id=context.vacancy_id,
        ),
    )
