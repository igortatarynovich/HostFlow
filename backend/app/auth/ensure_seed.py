from __future__ import annotations

import datetime as dt
import json
import os
import uuid
from typing import Optional, Set

from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import async_session_maker
from backend.app.models.document_ruleset import DocumentRulesetVersion
from backend.app.services.default_tenant_ruleset_baseline import (
    BASELINE_RULESET_COMMENT,
    load_baseline_ruleset_dict,
    ruleset_required_matrix_empty,
)

# Пароль хешируем через passlib[bcrypt]
try:
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
except Exception:
    pwd_context = None


ADMIN_EMAIL = "admin@hostflow.dev"
ADMIN_PASSWORD = "Admin@025"
HR_OFFICER_EMAIL = "hr.officer@hostflow.dev"
HR_OFFICER_PASSWORD = "HrOfficer@025"
DEFAULT_TENANT_ID = "11111111-1111-1111-1111-111111111111"

_ASYNC_URL = os.getenv("ASYNC_DATABASE_URL") or ""
_SYNC_URL = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI") or ""
IS_SQLITE = _ASYNC_URL.startswith("sqlite:") or _SYNC_URL.startswith("sqlite:")


async def _table_exists(db: AsyncSession, name: str) -> bool:
    # SQLite
    if IS_SQLITE:
        try:
            res = await db.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name=:n"),
                {"n": name},
            )
            if res.scalar_one_or_none():
                return True
        except Exception:
            pass
    # PostgreSQL
    try:
        res = await db.execute(text("SELECT to_regclass(:n)"), {"n": name})
        tbl = res.scalar_one_or_none()
        # в PG для отсутствующей таблицы вернётся None
        if tbl:
            return True
    except Exception:
        pass
    return False


async def _columns(db: AsyncSession, table: str) -> Set[str]:
    cols: Set[str] = set()
    # SQLite
    if IS_SQLITE:
        try:
            res = await db.execute(text(f"PRAGMA table_info({table})"))
            for row in res:
                # row: cid, name, type, notnull, dflt_value, pk
                cols.add(row[1])
            if cols:
                return cols
        except Exception:
            pass
    # PG
    try:
        res = await db.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = :t
            """),
            {"t": table},
        )
        cols = {r[0] for r in res}
    except Exception:
        cols = set()
    return cols


async def _user_exists(db: AsyncSession, email: str) -> bool:
    try:
        res = await db.execute(
            text("SELECT 1 FROM users WHERE email = :email LIMIT 1"), {"email": email}
        )
        return res.first() is not None
    except Exception:
        # Если нет индекса/колонки — считаем, что нет
        return False


async def _ensure_membership_with_role(
    db: AsyncSession,
    *,
    user_id: Optional[str],
    tenant_id: str,
    membership_role: str,
    now: dt.datetime,
) -> None:
    if not user_id:
        return
    if not await _table_exists(db, "user_memberships"):
        return
    try:
        await db.execute(
            text(
                """
                INSERT INTO user_memberships (id, user_id, tenant_id, role, created_at, updated_at)
                VALUES (:id, :user_id, :tenant_id, :role, :created_at, :updated_at)
                ON CONFLICT(user_id, tenant_id) DO UPDATE SET role=excluded.role
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "tenant_id": tenant_id,
                "role": membership_role,
                "created_at": now,
                "updated_at": now,
            },
        )
        await db.commit()
    except Exception as membership_err:
        await db.rollback()
        print(f"[seed] user_membership ({membership_role}) insert skipped: {membership_err}")


async def _ensure_default_tenant_document_ruleset_baseline(db: AsyncSession) -> None:
    """Repair empty active ruleset rows for the default dev tenant (idempotent)."""
    if not await _table_exists(db, "document_ruleset_versions"):
        return
    try:
        baseline = load_baseline_ruleset_dict()
    except Exception as exc:
        print(f"[seed] ruleset baseline load skipped: {exc}")
        return

    res = await db.execute(
        select(DocumentRulesetVersion).where(
            DocumentRulesetVersion.tenant_id == DEFAULT_TENANT_ID,
            DocumentRulesetVersion.is_active.is_(True),
        )
    )
    changed = False
    for row in res.scalars():
        if not ruleset_required_matrix_empty(row.json_data):
            continue
        await db.execute(
            update(DocumentRulesetVersion)
            .where(DocumentRulesetVersion.id == row.id)
            .values(json_data=baseline, comment=BASELINE_RULESET_COMMENT)
        )
        changed = True
    if changed:
        try:
            await db.commit()
            print("[seed] default-tenant document ruleset: repaired empty active row(s)")
        except Exception as exc:
            await db.rollback()
            print(f"[seed] default-tenant ruleset repair commit failed: {exc}")
            return

    res_g = await db.execute(
        select(DocumentRulesetVersion).where(
            DocumentRulesetVersion.tenant_id == DEFAULT_TENANT_ID,
            DocumentRulesetVersion.own_company_id.is_(None),
            DocumentRulesetVersion.is_active.is_(True),
        )
    )
    if any(not ruleset_required_matrix_empty(r.json_data) for r in res_g.scalars().all()):
        return

    mv = await db.scalar(
        select(func.max(DocumentRulesetVersion.version)).where(
            DocumentRulesetVersion.tenant_id == DEFAULT_TENANT_ID,
            DocumentRulesetVersion.own_company_id.is_(None),
        )
    )
    next_v = int(mv or 0) + 1
    db.add(
        DocumentRulesetVersion(
            id=str(uuid.uuid4()),
            tenant_id=DEFAULT_TENANT_ID,
            own_company_id=None,
            version=next_v,
            json_data=baseline,
            comment=BASELINE_RULESET_COMMENT,
            is_active=True,
            signature="",
        )
    )
    try:
        await db.commit()
        print("[seed] default-tenant document ruleset: inserted global baseline version")
    except Exception as exc:
        await db.rollback()
        print(f"[seed] default-tenant ruleset insert failed: {exc}")


async def _ensure_hr_officer_dev_user(db: AsyncSession, cols: Set[str], now: dt.datetime) -> None:
    """Dev/test HR officer on the default tenant (same pattern as admin seed)."""
    if pwd_context is None:
        return
    hr_user_id: Optional[str] = None
    if await _user_exists(db, HR_OFFICER_EMAIL):
        try:
            res = await db.execute(
                text("SELECT id FROM users WHERE email = :email LIMIT 1"),
                {"email": HR_OFFICER_EMAIL},
            )
            row = res.first()
            if row:
                hr_user_id = row[0]
        except Exception:
            hr_user_id = None

        assignments = []
        params: dict[str, object] = {"email": HR_OFFICER_EMAIL}

        if "password_hash" in cols:
            params["password_hash"] = pwd_context.hash(HR_OFFICER_PASSWORD)
            assignments.append("password_hash = :password_hash")
        if "updated_at" in cols:
            params["updated_at"] = now
            assignments.append("updated_at = :updated_at")
        if "is_active" in cols:
            params["is_active"] = True
            assignments.append("is_active = :is_active")
        if "tenant_id" in cols:
            params["tenant_id"] = DEFAULT_TENANT_ID
            assignments.append("tenant_id = :tenant_id")
        if "role" in cols:
            params["role"] = "hr_officer"
            assignments.append("role = :role")
        if "full_name" in cols:
            params["full_name"] = "HostFlow HR Officer (dev)"
            assignments.append("full_name = :full_name")
        if "preferences" in cols:
            params["preferences"] = json.dumps({})
            if IS_SQLITE:
                assignments.append("preferences = :preferences")
            else:
                assignments.append("preferences = CAST(:preferences AS jsonb)")

        if assignments:
            update_sql = ", ".join(assignments)
            try:
                await db.execute(
                    text(f"UPDATE users SET {update_sql} WHERE email = :email"),
                    params,
                )
                await db.commit()
                print(f"[seed] HR officer обновлён: {HR_OFFICER_EMAIL}")
            except Exception as update_err:
                await db.rollback()
                print(f"[seed] обновление HR officer не удалось: {update_err}")
                return
        await _ensure_membership_with_role(
            db,
            user_id=hr_user_id,
            tenant_id=DEFAULT_TENANT_ID,
            membership_role="hr_officer",
            now=now,
        )
        return

    new_id = str(uuid.uuid4())
    insert_cols: list[str] = []
    insert_vals: list[object] = []

    if not await _user_exists(db, HR_OFFICER_EMAIL):
        try:
            if IS_SQLITE:
                cnt_row = await db.execute(
                    text(
                        "SELECT COUNT(*) FROM users WHERE tenant_id = :tid "
                        "AND lower(role) = lower(:role) AND is_active IS TRUE"
                    ),
                    {"tid": DEFAULT_TENANT_ID, "role": "hr_officer"},
                )
            else:
                cnt_row = await db.execute(
                    text(
                        "SELECT COUNT(*) FROM users WHERE tenant_id = :tid "
                        "AND lower(role::text) = lower(:role) AND is_active IS TRUE"
                    ),
                    {"tid": DEFAULT_TENANT_ID, "role": "hr_officer"},
                )
            cnt = int(cnt_row.scalar_one() or 0)
        except Exception:
            cnt = 0
        if cnt > 0:
            return

    def add(col: str, val: Optional[object]) -> None:
        if col in cols and val is not None:
            insert_cols.append(col)
            insert_vals.append(val)

    add("id", new_id)
    add("email", HR_OFFICER_EMAIL)
    add("password_hash", pwd_context.hash(HR_OFFICER_PASSWORD))
    add("role", "hr_officer")
    add("is_active", True)
    add("tenant_id", DEFAULT_TENANT_ID)
    add("created_at", now)
    add("updated_at", now)
    add("full_name", "HostFlow HR Officer (dev)")
    add("preferences", json.dumps({}))

    if not insert_cols:
        print("[seed] HR officer: нет подходящих колонок users — пропускаю")
        return

    placeholders = ", ".join([f":v{i}" for i in range(len(insert_vals))])
    columns_ddl = ", ".join(insert_cols)
    sql = f"INSERT INTO users ({columns_ddl}) VALUES ({placeholders})"
    params_ins = {f"v{i}": insert_vals[i] for i in range(len(insert_vals))}

    try:
        await db.execute(text(sql), params_ins)
        await db.commit()
        print(f"[seed] HR officer создан: {HR_OFFICER_EMAIL} / {HR_OFFICER_PASSWORD}")
    except Exception as e:
        print(f"[seed] вставка HR officer не удалась: {e}")
        await db.rollback()
        return

    user_id_value = new_id if "id" in insert_cols else None
    if user_id_value is None:
        try:
            res = await db.execute(
                text("SELECT id FROM users WHERE email=:email LIMIT 1"),
                {"email": HR_OFFICER_EMAIL},
            )
            row = res.first()
            if row:
                user_id_value = row[0]
        except Exception:
            user_id_value = None
    await _ensure_membership_with_role(
        db,
        user_id=user_id_value,
        tenant_id=DEFAULT_TENANT_ID,
        membership_role="hr_officer",
        now=now,
    )


async def ensure_auth_seed() -> None:
    """
    Создаёт дефолтного администратора, если пользователей с этим email ещё нет.
    Работает на SQLite и PostgreSQL. Явно задаёт id (uuid4), если колонка существует.
    """
    if pwd_context is None:
        print("[seed] passlib не установлен — пропускаю сидинг")
        return

    async with async_session_maker() as db:
        # -1) ensure tenants table has the default tenant
        if await _table_exists(db, "tenants"):
            cols_tenants = await _columns(db, "tenants")
            params = {
                "id": DEFAULT_TENANT_ID,
                "name": "Superadmin",
                "slug": "superadmin",
                "api_key": str(uuid.uuid4()).replace("-", ""),
                "is_active": True,
                "settings": "{}",
            }
            if "workspace_label" in cols_tenants:
                params["workspace_label"] = "Superadmin"
            columns = []
            values = []
            for key, value in params.items():
                if key in cols_tenants:
                    columns.append(key)
                    values.append(value)
            if columns:
                insert_cols = ", ".join(columns)
                placeholder = ", ".join(f":t{i}" for i in range(len(values)))
                conflict_updates = ["name = excluded.name", "slug = excluded.slug"]
                if "workspace_label" in columns:
                    conflict_updates.append("workspace_label = excluded.workspace_label")
                stmt = text(
                    f"INSERT INTO tenants ({insert_cols}) VALUES ({placeholder}) "
                    "ON CONFLICT(id) DO UPDATE SET " + ", ".join(conflict_updates)
                )
                await db.execute(
                    stmt, {f"t{i}": values[i] for i in range(len(values))}
                )
                await db.commit()

        # 0) таблица users должна существовать (миграции уже прогоняются на старте)
        if not await _table_exists(db, "users"):
            print("[seed] таблица users не найдена — пропускаю сидинг")
            return

        cols = await _columns(db, "users")

        if await _table_exists(db, "document_ruleset_versions"):
            await _ensure_default_tenant_document_ruleset_baseline(db)

        async def ensure_membership(user_id: Optional[str], now: dt.datetime) -> None:
            if not user_id:
                return
            if not await _table_exists(db, "user_memberships"):
                return
            try:
                await db.execute(
                    text(
                        """
                        INSERT INTO user_memberships (id, user_id, tenant_id, role, created_at, updated_at)
                        VALUES (:id, :user_id, :tenant_id, :role, :created_at, :updated_at)
                        ON CONFLICT(user_id, tenant_id) DO UPDATE SET role=excluded.role
                        """
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "user_id": user_id,
                        "tenant_id": DEFAULT_TENANT_ID,
                        "role": "owner",
                        "created_at": now,
                        "updated_at": now,
                    },
                )
                await db.commit()
            except Exception as membership_err:
                await db.rollback()
                print(f"[seed] user_membership insert skipped: {membership_err}")

        now = dt.datetime.utcnow()

        # 1) если такой email уже есть — обновляем пароль и связанные поля
        existing_user_id: Optional[str] = None
        if await _user_exists(db, ADMIN_EMAIL):
            try:
                res = await db.execute(
                    text("SELECT id FROM users WHERE email = :email LIMIT 1"),
                    {"email": ADMIN_EMAIL},
                )
                row = res.first()
                if row:
                    existing_user_id = row[0]
            except Exception:
                existing_user_id = None

            assignments = []
            params: dict[str, object] = {"email": ADMIN_EMAIL}

            if "password_hash" in cols:
                params["password_hash"] = pwd_context.hash(ADMIN_PASSWORD)
                assignments.append("password_hash = :password_hash")
            if "updated_at" in cols:
                params["updated_at"] = now
                assignments.append("updated_at = :updated_at")
            if "is_active" in cols:
                params["is_active"] = True
                assignments.append("is_active = :is_active")
            if "tenant_id" in cols:
                params["tenant_id"] = DEFAULT_TENANT_ID
                assignments.append("tenant_id = :tenant_id")
            if "role" in cols:
                params["role"] = "superadmin"
                assignments.append("role = :role")

            if assignments:
                update_sql = ", ".join(assignments)
                try:
                    await db.execute(
                        text(f"UPDATE users SET {update_sql} WHERE email = :email"),
                        params,
                    )
                    await db.commit()
                    print(f"[seed] admin существовал: пароль и статус обновлены для {ADMIN_EMAIL}")
                except Exception as update_err:
                    await db.rollback()
                    print(f"[seed] обновление admin не удалось: {update_err}")
                    return
            else:
                print("[seed] admin существует, подходящих колонок для обновления не найдено — пропускаю")

            await ensure_membership(existing_user_id, now)
            await _ensure_hr_officer_dev_user(db, cols, now)
            return

        # 2) готовим поля для создания
        new_id = str(uuid.uuid4())

        # Базовый набор: email, password_hash обязателен почти везде
        insert_cols = []
        insert_vals = []

        def add(col: str, val: Optional[object]):
            if col in cols and val is not None:
                insert_cols.append(col)
                insert_vals.append(val)

        # Первичный ключ id — задаём явно, если колонка есть
        add("id", new_id)

        # Жизненно необходимые поля
        add("email", ADMIN_EMAIL)
        add("password_hash", pwd_context.hash(ADMIN_PASSWORD))

        # Частые поля
        add("role", "superadmin")  # платформенный админ по умолчанию
        add("is_active", True)
        add("tenant_id", DEFAULT_TENANT_ID)
        add("created_at", now)
        add("updated_at", now)

        # Иногда встречаются альтернативные/алиасные поля
        # add("is_admin", True)  # раскомментируй, если в схеме есть is_admin вместо role

        if not insert_cols:
            print("[seed] не удалось подобрать подходящие колонки — пропускаю")
            return

        placeholders = ", ".join([f":v{i}" for i in range(len(insert_vals))])
        columns_ddl = ", ".join(insert_cols)
        sql = f"INSERT INTO users ({columns_ddl}) VALUES ({placeholders})"
        params = {f"v{i}": insert_vals[i] for i in range(len(insert_vals))}

        try:
            await db.execute(text(sql), params)
            await db.commit()
            print(f"[seed] admin пользователь создан: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
        except Exception as e:
            # Если что-то не так (например, в схеме другие имена колонок) — печатаем и не валим стартап
            print(f"[seed] вставка admin не удалась: {e} — проверь схему users")
            await db.rollback()
        else:
            user_id_value = new_id if "id" in insert_cols else None
            if user_id_value is None:
                try:
                    res = await db.execute(
                        text("SELECT id FROM users WHERE email=:email LIMIT 1"),
                        {"email": ADMIN_EMAIL},
                    )
                    row = res.first()
                    if row:
                        user_id_value = row[0]
                except Exception:
                    user_id_value = None
            await ensure_membership(user_id_value, now)
            await _ensure_hr_officer_dev_user(db, cols, now)
