from __future__ import annotations

from backend.app.constants.stages_adapter import DEFAULT_STAGE_CODE
from fastapi import APIRouter

# Основные константы стадий. Если модуль отсутствует или в нём иные имена —
# ниже есть безопасные дефолты, чтобы приложение поднималось без падения.
try:  # pragma: no cover - защитный импорт
    from backend.app.constants.stages import (  # type: ignore
        KANBAN_COLUMN_OF as KANBAN_COLUMN_OF_CONST,
        LABELS as LABELS_CONST,
        ORDER as ORDER_CONST,
        STAGES_BY_GROUP as STAGES_BY_GROUP_CONST,
        STATUS_REASON_CHOICES as STATUS_REASON_CHOICES_CONST,
    )
except Exception:  # pragma: no cover
    STAGES_BY_GROUP: dict[str, list[str]] = {}
    LABELS: dict[str, str] = {}
    KANBAN_COLUMN_OF: dict[str, str] = {}
    ORDER: list[str] = []
    STATUS_REASON_CHOICES: dict[str, list[dict[str, str]]] = {}

# Assign imported constants to expected names if they exist
if 'STAGES_BY_GROUP_CONST' in locals():
    STAGES_BY_GROUP = STAGES_BY_GROUP_CONST
    LABELS = LABELS_CONST
    KANBAN_COLUMN_OF = KANBAN_COLUMN_OF_CONST
    ORDER = ORDER_CONST
    STATUS_REASON_CHOICES = STATUS_REASON_CHOICES_CONST

# Каталоги для форм (безопасный импорт с дефолтами)
from typing import Any, Union

CatalogType = Union[list[dict[str, Any]], list[str], dict[str, Any]]

try:  # pragma: no cover - защитный импорт
    from backend.app.constants import catalogs as CATALOGS  # type: ignore
except Exception:  # pragma: no cover
    CATALOGS = None  # type: ignore

COUNTRIES: CatalogType = getattr(CATALOGS, "COUNTRIES", [])
LANGUAGES: CatalogType = getattr(CATALOGS, "LANGUAGES", [])
DIAL_CODES: CatalogType = getattr(CATALOGS, "DIAL_CODES", [])
MANAGERS: CatalogType = getattr(CATALOGS, "MANAGERS", [])


router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/stages")
async def stages_meta():
    """
    Справочник стадий:
    - default: код стадии по умолчанию
    - codes: список всех кодов в порядке групп
    - labels: код -> метка
    - groups: группа-канбан -> список кодов
    - column_of: код -> колонка канбана
    - order: явный порядок кодов
    """
    codes: list[str] = []
    for _, codes_in_group in STAGES_BY_GROUP.items():
        codes.extend(codes_in_group)

    # На случай если групп нет, но есть явный ORDER — вернём его как codes
    if not codes and ORDER:
        codes = list(ORDER)

    return {
        "default": DEFAULT_STAGE_CODE,
        "codes": codes,
        "labels": LABELS,
        "groups": STAGES_BY_GROUP,
        "column_of": KANBAN_COLUMN_OF,
        "order": ORDER,
        "reason_choices": STATUS_REASON_CHOICES,
    }

# --- Catalogs API ---
catalogs_router = APIRouter(prefix="/catalogs", tags=["catalogs"])


@catalogs_router.get("/countries")
async def get_countries():
    return COUNTRIES


@catalogs_router.get("/languages")
async def get_languages():
    return LANGUAGES


@catalogs_router.get("/dial-codes")
async def get_dial_codes():
    return DIAL_CODES


@catalogs_router.get("/managers")
async def get_managers():
    return MANAGERS
