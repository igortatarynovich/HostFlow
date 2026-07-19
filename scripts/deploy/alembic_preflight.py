#!/usr/bin/env python3
"""
Deploy / local preflight for HostFlow checkout vs Alembic chain.

Prints and validates:
  * git commit, branch, status (dirty?)
  * alembic current (if DATABASE_URL available)
  * alembic heads (exactly one)
  * revision-graph integrity (every down_revision present)

Exit 0 only when the revision graph is valid and there is exactly one head.
Does not run upgrade (operator decides after reviewing the report).

Usage:
    python3 scripts/deploy/alembic_preflight.py
    python3 scripts/deploy/alembic_preflight.py --require-clean-tree
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND = REPO_ROOT / "backend"
GRAPH_CHECK = BACKEND / "scripts" / "check_alembic_revision_graph.py"


def _run(cmd: list[str], *, cwd: Path | None = None, env: dict | None = None) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd or REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-clean-tree",
        action="store_true",
        help="fail if git working tree is dirty (blocks partial-copy deploys)",
    )
    parser.add_argument(
        "--with-alembic",
        action="store_true",
        default=True,
        help="run ScriptDirectory graph build (default: on)",
    )
    parser.add_argument(
        "--no-with-alembic",
        action="store_false",
        dest="with_alembic",
        help="skip Alembic ScriptDirectory load",
    )
    args = parser.parse_args()

    print("=== HostFlow Alembic / checkout preflight ===")
    code, commit = _run(["git", "rev-parse", "HEAD"])
    print(f"git commit: {commit if code == 0 else 'UNKNOWN'}")

    code, branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    print(f"git branch: {branch if code == 0 else 'UNKNOWN'}")

    code, status = _run(["git", "status", "--short"])
    dirty = bool(status.strip()) if code == 0 else True
    print(f"git status: {'DIRTY' if dirty else 'clean'}")
    if dirty and status.strip():
        # Cap noise — show first lines only.
        lines = status.strip().splitlines()
        for line in lines[:30]:
            print(f"  {line}")
        if len(lines) > 30:
            print(f"  … +{len(lines) - 30} more")

    if args.require_clean_tree and dirty:
        print("[preflight] FAIL — working tree is dirty", file=sys.stderr)
        return 2

    # Alembic current / heads when DB URL is present.
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("ASYNC_DATABASE_URL")
    if db_url:
        env = os.environ.copy()
        env["DATABASE_URL"] = db_url
        code, current = _run(
            ["alembic", "current"],
            cwd=BACKEND,
            env=env,
        )
        print("--- alembic current ---")
        print(current or "(empty)")
        code, heads = _run(["alembic", "heads"], cwd=BACKEND, env=env)
        print("--- alembic heads ---")
        print(heads or "(empty)")
    else:
        print("DATABASE_URL not set — skipping alembic current/heads against DB")

    graph_cmd = [sys.executable, str(GRAPH_CHECK)]
    if args.with_alembic:
        graph_cmd.append("--with-alembic")
    code, graph_out = _run(graph_cmd, cwd=REPO_ROOT)
    print("--- revision graph ---")
    print(graph_out or "(empty)")
    if code != 0:
        print("[preflight] FAIL — revision graph invalid", file=sys.stderr)
        return code

    print("[preflight] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
