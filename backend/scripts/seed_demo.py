from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import create_async_engine

# backend/scripts/seed_demo.py



TENANT_ID = "11111111-1111-1111-1111-111111111111"
DB_URL = (
    os.environ.get("DATABASE_URL")
    or os.environ.get("ASYNC_DATABASE_URL")
    or "postgresql+asyncpg://hf_app:hf_app@127.0.0.1:5432/hostflow"
)

engine = create_async_engine(DB_URL, echo=False, pool_pre_ping=True, future=True)

# -------------------- helpers --------------------


def now_aware_utc() -> datetime:
    return datetime.now(timezone.utc)


def to_naive_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo is None else dt.astimezone(timezone.utc).replace(tzinfo=None)


def to_aware_utc(dt: datetime) -> datetime:
    return (
        dt.replace(tzinfo=timezone.utc)
        if dt.tzinfo is None
        else dt.astimezone(timezone.utc)
    )


async def get_column_info(conn, table: str) -> Dict[str, Dict[str, str]]:
    """
    Возвращает {col: {data_type, udt_name, typname, fmt}} для public.{table}.
    typname/format_type берём из pg_catalog — это надёжнее для JSON/ARRAY.
    """
    q = sa.text(
        """
        WITH cols AS (
          SELECT lower(c.column_name) AS column_name,
                 c.data_type,
                 c.udt_name
          FROM information_schema.columns c
          WHERE c.table_schema = 'public' AND c.table_name = :table
        )
        SELECT cols.column_name,
               cols.data_type,
               cols.udt_name,
               t.typname,
               format_type(a.atttypid, a.atttypmod) AS fmt
        FROM cols
        JOIN pg_class pc ON pc.relname = :table
        JOIN pg_namespace pn ON pn.oid = pc.relnamespace AND pn.nspname='public'
        JOIN pg_attribute a ON a.attrelid = pc.oid AND a.attnum > 0 AND NOT a.attisdropped
        JOIN pg_type t ON t.oid = a.atttypid
        WHERE lower(a.attname) = cols.column_name
        """
    )
    rows = (await conn.execute(q, {"table": table.lower()})).mappings().all()
    return {
        r["column_name"]: {
            "data_type": r["data_type"],
            "udt_name": r["udt_name"],
            "typname": r["typname"],
            "fmt": r["fmt"],
        }
        for r in rows
    }


def col_is_text(colspec: Dict[str, str]) -> bool:
    dt = (colspec.get("data_type") or "").upper()
    udt = (colspec.get("udt_name") or "").lower()
    fmt = (colspec.get("fmt") or "").lower()
    return (
        dt in {"CHARACTER VARYING", "TEXT"}
        or udt in {"varchar", "text"}
        or fmt.startswith("character varying")
        or fmt == "text"
    )


def col_is_array(colspec: Dict[str, str]) -> bool:
    return (colspec.get("data_type") or "").upper() == "ARRAY" or (
        colspec.get("fmt") or ""
    ).startswith("")


def col_is_jsonlike(colspec: Dict[str, str]) -> bool:
    dt = (colspec.get("data_type") or "").upper()
    udt = (colspec.get("udt_name") or "").lower()
    typ = (colspec.get("typname") or "").lower()
    fmt = (colspec.get("fmt") or "").lower()
    return (
        dt in {"JSON", "JSONB"}
        or udt in {"json", "jsonb"}
        or typ in {"json", "jsonb"}
        or fmt.startswith("json")
    )


def col_is_timestamptz(colspec: Dict[str, str]) -> bool:
    return (colspec.get("data_type") or "").lower() == "timestamp with time zone" or (
        colspec.get("fmt") or ""
    ).startswith("timestamp with time zone")


def normalize_ts_for_column(
    dt: datetime, colspec: Optional[Dict[str, str]]
) -> datetime:
    if not colspec:
        return to_naive_utc(dt)
    return to_aware_utc(dt) if col_is_timestamptz(colspec) else to_naive_utc(dt)


def mk_docs_progress(i: int) -> Dict[str, Any]:
    base = now_aware_utc() - timedelta(days=30 - i)
    return {
        "passport": {
            "status": "received" if i % 3 else "missing",
            "date": (base + timedelta(days=1)).isoformat(),
        },
        "license": {
            "status": "received" if i % 2 else "in_progress",
            "date": (base + timedelta(days=5)).isoformat(),
        },
        "medical": {
            "status": "in_progress",
            "date": (base + timedelta(days=8)).isoformat(),
        },
        "permit": {
            "status": "pending",
            "date": (base + timedelta(days=12)).isoformat(),
        },
    }


def mk_address(i: int) -> Dict[str, Any]:
    return {
        "country": "PL",
        "city": "Warsaw",
        "street": f"Candidate St {i}",
        "zip": f"00-{i:03d}",
    }


def build_insert_stmt(
    table: str, payload: Dict[str, Any], jsonb_keys: Tuple[str, ...] = ()
) -> Tuple[sa.TextClause, Dict[str, Any]]:
    cols = list(payload.keys())
    placeholders = [f":{k}" for k in cols]
    sql = f"""
        INSERT INTO {table} ({", ".join(cols)})
        VALUES ({", ".join(placeholders)})
        ON CONFLICT (id) DO NOTHING
    """
    stmt = sa.text(sql)
    for k in jsonb_keys:
        if k in payload:
            stmt = stmt.bindparams(sa.bindparam(k, type_=JSONB))
    return stmt, payload


# -------------------- seeders --------------------


async def seed_users(conn):
    user_cols = await get_column_info(conn, "users")
    def have(c: str) -> bool:
        return c in user_cols

    created_spec = user_cols.get("created_at")
    updated_spec = user_cols.get("updated_at")
    now = now_aware_utc()
    created_at = normalize_ts_for_column(now, created_spec)
    updated_at = normalize_ts_for_column(now, updated_spec)

    base_users = [
        ("mgr-alex", "Alex Manager", "alex.manager@example.com"),
        ("mgr-olga", "Olga Manager", "olga.manager@example.com"),
        ("mgr-ivan", "Ivan Manager", "ivan.manager@example.com"),
    ]

    for short_id, full_name, email in base_users:
        row: Dict[str, Any] = {"id": str(uuid.uuid4())}
        if have("short_id"):
            row["short_id"] = short_id
        if have("full_name"):
            row["full_name"] = full_name
        if have("email"):
            row["email"] = email
        if have("password_hash"):
            row["password_hash"] = (
                "$2b$12$abcdefghijklmnopqrstuvabcdefghiJKLmnopqrstuVWXYZ12"
            )
        if have("role"):
            row["role"] = "manager"
        if have("extra"):
            row["extra"] = {"permissions": ["manage_candidates"]}
        if have("created_at"):
            row["created_at"] = created_at
        if have("updated_at"):
            row["updated_at"] = updated_at

        stmt, payload = build_insert_stmt(
            "users", row, ("extra",) if "extra" in row else ()
        )
        await conn.execute(stmt, payload)

    # карта short_id -> id (если short_id есть)
    if have("short_id"):
        rows = (
            (
                await conn.execute(
                    sa.text(
                        "SELECT id, short_id FROM users WHERE short_id IN ('mgr-alex','mgr-olga','mgr-ivan')"
                    )
                )
            )
            .mappings()
            .all()
        )
        return {r["short_id"]: r["id"] for r in rows}
    else:
        rows = (
            await conn.execute(
                sa.text(
                    "SELECT id FROM users ORDER BY created_at NULLS LAST, id LIMIT 3"
                )
            )
        ).all()
        return {f"manager{i + 1}": r[0] for i, r in enumerate(rows)}


async def seed_companies(conn):
    cols = await get_column_info(conn, "companies")
    def have(c: str) -> bool:
        return c in cols
    created_spec = cols.get("created_at")
    updated_spec = cols.get("updated_at")
    now = now_aware_utc()
    created_at = normalize_ts_for_column(now, created_spec)
    updated_at = normalize_ts_for_column(now, updated_spec)

    for i in range(1, 6):
        row: Dict[str, Any] = {"id": str(uuid.uuid4())}
        if have("tenant_id"):
            row["tenant_id"] = TENANT_ID
        if have("name"):
            row["name"] = f"Company {i:02d}"
        if have("country"):
            row["country"] = "PL"
        if have("city"):
            row["city"] = "Warsaw"
        if have("address"):
            row["address"] = f"Main Street {i}, Warsaw, PL"
        if have("contacts"):
            row["contacts"] = {
                "phone": f"+48 22 000 00 {i:02d}",
                "email": f"contact{i:02d}@example.com",
            }
        if have("extra"):
            row["extra"] = {"industry": "Logistics" if i % 2 else "Manufacturing"}
        if have("created_at"):
            row["created_at"] = created_at
        if have("updated_at"):
            row["updated_at"] = updated_at

        stmt, payload = build_insert_stmt(
            "companies", row, tuple(k for k in ("contacts", "extra") if k in row)
        )
        await conn.execute(stmt, payload)

    if have("tenant_id"):
        rows = (
            await conn.execute(
                sa.text("SELECT id FROM companies WHERE tenant_id=:t ORDER BY name"),
                {"t": TENANT_ID},
            )
        ).all()
    else:
        rows = (
            await conn.execute(sa.text("SELECT id FROM companies ORDER BY name"))
        ).all()
    return [r[0] for r in rows]


async def seed_vacancies(conn, company_ids: List[str]):
    cols = await get_column_info(conn, "vacancies")
    def have(c: str) -> bool:
        return c in cols

    created_spec = cols.get("created_at")
    updated_spec = cols.get("updated_at")
    now = now_aware_utc()
    created_at = normalize_ts_for_column(now, created_spec)
    updated_at = normalize_ts_for_column(now, updated_spec)

    salary_from_is_text = have("salary_from") and col_is_text(cols["salary_from"])
    salary_to_is_text = have("salary_to") and col_is_text(cols["salary_to"])

    for idx, company_id in enumerate(company_ids[:5], 1):
        s_from = 2000 + idx * 100
        s_to = 3000 + idx * 150

        row: Dict[str, Any] = {"id": str(uuid.uuid4())}
        if have("tenant_id"):
            row["tenant_id"] = TENANT_ID
        if have("company_id"):
            row["company_id"] = company_id
        if have("title"):
            row["title"] = f"Truck Driver {idx}"
        if have("description"):
            row["description"] = f"Long-haul driver position #{idx}"
        if have("location"):
            row["location"] = "EU"
        if have("salary_from"):
            row["salary_from"] = str(s_from) if salary_from_is_text else s_from
        if have("salary_to"):
            row["salary_to"] = str(s_to) if salary_to_is_text else s_to
        if have("currency"):
            row["currency"] = "EUR"
        if have("status"):
            row["status"] = "open"
        if have("extra"):
            row["extra"] = {"shift": "2/2", "experience": "1+ years"}
        if have("created_at"):
            row["created_at"] = created_at
        if have("updated_at"):
            row["updated_at"] = updated_at

        stmt, payload = build_insert_stmt(
            "vacancies", row, ("extra",) if "extra" in row else ()
        )
        await conn.execute(stmt, payload)

    if have("tenant_id") and have("created_at"):
        rows = (
            await conn.execute(
                sa.text(
                    "SELECT id FROM vacancies WHERE tenant_id=:t ORDER BY created_at"
                ),
                {"t": TENANT_ID},
            )
        ).all()
    else:
        rows = (
            await conn.execute(sa.text("SELECT id FROM vacancies ORDER BY id"))
        ).all()
    return [r[0] for r in rows]


async def seed_candidates(
    conn, company_ids: List[str], vacancy_ids: List[str], manager_ids: List[str]
):
    cols = await get_column_info(conn, "candidates")
    def have(c: str) -> bool:
        return c in cols

    created_spec = cols.get("created_at")
    updated_spec = cols.get("updated_at")
    now = now_aware_utc()
    created_at = normalize_ts_for_column(now, created_spec)
    updated_at = normalize_ts_for_column(now, updated_spec)

    # типы языков/доков
    languages_json = have("languages") and col_is_jsonlike(cols["languages"])
    languages_array = (
        have("languages") and (cols["languages"]["data_type"] or "").upper() == "ARRAY"
    )
    docs_json = have("docs_progress") and col_is_jsonlike(cols["docs_progress"])

    stages = [
        "new",
        "contacted",
        "docs_wait",
        "docs_got",
        "permit_ordered",
        "permit_received",
        "visa",
        "red_paper",
        "trip_plan",
        "at_client",
        "employed",
        "on_trip",
        "probation_ok",
        "rejected",
    ]

    for i in range(1, 26):
        langs_list = ["ru", "en"] if i % 3 else ["ru", "en", "pl"]
        docs_obj = mk_docs_progress(i)

        row: Dict[str, Any] = {"id": str(uuid.uuid4())}
        if have("tenant_id"):
            row["tenant_id"] = TENANT_ID
        if have("short_id"):
            row["short_id"] = f"CND-{1000 + i}"
        if have("first_name"):
            row["first_name"] = f"Candidate{i}"
        if have("last_name"):
            row["last_name"] = "Demo"
        if have("phone"):
            row["phone"] = f"+48 555 000 {i:03d}"
        if have("email"):
            row["email"] = f"candidate{i}@example.com"

        if have("languages"):
            if languages_array:
                row["languages"] = langs_list
            elif languages_json:
                row["languages"] = langs_list  # биндим как JSONB ниже
            else:
                row["languages"] = ", ".join(langs_list)

        if have("stage"):
            row["stage"] = stages[(i - 1) % len(stages)]
        if have("note"):
            row["note"] = f"Demo candidate #{i}"
        if have("manager") and manager_ids:
            row["manager"] = manager_ids[(i - 1) % len(manager_ids)]
        if have("company_id") and company_ids:
            row["company_id"] = company_ids[(i - 1) % len(company_ids)]
        if have("vacancy_id") and vacancy_ids:
            row["vacancy_id"] = vacancy_ids[(i - 1) % len(vacancy_ids)]

        if have("docs_progress"):
            if docs_json:
                row["docs_progress"] = docs_obj
            else:
                row["docs_progress"] = str(docs_obj)

        if have("extra"):
            row["extra"] = {
                "address": {
                    "country": "PL",
                    "city": "Warsaw",
                    "street": f"Candidate St {i}",
                    "zip": f"00-{i:03d}",
                },
                "source": "seed-demo",
                "tags": ["demo", "seed", f"batch-{(i - 1) // 5 + 1}"],
                "meta": {"rating": (i % 5) + 1},
            }

        if have("created_at"):
            row["created_at"] = created_at
        if have("updated_at"):
            row["updated_at"] = updated_at

        jsonb_keys: List[str] = []
        if have("extra"):
            jsonb_keys.append("extra")
        if have("docs_progress") and docs_json:
            jsonb_keys.append("docs_progress")
        if have("languages") and languages_json:
            jsonb_keys.append("languages")

        stmt, payload = build_insert_stmt("candidates", row, tuple(jsonb_keys))
        await conn.execute(stmt, payload)


# -------------------- entrypoint --------------------


async def main():
    async with engine.begin() as conn:
        user_map = await seed_users(conn)
        company_ids = await seed_companies(conn)
        vacancy_ids = await seed_vacancies(conn, company_ids)
        await seed_candidates(conn, company_ids, vacancy_ids, list(user_map.values()))
    await engine.dispose()
    print("[seed] done")


if __name__ == "__main__":
    asyncio.run(main())
