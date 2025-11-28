from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, require_roles
from backend.app.db.deps import get_db_with_tenant as get_db_with_tenant
from backend.app.models.candidate import Candidate

# backend/app/api/v1/candidate_profile.py




# --- Опциональные модули: импортируем целиком и проверяем атрибуты через hasattr ---
try:
    from backend.app.services import (  # type: ignore[import-not-found]
        doc_classify as _docclass,
    )
except Exception:
    _docclass = None  # type: ignore[assignment]

try:
    from backend.app.services import (  # type: ignore[import-not-found]
        extractors as _extractors,
    )
except Exception:
    _extractors = None  # type: ignore[assignment]

router = APIRouter(prefix="/candidate-profile", tags=["candidate-profile"])


# ====== безопасные обёртки над извлекателями ======
def _extract_passport_name(path: str) -> Optional[Dict[str, str]]:
    # сначала пробуем "умный" модуль, если есть
    if _docclass and hasattr(_docclass, "extract_passport_latin_name"):
        try:
            return _docclass.extract_passport_latin_name(path)  # type: ignore[attr-defined]
        except Exception:
            pass
    # затем — базовый модуль, если есть
    if _extractors and hasattr(_extractors, "extract_passport_latin_name"):
        try:
            return _extractors.extract_passport_latin_name(path)  # type: ignore[attr-defined]
        except Exception:
            pass
    return None


def _extract_birth_date(path: str) -> Optional[date]:
    if _docclass and hasattr(_docclass, "extract_birth_date"):
        try:
            return _docclass.extract_birth_date(path)  # type: ignore[attr-defined]
        except Exception:
            pass
    if _extractors and hasattr(_extractors, "extract_birth_date"):
        try:
            return _extractors.extract_birth_date(path)  # type: ignore[attr-defined]
        except Exception:
            pass
    return None


# ====== Pydantic ======
class ExperienceItem(BaseModel):
    company: Optional[str] = None
    position: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    description: Optional[str] = None


class LicenseItem(BaseModel):
    type: Optional[str] = None
    country: Optional[str] = None
    issued_date: Optional[date] = None
    expires_date: Optional[date] = None
    number: Optional[str] = None


class CandidateProfile(BaseModel):
    id: str
    tenant_id: str
    short_id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    stage: Optional[str] = None
    manager: Optional[str] = None
    note: Optional[str] = None

    first_name_lat: Optional[str] = None
    last_name_lat: Optional[str] = None
    birth_date: Optional[date] = None
    citizenship: Optional[str] = None

    address: Optional[str] = None
    languages: List[str] = Field(default_factory=list)

    experience: List[ExperienceItem] = Field(default_factory=list)
    licenses: List[LicenseItem] = Field(default_factory=list)

    available_from: Optional[date] = None
    interview_date: Optional[date] = None

    created_at: datetime
    updated_at: datetime


class CandidateProfilePatch(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    stage: Optional[str] = None
    manager: Optional[str] = None
    note: Optional[str] = None

    first_name_lat: Optional[str] = None
    last_name_lat: Optional[str] = None
    birth_date: Optional[date] = None
    citizenship: Optional[str] = None

    address: Optional[str] = None
    languages: Optional[List[str]] = None

    experience: Optional[List[ExperienceItem]] = None
    licenses: Optional[List[LicenseItem]] = None

    available_from: Optional[date] = None
    interview_date: Optional[date] = None


class QuestionnaireSchema(BaseModel):
    groups: Dict[str, Dict[str, Any]] = Field(
        default_factory=lambda: {
            "driver_basic": {
                "title": "Базовый скрининг водителя",
                "weight": 1.0,
                "questions": [
                    {"code": "exp_ce", "label": "Опыт C+E > 1 года", "points_yes": 2, "points_no": 0},
                    {"code": "card_tacho", "label": "Есть тахокарта", "points_yes": 1, "points_no": 0},
                    {"code": "code95", "label": "Есть код 95", "points_yes": 2, "points_no": 0},
                    {"code": "eu_permit", "label": "Есть разрешение на работу в ЕС", "points_yes": 2, "points_no": 0},
                ],
            },
            "soft": {
                "title": "Софт-факторы",
                "weight": 0.6,
                "questions": [
                    {"code": "punctual", "label": "Пунктуальность", "points_yes": 1, "points_no": 0},
                    {"code": "communication", "label": "Коммуникация", "points_yes": 1, "points_no": 0},
                ],
            },
        }
    )


class QuestionnaireAnswers(BaseModel):
    answers: Dict[str, str] = Field(default_factory=dict)
    score: float = 0.0


# ====== helpers ======
def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _now_naive() -> datetime:
    return _now_utc().replace(tzinfo=None)


def _safe_json_load(v) -> dict:
    if not v:
        return {}
    if isinstance(v, dict):
        return v
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return {}
    return {}


def _dump_extra_for_model(c: Candidate, extra: dict) -> None:
    c.extra = json.dumps(extra, ensure_ascii=False, default=str)


def _iso_to_date(v) -> Optional[date]:
    if not v:
        return None
    try:
        return date.fromisoformat(str(v)[:10])
    except Exception:
        return None


def _normalize_dates_list(items: List[dict], mappings: Dict[str, str]) -> List[dict]:
    out: List[dict] = []
    for d in items or []:
        if not isinstance(d, dict):
            continue
        nd = dict(d)
        for k in mappings.keys():
            if nd.get(k) is not None:
                nd[k] = str(nd[k])
        out.append(nd)
    return out


def _get_profile(extra: dict) -> dict:
    prof = extra.get("profile")
    if not isinstance(prof, dict):
        prof = {}
        extra["profile"] = prof
    prof.setdefault("languages", [])
    prof.setdefault("experience", [])
    prof.setdefault("licenses", [])
    return prof


def _get_questionnaire(extra: dict) -> dict:
    q = extra.get("questionnaire")
    if not isinstance(q, dict):
        q = {"answers": {}, "score": 0.0}
        extra["questionnaire"] = q
    q.setdefault("answers", {})
    q.setdefault("score", 0.0)
    return q


def _calc_score(schema: QuestionnaireSchema, answers: Dict[str, str]) -> float:
    score = 0.0
    for g in schema.groups.values():
        w = float(g.get("weight") or 1.0)
        for q in g.get("questions", []):
            code = q.get("code")
            if not code:
                continue
            val = (answers.get(code) or "unknown").lower()
            if val == "yes":
                score += w * float(q.get("points_yes") or 0)
            elif val == "no":
                score += w * float(q.get("points_no") or 0)
    return score


def _candidate_to_profile(c: Candidate, extra: dict) -> CandidateProfile:
    prof = _get_profile(extra)

    return CandidateProfile(
        id=c.id,
        tenant_id=c.tenant_id,
        short_id=c.short_id,
        first_name=c.first_name,
        last_name=c.last_name,
        email=c.email,
        phone=c.phone,
        stage=c.stage,
        manager=c.manager,
        note=c.note,
        first_name_lat=prof.get("first_name_lat"),
        last_name_lat=prof.get("last_name_lat"),
        birth_date=_iso_to_date(prof.get("birth_date")),
        citizenship=prof.get("citizenship"),
        address=prof.get("address"),
        languages=list(prof.get("languages") or []),
        experience=[
            ExperienceItem(
                company=raw.get("company"),
                position=raw.get("position"),
                start_date=_iso_to_date(raw.get("start_date")),
                end_date=_iso_to_date(raw.get("end_date")),
                description=raw.get("description"),
            )
            for raw in (prof.get("experience") or []) if isinstance(raw, dict)
        ],
        licenses=[
            LicenseItem(
                type=raw.get("type"),
                country=raw.get("country"),
                issued_date=_iso_to_date(raw.get("issued_date")),
                expires_date=_iso_to_date(raw.get("expires_date")),
                number=raw.get("number"),
            )
            for raw in (prof.get("licenses") or []) if isinstance(raw, dict)
        ],
        available_from=_iso_to_date(prof.get("available_from")),
        interview_date=_iso_to_date(prof.get("interview_date")),
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


async def _get_candidate(db: AsyncSession, tenant_id: UUID, candidate_id: UUID) -> Candidate:
    row = await db.execute(
        select(Candidate).where(
            Candidate.id == str(candidate_id),
            Candidate.tenant_id == str(tenant_id),
            Candidate.deleted_at.is_(None),
        )
    )
    c = row.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return c


# ====== endpoints ======
@router.get("/{candidate_id}", response_model=CandidateProfile)
async def get_profile(
    candidate_id: UUID,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
):
    db, tenant_id = db_tenant
    c = await _get_candidate(db, tenant_id, candidate_id)
    return _candidate_to_profile(c, _safe_json_load(c.extra))


@router.patch(
    "/{candidate_id}",
    response_model=CandidateProfile,
    dependencies=[Depends(require_roles(Role.manager, Role.admin))],
)
async def patch_profile(
    candidate_id: UUID,
    payload: CandidateProfilePatch,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
):
    db, tenant_id = db_tenant
    c = await _get_candidate(db, tenant_id, candidate_id)
    extra = _safe_json_load(c.extra)
    prof = _get_profile(extra)

    base_updates: Dict[str, Any] = {}
    for f in ["first_name", "last_name", "email", "phone", "stage", "manager", "note"]:
        val = getattr(payload, f)
        if val is not None:
            base_updates[f] = val
    if base_updates:
        await db.execute(
            update(Candidate)
            .where(Candidate.id == str(candidate_id), Candidate.tenant_id == str(tenant_id))
            .values(**base_updates, updated_at=_now_naive())
        )

    for f in ["first_name_lat", "last_name_lat", "citizenship", "address"]:
        val = getattr(payload, f)
        if val is not None:
            prof[f] = val

    for f in ["birth_date", "available_from", "interview_date"]:
        val = getattr(payload, f)
        if val is not None:
            prof[f] = str(val)

    if payload.languages is not None:
        prof["languages"] = list(payload.languages or [])

    if payload.experience is not None:
        prof["experience"] = _normalize_dates_list(
            [x.dict() for x in (payload.experience or [])],
            {"start_date": "date", "end_date": "date"},
        )

    if payload.licenses is not None:
        prof["licenses"] = _normalize_dates_list(
            [x.dict() for x in (payload.licenses or [])],
            {"issued_date": "date", "expires_date": "date"},
        )

    _dump_extra_for_model(c, extra)

    await db.execute(
        update(Candidate)
        .where(Candidate.id == str(candidate_id), Candidate.tenant_id == str(tenant_id))
        .values(extra=c.extra, updated_at=_now_naive())
    )

    await db.commit()
    await db.refresh(c)
    return _candidate_to_profile(c, _safe_json_load(c.extra))


@router.get("/{candidate_id}/questionnaire", response_model=QuestionnaireAnswers)
async def get_questionnaire(
    candidate_id: UUID,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
):
    db, tenant_id = db_tenant
    c = await _get_candidate(db, tenant_id, candidate_id)
    q = _get_questionnaire(_safe_json_load(c.extra))
    return QuestionnaireAnswers(answers=q.get("answers") or {}, score=float(q.get("score") or 0.0))


@router.patch(
    "/{candidate_id}/questionnaire",
    response_model=QuestionnaireAnswers,
    dependencies=[Depends(require_roles(Role.manager, Role.admin))],
)
async def patch_questionnaire(
    candidate_id: UUID,
    payload: QuestionnaireAnswers,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
):
    db, tenant_id = db_tenant
    c = await _get_candidate(db, tenant_id, candidate_id)
    extra = _safe_json_load(c.extra)
    q = _get_questionnaire(extra)

    q["answers"] = dict(payload.answers or {})
    schema = QuestionnaireSchema()
    q["score"] = _calc_score(schema, q["answers"])

    _dump_extra_for_model(c, extra)

    await db.execute(
        update(Candidate)
        .where(Candidate.id == str(candidate_id), Candidate.tenant_id == str(tenant_id))
        .values(extra=c.extra, updated_at=_now_naive())
    )

    await db.commit()
    await db.refresh(c)
    return QuestionnaireAnswers(answers=q["answers"], score=float(q["score"]))


@router.post(
    "/{candidate_id}/autofill-from-docs",
    response_model=CandidateProfile,
    dependencies=[Depends(require_roles(Role.manager, Role.admin))],
)
async def autofill_from_docs(
    candidate_id: UUID,
    prefer_doc_key: str = Query("passport"),
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
):
    db, tenant_id = db_tenant
    c = await _get_candidate(db, tenant_id, candidate_id)
    extra = _safe_json_load(c.extra)
    prof = _get_profile(extra)

    # документы: строго фильтруем типы, чтобы Pylance знал, что мы работаем с dict
    raw_docs = _safe_json_load(c.extra).get("documents")
    docs_list: List[Any] = raw_docs if isinstance(raw_docs, list) else []

    files: List[Dict[str, Any]] = []
    for d in docs_list:
        if isinstance(d, dict) and d.get("key") == prefer_doc_key:
            fs = d.get("files") or []
            files.extend([x for x in fs if isinstance(x, dict)])

    if not files:
        for d in docs_list:
            if isinstance(d, dict):
                fs = d.get("files") or []
                files.extend([x for x in fs if isinstance(x, dict)])

    picked: Optional[Dict[str, Any]] = None
    for f in files:
        p = f.get("path")
        if isinstance(p, str) and p:
            picked = f
            break

    if picked is not None:
        path_val = picked.get("path")
        if isinstance(path_val, str) and path_val:
            # имя/фамилия латиницей
            _name_data = _extract_passport_name(path_val)
            name_data: Dict[str, str] = _name_data if isinstance(_name_data, dict) else {}
            first_lat = name_data.get("first_name_lat")
            last_lat = name_data.get("last_name_lat")
            if isinstance(first_lat, str) and first_lat:
                prof["first_name_lat"] = first_lat
            if isinstance(last_lat, str) and last_lat:
                prof["last_name_lat"] = last_lat

            # дата рождения
            bday = _extract_birth_date(path_val)
            if isinstance(bday, date) and not prof.get("birth_date"):
                prof["birth_date"] = str(bday)  # ISO

    _dump_extra_for_model(c, extra)

    await db.execute(
        update(Candidate)
        .where(Candidate.id == str(candidate_id), Candidate.tenant_id == str(tenant_id))
        .values(extra=c.extra, updated_at=_now_naive())
    )

    await db.commit()
    await db.refresh(c)
    return _candidate_to_profile(c, _safe_json_load(c.extra))
