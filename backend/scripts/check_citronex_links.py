#!/usr/bin/env python3
"""
Проверка связей Citronex: есть ли tenant_links с client_tenant_id = Citronex.
Запуск: из корня backend или репо
  python -m backend.scripts.check_citronex_links
  или с подключением к БД: DATABASE_URL=... python -m backend.scripts.check_citronex_links
"""
import asyncio
import os
import sys

CITRONEX_TENANT_ID = "517319d0-b53e-493d-9ac8-40f23091a35d"


async def main():
    try:
        from sqlalchemy import text, select
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
    except ImportError:
        print("Install sqlalchemy and asyncpg (or aiosqlite).")
        sys.exit(1)

    db_url = os.environ.get("DATABASE_URL", "").strip()
    if not db_url:
        print("Set DATABASE_URL (e.g. postgresql+asyncpg://user:pass@host/db)")
        sys.exit(1)
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 1) tenant_links для Citronex
        r = await session.execute(
            text("""
                SELECT id, agency_tenant_id, client_tenant_id, handoff_include_company_id, status
                FROM tenant_links
                WHERE client_tenant_id = :tid
            """),
            {"tid": CITRONEX_TENANT_ID},
        )
        rows = r.fetchall()
        print(f"tenant_links с client_tenant_id = Citronex: {len(rows)}")
        for row in rows:
            print(f"  id={row[0]}, agency={row[1]}, handoff_company={row[3]}, status={row[4]}")

        if not rows:
            print("\n  Нет связей — список кандидатов у Citronex будет пустым.")
            # Есть ли handoffs к Citronex
            r2 = await session.execute(
                text("""
                    SELECT agency_tenant_id, client_company_id
                    FROM candidate_handoffs
                    WHERE client_tenant_id = :tid
                    LIMIT 3
                """),
                {"tid": CITRONEX_TENANT_ID},
            )
            handoffs = r2.fetchall()
            print(f"\n  candidate_handoffs с client_tenant_id = Citronex: {len(handoffs)}")
            for h in handoffs:
                print(f"    agency={h[0]}, client_company_id={h[1]}")
            print("\n  Запустите миграции: alembic upgrade head")
            return

        # 2) Вакансии по handoff_include_company_id
        company_ids = [str(r[3]) for r in rows if r[3]]
        if company_ids:
            placeholders = ", ".join(f":c{i}" for i in range(len(company_ids)))
            r3 = await session.execute(
                text(f"SELECT id, company_id FROM vacancies WHERE company_id IN ({placeholders})"),
                {f"c{i}": cid for i, cid in enumerate(company_ids)},
            )
            vacs = r3.fetchall()
            print(f"\nВакансий по этим компаниям: {len(vacs)}")
            if not vacs:
                print("  Нет вакансий у связанных компаний — кандидаты по вакансиям не появятся.")
        # 3) Кандидаты по handoff
        r4 = await session.execute(
            text("""
                SELECT COUNT(DISTINCT candidate_id)
                FROM candidate_handoffs
                WHERE client_tenant_id = :tid
            """),
            {"tid": CITRONEX_TENANT_ID},
        )
        handoff_count = r4.scalar()
        print(f"\nКандидатов с handoff в Citronex: {handoff_count}")


if __name__ == "__main__":
    asyncio.run(main())
