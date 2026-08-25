#!/usr/bin/env python3
"""
Repository Health Gate — block new product work when the checkout is unsafe.

Checks (all required for exit 0):
  1. Clean working tree (no staged/unstaged/untracked tracked-path noise;
     ignored files are OK)
  2. On integration/release-product-a-b (or allow --allow-branch)
  3. Fast-forward only vs origin/integration/release-product-a-b (ahead=0, behind=0
     when on integration; when on a feature branch, base tip is fetched & compared
     only if --require-integration-ff)
  4. Exactly one Alembic head (revision-graph script)
  5. No stale git worktrees (registered path missing on disk)
  6. No dirty secondary worktrees (optional --strict-worktrees)
  7. GIT-IMPORT-INTEGRITY (TS/TSX local imports resolve)
  8. No untracked Alembic migration files under backend/alembic/versions/

Usage:
  python3 scripts/repo_health_gate.py
  python3 scripts/repo_health_gate.py --strict-worktrees
  python3 scripts/repo_health_gate.py --allow-branch fix/foo
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = "integration/release-product-a-b"
IMPORT_GATE = REPO_ROOT / "hostflow-frontend" / "scripts" / "check_ts_import_integrity.py"
ALEMBIC_GRAPH = REPO_ROOT / "backend" / "scripts" / "check_alembic_revision_graph.py"


def _run(cmd: list[str], *, cwd: Path | None = None) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd or REPO_ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out.strip()


def _ok(msg: str) -> None:
    print(f"[health] OK  — {msg}")


def _fail(msg: str, failures: list[str]) -> None:
    print(f"[health] FAIL — {msg}", file=sys.stderr)
    failures.append(msg)


def main() -> int:
    parser = argparse.ArgumentParser(description="HostFlow repository health gate")
    parser.add_argument(
        "--allow-branch",
        action="append",
        default=[],
        help="Additional branch names allowed besides integration (repeatable)",
    )
    parser.add_argument(
        "--require-integration-ff",
        action="store_true",
        help="Require local integration branch tip == origin (even when checked out elsewhere)",
    )
    parser.add_argument(
        "--strict-worktrees",
        action="store_true",
        help="Fail if any linked worktree has a dirty working tree",
    )
    parser.add_argument(
        "--skip-import-integrity",
        action="store_true",
        help="Skip TS import integrity (not recommended)",
    )
    args = parser.parse_args()
    failures: list[str] = []

    print("=== HostFlow Repository Health Gate ===")

    # --- branch ---
    rc, branch = _run(["git", "branch", "--show-current"])
    branch = branch.strip()
    allowed = {INTEGRATION, *args.allow_branch}
    if branch in allowed:
        _ok(f"branch {branch}")
    else:
        _fail(
            f"branch {branch!r} not in allowed set {sorted(allowed)} "
            f"(pass --allow-branch if intentional)",
            failures,
        )

    # --- clean tree ---
    rc, porcelain = _run(["git", "status", "--porcelain"])
    if porcelain:
        _fail(f"working tree not clean:\n{porcelain}", failures)
    else:
        _ok("working tree clean")

    # --- FF vs origin integration ---
    _run(["git", "fetch", "origin", INTEGRATION, "--quiet"])
    rc, counts = _run(
        ["git", "rev-list", "--left-right", "--count", f"HEAD...origin/{INTEGRATION}"]
    )
    if rc == 0 and counts:
        left, right = (int(x) for x in counts.split())
        if branch == INTEGRATION:
            if left == 0 and right == 0:
                _ok(f"HEAD == origin/{INTEGRATION}")
            elif left == 0 and right > 0:
                _fail(
                    f"behind origin/{INTEGRATION} by {right} (fast-forward required)",
                    failures,
                )
            else:
                _fail(
                    f"diverged from origin/{INTEGRATION} (ahead={left} behind={right})",
                    failures,
                )
        elif args.require_integration_ff:
            rc2, icounts = _run(
                [
                    "git",
                    "rev-list",
                    "--left-right",
                    "--count",
                    f"{INTEGRATION}...origin/{INTEGRATION}",
                ]
            )
            if rc2 == 0:
                a, b = (int(x) for x in icounts.split())
                if a == 0 and b == 0:
                    _ok(f"local {INTEGRATION} == origin")
                else:
                    _fail(
                        f"local {INTEGRATION} not FF with origin (ahead={a} behind={b})",
                        failures,
                    )
        else:
            _ok(f"on {branch}; integration FF check skipped (use --require-integration-ff)")
    else:
        _fail(f"could not compare to origin/{INTEGRATION}: {counts}", failures)

    # --- alembic single head ---
    if ALEMBIC_GRAPH.is_file():
        rc, out = _run([sys.executable, str(ALEMBIC_GRAPH)])
        if rc == 0:
            _ok("alembic revision graph / single head")
        else:
            _fail(f"alembic graph check failed:\n{out}", failures)
    else:
        rc, out = _run(["alembic", "heads"], cwd=REPO_ROOT / "backend")
        heads = [ln for ln in out.splitlines() if "(head)" in ln]
        if rc == 0 and len(heads) == 1:
            _ok(f"alembic heads: {heads[0]}")
        else:
            _fail(f"expected 1 alembic head, got {len(heads)}:\n{out}", failures)

    # --- worktrees ---
    rc, wt_out = _run(["git", "worktree", "list", "--porcelain"])
    stale: list[str] = []
    dirty_wt: list[str] = []
    current: dict[str, str] = {}
    for line in wt_out.splitlines():
        if line.startswith("worktree "):
            if current.get("path"):
                path = Path(current["path"])
                if not path.is_dir():
                    stale.append(current["path"])
                elif args.strict_worktrees and path.resolve() != REPO_ROOT.resolve():
                    drc, dstatus = _run(["git", "status", "--porcelain"], cwd=path)
                    if dstatus.strip():
                        dirty_wt.append(current["path"])
            current = {"path": line.split(" ", 1)[1]}
        elif line.startswith("branch "):
            current["branch"] = line.split(" ", 1)[1]
    if current.get("path"):
        path = Path(current["path"])
        if not path.is_dir():
            stale.append(current["path"])
        elif args.strict_worktrees and path.resolve() != REPO_ROOT.resolve():
            drc, dstatus = _run(["git", "status", "--porcelain"], cwd=path)
            if dstatus.strip():
                dirty_wt.append(current["path"])

    if stale:
        _fail(f"stale worktree(s) (path missing): {stale}", failures)
    else:
        _ok("no stale worktrees")

    if args.strict_worktrees:
        if dirty_wt:
            _fail(f"dirty secondary worktree(s): {dirty_wt}", failures)
        else:
            _ok("secondary worktrees clean")

    # --- untracked alembic migrations ---
    versions = REPO_ROOT / "backend" / "alembic" / "versions"
    untracked_migs: list[str] = []
    if versions.is_dir():
        rc, untracked = _run(
            ["git", "ls-files", "--others", "--exclude-standard", "--", str(versions)]
        )
        for line in untracked.splitlines():
            if line.endswith(".py"):
                untracked_migs.append(line)
    if untracked_migs:
        _fail(f"untracked alembic migration(s): {untracked_migs}", failures)
    else:
        _ok("no untracked alembic migrations")

    # --- import integrity ---
    if args.skip_import_integrity:
        _ok("import integrity skipped")
    elif IMPORT_GATE.is_file():
        rc, out = _run([sys.executable, str(IMPORT_GATE)])
        if rc == 0:
            _ok(out.splitlines()[-1] if out else "import integrity")
        else:
            _fail(f"import integrity failed:\n{out}", failures)
    else:
        _fail(f"missing import gate script: {IMPORT_GATE}", failures)

    print("---")
    if failures:
        print(f"[health] FAILED ({len(failures)} check(s))", file=sys.stderr)
        print(
            "Do not start new product PRs until health is restored.",
            file=sys.stderr,
        )
        return 1

    print("[health] PASSED — safe to start product work")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
