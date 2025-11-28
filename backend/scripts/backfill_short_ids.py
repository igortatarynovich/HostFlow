from __future__ import annotations

import os
import random
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.models.candidate import Candidate  # type: ignore

# backend/scripts/backfill_short_ids.py


# --- корректируем PYTHONPATH так, чтобы можно было импортировать app.* ---
THIS = Path(__file__).resolve()
BACKEND_DIR = THIS.parents[1]  # .../backend
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# 1) пробуем взять URL из ваших настроек, если есть
DB_URL = None
try:
    # популярные варианты расположения настроек
    from backend.app.core.config import settings  # type: ignore

    DB_URL = getattr(settings, "SQLALCHEMY_DATABASE_URI", None) or getattr(
        settings, "DATABASE_URL", None
    )
except Exception:
    pass

# 2) если не нашли — пробуем env
if not DB_URL:
    DB_URL = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI")

if not DB_URL:
    raise RuntimeError(
        "Не найден URL БД. Укажите его в app.core.config.settings или в переменной окружения DATABASE_URL."
    )

engine = create_engine(DB_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# --- импорты доменной модели и генератора short_id ---

# Если вы уже добавили app/core/ids.py — используем его.
# Если нет — используем локальный генератор.
try:
    from backend.app.core.ids import make_short_id  # type: ignore
except Exception:
    def make_short_id(n: int = 6) -> str:
        alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # без 0/O/1/I
        return "".join(random.choice(alphabet) for _ in range(n))


def ensure_short_id(db: Session, cand: Candidate, attempts: int = 6) -> bool:
    """Присвоить short_id, если пустой. Возвращает True, если был изменён."""
    if getattr(cand, "short_id", None):
        return False
    for _ in range(attempts):
        sid = make_short_id()
        exists = (
            db.query(Candidate)
            .filter(Candidate.short_id == sid)  # type: ignore[attr-defined]
            .first()
            is not None
        )
        if not exists:
            cand.short_id = sid  # type: ignore[attr-defined]
            return True
    return False


def backfill_short_ids(batch_size: int = 500) -> None:
    db: Session = SessionLocal()
    updated = 0
    try:
        q = db.query(Candidate).filter(
            (Candidate.short_id.is_(None)) | (Candidate.short_id == "")  # type: ignore[attr-defined]
        )

        # обходим партиями (чтобы не грузить всю таблицу в память)
        offset = 0
        while True:
            chunk = q.order_by(Candidate.id).offset(offset).limit(batch_size).all()  # type: ignore[attr-defined]
            if not chunk:
                break
            for c in chunk:
                if ensure_short_id(db, c):
                    updated += 1
            db.commit()
            offset += batch_size

        print(f"✅ Готово: обновлено кандидатов: {updated}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    backfill_short_ids()
