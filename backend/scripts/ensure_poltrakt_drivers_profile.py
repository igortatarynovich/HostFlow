#!/usr/bin/env python3
"""Create/update Poltrakt Drivers funnel + profile and bind POLTRAKT company vacancies (Focus).

Uses the same candidate stage **codes** as Driver CE so existing ``candidates.stage`` rows stay valid;
only kanban columns become recruitment / employment / closed.

**From the dev host** (Compose maps Postgres to 127.0.0.1:5432; hostname ``db`` does not resolve):

  cd /opt/HostFlow && python3 backend/scripts/ensure_poltrakt_drivers_profile.py

The script rewrites ``@db:`` → ``@127.0.0.1:`` in DB URLs when ``db`` is not resolvable.
Override target host: ``HOSTFLOW_SCRIPT_DB_HOST=localhost``.

**From inside the backend container** (``db`` resolves):

  docker compose exec backend python3 /app/scripts/ensure_poltrakt_drivers_profile.py

Optional:

  python3 backend/scripts/ensure_poltrakt_drivers_profile.py \\
    --tenant-id <uuid> --company-id <uuid>
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import socket
import sys
from pathlib import Path


def _configure_sys_path() -> None:
    """Host: repo root (parent of ``backend`` package). Docker: backend dir (``/app``)."""
    backend_root = Path(__file__).resolve().parent.parent
    repo_root = backend_root.parent
    if (repo_root / "backend").is_dir() and (repo_root / "backend").resolve() == backend_root.resolve():
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))
    elif str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))


def _localize_db_host_in_env() -> None:
    """Mirror tests/conftest: ``@db`` only resolves inside Compose network."""
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

from backend.app.constants.hostflow_canonical_tenants import (
    FOCUS_PERSONNEL_TENANT_ID,
    FOCUS_POLTRAKT_COMPANY_ID,
)
from backend.app.db.session import async_session_maker
from backend.app.seed_candidate_profiles import ensure_poltrakt_drivers_profile_for_tenant


async def main() -> None:
    p = argparse.ArgumentParser(description="Ensure Poltrakt Drivers profile + funnel for a tenant.")
    p.add_argument("--tenant-id", default=FOCUS_PERSONNEL_TENANT_ID)
    p.add_argument("--company-id", default=FOCUS_POLTRAKT_COMPANY_ID)
    args = p.parse_args()

    async with async_session_maker() as db:
        await ensure_poltrakt_drivers_profile_for_tenant(
            db,
            str(args.tenant_id).strip(),
            poltrakt_company_id=str(args.company_id).strip(),
        )

    print(
        f"OK: Poltrakt Drivers profile ensured for tenant {args.tenant_id!r}, "
        f"company {args.company_id!r}."
    )


if __name__ == "__main__":
    asyncio.run(main())
