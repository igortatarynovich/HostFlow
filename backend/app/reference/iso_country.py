"""ISO-3166 alpha-2 normalization for document and citizenship adapters."""

from __future__ import annotations

from typing import Any, Optional

_LEGACY_COUNTRY_TO_ISO2: dict[str, str] = {
    "pl": "PL",
    "pol": "PL",
    "poland": "PL",
    "polska": "PL",
    "ua": "UA",
    "ukr": "UA",
    "ukraine": "UA",
    "ukraina": "UA",
    "украина": "UA",
    "by": "BY",
    "blr": "BY",
    "belarus": "BY",
    "białoruś": "BY",
    "belarusia": "BY",
    "md": "MD",
    "mda": "MD",
    "moldova": "MD",
    "mołdawia": "MD",
    "ge": "GE",
    "geo": "GE",
    "georgia": "GE",
    "gruzja": "GE",
    "ru": "RU",
    "rus": "RU",
    "russia": "RU",
    "rosja": "RU",
    "de": "DE",
    "deu": "DE",
    "germany": "DE",
    "niemcy": "DE",
    "lt": "LT",
    "ltu": "LT",
    "lithuania": "LT",
    "litwa": "LT",
    "lv": "LV",
    "lva": "LV",
    "latvia": "LV",
    "łotwa": "LV",
    "ee": "EE",
    "est": "EE",
    "estonia": "EE",
    "cz": "CZ",
    "cze": "CZ",
    "czech": "CZ",
    "czechia": "CZ",
    "czech_republic": "CZ",
    "sk": "SK",
    "svk": "SK",
    "slovakia": "SK",
    "słowacja": "SK",
    "ro": "RO",
    "rou": "RO",
    "romania": "RO",
    "rumunia": "RO",
    "bg": "BG",
    "bgr": "BG",
    "bulgaria": "BG",
    "bułgaria": "BG",
    "hu": "HU",
    "hun": "HU",
    "hungary": "HU",
    "węgry": "HU",
    "gb": "GB",
    "gbr": "GB",
    "uk": "GB",
    "united_kingdom": "GB",
    "great_britain": "GB",
    "wielka_brytania": "GB",
    "in": "IN",
    "ind": "IN",
    "india": "IN",
    "indie": "IN",
    "np": "NP",
    "npl": "NP",
    "nepal": "NP",
    "uz": "UZ",
    "uzb": "UZ",
    "uzbekistan": "UZ",
    "kg": "KG",
    "kgz": "KG",
    "kyrgyzstan": "KG",
    "tj": "TJ",
    "tjk": "TJ",
    "tajikistan": "TJ",
    "az": "AZ",
    "aze": "AZ",
    "azerbaijan": "AZ",
    "am": "AM",
    "arm": "AM",
    "armenia": "AM",
    "kz": "KZ",
    "kaz": "KZ",
    "kazakhstan": "KZ",
}


def normalize_country_iso2(value: Any) -> Optional[str]:
    """Return uppercase ISO-2 when value is unambiguous, else None."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) == 2 and text.isalpha():
        return text.upper()
    key = text.lower().replace("-", "_").replace(" ", "_")
    mapped = _LEGACY_COUNTRY_TO_ISO2.get(key)
    if mapped:
        return mapped
    compact = key.replace("_", "")
    return _LEGACY_COUNTRY_TO_ISO2.get(compact)


__all__ = ["normalize_country_iso2"]
