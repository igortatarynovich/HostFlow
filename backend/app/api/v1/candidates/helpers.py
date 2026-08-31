from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, or_
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.constants.catalogs import DIAL_CODES
from fastapi import HTTPException

from backend.app.constants.stages_adapter import STAGES
from backend.app.constants.stages import LABELS
from backend.app.models import Candidate
from backend.app.models.candidate import next_candidate_short_id
from backend.app.models.document import Document


def _utc_naive() -> datetime:
    # наивное (без tzinfo) UTC-время, совместимо с TIMESTAMP WITHOUT TIME ZONE
    return datetime.utcnow().replace(tzinfo=None)

# ---------- stages helpers ----------

def _iter_stages():
    """Yield pairs (code, meta) from STAGES for both dict and list shapes."""
    try:
        if isinstance(STAGES, dict):
            for code, meta in STAGES.items():
                yield str(code), meta
            return
        for item in STAGES:  # type: ignore[assignment]
            if isinstance(item, dict):
                code = str(item.get("code") or "").strip()
                if code:
                    yield code, item
    except Exception:
        return

def is_stage_code(value: str) -> bool:
    if not value:
        return False
    v = value.strip()
    for code, _ in _iter_stages():
        if code == v:
            return True
    return False

def code_for_label(label: str) -> Optional[str]:
    if not label:
        return None
    norm_label = label.strip().casefold()
    for code, meta in _iter_stages():
        name = str((meta or {}).get("label", "")).strip().casefold()
        if name == norm_label:
            return code
    return None

_STAGE_CODE_ALIASES = {
    "planning_arrival": "trip_plan",
    "plan_arrival": "trip_plan",
    "planning-trip": "trip_plan",
}

def _normalize_stage_to_code(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    v = value.strip()
    v_lower = v.lower()
    alias = _STAGE_CODE_ALIASES.get(v_lower)
    if alias:
        return alias
    if is_stage_code(v_lower):
        return v_lower
    return code_for_label(v) or code_for_label(v_lower) or None


def _validate_stage_transition(
    current: Optional[str],
    target: str,
    *,
    allow_revert: bool = True,
    max_skip: int = 1,
) -> None:
    """
    Validate stage code but DO NOT restrict transition order.

    Исторически функция ограничивала переходы по пайплайну (нельзя было
    «перепрыгивать» через несколько этапов). По факту это мешает работе
    в нестандартных ситуациях, когда рекрутеру или клиенту нужно
    вручную проставить любой этап в любой момент.

    Текущая политика:
    - Запрещаем только пустой код стадии.
    - Известность кода проверяет ``resolve_writable_stage_code`` (глобальный
      каталог **или** ``funnel_stages`` тенанта).
    - Любые переходы между валидными стадиями разрешены (вперёд, назад,
      через сколько угодно шагов).
    """
    if not target:
        raise HTTPException(status_code=422, detail="Stage must not be empty")


async def resolve_writable_stage_code(
    db: AsyncSession,
    *,
    tenant_id: str,
    raw: str,
) -> str:
    """Accept a global pipeline code **or** a tenant funnel stage code.

    Candidate PATCH used to 422 any funnel-local code (e.g. a custom
    ``skontaktowac__sie_pozniej`` row) because ``_normalize_stage_to_code``
    only knows ``constants/stages.py``.
    """
    text = str(raw or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="Stage must not be empty")
    normalized = _normalize_stage_to_code(text)
    if normalized:
        return normalized

    from backend.app.models.funnel import Funnel, FunnelStage

    found = (
        await db.execute(
            select(FunnelStage.id)
            .join(Funnel, Funnel.id == FunnelStage.funnel_id)
            .where(
                Funnel.tenant_id == str(tenant_id),
                FunnelStage.code == text,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if found is None:
        raise HTTPException(status_code=422, detail=f"Unknown stage '{text}'")
    return text

def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        s_ = s.strip()
        if len(s_) == 10:
            return datetime.fromisoformat(s_ + "T00:00:00")
        return datetime.fromisoformat(s_)
    except Exception:
        return None

async def _generate_unique_short_id(db: AsyncSession, attempts: int = 10) -> str:
    """
    Generate the next sequential candidate short_id (CND000001…).

    Uses the same logic as the model before_insert hook to keep a single numbering
    scheme regardless of creation source (manual, webhook, etc.).
    """
    _ = attempts  # unused, kept for backward compatibility
    # Use session.run_sync and pass a real connection into next_candidate_short_id.
    # Passing the session itself leads to AttributeError: 'Session' object has no attribute 'dialect'.
    def _inner(session):
        conn = session.connection()
        return next_candidate_short_id(conn)

    return await db.run_sync(_inner)

async def _ensure_short_id(db: AsyncSession, cand: Candidate) -> None:
    if getattr(cand, "short_id", None):
        return
    cand.short_id = await _generate_unique_short_id(db)

# ---------- json & phone helpers ----------

def _merge_dict(a: Optional[dict], b: Optional[dict]) -> dict:
    return {**(a or {}), **(b or {})}

def _ensure_langs(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str):
        s = value.strip()
        return [p.strip() for p in s.split(",") if p.strip()] if s else []
    return []

def _dump_json_str(d: Optional[Dict[str, Any]]) -> str:
    """Готовим строку для колонок VARCHAR: '{}' и ensure_ascii=False."""
    return json.dumps(d or {}, ensure_ascii=False, separators=(",", ":"))

def _as_dict_safe(v: Any) -> Dict[str, Any]:
    """Надёжно приводим значение из БД к dict (поддержка legacy-строк)."""
    if v is None:
        return {}
    if isinstance(v, dict):
        return v
    if isinstance(v, str):
        try:
            j = json.loads(v)
            return j if isinstance(j, dict) else {}
        except Exception:
            return {}
    return {}

def _dial_code_for_country(cc: str) -> str:
    """Возвращает "+XXX" по ISO-коду страны. Поддерживает DIAL_CODES как dict или список словарей.
    Гарантирует префикс '+', даже если источник хранит число без '+'.
    """
    if not cc:
        return ""
    cc = cc.strip().upper()
    raw = ""
    if isinstance(DIAL_CODES, dict):
        raw = str(DIAL_CODES.get(cc) or "").strip()
    else:
        try:
            for x in DIAL_CODES:  # type: ignore[assignment]
                if isinstance(x, dict) and (str(x.get("country") or "").upper() == cc):
                    raw = str(x.get("dial_code") or "").strip()
                    break
        except Exception:
            raw = ""
    if not raw:
        return ""
    # Нормализуем: добавляем '+' если его нет
    return raw if raw.startswith("+") else f"+{raw}"


def normalize_phone_country_code(value: Optional[str]) -> Optional[str]:
    """Нормализует телефонный префикс: '+49' из '49', '+49', ' 49 ', '' -> None."""
    if not value:
        return None
    v = str(value).strip()
    if not v:
        return None
    return v if v.startswith("+") else f"+{v}"

def _build_phone_display(extra: Dict[str, Any], phone_raw: Optional[str], phone_country_code: Optional[str] = None) -> Optional[str]:
    """Строит удобочитаемый телефон из кода страны/префикса и номера.
    Источники префикса (по приоритету):
      1) явный аргумент `phone_country_code`
      2) extra['phone_country_code'] или extra['phone_prefix']
      3) DIAL_CODES по extra['phone_country']
    Всегда приводит префикс к виду '+NNN'.
    """
    prefix = normalize_phone_country_code(phone_country_code)

    if not prefix and isinstance(extra, dict):
        # попробуем найти в extra
        prefix = normalize_phone_country_code(extra.get("phone_country_code")) or \
                 normalize_phone_country_code(extra.get("phone_prefix"))
        if not prefix:
            country = (extra.get("phone_country") or "").strip().upper()
            if country:
                prefix = normalize_phone_country_code(_dial_code_for_country(country))

    number = (phone_raw or "").strip()
    if prefix and number:
        return f"{prefix} {number}"
    if number:
        return number
    if prefix:
        return prefix
    return None

# ---------- documents helper ----------

def _uploaded_condition():
    """SQLAlchemy condition that means a document has an uploaded file."""
    status_has_file = or_(
        Document.status == "pending_validation",
        Document.status == "verified",
    )
    conds = [status_has_file]
    conds.append(and_(Document.filename.isnot(None), func.length(Document.filename) > 0))
    file_url_col = getattr(Document, "file_url", None)
    if file_url_col is not None:
        conds.append(and_(file_url_col.isnot(None), func.length(file_url_col) > 0))
    path_col = getattr(Document, "path", None)
    if path_col is not None:
        conds.append(and_(path_col.isnot(None), func.length(path_col) > 0))
    size_col = getattr(Document, "file_size", None)
    if size_col is not None:
        try:
            conds.append(and_(size_col.isnot(None), size_col > 0))
        except Exception:
            pass
    json_keys = ["$.file_url", "$.filename", "$.path", "$.url", "$.storage_key", "$.s3_key", "$.key", "$.blob_path", "$.gcs_path", "$.name"]
    try:
        for jk in json_keys:
            col = func.json_extract(Document.extra, jk)
            conds.append(and_(col.isnot(None), func.length(col) > 0))
    except Exception:
        pass
    try:
        for needle in ['"file_url"', '"filename"', '"path"', '"url"', '"storage_key"', '"s3_key"', '"blob_path"']:
            conds.append(func.instr(Document.extra, needle) > 0)
    except Exception:
        pass
    return or_(*conds)

# ---------- documents counters utilities ----------

def _has_file_for_doc(d: Document) -> bool:
    # 1) статусы, которые означают, что файл есть
    if str(getattr(d, "status", "") or "").strip().lower() in {
        "pending_validation",
        "verified",
        "invalid",
        "expired",
    }:
        return True

    # 2) прямые колонки
    for attr in ("filename", "file_name", "stored_filename", "original_filename", "content_name"):
        val = (getattr(d, attr, None) or "")
        if isinstance(val, str) and val.strip():
            return True

    for attr in ("file_url", "url", "public_url"):
        if hasattr(d, attr):
            val = (getattr(d, attr, None) or "")
            if isinstance(val, str) and val.strip():
                return True

    for attr in ("path", "file_path", "stored_path", "blob_path", "gcs_path"):
        if hasattr(d, attr):
            val = (getattr(d, attr, None) or "")
            if isinstance(val, str) and val.strip():
                return True

    # размер
    size_val = getattr(d, "file_size", None)
    try:
        if size_val is not None:
            size_num = int(size_val) if not isinstance(size_val, (int, float)) else size_val
            if size_num and size_num > 0:
                return True
    except Exception:
        pass

    # 3) JSON/TEXT extra
    extra: dict = {}
    try:
        extra_raw = getattr(d, "extra", None)
        if isinstance(extra_raw, dict):
            extra = extra_raw
        elif isinstance(extra_raw, str):
            try:
                import json as _json
                extra = _json.loads(extra_raw)
            except Exception:
                extra = {}
    except Exception:
        extra = {}

    string_keys = [
        "file_url", "filename", "file_name", "original_filename",
        "stored_filename", "path", "file_path", "stored_path",
        "url", "public_url", "storage_key", "s3_key", "blob_path",
        "gcs_path", "key", "name", "mime", "content_type", "hash"
    ]
    for k in string_keys:
        v = extra.get(k)
        if isinstance(v, str) and v.strip():
            return True

    for k in ("size", "file_size", "bytes", "length", "pages", "uploaded"):
        v = extra.get(k)
        try:
            if isinstance(v, bool) and v:
                return True
            if isinstance(v, (int, float)) and v > 0:
                return True
            if isinstance(v, str) and v.strip().isdigit() and int(v) > 0:
                return True
        except Exception:
            pass

    try:
        extra_text = (getattr(d, "extra", "") or "")
        if any(s in extra_text for s in (
            '"file_url"', '"filename"', '"file_name"', '"original_filename"',
            '"stored_filename"', '"url"', '"public_url"', '"storage_key"',
            '"s3_key"', '"blob_path"', '"gcs_path"', '"file_path"', '"stored_path"'
        )):
            return True
    except Exception:
        pass

    return False


async def compute_docs_counters(db: AsyncSession, candidate_ids: list[str]) -> dict[str, dict[str, int]]:
    if not candidate_ids:
        return {}
    docs_rows = await db.execute(
        select(Document).where(
            and_(
                Document.candidate_id.in_(candidate_ids),
                Document.deleted_at.is_(None),
            )
        )
    )
    by_cid: dict[str, list[Document]] = {}
    for d in docs_rows.scalars().all():
        cid = str(getattr(d, "candidate_id", "") or "")
        by_cid.setdefault(cid, []).append(d)

    result: dict[str, dict[str, int]] = {}
    for cid, docs in by_cid.items():
        total_i = len(docs)
        ready_i = sum(1 for d in docs if str(getattr(d, "status", "") or "").lower() == "verified")
        submitted_i = sum(1 for d in docs if str(getattr(d, "status", "") or "").lower() == "pending_validation")
        planned_i = sum(1 for d in docs if str(getattr(d, "status", "") or "").lower() == "planned")
        uploaded_i = sum(1 for d in docs if _has_file_for_doc(d))
        completed_i = max(uploaded_i, ready_i)
        result[cid] = {
            "total": total_i,
            "ready": ready_i,
            "submitted": submitted_i,
            "planned": planned_i,
            "uploaded": uploaded_i,
            "completed": completed_i,
        }
    return result


async def compute_docs_summary_for_candidate(db: AsyncSession, candidate_id: str) -> dict[str, int]:
    docs_rows = await db.execute(
        select(Document).where(
            and_(
                Document.candidate_id == candidate_id,
                Document.deleted_at.is_(None),
            )
        )
    )
    docs_list = docs_rows.scalars().all()
    total_i = len(docs_list)
    ready_i = sum(1 for d in docs_list if str(getattr(d, "status", "") or "").lower() == "verified")
    submitted_i = sum(1 for d in docs_list if str(getattr(d, "status", "") or "").lower() == "pending_validation")
    planned_i = sum(1 for d in docs_list if str(getattr(d, "status", "") or "").lower() == "planned")
    uploaded_i = sum(1 for d in docs_list if _has_file_for_doc(d))
    completed_i = max(uploaded_i, ready_i)
    return {
        "total": total_i,
        "ready": ready_i,
        "submitted": submitted_i,
        "planned": planned_i,
        "uploaded": uploaded_i,
        "completed": completed_i,
        # aliases for UI
        "completed_count": completed_i,
        "uploaded_count": uploaded_i,
        "ready_count": ready_i,
        "have": completed_i,
        "done": completed_i,
        "files": completed_i,
        "total_count": total_i,
    }


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _non_empty_str(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None


def resolve_preferred_contact_from_storage(
    extra: Any,
    contacts: Any = None,
) -> Optional[str]:
    """Resolve preferred contact channel from legacy and profile-contract storage paths."""
    extra_data = _as_dict(extra)
    contacts_data = _as_dict(contacts)
    nested_contacts = _as_dict(extra_data.get("contacts"))
    for source in (
        extra_data.get("preferred_contact"),
        contacts_data.get("preferred_messenger"),
        nested_contacts.get("preferred_messenger"),
    ):
        resolved = _non_empty_str(source)
        if resolved:
            return resolved
    return None


def resolve_poland_stay_basis_from_storage(
    extra: Any,
    personal_data: Any = None,
) -> Optional[str]:
    """Resolve Poland stay basis from legacy and profile-contract storage paths."""
    extra_data = _as_dict(extra)
    personal = _as_dict(personal_data)
    nested_personal = _as_dict(extra_data.get("personal_data"))
    nested_profile_personal = _as_dict(extra_data.get("personal"))
    for source in (
        extra_data.get("poland_stay_basis"),
        extra_data.get("poland_stay_basis_raw"),
        personal.get("residency_status"),
        nested_personal.get("residency_status"),
        nested_profile_personal.get("residency_status"),
    ):
        resolved = _non_empty_str(source)
        if resolved:
            return resolved
    return None
