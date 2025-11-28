from __future__ import annotations

import re
from collections import OrderedDict
from fastapi import APIRouter, Query

router = APIRouter()

# Базовый список стадий (код -> лейбл). Порядок важен для фронта.
STAGES: "OrderedDict[str, str]" = OrderedDict(
    [
        ("new", "New Lead"),
        ("contacted", "Contacted"),
        ("interview", "Interview"),
        ("offer", "Offer"),
        ("hired", "Hired"),
        ("rejected", "Rejected"),
    ]
)

# Синонимы для нормализации (слепляем строку, убираем не-буквы)
ALIASES: dict[str, str] = {
    "newlead": "new",
    "new": "new",
    "lead": "new",
    "contact": "contacted",
    "contacted": "contacted",
    "interview": "interview",
    "offer": "offer",
    "hired": "hired",
    "reject": "rejected",
    "rejected": "rejected",
}

DEFAULT_STAGE = "new"


def _canon(s: str) -> str:
    """переводит произвольный ввод в канонический ключ: только буквы, нижний регистр"""
    return re.sub(r"[^a-z]+", "", (s or "").strip().lower())


@router.get("/stages")
async def list_stages():
    """Полный список стадий в нужном порядке."""
    return [{"code": code, "label": label} for code, label in STAGES.items()]


@router.get("/stages/normalize")
async def normalize_stage(value: str = Query("", description="Любая строка со стадией")):
    """
    Нормализует значение кода стадии. Понимает синонимы и регистр.
    Возвращает и code, и label (никогда не null).
    """
    key = _canon(value)
    code = (
        key
        if key in STAGES
        else ALIASES.get(key, DEFAULT_STAGE)
    )
    return {"code": code, "label": STAGES[code]}