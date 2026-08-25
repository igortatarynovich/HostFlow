#!/usr/bin/env python3
"""
GIT-IMPORT-INTEGRITY — fail if local TS/TSX imports do not resolve to existing files.

Catches the deployHosts/csrf class of failures: code imports a module that is
missing from the tree (or uses a broken relative path), while other CI gates
still pass.

Resolves:
  * relative imports (./ ../)
  * aliases from vite.config.ts + tsconfig.app.json (@/, @api/, @shared/, …)

Skips bare package imports (react, axios, …).

Usage (repo root or hostflow-frontend):
  python3 hostflow-frontend/scripts/check_ts_import_integrity.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = FRONTEND_ROOT.parent
SRC_ROOT = FRONTEND_ROOT / "src"

IMPORT_RE = re.compile(
    r"""(?<![.\w])(?:import|export)\s+(?:type\s+)?(?:[^'"\n]+?\s+from\s+)?['"]([^'"]+)['"]"""
    r"""|import\s*\(\s*['"]([^'"]+)['"]\s*\)"""
)

# File extensions tried when the import omits an extension (Vite/TS bundler mode).
FILE_EXTS = (
    "",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".json",
    ".css",
    ".scss",
    ".svg",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
)


def _strip_json_comments(raw: str) -> str:
    raw = re.sub(r"/\*.*?\*/", "", raw, flags=re.S)
    raw = re.sub(r"//.*?$", "", raw, flags=re.M)
    return raw


def _load_aliases() -> dict[str, Path]:
    """Map alias prefix (with trailing / when applicable) → filesystem root."""
    aliases: dict[str, Path] = {}

    vite = (FRONTEND_ROOT / "vite.config.ts").read_text(encoding="utf-8")
    for key, rel in re.findall(
        r"""['"](@[\w/-]*)['"]\s*:\s*path\.resolve\(__dirname\s*,\s*['"]([^'"]+)['"]\)""",
        vite,
    ):
        aliases[key] = (FRONTEND_ROOT / rel).resolve()

    tsconfig_path = FRONTEND_ROOT / "tsconfig.app.json"
    if tsconfig_path.is_file():
        data = _strip_json_comments(tsconfig_path.read_text(encoding="utf-8"))
        # Minimal parse of "paths" — supports "@/*" and "@shared/*"
        for key, targets in re.findall(
            r""""(@[\w/-]*\*?)\"\s*:\s*\[\s*\"([^\"]+)\"\s*\]""",
            data,
        ):
            target = targets.replace("/*", "").rstrip("/") or "."
            prefix = key.replace("/*", "")
            aliases.setdefault(prefix, (FRONTEND_ROOT / target).resolve())

    return aliases


def _module_exists(target: Path) -> bool:
    if target.is_file():
        return True
    for ext in FILE_EXTS:
        candidate = Path(str(target) + ext) if ext else target
        if candidate.is_file():
            return True
    if target.is_dir():
        for name in ("index.ts", "index.tsx", "index.js", "index.jsx"):
            if (target / name).is_file():
                return True
    return False


def _resolve(from_file: Path, spec: str, aliases: dict[str, Path]) -> Path | None:
    if not spec or spec.startswith(("http:", "https:", "data:", "virtual:")):
        return None
    if spec.startswith("."):
        return (from_file.parent / spec).resolve()

    # Longest alias prefix wins (@api before @)
    for prefix in sorted(aliases, key=len, reverse=True):
        if spec == prefix or spec.startswith(prefix + "/"):
            rest = spec[len(prefix) :].lstrip("/")
            return (aliases[prefix] / rest).resolve() if rest else aliases[prefix]
        # tsconfig style @api/* matched as prefix @api already

    # Bare package / node builtin — out of scope
    return None


def main() -> int:
    if not SRC_ROOT.is_dir():
        print(f"GIT-IMPORT-INTEGRITY: missing {SRC_ROOT}", file=sys.stderr)
        return 2

    aliases = _load_aliases()
    missing: list[str] = []
    checked = 0

    files = sorted(list(SRC_ROOT.rglob("*.ts")) + list(SRC_ROOT.rglob("*.tsx")))
    for path in files:
        if "node_modules" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in IMPORT_RE.finditer(text):
            spec = match.group(1) or match.group(2)
            if not spec:
                continue
            target = _resolve(path, spec, aliases)
            if target is None:
                continue
            checked += 1
            if not _module_exists(target):
                try:
                    rel_target = target.relative_to(REPO_ROOT)
                except ValueError:
                    rel_target = target
                rel_file = path.relative_to(FRONTEND_ROOT)
                missing.append(f"  {rel_file}: {spec!r} → missing {rel_target}")

    if missing:
        # Deduplicate while preserving order
        seen: set[str] = set()
        uniq: list[str] = []
        for row in missing:
            if row not in seen:
                seen.add(row)
                uniq.append(row)
        print(
            "GIT-IMPORT-INTEGRITY FAIL — unresolved local TS/TSX import(s):\n"
            + "\n".join(uniq),
            file=sys.stderr,
        )
        print(
            f"(checked {checked} local imports; {len(uniq)} missing)",
            file=sys.stderr,
        )
        return 1

    print(
        f"GIT-IMPORT-INTEGRITY OK — {checked} local imports resolved "
        f"({len(aliases)} aliases: {', '.join(sorted(aliases))})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
