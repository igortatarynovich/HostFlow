from __future__ import annotations

from typing import Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.reference.company_setup_catalogs import (
    list_business_types,
    list_first_modules,
    list_industries,
    list_platform_identities,
    list_team_sizes,
    list_vacancy_search_categories,
)
from backend.app.reference.geo_cities_catalog import list_cities
from backend.app.constants.catalog_utils import (
    as_code_name_list,
    as_country_dial_list,
    to_options_company_setup,
    to_options_countries,
    to_options_dial_codes,
    to_options_languages,
    to_options_localized_catalog,
)
from backend.app.constants.catalogs import COUNTRIES, LANGUAGES
from backend.app.db.deps import get_db_with_tenant as get_db
from backend.app.services import users as users_service
from fastapi import APIRouter, Depends, Query

router = APIRouter()


@router.get("/catalogs/countries")
async def list_countries():
    return as_code_name_list(COUNTRIES)


@router.get("/catalogs/countries/options")
async def list_countries_options():
    return to_options_countries()


@router.get("/catalogs/languages")
async def list_languages():
    return [{"code": x["code"], "name": x["name"]} for x in LANGUAGES]


@router.get("/catalogs/languages/options")
async def list_languages_options():
    return to_options_languages()


@router.get("/catalogs/dial-codes")
async def list_dial_codes():
    return as_country_dial_list()


@router.get("/catalogs/dial-codes/options")
async def list_dial_codes_options():
    return to_options_dial_codes()


@router.get("/catalogs/industries/options")
async def list_industries_options():
    return to_options_localized_catalog(list_industries())


@router.get("/catalogs/team-sizes/options")
async def list_team_sizes_options(
    onboarding: bool = Query(False, description="Use onboarding wizard bucket sizes"),
):
    return to_options_localized_catalog(list_team_sizes(onboarding=onboarding))


@router.get("/catalogs/business-types/options")
async def list_business_types_options():
    return to_options_localized_catalog(list_business_types())


@router.get("/catalogs/platform-identities/options")
async def list_platform_identities_options():
    return to_options_localized_catalog(list_platform_identities())


@router.get("/catalogs/first-modules/options")
async def list_first_modules_options():
    return to_options_localized_catalog(list_first_modules())


@router.get("/catalogs/vacancy-categories/options")
async def list_vacancy_categories_options(
    launch_search_only: bool = Query(False, description="Only categories supported by launch-search wizard"),
):
    return to_options_localized_catalog(
        list_vacancy_search_categories(launch_search_only=launch_search_only)
    )


@router.get("/catalogs/cities/options")
async def list_cities_options(
    country: str | None = Query(None, description="ISO alpha-2 country code"),
):
    return to_options_localized_catalog(list_cities(country_code=country))


@router.get("/catalogs/regions/options")
async def list_regions_options(
    country: str | None = Query(None, description="ISO alpha-2 country code"),
):
    from backend.app.reference.questionnaire_catalogs import list_regions

    return to_options_localized_catalog(list_regions(country_code=country))


@router.get("/catalogs/professions/options")
async def list_professions_options():
    from backend.app.reference.questionnaire_catalogs import list_professions

    return to_options_localized_catalog(list_professions())


@router.get("/catalogs/services/options")
async def list_advertised_services_options():
    from backend.app.reference.questionnaire_catalogs import list_advertised_services

    return to_options_localized_catalog(list_advertised_services())


@router.get("/catalogs/company-setup/options")
async def list_company_setup_options():
    return to_options_company_setup(
        countries=to_options_countries(),
        industries=to_options_localized_catalog(list_industries()),
        team_sizes=to_options_localized_catalog(list_team_sizes(onboarding=False)),
        platform_identities=to_options_localized_catalog(list_platform_identities()),
        first_modules=to_options_localized_catalog(list_first_modules()),
        business_types=to_options_localized_catalog(list_business_types()),
    )


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
    db, tenant_uuid = db_tenant
    role_list = (
        [p.strip() for p in roles.split(",") if p.strip()] if roles and roles.strip() else None
    )
    return await users_service.get_tenant_managers(
        db, str(tenant_uuid), membership_roles=role_list
    )
