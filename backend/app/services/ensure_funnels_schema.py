"""Ensure dev/test SQLite has funnels and funnel_stages tables."""

from __future__ import annotations

import os
import sqlite3
import uuid
from contextlib import closing


def _db_path() -> str:
    return os.environ.get("DEV_DB_PATH") or os.path.join(os.getcwd(), "app.db")


def _table_exists(cur: sqlite3.Cursor, name: str) -> bool:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None


def _column_exists(cur: sqlite3.Cursor, table: str, column: str) -> bool:
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


DEFAULT_STAGES = [
    ("new", "Новый", 0),
    ("no_answer", "Не отвечает", 1),
    ("contacted", "Контакт установлен", 2),
    ("questionnaire_submitted", "Анкета заполнена", 3),
    ("docs_wait", "Ожидаем документы", 4),
    ("docs_got", "Документы получены", 5),
    ("permit_ordered", "Заказ разрешения на работу", 6),
    ("permit_received", "Разрешение на работу получено", 7),
    ("visa", "Виза", 8),
    ("red_paper", "Красная бумага заказана", 9),
    ("trip_plan", "Планируем приезд", 10),
    ("at_client", "На базе клиента", 11),
    ("on_trip", "Выехал в рейс", 12),
    ("probation_ok", "Прошёл пробный период", 13),
    ("employment_pending", "На трудоустройстве", 14),
    ("employed", "Трудоустроен", 15),
    ("rejected", "Отклонён", 16),
    ("declined", "Отказался", 17),
    ("ready_for_handoff", "Готов к передаче", 18),
    ("processing_by_client", "Обработка заказчиком", 19),
    ("docs_submitted_permit", "Документы поданы на разрешение", 20),
    ("handoff_returned", "Возвращён", 21),
]
TERMINAL_CODES = {"probation_ok", "rejected", "declined"}


def ensure_funnels_schema() -> None:
    """Ensure funnels and funnel_stages tables exist for SQLite dev."""
    path = _db_path()
    if not os.path.exists(path):
        return

    with closing(sqlite3.connect(path)) as conn:
        cur = conn.cursor()

        if not _table_exists(cur, "funnels"):
            cur.execute(
                """
                CREATE TABLE funnels (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    is_default INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS ix_funnels_tenant_id ON funnels(tenant_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS ix_funnels_type ON funnels(type)")

        if not _table_exists(cur, "funnel_stages"):
            cur.execute(
                """
                CREATE TABLE funnel_stages (
                    id TEXT PRIMARY KEY,
                    funnel_id TEXT NOT NULL REFERENCES funnels(id) ON DELETE CASCADE,
                    code TEXT NOT NULL,
                    label TEXT NOT NULL,
                    "order" INTEGER NOT NULL DEFAULT 0,
                    is_terminal INTEGER NOT NULL DEFAULT 0,
                    UNIQUE(funnel_id, code)
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS ix_funnel_stages_funnel_id ON funnel_stages(funnel_id)")

            # Seed default funnel
            default_funnel_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO funnels (id, tenant_id, type, name, is_default)
                VALUES (?, 'default', 'candidate', 'Driver Recruitment', 1)
                """,
                (default_funnel_id,),
            )
            for code, label, ord_val in DEFAULT_STAGES:
                cur.execute(
                    """
                    INSERT INTO funnel_stages (id, funnel_id, code, label, "order", is_terminal)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        default_funnel_id,
                        code,
                        label,
                        ord_val,
                        1 if code in TERMINAL_CODES else 0,
                    ),
                )

        if _table_exists(cur, "funnel_stages") and not _column_exists(
            cur, "funnel_stages", "stage_contract_v1"
        ):
            cur.execute("ALTER TABLE funnel_stages ADD COLUMN stage_contract_v1 TEXT")

        if _table_exists(cur, "funnel_stages") and not _column_exists(
            cur, "funnel_stages", "conversion_root_v1"
        ):
            cur.execute("ALTER TABLE funnel_stages ADD COLUMN conversion_root_v1 TEXT")

        # funnel_id on candidate_profiles
        if _table_exists(cur, "candidate_profiles") and not _column_exists(
            cur, "candidate_profiles", "funnel_id"
        ):
            cur.execute(
                "ALTER TABLE candidate_profiles ADD COLUMN funnel_id TEXT REFERENCES funnels(id)"
            )

        conn.commit()
