from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple

from .catalogs import COUNTRIES, DIAL_CODES, LANGUAGES

# backend/app/constants/catalog_utils.py
# -*- coding: utf-8 -*-




# ---------- emoji-флаг по ISO-коду ----------
def flag(code: str) -> str:
    """
    Вернёт emoji-флаг по ISO alpha-2 (напр. 'PL' -> '🇵🇱').
    Для невалидного кода — пустую строку.
    """
    if not code or len(code) != 2:
        return ""
    try:
        cu = code.upper()
        a: str = cu[0]
        b: str = cu[1]
        base = 0x1F1E6
        return chr(base + (ord(a) - ord("A"))) + chr(base + (ord(b) - ord("A")))
    except Exception:
        return ""


# ---------- мапки для быстрых поисков ----------
def country_name(code: str) -> str:
    """Руское название страны по коду (или сам код, если не нашли)."""
    return COUNTRIES.get(code.upper(), code.upper())


def dial_code_by_country(code: str) -> str | None:
    """Телефонный код страны по ISO-2 (или None)."""
    return DIAL_CODES.get(code.upper())


def country_by_dial(dial: str) -> List[Tuple[str, str]]:
    """
    Найти страны по телефонному коду (могут совпадать, напр. '+1' США/Канада).
    Возвращает список (iso2, country_name).
    """
    dial = dial.strip()
    out: List[Tuple[str, str]] = []
    for iso, d in DIAL_CODES.items():
        if d == dial:
            out.append((iso, country_name(iso)))
    return sorted(out, key=lambda x: x[1])


# ---------- генераторы «options» для фронта ----------
def to_options_countries() -> List[Dict[str, Any]]:
    """
    [{ value: 'PL', label: '🇵🇱 Польша', meta: {code, name, dial_code} }, ...]
    Отсортировано по label.
    """
    options: List[Dict[str, Any]] = []
    for iso, name in COUNTRIES.items():
        options.append(
            {
                "value": iso,
                "label": f"{flag(iso)} {name}".strip(),
                "meta": {
                    "code": iso,
                    "name": name,
                    "dial_code": DIAL_CODES.get(iso),
                },
            }
        )
    options.sort(key=lambda x: x["label"])
    return options


def to_options_languages() -> List[Dict[str, str]]:
    """
    [{ value: 'ru', label: 'Русский' }, ...]
    Отсортировано по label.
    """
    opts = [{"value": it["code"], "label": it["name"]} for it in LANGUAGES]
    opts.sort(key=lambda x: x["label"])
    return opts


def to_options_dial_codes() -> List[Dict[str, Any]]:
    """
    [{ value: '+48', label: '🇵🇱 +48 — Польша', meta: {country:'PL', name:'Польша'} }, ...]
    Отсортировано по label (т.е. по стране).
    """
    options: List[Dict[str, Any]] = []
    for iso, dial in DIAL_CODES.items():
        name = country_name(iso)
        options.append(
            {
                "value": dial,
                "label": f"{flag(iso)} {dial} — {name}".strip(),
                "meta": {"country": iso, "name": name},
            }
        )
    options.sort(key=lambda x: x["label"])
    return options


def to_options_localized_catalog(items: Iterable[Any]) -> List[Dict[str, Any]]:
    """Map LocalizedCatalogItem / CityCatalogItem rows to frontend option DTOs."""
    options: List[Dict[str, Any]] = []
    for item in items:
        code = str(getattr(item, "code", "") or "").strip()
        if not code:
            continue
        label_ru = str(getattr(item, "label_ru", "") or code).strip()
        label_en = str(getattr(item, "label_en", "") or label_ru).strip()
        meta = dict(getattr(item, "meta", {}) or {})
        if getattr(item, "country_code", None):
            meta.setdefault("country_code", str(item.country_code))
        options.append(
            {
                "value": code,
                "label": label_ru,
                "meta": {
                    **meta,
                    "label_ru": label_ru,
                    "label_en": label_en,
                },
            }
        )
    options.sort(key=lambda x: x["label"])
    return options


def to_options_company_setup(
    *,
    countries: List[Dict[str, Any]],
    industries: List[Dict[str, Any]],
    team_sizes: List[Dict[str, Any]],
    platform_identities: List[Dict[str, Any]],
    first_modules: List[Dict[str, Any]],
    business_types: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    return {
        "countries": countries,
        "industries": industries,
        "team_sizes": team_sizes,
        "platform_identities": platform_identities,
        "first_modules": first_modules,
        "business_types": business_types,
    }


# ---------- вспомогательные преобразования ----------
def as_code_name_list(d: Dict[str, str]) -> List[Dict[str, str]]:
    """
    Преобразовать {'PL':'Польша', ...} -> [{'code':'PL','name':'Польша'}, ...] (сортировано).
    Удобно для старого API.
    """
    items = [{"code": k, "name": v} for k, v in d.items()]
    items.sort(key=lambda x: x["name"])
    return items


def as_country_dial_list() -> List[Dict[str, str]]:
    """
    [{country:'PL', dial_code:'+48'}, ...] — “сырой” формат, как в текущем API.
    """
    items = [{"country": iso, "dial_code": dial} for iso, dial in DIAL_CODES.items()]
    items.sort(key=lambda x: country_name(x["country"]))
    return items


__all__ = [
    "flag",
    "country_name",
    "dial_code_by_country",
    "country_by_dial",
    "to_options_countries",
    "to_options_languages",
    "to_options_dial_codes",
    "to_options_localized_catalog",
    "to_options_company_setup",
    "as_code_name_list",
    "as_country_dial_list",
]
