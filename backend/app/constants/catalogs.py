# backend/app/constants/catalogs.py
# -*- coding: utf-8 -*-

"""Runtime country/dial catalogs are projections of the Country Registry (R2).

Identity SoT: ``docs/specs/platform/country-registry-v1.json`` via
``backend.app.reference.country_registry``. Languages remain a local list.
"""

from backend.app.reference.country_registry import list_country_registry_entries

_ENTRIES = list_country_registry_entries()

COUNTRIES: dict[str, str] = {
    entry.identity.alpha2: entry.labels.ru for entry in _ENTRIES
}

# --- Languages (Европа + популярные; названия на русском) ---
LANGUAGES: list[dict[str, str]] = [
    {"code": "pl", "name": "Польский"},
    {"code": "en", "name": "Английский"},
    {"code": "uk", "name": "Украинский"},
    {"code": "ru", "name": "Русский"},
    {"code": "de", "name": "Немецкий"},
    {"code": "fr", "name": "Французский"},
    {"code": "es", "name": "Испанский"},
    {"code": "it", "name": "Итальянский"},
    {"code": "pt", "name": "Португальский"},
    {"code": "nl", "name": "Нидерландский"},
    {"code": "cs", "name": "Чешский"},
    {"code": "sk", "name": "Словацкий"},
    {"code": "ro", "name": "Румынский"},
    {"code": "bg", "name": "Болгарский"},
    {"code": "hu", "name": "Венгерский"},
    {"code": "lt", "name": "Литовский"},
    {"code": "lv", "name": "Латышский"},
    {"code": "et", "name": "Эстонский"},
    {"code": "sv", "name": "Шведский"},
    {"code": "da", "name": "Датский"},
    {"code": "fi", "name": "Финский"},
    {"code": "no", "name": "Норвежский"},
    {"code": "el", "name": "Греческий"},
    {"code": "tr", "name": "Турецкий"},
    {"code": "ar", "name": "Арабский"},
    {"code": "he", "name": "Иврит"},
    {"code": "zh", "name": "Китайский"},
    {"code": "hi", "name": "Хинди"},
    {"code": "vi", "name": "Вьетнамский"},
    {"code": "th", "name": "Тайский"},
    {"code": "id", "name": "Индонезийский"},
    {"code": "other", "name": "Другое"},
]

# Backward compatibility: старый код мог импортить LANGUAGES_EU
LANGUAGES_EU = LANGUAGES

DIAL_CODES: dict[str, str] = {
    entry.identity.alpha2: entry.classifications.dial_code for entry in _ENTRIES
}

__all__ = ["COUNTRIES", "LANGUAGES", "LANGUAGES_EU", "DIAL_CODES"]
