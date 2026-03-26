#!/usr/bin/env python3
"""
Fail if new SPA-style string literals `/app/...` appear outside the allowlist.

Filesystem container paths (Path("/app/public"), etc.) live in a few known files.
All user-facing SPA routes must go through **app/constants/spa_paths.py**
(generated from **shared/crm_app_paths.json** — docs/SSOT.md §1.6).

Usage (from repo root, with PYTHONPATH=backend):
  python3 backend/scripts/check_spa_path_literals.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = BACKEND_ROOT / "app"

# Only **app/constants/spa_paths.py** may define arbitrary `/app/*` URL strings.
SKIP_FILES = {
    APP_ROOT / "constants" / "spa_paths.py",
}

# Known **filesystem** paths inside containers / dev tooling (not SPA routes).
SKIP_PATH_PREFIXES = (
    "/app/public",
    "/app/docs",
    "/app/samples",
    "/app/document_specs",
    "/app/templates",
    "/app/alembic",
)


def _walk_strings(path: Path) -> list[tuple[int, str]]:
    src = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(src, filename=str(path))
    except SyntaxError as e:
        return [(e.lineno or 1, f"<syntax error: {e}>")]

    out: list[tuple[int, str]] = []

    class V(ast.NodeVisitor):
        def visit_Constant(self, node: ast.Constant) -> None:
            if isinstance(node.value, str) and node.value.startswith("/app/"):
                out.append((node.lineno, node.value))
            self.generic_visit(node)

    V().visit(tree)
    return out


def main() -> int:
    bad: list[str] = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        if path in SKIP_FILES:
            continue
        for lineno, value in _walk_strings(path):
            if any(value.startswith(p) for p in SKIP_PATH_PREFIXES):
                continue
            rel = path.relative_to(BACKEND_ROOT)
            bad.append(f"  {rel}:{lineno}: {value!r}")

    if bad:
        print(
            "Disallowed SPA `/app/...` string literal(s) — use app/constants/spa_paths.py:\n"
            + "\n".join(bad),
            file=sys.stderr,
        )
        return 1
    print("SPA path literal check passed (app/).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
