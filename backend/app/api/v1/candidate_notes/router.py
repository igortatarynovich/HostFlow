from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
import uuid
from datetime import datetime

# Предполагаемые общие зависимости/типы проекта
try:
    from app.auth.deps import get_current_user, require_roles
except Exception:  # pragma: no cover
    from ..deps import get_current_user, require_roles  # type: ignore

try:
    from app.constants.roles import Role
except Exception:  # pragma: no cover
    from app.models.roles import Role  # type: ignore

# DB accessor (dynamic import to satisfy linters and runtime)
from typing import Any
import importlib

_db_mod: Any = None
for _mod in ("app.db", "app.core.db"):
    try:
        _db_mod = importlib.import_module(_mod)
        break
    except Exception:  # pragma: no cover
        continue

if _db_mod is None:
    db: Any = None  # type: ignore
else:
    db = getattr(_db_mod, "db", getattr(_db_mod, "database", None))  # type: ignore

router = APIRouter(prefix="/api/v1/candidates", tags=["candidate-notes"])

# Роли, которым разрешена работа с заметками
ALLOW_NOTES_ROLES = (
    getattr(Role, "manager", "MANAGER"),
    getattr(Role, "admin", "ADMIN"),
    getattr(Role, "recruiter", "RECRUITER"),
    getattr(Role, "administrator", "ADMINISTRATOR"),
)

async def _get_db(request: Request):
    dbi = getattr(getattr(request.app, 'state', None), 'db', None)
    if dbi is not None:
        return dbi
    if db is not None:
        return db
    raise HTTPException(status_code=500, detail="DB connection is not initialized")

def _to_iso(dt) -> str:
    if isinstance(dt, str):
        return dt
    if isinstance(dt, datetime):
        # нормализуем до секунд и добавляем Z
        return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z") + ("" if str(dt.tzinfo or "").endswith("UTC") else "")
    return str(dt)

def _map_note_row(row) -> dict:
    return {
        "id": str(row["id"]) if isinstance(row, (dict,)) else str(row.id),
        "text": row["text"] if isinstance(row, (dict,)) else row.text,
        "visibility": row["visibility"] if isinstance(row, (dict,)) else row.visibility,
        "author_id": str(row["author_id"]) if isinstance(row, (dict,)) else str(row.author_id),
        "created_at": _to_iso(row["created_at"] if isinstance(row, (dict,)) else row.created_at),
    }


class NoteIn(BaseModel):
    text: str = Field(min_length=1)
    visibility: str = Field(default="internal", pattern="^(internal|client|candidate)$")


class NoteOut(BaseModel):
    id: str
    text: str
    visibility: str
    author_id: str
    created_at: str


@router.get("/{candidate_id}/notes", response_model=List[NoteOut])
async def list_candidate_notes(candidate_id: str, request: Request, user=Depends(get_current_user), _=Depends(require_roles(*ALLOW_NOTES_ROLES))):
    dbi = await _get_db(request)
    rows = await dbi.fetch_all(
        """
        SELECT id, text, visibility, author_id, created_at
        FROM candidate_notes
        WHERE candidate_id = :cid AND tenant_id = :tid
        ORDER BY created_at DESC
        """,
        {"cid": candidate_id, "tid": user.tenant_id},
    )
    return [_map_note_row(r) for r in rows]


@router.post("/{candidate_id}/notes", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
async def add_candidate_note(candidate_id: str, payload: NoteIn, request: Request, user=Depends(get_current_user), _=Depends(require_roles(*ALLOW_NOTES_ROLES))):
    dbi = await _get_db(request)
    note_id = str(uuid.uuid4())

    # автор — из контекста: поддерживаем id / user_id / sub
    author_id = getattr(user, "id", None) or getattr(user, "user_id", None) or getattr(user, "sub", None)
    if not author_id:
        raise HTTPException(status_code=500, detail="candidate_notes.add failed: user id is missing in context")

    # вставка (без RETURNING — совместимо с SQLite)
    await dbi.execute(
        """
        INSERT INTO candidate_notes (id, tenant_id, candidate_id, author_id, text, visibility)
        VALUES (:id, :tid, :cid, :uid, :text, :vis)
        """,
        {"id": note_id, "tid": user.tenant_id, "cid": candidate_id, "uid": author_id, "text": payload.text, "vis": payload.visibility},
    )
    # выборка свежей записи
    row = await dbi.fetch_one(
        """
        SELECT id, text, visibility, author_id, created_at
        FROM candidate_notes
        WHERE id = :id AND tenant_id = :tid
        """,
        {"id": note_id, "tid": user.tenant_id},
    )
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create note")
    return _map_note_row(row)