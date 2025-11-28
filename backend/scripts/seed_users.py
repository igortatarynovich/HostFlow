# backend/scripts/seed_users.py
import os
from datetime import datetime, timezone
from uuid import uuid4

import psycopg2
import psycopg2.extras
from passlib.hash import bcrypt

# Берём подключение из SYNC_DATABASE_URL или DATABASE_URL
DB_URL = os.getenv("SYNC_DATABASE_URL") or os.getenv("DATABASE_URL")
if not DB_URL:
    # Фоллбэк на локальный контейнер/локальный PG
    DB_URL = "postgresql://hostflow:hostflow@localhost:5432/hostflow"

USERS = [
    # платформенный суперадмин
    {"email": "admin@hostflow.dev", "role": "superadmin", "password": "Admin@025"},
    # менеджеры
    {"email": "maria.manager@hostflow.dev", "role": "manager", "password": "manager"},
    {"email": "ivan.manager@hostflow.dev", "role": "manager", "password": "manager"},
    {"email": "olga.manager@hostflow.dev", "role": "manager", "password": "manager"},
    {"email": "peter.manager@hostflow.dev", "role": "manager", "password": "manager"},
    {"email": "kate.manager@hostflow.dev", "role": "manager", "password": "manager"},
]

SQL = """
INSERT INTO users (id, email, password_hash, role, created_at)
VALUES (%(id)s, %(email)s, %(password_hash)s, %(role)s, %(created_at)s)
ON CONFLICT (email) DO NOTHING;
"""


def main():
    print(f"[seed-users] Using DB: {DB_URL}")
    conn = psycopg2.connect(DB_URL)
    try:
        with conn, conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            for u in USERS:
                rec = {
                    "id": str(uuid4()),
                    "email": u["email"],
                    "password_hash": bcrypt.hash(u["password"]),
                    "role": u["role"],  # enum role должен содержать 'admin' и 'manager'
                    "created_at": datetime.now(timezone.utc),
                }
                cur.execute(SQL, rec)
        print(
            f"[seed-users] ✅ Done: создан(ы) {len(USERS)} пользователей (admin + 5 manager)."
        )
        print("[seed-users] Пароли: admin=Admin@025, manager*=manager")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
