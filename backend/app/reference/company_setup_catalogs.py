"""Canonical company-setup and launch-search reference catalogs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Final


@dataclass(frozen=True)
class LocalizedCatalogItem:
    code: str
    label_ru: str
    label_en: str
    meta: dict[str, Any] = field(default_factory=dict)


INDUSTRIES: Final[tuple[LocalizedCatalogItem, ...]] = (
    LocalizedCatalogItem("transport_logistics", "Транспорт и логистика", "Transport & logistics"),
    LocalizedCatalogItem("manufacturing", "Производство", "Manufacturing"),
    LocalizedCatalogItem("construction", "Строительство", "Construction"),
    LocalizedCatalogItem("retail", "Розничная торговля", "Retail"),
    LocalizedCatalogItem("horeca", "HoReCa", "HoReCa"),
    LocalizedCatalogItem("it", "IT", "IT"),
    LocalizedCatalogItem("healthcare", "Медицина", "Healthcare"),
    LocalizedCatalogItem("finance", "Финансы", "Finance"),
    LocalizedCatalogItem("education", "Образование", "Education"),
    LocalizedCatalogItem("agriculture", "Сельское хозяйство", "Agriculture"),
    LocalizedCatalogItem("energy", "Энергетика", "Energy"),
    LocalizedCatalogItem("telecom", "Телеком", "Telecommunications"),
    LocalizedCatalogItem("real_estate", "Недвижимость", "Real estate"),
    LocalizedCatalogItem("cleaning_services", "Клининг и facility", "Cleaning & facility"),
    LocalizedCatalogItem("other", "Другое", "Other"),
)

TEAM_SIZES: Final[tuple[LocalizedCatalogItem, ...]] = (
    LocalizedCatalogItem("solo", "Только я", "Just me"),
    LocalizedCatalogItem("2_10", "2–10", "2–10"),
    LocalizedCatalogItem("11_50", "11–50", "11–50"),
    LocalizedCatalogItem("51_250", "51–250", "51–250"),
    LocalizedCatalogItem("251_1000", "251–1000", "251–1000"),
    LocalizedCatalogItem("1000_plus", "Более 1000", "1000+"),
)

BUSINESS_TYPES: Final[tuple[LocalizedCatalogItem, ...]] = (
    LocalizedCatalogItem("agency", "Кадровое агентство", "Recruitment agency"),
    LocalizedCatalogItem("employer", "Работодатель", "Employer"),
    LocalizedCatalogItem("services", "Сервисная компания", "Services company"),
)

PLATFORM_IDENTITIES: Final[tuple[LocalizedCatalogItem, ...]] = (
    LocalizedCatalogItem(
        "recruitment_agency",
        "Кадровое агентство",
        "Recruitment agency",
        meta={"emoji": "👥", "business_type": "agency", "industry_hint": "transport_logistics", "business_model": "recruitment_agency"},
    ),
    LocalizedCatalogItem(
        "transport_company",
        "Транспортная компания",
        "Transport company",
        meta={"emoji": "🚛", "business_type": "employer", "industry_hint": "transport_logistics", "business_model": "transport_company"},
    ),
    LocalizedCatalogItem(
        "manufacturing_company",
        "Производственная компания",
        "Manufacturing company",
        meta={"emoji": "🏭", "business_type": "employer", "industry_hint": "manufacturing", "business_model": "manufacturing_company"},
    ),
    LocalizedCatalogItem(
        "construction_company",
        "Строительство",
        "Construction",
        meta={"emoji": "🏗️", "business_type": "employer", "industry_hint": "construction", "business_model": "construction_company"},
    ),
    LocalizedCatalogItem(
        "logistics_operator",
        "Логистический оператор",
        "Logistics operator",
        meta={"emoji": "📦", "business_type": "employer", "industry_hint": "transport_logistics", "business_model": "logistics_operator"},
    ),
    LocalizedCatalogItem(
        "cleaning_services",
        "Клининг",
        "Cleaning services",
        meta={"emoji": "🧹", "business_type": "services", "industry_hint": "cleaning_services", "business_model": "cleaning_services"},
    ),
    LocalizedCatalogItem(
        "horeca_business",
        "Ресторан / HoReCa",
        "Restaurant / HoReCa",
        meta={"emoji": "🍽️", "business_type": "employer", "industry_hint": "horeca", "business_model": "horeca"},
    ),
    LocalizedCatalogItem(
        "healthcare_business",
        "Медицина",
        "Healthcare",
        meta={"emoji": "🏥", "business_type": "employer", "industry_hint": "healthcare", "business_model": "healthcare"},
    ),
    LocalizedCatalogItem(
        "other",
        "Другое",
        "Other",
        meta={"emoji": "💼", "business_type": "employer", "industry_hint": "other", "business_model": "other"},
    ),
)

FIRST_MODULES: Final[tuple[LocalizedCatalogItem, ...]] = (
    LocalizedCatalogItem(
        "recruitment",
        "Найти сотрудников",
        "Find employees",
        meta={"emoji": "🔍", "description_ru": "Вакансии, кандидаты, источники", "description_en": "Vacancies, candidates, sources", "enabled": True},
    ),
    LocalizedCatalogItem(
        "hr",
        "Управлять сотрудниками",
        "Manage employees",
        meta={"emoji": "👤", "description_ru": "Кадры, документы, отпуска", "description_en": "HR, documents, time off", "enabled": False},
    ),
    LocalizedCatalogItem(
        "fleet",
        "Управлять транспортом",
        "Manage fleet",
        meta={"emoji": "🚛", "description_ru": "Автопарк, водители, рейсы", "description_en": "Vehicles, drivers, trips", "enabled": False},
    ),
    LocalizedCatalogItem(
        "orders",
        "Управлять заказами",
        "Manage orders",
        meta={"emoji": "📋", "description_ru": "Клиенты, заказы, услуги", "description_en": "Clients, orders, services", "enabled": False},
    ),
    LocalizedCatalogItem(
        "explore",
        "Просто посмотреть систему",
        "Just explore",
        meta={"emoji": "👀", "description_ru": "Ознакомительный режим", "description_en": "Look around first", "enabled": False},
    ),
)

# Launch-search roles map to vacancy_categories codes with launch-search runtime support.
VACANCY_SEARCH_CATEGORIES: Final[tuple[LocalizedCatalogItem, ...]] = (
    LocalizedCatalogItem(
        "driver",
        "Водитель",
        "Driver",
        meta={
            "emoji": "🚛",
            "subtitle_ru": "CE, кат. C, международные рейсы",
            "subtitle_en": "CE, class C, international routes",
            "launch_search_supported": True,
        },
    ),
    LocalizedCatalogItem(
        "warehouse",
        "Склад",
        "Warehouse",
        meta={
            "emoji": "📦",
            "subtitle_ru": "Комплектовщик, погрузчик, логистика",
            "subtitle_en": "Picker, forklift, logistics",
            "launch_search_supported": True,
        },
    ),
    LocalizedCatalogItem(
        "office",
        "Офис",
        "Office",
        meta={
            "emoji": "🏢",
            "subtitle_ru": "Диспетчер, бухгалтер, менеджер",
            "subtitle_en": "Dispatcher, accountant, manager",
            "launch_search_supported": True,
        },
    ),
    LocalizedCatalogItem(
        "dispatcher",
        "Диспетчер",
        "Dispatcher",
        meta={
            "emoji": "📡",
            "subtitle_ru": "Планирование рейсов и координация",
            "subtitle_en": "Route planning and coordination",
            "launch_search_supported": False,
        },
    ),
    LocalizedCatalogItem(
        "mechanic",
        "Механик",
        "Mechanic",
        meta={
            "emoji": "🔧",
            "subtitle_ru": "Техобслуживание и ремонт",
            "subtitle_en": "Maintenance and repair",
            "launch_search_supported": False,
        },
    ),
    LocalizedCatalogItem(
        "other",
        "Другое",
        "Other",
        meta={
            "emoji": "✏️",
            "subtitle_ru": "Своя формулировка",
            "subtitle_en": "Custom role",
            "launch_search_supported": True,
        },
    ),
)

INDUSTRY_CODES: Final[frozenset[str]] = frozenset(item.code for item in INDUSTRIES)
TEAM_SIZE_CODES: Final[frozenset[str]] = frozenset(item.code for item in TEAM_SIZES)
BUSINESS_TYPE_CODES: Final[frozenset[str]] = frozenset(item.code for item in BUSINESS_TYPES)
PLATFORM_IDENTITY_CODES: Final[frozenset[str]] = frozenset(item.code for item in PLATFORM_IDENTITIES)
VACANCY_SEARCH_CATEGORY_CODES: Final[frozenset[str]] = frozenset(item.code for item in VACANCY_SEARCH_CATEGORIES)


def list_industries() -> tuple[LocalizedCatalogItem, ...]:
    return INDUSTRIES


def list_team_sizes(*, onboarding: bool = False) -> tuple[LocalizedCatalogItem, ...]:
    """Return team-size buckets.

    ``onboarding`` is reserved for a tighter wizard subset; today both paths share
    the same canonical catalog so callers (API + reference foundation) stay compatible.
    """
    _ = onboarding
    return TEAM_SIZES


def list_business_types() -> tuple[LocalizedCatalogItem, ...]:
    return BUSINESS_TYPES


def list_platform_identities() -> tuple[LocalizedCatalogItem, ...]:
    return PLATFORM_IDENTITIES


def list_first_modules() -> tuple[LocalizedCatalogItem, ...]:
    return FIRST_MODULES


def list_vacancy_search_categories(*, launch_search_only: bool = False) -> tuple[LocalizedCatalogItem, ...]:
    if not launch_search_only:
        return VACANCY_SEARCH_CATEGORIES
    return tuple(
        item
        for item in VACANCY_SEARCH_CATEGORIES
        if bool(item.meta.get("launch_search_supported"))
    )


def normalize_industry_code(value: str | None) -> str | None:
    if value is None:
        return None
    code = str(value).strip().lower().replace("-", "_")
    return code if code in INDUSTRY_CODES else None


def get_platform_identity(code: str) -> LocalizedCatalogItem | None:
    normalized = str(code or "").strip().lower()
    for item in PLATFORM_IDENTITIES:
        if item.code == normalized:
            return item
    return None
