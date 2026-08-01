"""Resolve promotion targets for Campaign foundation (ADR-024 Stage 3A).

Registry validation decides *what kinds* of targets are allowed.
This module decides whether a concrete ``target_id`` exists and is
accessible under the Campaign's tenant + own-company scope.

Campaign never takes ownership of Recruitment/Sales domain rows —
it only references them by type/id.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.validation import CampaignValidationError
from backend.app.models.additional_service import Service, ServiceOrder
from backend.app.models.client_account import ClientAccount
from backend.app.models.fleet_vehicle import FleetVehicle
from backend.app.models.vacancy import Vacancy


async def assert_promotion_target_accessible(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str,
    target_type: str,
    target_id: str,
) -> None:
    """Raise CampaignValidationError if the target cannot be promoted.

    Missing / cross-company targets → 404 (no existence leak).
    Unsupported target types without SoT → 422.
    """
    tt = str(target_type or "").strip().lower()
    tid = str(target_id or "").strip()
    if not tt or not tid:
        raise CampaignValidationError("target_type and target_id are required")

    if tt in {"vacancy", "search"}:
        await _assert_vacancy(db, tenant_id=tenant_id, own_company_id=own_company_id, target_id=tid)
        return
    if tt == "service":
        await _assert_service(db, tenant_id=tenant_id, target_id=tid)
        return
    if tt == "service_order":
        await _assert_service_order(db, tenant_id=tenant_id, target_id=tid)
        return
    if tt == "client_account":
        await _assert_client_account(
            db, tenant_id=tenant_id, own_company_id=own_company_id, target_id=tid
        )
        return
    if tt == "vehicle":
        await _assert_vehicle(db, tenant_id=tenant_id, target_id=tid)
        return
    if tt == "employee_role":
        raise CampaignValidationError(
            "promotion target_type 'employee_role' is not available yet (no HR opening SoT)",
            status_code=422,
        )
    raise CampaignValidationError(f"Unknown promotion target_type: {tt!r}")


async def _assert_vacancy(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str,
    target_id: str,
) -> None:
    row = await db.execute(
        select(Vacancy.id).where(
            Vacancy.id == target_id,
            Vacancy.tenant_id == tenant_id,
            Vacancy.own_company_id == own_company_id,
            Vacancy.is_archived.is_(False),
        )
    )
    if row.scalar_one_or_none() is None:
        raise CampaignValidationError("Promotion target not found", status_code=404)


async def _assert_service(db: AsyncSession, *, tenant_id: str, target_id: str) -> None:
    # Service catalog is tenant-scoped (no own_company_id on services).
    row = await db.execute(
        select(Service.id).where(
            Service.id == target_id,
            Service.tenant_id == tenant_id,
            Service.is_active.is_(True),
        )
    )
    if row.scalar_one_or_none() is None:
        raise CampaignValidationError("Promotion target not found", status_code=404)


async def _assert_service_order(db: AsyncSession, *, tenant_id: str, target_id: str) -> None:
    # Orders are tenant-scoped; company_id is the client counterparty (optional).
    row = await db.execute(
        select(ServiceOrder.id).where(
            ServiceOrder.id == target_id,
            ServiceOrder.tenant_id == tenant_id,
        )
    )
    if row.scalar_one_or_none() is None:
        raise CampaignValidationError("Promotion target not found", status_code=404)


async def _assert_client_account(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str,
    target_id: str,
) -> None:
    row = await db.execute(
        select(ClientAccount.id).where(
            ClientAccount.id == target_id,
            ClientAccount.tenant_id == tenant_id,
            ClientAccount.own_company_id == own_company_id,
        )
    )
    if row.scalar_one_or_none() is None:
        raise CampaignValidationError("Promotion target not found", status_code=404)


async def _assert_vehicle(db: AsyncSession, *, tenant_id: str, target_id: str) -> None:
    # Fleet vehicles are tenant-scoped; operating_company_id is client Company, not OwnCompany.
    row = await db.execute(
        select(FleetVehicle.id).where(
            FleetVehicle.id == target_id,
            FleetVehicle.tenant_id == tenant_id,
        )
    )
    if row.scalar_one_or_none() is None:
        raise CampaignValidationError("Promotion target not found", status_code=404)
