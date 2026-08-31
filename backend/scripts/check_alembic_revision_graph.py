#!/usr/bin/env python3
"""
Alembic revision-graph integrity gate.

Extends the single-head rule with the failure mode that broke /opt/HostFlow:

    a child migration is present (e.g. R5) but its ``down_revision`` parent
    file is missing (e.g. R4). ``check_alembic_heads`` alone can still report
    "1 head" while Alembic itself cannot build the revision map.

Checks (no database required):

1. Every ``down_revision`` target exists as a revision file in the versions dir.
2. The revision graph has no cycles (DFS).
3. Exactly one head.
4. Optional: Alembic ``ScriptDirectory`` can build the revision map
   (same KeyError path as ``alembic upgrade head``).

Exit codes:
    0 — OK
    1 — graph / parser failure (0 heads, cycle, ScriptDirectory error)
    2 — more than one head, missing parent, or versions dir missing

Usage:
    python3 backend/scripts/check_alembic_revision_graph.py
    python3 backend/scripts/check_alembic_revision_graph.py --with-alembic
    python3 backend/scripts/check_alembic_revision_graph.py --quiet
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VERSIONS_DIR = BACKEND_ROOT / "alembic" / "versions"
DEFAULT_ALEMBIC_INI = BACKEND_ROOT.parent / "alembic.ini"

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

# Reuse the proven parser from the heads guard.
from check_alembic_heads import (  # noqa: E402
    _collect_revisions,
    _find_heads,
)


def _as_parents(down: str | tuple[str, ...] | None) -> tuple[str, ...]:
    if down is None:
        return ()
    if isinstance(down, tuple):
        return tuple(p for p in down if p)
    return (down,)


def _missing_parents(
    revisions: dict[str, str | tuple[str, ...] | None],
) -> list[tuple[str, str]]:
    missing: list[tuple[str, str]] = []
    for rev_id, down in revisions.items():
        for parent in _as_parents(down):
            if parent not in revisions:
                missing.append((rev_id, parent))
    return sorted(missing)


def _find_cycle(revisions: dict[str, str | tuple[str, ...] | None]) -> list[str] | None:
    """Return one cycle path if present, else None.

    Note: some legacy HostFlow revision pairs form a cycle in file metadata.
    Cycle detection is advisory (warning) — missing parents + Alembic
    ScriptDirectory are the blocking gates.
    """
    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []

    def dfs(node: str) -> list[str] | None:
        if node in visiting:
            if node in stack:
                i = stack.index(node)
                return stack[i:] + [node]
            return [node, node]
        if node in visited or node not in revisions:
            return None
        visiting.add(node)
        stack.append(node)
        for parent in _as_parents(revisions[node]):
            found = dfs(parent)
            if found is not None:
                return found
        stack.pop()
        visiting.remove(node)
        visited.add(node)
        return None

    for rev_id in revisions:
        found = dfs(rev_id)
        if found is not None:
            return found
    return None


def _check_alembic_script_map(*, alembic_ini: Path, versions_dir: Path) -> str | None:
    """Return error message if Alembic cannot build the revision map."""
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory
    except ImportError as exc:
        return f"alembic import failed: {exc}"

    if not alembic_ini.is_file():
        return f"alembic.ini not found: {alembic_ini}"

    script_location = versions_dir.parent  # …/alembic (contains env.py + versions/)
    cfg = Config(str(alembic_ini))
    cfg.set_main_option("script_location", str(script_location))
    try:
        script = ScriptDirectory.from_config(cfg)
        # Force revision map construction (raises KeyError on missing parent).
        heads = list(script.get_heads())
    except Exception as exc:  # noqa: BLE001 — surface Alembic's exact failure
        return f"ScriptDirectory failed: {type(exc).__name__}: {exc}"

    if len(heads) != 1:
        return f"ScriptDirectory reports {len(heads)} heads: {', '.join(heads)}"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--versions-dir",
        type=Path,
        default=DEFAULT_VERSIONS_DIR,
        help=f"Alembic versions directory (default: {DEFAULT_VERSIONS_DIR})",
    )
    parser.add_argument(
        "--alembic-ini",
        type=Path,
        default=DEFAULT_ALEMBIC_INI,
        help=f"alembic.ini path for --with-alembic (default: {DEFAULT_ALEMBIC_INI})",
    )
    parser.add_argument(
        "--with-alembic",
        action="store_true",
        help="also load Alembic ScriptDirectory (catches KeyError on missing parents)",
    )
    parser.add_argument("--quiet", action="store_true", help="only print on failure")
    args = parser.parse_args()

    versions_dir: Path = args.versions_dir
    if not versions_dir.is_dir():
        print(f"[alembic-graph] versions dir not found: {versions_dir}", file=sys.stderr)
        return 2

    revisions = _collect_revisions(versions_dir)
    if not revisions:
        if not args.quiet:
            print("[alembic-graph] no migrations found — OK")
        return 0

    missing = _missing_parents(revisions)
    if missing:
        print(
            f"[alembic-graph] FAIL — {len(missing)} down_revision target(s) missing "
            f"across {len(revisions)} revision files. "
            "Do not partial-copy migration chains between checkouts.",
            file=sys.stderr,
        )
        for child, parent in missing:
            print(f"  MISSING PARENT: {parent}  (referenced by {child})", file=sys.stderr)
        return 2

    cycle = _find_cycle(revisions)
    if cycle is not None and not args.quiet:
        print(
            "[alembic-graph] WARN — cycle in revision metadata (legacy): "
            + " -> ".join(cycle),
            file=sys.stderr,
        )

    heads = _find_heads(revisions)
    if len(heads) == 0:
        print(
            "[alembic-graph] FAIL — 0 heads detected. Every revision is a parent; "
            "the graph has a cycle or the parser missed a file.",
            file=sys.stderr,
        )
        return 1

    if len(heads) > 1:
        print(
            f"[alembic-graph] FAIL — {len(heads)} heads across {len(revisions)} revisions. "
            "Create a merge-revision (`alembic merge heads -m 'merge heads'`) "
            "so `alembic upgrade head` stays deterministic.",
            file=sys.stderr,
        )
        for head in heads:
            print(f"  HEAD: {head}", file=sys.stderr)
        return 2

    if args.with_alembic:
        err = _check_alembic_script_map(
            alembic_ini=args.alembic_ini,
            versions_dir=versions_dir,
        )
        if err is not None:
            print(f"[alembic-graph] FAIL — {err}", file=sys.stderr)
            return 1

    if not args.quiet:
        extra = " (+ ScriptDirectory OK)" if args.with_alembic else ""
        print(
            f"[alembic-graph] OK — 1 head across {len(revisions)} revisions: "
            f"{heads[0]}{extra}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
