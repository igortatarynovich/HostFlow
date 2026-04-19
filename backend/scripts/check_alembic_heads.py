#!/usr/bin/env python3
"""
Fail fast if `backend/alembic/versions/` contains more than one head.

Rationale (docs/HOSTFLOW_AUDIT_AND_PLAN.md, Phase 0):
    Multiple Alembic heads make `alembic upgrade head` non-deterministic
    (it will either fail with "Multiple head revisions are present" or upgrade
    an unpredictable branch). CI must catch a second head the moment it is
    introduced, not during deploy.

This check parses migration files directly — no database required. It handles:
    * single-line `down_revision = "xxxx"`
    * single-line `down_revision = None`
    * multi-line tuples: `down_revision: ... = (\n    "a",\n    "b",\n)`

Exit codes:
    0 — exactly one head (or zero migrations)
    1 — zero heads (every revision is a parent — impossible in a sane graph)
    2 — more than one head (CI failure; add a merge-revision)

Usage:
    python3 backend/scripts/check_alembic_heads.py
    python3 backend/scripts/check_alembic_heads.py --versions-dir path/to/versions
    python3 backend/scripts/check_alembic_heads.py --quiet    # only print on failure
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VERSIONS_DIR = BACKEND_ROOT / "alembic" / "versions"

# Matches `revision = "..."` or `revision: <annot> = "..."`.
_REVISION_RE = re.compile(
    r"^revision(?:\s*:\s*[^=\n]*)?\s*=\s*[\"']([^\"']+)[\"']",
    re.MULTILINE,
)
# Greedy-but-bounded capture for down_revision: starts at `=`, ends at a newline
# that introduces a new top-level identifier (branch_labels / depends_on / def / class).
_DOWN_REVISION_RE = re.compile(
    r"^down_revision(?:\s*:\s*[^=\n]*)?\s*=\s*"
    r"(?P<body>.+?)"
    r"(?=\n(?:branch_labels|depends_on|def |class |@)\b|\Z)",
    re.MULTILINE | re.DOTALL,
)


def _parse_down_revision(body: str) -> str | tuple[str, ...] | None:
    """Parse a `down_revision = ...` RHS into None / str / tuple[str,...]."""
    stripped = body.strip()
    if not stripped or stripped.startswith("None"):
        return None
    quoted = re.findall(r"[\"']([^\"']+)[\"']", stripped)
    if not quoted:
        return None
    if len(quoted) == 1 and not stripped.startswith("("):
        return quoted[0]
    return tuple(quoted)


def _collect_revisions(versions_dir: Path) -> dict[str, str | tuple[str, ...] | None]:
    """Return {revision_id: down_revision_value} parsed from every *.py in the dir."""
    revisions: dict[str, str | tuple[str, ...] | None] = {}
    for path in sorted(versions_dir.glob("*.py")):
        if path.name.startswith("__"):
            continue
        try:
            src = path.read_text(encoding="utf-8")
        except OSError:
            continue
        rev_match = _REVISION_RE.search(src)
        if not rev_match:
            continue
        rev_id = rev_match.group(1)
        down_match = _DOWN_REVISION_RE.search(src)
        down_value = _parse_down_revision(down_match.group("body")) if down_match else None
        revisions[rev_id] = down_value
    return revisions


def _find_heads(revisions: dict[str, str | tuple[str, ...] | None]) -> list[str]:
    """A head is a revision no other revision points at via down_revision."""
    parents: set[str] = set()
    for down in revisions.values():
        if down is None:
            continue
        if isinstance(down, tuple):
            parents.update(down)
        else:
            parents.add(down)
    return sorted(rev for rev in revisions if rev not in parents)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--versions-dir",
        type=Path,
        default=DEFAULT_VERSIONS_DIR,
        help=f"Alembic versions directory (default: {DEFAULT_VERSIONS_DIR})",
    )
    parser.add_argument("--quiet", action="store_true", help="only print on failure")
    args = parser.parse_args()

    versions_dir: Path = args.versions_dir
    if not versions_dir.is_dir():
        print(f"[alembic-heads] versions dir not found: {versions_dir}", file=sys.stderr)
        return 2

    revisions = _collect_revisions(versions_dir)
    heads = _find_heads(revisions)

    if not revisions:
        if not args.quiet:
            print("[alembic-heads] no migrations found — OK")
        return 0

    if len(heads) == 1:
        if not args.quiet:
            print(f"[alembic-heads] OK — 1 head across {len(revisions)} revisions: {heads[0]}")
        return 0

    if len(heads) == 0:
        print(
            "[alembic-heads] FAIL — 0 heads detected. Every revision is a parent; "
            "the graph has a cycle or the parser missed a file.",
            file=sys.stderr,
        )
        return 1

    print(
        f"[alembic-heads] FAIL — {len(heads)} heads across {len(revisions)} revisions. "
        "Create a merge-revision (`alembic merge heads -m 'merge heads'`) "
        "so `alembic upgrade head` stays deterministic.",
        file=sys.stderr,
    )
    for head in heads:
        print(f"  HEAD: {head}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
