"""Platform reference catalogs for B2B targeted-advertising questionnaire.

Single source of truth for professions, services, and regions used by intake forms,
CRM filters, and analytics — not per-form static option lists.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Final


@dataclass(frozen=True)
class LocalizedCatalogItem:
    code: str
    label_ru: str
    label_en: str
    meta: dict[str, Any] = field(default_factory=dict)


PROFESSIONS: Final[tuple[LocalizedCatalogItem, ...]] = (
    LocalizedCatalogItem("driver_ce", "Водитель C+E", "Driver C+E"),
    LocalizedCatalogItem("driver_c", "Водитель C", "Driver C"),
    LocalizedCatalogItem("driver_b", "Водитель B", "Driver B"),
    LocalizedCatalogItem("dispatcher", "Диспетчер", "Dispatcher"),
    LocalizedCatalogItem("logistician", "Логист", "Logistician"),
    LocalizedCatalogItem("warehouse_worker", "Кладовщик", "Warehouse worker"),
    LocalizedCatalogItem("welder", "Сварщик", "Welder"),
    LocalizedCatalogItem("mechanic", "Механик", "Mechanic"),
    LocalizedCatalogItem("production_worker", "Рабочий производства", "Production worker"),
    LocalizedCatalogItem("office_staff", "Офисный сотрудник", "Office staff"),
    LocalizedCatalogItem("other", "Указать свою", "Custom profession"),
)

ADVERTISED_SERVICES: Final[tuple[LocalizedCatalogItem, ...]] = (
    LocalizedCatalogItem("targeted_advertising", "Таргетированная реклама", "Targeted advertising"),
    LocalizedCatalogItem("website_creation", "Создание сайта", "Website creation"),
    LocalizedCatalogItem("accounting", "Бухгалтерские услуги", "Accounting services"),
    LocalizedCatalogItem("freight", "Грузоперевозки", "Freight transport"),
    LocalizedCatalogItem("car_sales", "Продажа автомобилей", "Car sales"),
    LocalizedCatalogItem("dentistry", "Стоматология", "Dentistry"),
    LocalizedCatalogItem("legal", "Юридические услуги", "Legal services"),
    LocalizedCatalogItem("cleaning", "Клининг", "Cleaning services"),
    LocalizedCatalogItem("construction", "Строительные услуги", "Construction services"),
    LocalizedCatalogItem("other", "Другая услуга", "Other service"),
)

REGIONS: Final[tuple[LocalizedCatalogItem, ...]] = (
    # Poland — voivodeships (starter set)
    LocalizedCatalogItem("PL-MZ", "Мазовецкое", "Masovian", meta={"country_code": "PL"}),
    LocalizedCatalogItem("PL-MA", "Малопольское", "Lesser Poland", meta={"country_code": "PL"}),
    LocalizedCatalogItem("PL-DS", "Нижнесилезское", "Lower Silesian", meta={"country_code": "PL"}),
    LocalizedCatalogItem("PL-WP", "Великопольское", "Greater Poland", meta={"country_code": "PL"}),
    LocalizedCatalogItem("PL-PM", "Поморское", "Pomeranian", meta={"country_code": "PL"}),
    LocalizedCatalogItem("PL-SL", "Силезское", "Silesian", meta={"country_code": "PL"}),
    LocalizedCatalogItem("PL-LD", "Лодзинское", "Łódź", meta={"country_code": "PL"}),
    # Germany — starter Bundesländer
    LocalizedCatalogItem("DE-BE", "Берлин", "Berlin", meta={"country_code": "DE"}),
    LocalizedCatalogItem("DE-BY", "Бавария", "Bavaria", meta={"country_code": "DE"}),
    LocalizedCatalogItem("DE-NW", "Северный Рейн-Вестфалия", "North Rhine-Westphalia", meta={"country_code": "DE"}),
    LocalizedCatalogItem("DE-HH", "Гамбург", "Hamburg", meta={"country_code": "DE"}),
    LocalizedCatalogItem("DE-HE", "Гессен", "Hesse", meta={"country_code": "DE"}),
    # Ukraine
    LocalizedCatalogItem("UA-KY", "Киевская область", "Kyiv region", meta={"country_code": "UA"}),
    LocalizedCatalogItem("UA-LV", "Львовская область", "Lviv region", meta={"country_code": "UA"}),
    LocalizedCatalogItem("UA-OD", "Одесская область", "Odesa region", meta={"country_code": "UA"}),
)


def list_professions() -> tuple[LocalizedCatalogItem, ...]:
    return PROFESSIONS


def list_advertised_services() -> tuple[LocalizedCatalogItem, ...]:
    return ADVERTISED_SERVICES


def list_regions(*, country_code: str | None = None) -> tuple[LocalizedCatalogItem, ...]:
    if not country_code:
        return REGIONS
    cc = str(country_code).strip().upper()
    return tuple(item for item in REGIONS if str(item.meta.get("country_code") or "").upper() == cc)
