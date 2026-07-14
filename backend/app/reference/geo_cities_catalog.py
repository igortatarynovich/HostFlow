"""Major cities reference catalog grouped by country (ISO alpha-2)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class CityCatalogItem:
    code: str
    label_ru: str
    label_en: str
    country_code: str


def _city(code: str, ru: str, en: str, country: str) -> CityCatalogItem:
    return CityCatalogItem(code=code, label_ru=ru, label_en=en, country_code=country)


# Curated starter set for onboarding / client setup. Extend via reference layer only.
CITIES: Final[tuple[CityCatalogItem, ...]] = (
    # Poland
    _city("warsaw", "Варшава", "Warsaw", "PL"),
    _city("krakow", "Краков", "Kraków", "PL"),
    _city("wroclaw", "Вроцлав", "Wrocław", "PL"),
    _city("poznan", "Познань", "Poznań", "PL"),
    _city("gdansk", "Гданьск", "Gdańsk", "PL"),
    _city("lodz", "Лодзь", "Łódź", "PL"),
    _city("katowice", "Катовице", "Katowice", "PL"),
    _city("lublin", "Люблин", "Lublin", "PL"),
    _city("szczecin", "Щецин", "Szczecin", "PL"),
    _city("bydgoszcz", "Быдгощ", "Bydgoszcz", "PL"),
    # Germany
    _city("berlin", "Берлин", "Berlin", "DE"),
    _city("hamburg", "Гамбург", "Hamburg", "DE"),
    _city("munich", "Мюнхен", "Munich", "DE"),
    _city("cologne", "Кёльн", "Cologne", "DE"),
    _city("frankfurt", "Франкфурт", "Frankfurt", "DE"),
    _city("stuttgart", "Штутгарт", "Stuttgart", "DE"),
    _city("dusseldorf", "Дüsseldorf", "Düsseldorf", "DE"),
    _city("dortmund", "Дортмунд", "Dortmund", "DE"),
    # Ukraine
    _city("kyiv", "Киев", "Kyiv", "UA"),
    _city("lviv", "Львов", "Lviv", "UA"),
    _city("odesa", "Одесса", "Odesa", "UA"),
    _city("kharkiv", "Харьков", "Kharkiv", "UA"),
    _city("dnipro", "Днепр", "Dnipro", "UA"),
    # Czechia
    _city("prague", "Прага", "Prague", "CZ"),
    _city("brno", "Брно", "Brno", "CZ"),
    _city("ostrava", "Острава", "Ostrava", "CZ"),
    # Slovakia
    _city("bratislava", "Братислава", "Bratislava", "SK"),
    _city("kosice", "Кošice", "Košice", "SK"),
    # Lithuania
    _city("vilnius", "Вильнюс", "Vilnius", "LT"),
    _city("kaunas", "Каунас", "Kaunas", "LT"),
    # United Kingdom
    _city("london", "Лондон", "London", "GB"),
    _city("manchester", "Мanchester", "Manchester", "GB"),
    _city("birmingham", "Бirmingham", "Birmingham", "GB"),
    # United States
    _city("new_york", "Нью-Йорк", "New York", "US"),
    _city("chicago", "Чикаго", "Chicago", "US"),
    _city("los_angeles", "Лос-Анджелес", "Los Angeles", "US"),
)

CITY_CODES: Final[frozenset[str]] = frozenset(item.code for item in CITIES)


def list_cities(*, country_code: str | None = None) -> tuple[CityCatalogItem, ...]:
    if not country_code:
        return CITIES
    cc = str(country_code).strip().upper()
    if cc in {"", "OTHER"}:
        return ()
    return tuple(item for item in CITIES if item.country_code == cc)
