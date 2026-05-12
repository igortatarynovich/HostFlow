#!/usr/bin/env python3
"""Grant POLTRAKT company access on Focus tenant to an existing recruiter (merge, non-destructive).

Recruiters see candidates only for companies in ``user_company_access`` for that tenant.
Vacancy-level visibility is derived from those companies (all vacancies with ``company_id = POLTRAKT``
scoped to the Focus tenant).

This script:

1. Adds the canonical Poltrakt company id to the user's access (merge).
2. Optionally **backfills** ``candidates.company_id`` to Poltrakt for rows that sit on a Poltrakt
   vacancy but have NULL or a mismatched ``company_id`` — so list filters and ACL stay aligned
   with ``GET /candidates`` (company OR vacancy OR assignee).

Default target: **Valentyna Liashok** (``valentyna.l@work-host.com``).

**From the dev host** (same DB URL rewrite as other Focus scripts):

  cd /opt/HostFlow && python3 backend/scripts/ensure_focus_recruiter_poltrakt_access.py

**Dry run** (no DB writes):

  python3 backend/scripts/ensure_focus_recruiter_poltrakt_access.py --dry-run

**Skip candidate backfill** (only ``user_company_access``):

  python3 backend/scripts/ensure_focus_recruiter_poltrakt_access.py --no-backfill-candidates

**Another user**:

  python3 backend/scripts/ensure_focus_recruiter_poltrakt_access.py --email other@example.com

**From inside the backend container**:

  docker compose exec backend python3 /app/scripts/ensure_focus_recruiter_poltrakt_access.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import socket
import sys
from pathlib import Path


def _configure_sys_path() -> None:
    backend_root = Path(__file__).resolve().parent.parent
    repo_root = backend_root.parent
    if (repo_root / "backend").is_dir() and (repo_root / "backend").resolve() == backend_root.resolve():
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))
    elif str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))


def _localize_db_host_in_env() -> None:
    override = (os.environ.get("HOSTFLOW_SCRIPT_DB_HOST") or "").strip()
    keys = ("ASYNC_DATABASE_URL", "SYNC_DATABASE_URL", "DATABASE_URL")
    if override:
        for key in keys:
            val = os.environ.get(key)
            if val and "@db:" in val:
                os.environ[key] = re.sub(r"@db:", f"@{override}:", val)
        return
    try:
        socket.getaddrinfo("db", 5432, type=socket.SOCK_STREAM)
        return
    except OSError:
        pass
    for key in keys:
        val = os.environ.get(key)
        if val and "@db:" in val:
            os.environ[key] = re.sub(r"@db:", "@127.0.0.1:", val)


def _load_dotenv_backends() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    backend_root = Path(__file__).resolve().parent.parent
    repo_root = backend_root.parent
    load_dotenv(repo_root / ".env", override=False)
    load_dotenv(backend_root / ".env", override=False)


_configure_sys_path()
_load_dotenv_backends()
_localize_db_host_in_env()

from sqlalchemy import func, or_, select, update  # noqa: E402

from backend.app.constants.hostflow_canonical_tenants import (  # noqa: E402
    FOCUS_PERSONNEL_TENANT_ID,
    FOCUS_POLTRAKT_COMPANY_ID,
)
from backend.app.db.session import async_session_maker  # noqa: E402
from backend.app.models.access import UserCompanyAccess  # noqa: E402
from backend.app.models.candidate import Candidate  # noqa: E402
from backend.app.models.company import Company  # noqa: E402
from backend.app.models.user import User  # noqa: E402
from backend.app.models.vacancy import Vacancy  # noqa: E402
from backend.app.services.users import _replace_company_access  # noqa: E402

DEFAULT_EMAIL = "valentyna.l@work-host.com"


async def _resolve_user(db, email: str | None, user_id: str | None, name_substring: str | None) -> User | None:
    if user_id:
        uid = str(user_id).strip()
        if uid:
            r = await db.execute(select(User).where(User.id == uid))
            return r.scalar_one_or_none()
    em = (email or "").strip()
    if em:
        res = await db.execute(select(User).where(func.lower(User.email) == em.lower()))
        return res.scalar_one_or_none()
    sub = (name_substring or "").strip()
    if sub:
        like = f"%{sub}%"
        return (
            await db.execute(select(User).where(User.full_name.ilike(like))).limit(2)
        ).scalars().first()
    return None


async def _poltrakt_vacancy_stats(db, tenant_id: str, company_id: str) -> tuple[int, int]:
    """Counts: Poltrakt vacancies on Focus; candidates on those vacancies needing company_id fix."""
    vac_stmt = (
        select(func.count())
        .select_from(Vacancy)
        .join(Company, Company.id == Vacancy.company_id)
        .where(Vacancy.company_id == company_id)
        .where(
            or_(
                Vacancy.tenant_id == tenant_id,
                Company.tenant_id == tenant_id,
            )
        )
    )
    n_vac = int((await db.execute(vac_stmt)).scalar_one() or 0)

    vac_ids = (
        select(Vacancy.id)
        .join(Company, Company.id == Vacancy.company_id)
        .where(Vacancy.company_id == company_id)
        .where(
            or_(
                Vacancy.tenant_id == tenant_id,
                Company.tenant_id == tenant_id,
            )
        )
    )
    cand_stmt = (
        select(func.count())
        .select_from(Candidate)
        .where(Candidate.tenant_id == tenant_id)
        .where(Candidate.deleted_at.is_(None))
        .where(Candidate.vacancy_id.in_(vac_ids))
        .where(or_(Candidate.company_id.is_(None), Candidate.company_id != company_id))
    )
    n_backfill = int((await db.execute(cand_stmt)).scalar_one() or 0)
    return n_vac, n_backfill


async def _run(args: argparse.Namespace) -> int:
    tenant_id = str(args.tenant_id).strip()
    company_id = str(args.company_id).strip()

    async with async_session_maker() as db:
        company = (await db.execute(select(Company).where(Company.id == company_id))).scalar_one_or_none()
        if company is None:
            sys.stderr.write(f"[poltrakt-access] No company row for id={company_id!r}\n")
            return 1
        if str(company.tenant_id) != tenant_id:
            sys.stderr.write(
                f"[poltrakt-access] Company {company_id} tenant_id={company.tenant_id!r} "
                f"!= expected Focus tenant {tenant_id!r}\n"
            )
            return 1

        user = await _resolve_user(db, args.email, args.user_id, args.name_substring)
        if user is None:
            sys.stderr.write(
                "[poltrakt-access] User not found. Pass --email, --user-id, or --name-substring.\n"
            )
            return 1

        prev_rows = (
            await db.execute(
                select(UserCompanyAccess.company_id).where(
                    UserCompanyAccess.tenant_id == tenant_id,
                    UserCompanyAccess.user_id == user.id,
                )
            )
        ).all()
        prev = {str(r[0]) for r in prev_rows if r[0]}

        if args.replace:
            next_ids = {company_id}
        else:
            next_ids = set(prev) | {company_id}

        n_vac, n_backfill = await _poltrakt_vacancy_stats(db, tenant_id, company_id)

        out: dict = {
            "user_id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "tenant_id": tenant_id,
            "poltrakt_company_id": company_id,
            "company_access_before": sorted(prev),
            "company_access_after": sorted(next_ids),
            "poltrakt_vacancies_in_scope": n_vac,
            "candidates_backfill_rowcount": n_backfill,
            "backfill_candidates_enabled": bool(args.backfill_candidates),
            "dry_run": bool(args.dry_run),
        }

        if args.dry_run:
            print(json.dumps(out, ensure_ascii=False, indent=2))
            return 0

        await _replace_company_access(
            db,
            tenant_id=tenant_id,
            user_id=user.id,
            company_ids=sorted(next_ids),
            can_edit=bool(args.can_edit),
        )

        backfill_done = 0
        if args.backfill_candidates and n_backfill > 0:
            vac_ids = (
                select(Vacancy.id)
                .join(Company, Company.id == Vacancy.company_id)
                .where(Vacancy.company_id == company_id)
                .where(
                    or_(
                        Vacancy.tenant_id == tenant_id,
                        Company.tenant_id == tenant_id,
                    )
                )
            )
            upd = (
                update(Candidate)
                .where(Candidate.tenant_id == tenant_id)
                .where(Candidate.deleted_at.is_(None))
                .where(Candidate.vacancy_id.in_(vac_ids))
                .where(or_(Candidate.company_id.is_(None), Candidate.company_id != company_id))
                .values(company_id=company_id)
            )
            res = await db.execute(upd)
            backfill_done = getattr(res, "rowcount", None)
            if backfill_done is None:
                backfill_done = n_backfill

        out["candidates_backfill_updated"] = backfill_done if args.backfill_candidates else 0
        await db.commit()
        print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def main() -> None:
    p = argparse.ArgumentParser(description="Merge POLTRAKT company access for a Focus recruiter.")
    p.add_argument("--email", default=DEFAULT_EMAIL, help=f"User email (default: {DEFAULT_EMAIL})")
    p.add_argument("--user-id", default=None, help="User UUID (overrides --email)")
    p.add_argument(
        "--name-substring",
        default=None,
        help="Fallback: match User.full_name ILIKE %%substring%% (if email/user-id not used)",
    )
    p.add_argument("--tenant-id", default=FOCUS_PERSONNEL_TENANT_ID)
    p.add_argument("--company-id", default=FOCUS_POLTRAKT_COMPANY_ID)
    p.add_argument(
        "--replace",
        action="store_true",
        help="Replace all company access with POLTRAKT only (default: merge with existing)",
    )
    p.add_argument(
        "--no-can-edit",
        action="store_true",
        help="Set can_edit=false on access rows (default: can_edit=true)",
    )
    p.add_argument("--dry-run", action="store_true", help="Print planned state without writing")
    p.add_argument(
        "--no-backfill-candidates",
        action="store_true",
        help="Do not set candidates.company_id to POLTRAKT when vacancy is POLTRAKT (default: backfill)",
    )
    args = p.parse_args()
    args.can_edit = not args.no_can_edit
    args.backfill_candidates = not args.no_backfill_candidates
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
