#!/usr/bin/env python3
"""
Удалить тестовые/синтетические Meta-лиды по совпадению normalized.full_name.

Типичные имена из тестовых payload (см. test_meta_webhook_import.py): Test Skeleton, Revived Lead, Graph Import.

Запуск из корня репозитория:

  PYTHONPATH=/opt/HostFlow python3 scripts/delete_meta_synthetic_leads.py --tenant-id <UUID> --dry-run
  PYTHONPATH=/opt/HostFlow python3 scripts/delete_meta_synthetic_leads.py --tenant-id <UUID> --execute

Опционально: --company-name POLTRAKT — подставить tenant_id по первой компании с таким именем (осторожно, если совпадений несколько).

Нужны те же DATABASE_URL / ASYNC_DATABASE_URL, что у API (см. backend/.env).
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import delete, select  # noqa: E402
from sqlalchemy import or_  # noqa: E402

from backend.app.db.deps import bind_tenant_context_to_session  # noqa: E402
from backend.app.db.session import async_session_maker  # noqa: E402
from backend.app.models.company import Company  # noqa: E402
from backend.app.models.lead import Lead  # noqa: E402

# Имена как в unit-тестах Meta webhook; не трогаем реальные ФИО по умолчанию.
DEFAULT_SYNTHETIC_FULL_NAMES = frozenset(
    {
        "Test Skeleton",
        "Revived Lead",
        "Graph Import",
    }
)


async def _resolve_tenant_by_company_name(db, fragment: str) -> str | None:
    q = (
        select(Company.tenant_id)
        .where(Company.name.ilike(f"%{fragment.strip()}%"))
        .limit(2)
    )
    rows = (await db.execute(q)).all()
    if len(rows) != 1:
        return None
    return str(rows[0][0])


async def _run(
    *,
    tenant_id: UUID | None,
    company_name_fragment: str | None,
    extra_names: list[str],
    only_needs_routing: bool,
    dry_run: bool,
) -> int:
    names = set(DEFAULT_SYNTHETIC_FULL_NAMES)
    for n in extra_names:
        t = (n or "").strip()
        if t:
            names.add(t)

    async with async_session_maker() as db:
        tid: UUID | None = tenant_id
        if tid is None and company_name_fragment:
            tid_s = await _resolve_tenant_by_company_name(db, company_name_fragment)
            if not tid_s:
                print(
                    "Не удалось однозначно определить tenant по --company-name "
                    f"(нужна ровно одна компания, совпадающая с «{company_name_fragment}»). "
                    "Укажите --tenant-id вручную.",
                    file=sys.stderr,
                )
                return 2
            tid = UUID(tid_s)
            print(f"[info] tenant_id из компании: {tid}")

        if tid is None:
            print("Нужен --tenant-id или однозначный --company-name.", file=sys.stderr)
            return 2

        await bind_tenant_context_to_session(db, tid)
        tid_str = str(tid)

        name_expr = Lead.normalized["full_name"].as_string()
        conds = [name_expr == n for n in sorted(names)]
        stmt_sel = select(Lead.id, name_expr).where(
            Lead.tenant_id == tid_str,
            or_(*conds),
        )
        if only_needs_routing:
            stmt_sel = stmt_sel.where(Lead.status == "needs_routing")

        found = (await db.execute(stmt_sel)).all()
        print(f"Найдено лидов: {len(found)} (full_name ∈ {sorted(names)!r}" + (", status=needs_routing" if only_needs_routing else "") + ")")
        for lid, fn in found[:50]:
            print(f"  {lid}  full_name={fn!r}")
        if len(found) > 50:
            print(f"  ... и ещё {len(found) - 50}")

        if dry_run:
            print("\n--dry-run: удаление не выполнялось. Повторите с --execute.")
            return 0

        if not found:
            return 0

        del_stmt = delete(Lead).where(Lead.tenant_id == tid_str, Lead.id.in_([r[0] for r in found]))
        res = await db.execute(del_stmt)
        await db.commit()
        print(f"\nУдалено строк: {getattr(res, 'rowcount', None)}")
        return 0


def main() -> None:
    p = argparse.ArgumentParser(description="Delete synthetic Meta leads by normalized full_name.")
    p.add_argument("--tenant-id", default=None, help="UUID тенанта")
    p.add_argument("--company-name", default=None, help="Фрагмент имени компании → один tenant_id")
    p.add_argument(
        "--extra-name",
        action="append",
        default=[],
        help="Дополнительное точное full_name для удаления (можно повторять)",
    )
    p.add_argument(
        "--any-status",
        action="store_true",
        help="Не ограничивать status=needs_routing (по умолчанию удаляем только needs_routing)",
    )
    p.add_argument(
        "--execute",
        action="store_true",
        help="Реально удалить (без этого только список кандидатов на удаление)",
    )
    args = p.parse_args()

    dry = not args.execute
    tid = None
    if args.tenant_id:
        tid = UUID(args.tenant_id.strip())

    only_nr = not args.any_status

    raise SystemExit(
        asyncio.run(
            _run(
                tenant_id=tid,
                company_name_fragment=args.company_name,
                extra_names=list(args.extra_name or []),
                only_needs_routing=only_nr,
                dry_run=dry,
            )
        )
    )


if __name__ == "__main__":
    main()
