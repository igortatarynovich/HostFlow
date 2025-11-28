from __future__ import annotations

import os
import secrets
import sqlite3
import string
import json

# --- Определяем путь к dev.db (~/HostFlow/backend/dev.db) ---
#   …/backend/app/auth/ensure_multitenancy.py
#   base_dir = …/backend/app
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))
DB_PATH = os.environ.get("DEV_DB_PATH") or os.path.join(PROJECT_ROOT, "app.db")

DEFAULT_TENANT_ID = os.environ.get(
    "DEFAULT_TENANT_ID", "11111111-1111-1111-1111-111111111111"
)


def _table_exists(cur: sqlite3.Cursor, name: str) -> bool:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None


def _column_exists(cur: sqlite3.Cursor, table: str, col: str) -> bool:
    cur.execute(f"PRAGMA table_info({table})")
    return any(r[1] == col for r in cur.fetchall())


def _generate_api_key(length: int = 40) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def ensure_auth_multitenancy() -> None:
    """
    Делает базовый мульти-тенант скелет для DEV:
      - создаёт таблицу tenants (если нет);
      - добавляет users.tenant_id (если нет).
    Работает поверх SQLite dev.db.
    """
    dsn = (
        os.environ.get("ASYNC_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or os.environ.get("SQLALCHEMY_DATABASE_URI")
        or ""
    )
    if dsn and not dsn.startswith("sqlite"):
        # PostgreSQL/другая СУБД — пропускаем dev-only SQLite миграции.
        return

    # SQLite синхронный, но вызывается из lifespan — держим интерфейс async.
    if not os.path.exists(DB_PATH):
        # БД создастся на лету; но таблиц может не быть — это нормально: их создаст create_all_tables()
        pass

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()

        # 1) Таблица tenants
        if not _table_exists(cur, "tenants"):
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS tenants (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    slug TEXT,
                    api_key TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    description TEXT,
                    settings TEXT,
                    created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                    updated_at TEXT DEFAULT (CURRENT_TIMESTAMP)
                )
                """
            )
        # 1.1) Обеспечить наличие дефолтного тенанта
        cur.execute(
            """
            INSERT OR IGNORE INTO tenants (id, name)
            VALUES (?, ?)
            """,
            (DEFAULT_TENANT_ID, "Default Tenant"),
        )

        # Ensure new columns exist for legacy databases
        for column, ddl in (
            ("slug", "ALTER TABLE tenants ADD COLUMN slug TEXT"),
            ("api_key", "ALTER TABLE tenants ADD COLUMN api_key TEXT"),
            ("is_active", "ALTER TABLE tenants ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1"),
            ("description", "ALTER TABLE tenants ADD COLUMN description TEXT"),
            ("settings", "ALTER TABLE tenants ADD COLUMN settings TEXT"),
        ):
            if not _column_exists(cur, "tenants", column):
                cur.execute(ddl)

        # Populate slug/api_key/settings defaults
        cur.execute(
            """
            UPDATE tenants
            SET slug = COALESCE(slug, lower(replace(name, ' ', '-'))),
                api_key = COALESCE(api_key, ?),
                settings = COALESCE(settings, ?)
            WHERE id = ?
            """,
            (_generate_api_key(), json.dumps({}), DEFAULT_TENANT_ID),
        )

        # 2) Колонка users.tenant_id
        if _table_exists(cur, "users") and not _column_exists(
            cur, "users", "tenant_id"
        ):
            # В SQLite ADD COLUMN всегда в конец и без NOT NULL (чтобы не рушить существующие строки)
            cur.execute("ALTER TABLE users ADD COLUMN tenant_id TEXT")

        # 3) Индекс для быстрой фильтрации по tenant_id (необязательно, но полезно)
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_users_tenant_id
            ON users(tenant_id)
            """
        )

        # 4) Проставить tenant_id по умолчанию существующим пользователям без tenant_id (для DEV)
        if _table_exists(cur, "users") and _column_exists(cur, "users", "tenant_id"):
            cur.execute(
                """
                UPDATE users
                SET tenant_id = ?
                WHERE tenant_id IS NULL OR tenant_id = ''
                """,
                (DEFAULT_TENANT_ID, ),
            )

        conn.commit()
    finally:
        conn.close()
