# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict, List

"""
Справочники для документов кандидата.

- DOC_STATUSES: допустимые статусы документов
- DEFAULT_DOCS: дефолтный набор документов, который можно инициализировать для кандидата
- Хелперы: is_valid_status(), default_docs_for()
"""

# Допустимые статусы документа
DOC_STATUSES: set[str] = {
    "pending",  # ожидание предоставления
    "in_progress",  # в процессе (оформление/проверка)
    "done",  # готов/принят
    "rejected",  # отклонён/не принят
    "na",  # не требуется
}


def is_valid_status(value: str) -> bool:
    return value in DOC_STATUSES


# Дефолтный набор документов (минимально универсальный для рекрутинга в ЕС)
# Можно смело редактировать/дополнять — API не меняется.
DEFAULT_DOCS: List[Dict[str, str]] = [
    {
        "key": "passport",
        "title": "Passport",
        "status": "pending",
    },
    {
        "key": "photo_3x4",
        "title": "Photo 3x4",
        "status": "pending",
    },
    {
        "key": "application_form",
        "title": "Application form",
        "status": "pending",
    },
    {
        "key": "consent_gdpr",
        "title": "GDPR consent",
        "status": "pending",
    },
    {
        "key": "work_permit",
        "title": "Work permit",
        "status": "pending",
    },
    {
        "key": "residence_card",
        "title": "Residence card",
        "status": "na",
    },
    {
        "key": "medical_certificate",
        "title": "Medical certificate",
        "status": "na",
    },
]


def default_docs_for(country_code: str | None = None) -> List[Dict[str, str]]:
    """
    На будущее: можно возвращать разные дефолтные списки под страну.
    Пока просто возвращаем общий DEFAULT_DOCS.
    """
    # пример кастомизации:
    # if country_code == "PL":
    #     return DEFAULT_DOCS + [{"key": "pesel", "title": "PESEL", "status": "pending"}]
    return [dict(x) for x in DEFAULT_DOCS]  # копия, чтобы не мутировать оригинал


__all__ = [
    "DOC_STATUSES",
    "is_valid_status",
    "DEFAULT_DOCS",
    "default_docs_for",
]
