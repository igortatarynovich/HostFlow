from __future__ import annotations

from typing import Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.constants.catalog_utils import (
    as_code_name_list,
    as_country_dial_list,
    to_options_countries,
    to_options_dial_codes,
    to_options_languages,
)

# константы и утилиты справочников
from backend.app.constants.catalogs import COUNTRIES, LANGUAGES
from backend.app.db.deps import get_db_with_tenant as get_db
from backend.app.services import users as users_service
from fastapi import APIRouter, Depends, Query


# backend/app/api/v1/catalogs.py




router = APIRouter()

# ===================== Countries =====================
@router.get("/catalogs/countries")
async def list_countries():
    return as_code_name_list(COUNTRIES)


@router.get("/catalogs/countries/options")
async def list_countries_options():
    return to_options_countries()


# ===================== Languages =====================
@router.get("/catalogs/languages")
async def list_languages():
    return [{"code": x["code"], "name": x["name"]} for x in LANGUAGES]


@router.get("/catalogs/languages/options")
async def list_languages_options():
    return to_options_languages()


# ===================== Dial codes =====================
@router.get("/catalogs/dial-codes")
async def list_dial_codes():
    return as_country_dial_list()


@router.get("/catalogs/dial-codes/options")
async def list_dial_codes_options():
    return to_options_dial_codes()


# ===================== Managers (через memberships, кросс-СУБД) =====================
@router.get("/catalogs/managers")
async def list_managers(
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db),
    roles: str | None = Query(
        default=None,
        description=(
            "Необязательно: роли membership через запятую "
            "(например recruiter или recruiter,supervisor). "
            "По умолчанию — owner, administrator, supervisor, recruiter."
        ),
    ),
):
    """
    Менеджеры/рекрутеры в текущем тенанте (X-Tenant-Id).
    Источник: user_memberships; только пользователи без deleted_at и с is_active.
    """
    db, tenant_uuid = db_tenant
    role_list = (
        [p.strip() for p in roles.split(",") if p.strip()] if roles and roles.strip() else None
    )
    return await users_service.get_tenant_managers(
        db, str(tenant_uuid), membership_roles=role_list
    )
