#!/usr/bin/env python3
"""Verify Stage 1A Alembic migrations upgrade/downgrade cleanly on PostgreSQL."""

from __future__ import annotations

import os
import subprocess
import sys


STAGE_1A_BASE = "202608250002_adr019_domain_event_outbox_3a1"
STAGE_1A_TABLE = "202607131400_client_accounts_stage_1a"
STAGE_1A_LINKS = "202607131401_client_account_link_columns"


def _run(*args: str) -> None:
    env = os.environ.copy()
    if not env.get("DATABASE_URL"):
        print("DATABASE_URL is required", file=sys.stderr)
        sys.exit(1)
    subprocess.run(args, cwd=os.path.join(os.path.dirname(__file__), ".."), check=True, env=env)


def main() -> int:
    _run("alembic", "upgrade", STAGE_1A_LINKS)
    _run("alembic", "downgrade", STAGE_1A_TABLE)
    _run("alembic", "upgrade", STAGE_1A_LINKS)
    _run("alembic", "downgrade", STAGE_1A_BASE)
    _run("alembic", "upgrade", "head")
    print("Stage 1A migration roundtrip OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
