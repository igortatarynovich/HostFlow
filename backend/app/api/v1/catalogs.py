from __future__ import annotations

import sqlalchemy as sa
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
from fastapi import APIRouter, Depends, Request


# backend/app/api/v1/catalogs.py




router = APIRouter()

DEV_TENANT_ID = "11111111-1111-1111-1111-111111111111"


def _get_tenant_id_from_request(request: Request) -> str:
    return request.headers.get("X-Tenant-Id", DEV_TENANT_ID)


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
    request: Request,
    dep = Depends(get_db),
):
    """
    Менеджеры/рекрутеры доступные в текущем тенанте.
    Источник: users (role in ['recruiter','supervisor','administrator']).
    Ответ: [{ id, short_id, full_name, email, label }]
    """
    # get_db may return either an AsyncSession or a tuple (AsyncSession, tenant_id)
    tenant_from_dep = None
    db = dep
    if isinstance(dep, tuple) and len(dep) >= 1:
        db = dep[0]
        if len(dep) > 1:
            tenant_from_dep = dep[1]

    tenant_id_raw = tenant_from_dep or _get_tenant_id_from_request(request)
    tenant_id = str(tenant_id_raw)

    ALLOWED_ROLES = ["recruiter", "supervisor", "administrator"]

    # Используем Core-таблицу, чтобы не зависеть от определения ORM-модели User
    users = sa.table(
        "users",
        sa.column("id"),
        sa.column("email"),
        sa.column("short_id"),
        sa.column("full_name"),
        sa.column("tenant_id"),
        sa.column("deleted_at"),
        sa.column("role"),
    )

    stmt = (
        sa.select(users.c.id, users.c.email, users.c.short_id, users.c.full_name)
        .where(
            users.c.tenant_id == tenant_id,
            users.c.deleted_at.is_(None),
            sa.cast(users.c.role, sa.String).in_(ALLOWED_ROLES),
        )
        .order_by(sa.func.coalesce(users.c.full_name, users.c.email).asc())
    )

    res = (await db.execute(stmt)).all()
    rows = [
        {
            "id": r.id,
            "short_id": r.short_id,
            "full_name": r.full_name,
            "email": r.email,
            "label": r.full_name or r.email,
        }
        for r in res
    ]
    return rows
