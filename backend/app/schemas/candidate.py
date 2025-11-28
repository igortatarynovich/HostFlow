from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
import json

from pydantic import BaseModel, ConfigDict, Field


# Универсальный базовый класс: разрешаем любые дополнительные ключи
class _BaseModel(BaseModel):
    model_config = ConfigDict(
        extra="allow", from_attributes=True, populate_by_name=True
    )


# ----- входные модели -----


class CandidateCreate(_BaseModel):
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    phone_country_code: Optional[str] = None
    languages: List[str] = Field(default_factory=list)
    stage: Optional[str] = None
    status_reason: Optional[List[str]] = None
    manager: Optional[str] = None  # UUID как строка
    vacancy_id: Optional[str] = None  # UUID как строка
    company_id: Optional[str] = None  # UUID как строка (обычно вычисляется по вакансии)
    note: Optional[str] = None

    # КЛЮЧЕВОЕ: не типизируем жёстко, оставляем как словарь
    extra: Optional[Dict[str, Any]] = Field(default_factory=dict)
    docs_progress: Optional[Dict[str, Any]] = Field(default_factory=dict)


class CandidateUpdate(_BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    phone_country_code: Optional[str] = None
    languages: Optional[List[str]] = None
    stage: Optional[str] = None
    status_reason: Optional[List[str]] = None
    manager: Optional[str] = None
    vacancy_id: Optional[str] = None
    company_id: Optional[str] = None
    note: Optional[str] = None

    # ТАК ЖЕ СВОБОДНЫЕ dict'ы
    extra: Optional[Dict[str, Any]] = None
    docs_progress: Optional[Dict[str, Any]] = None


# ----- выходная модель -----


class CandidateOut(_BaseModel):
    id: str
    tenant_id: Optional[str] = None
    short_id: Optional[str] = None

    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    phone_country_code: Optional[str] = None
    languages: List[str] = Field(default_factory=list)
    stage: Optional[str] = None
    status_reason: List[str] = Field(default_factory=list)
    manager: Optional[str] = None
    vacancy_id: Optional[str] = None
    company_id: Optional[str] = None
    note: Optional[str] = None

    # КЛЮЧЕВОЕ: свободные словари
    extra: Dict[str, Any] = Field(default_factory=dict)
    docs_progress: Dict[str, Any] = Field(default_factory=dict)

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_model(cls, m: Any) -> "CandidateOut":
        """
        Берём значения напрямую из ORM-модели.
        НИЧЕГО не «сжимаем» и не «нормализуем» — отдаём как есть.
        """
        return cls(
            id=str(getattr(m, "id")),
            tenant_id=getattr(m, "tenant_id", None),
            short_id=getattr(m, "short_id", None),
            first_name=getattr(m, "first_name"),
            last_name=getattr(m, "last_name"),
            email=getattr(m, "email", None),
            phone=getattr(m, "phone", None),
            phone_country_code=getattr(m, "phone_country_code", None),
            languages=list(getattr(m, "languages", []) or []),
            stage=getattr(m, "stage", None),
            status_reason=_parse_status_reason(getattr(m, "status_reason", None)),
            manager=getattr(m, "manager", None),
            vacancy_id=getattr(m, "vacancy_id", None),
            company_id=getattr(m, "company_id", None),
            note=getattr(m, "note", None),
            extra=dict(getattr(m, "extra", {}) or {}),
            docs_progress=dict(getattr(m, "docs_progress", {}) or {}),
            created_at=getattr(m, "created_at", None),
            updated_at=getattr(m, "updated_at", None),
        )


def _parse_status_reason(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return []
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                return [str(v).strip() for v in parsed if str(v).strip()]
        except Exception:
            parts = [p.strip() for p in s.split(",")]
            return [p for p in parts if p]
    return []
