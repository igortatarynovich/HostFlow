#!/usr/bin/env python3
"""
Merge gate: keep CRM tenant DB bind fail-closed.

Checks:
1. ``get_db_with_tenant`` in ``backend/app/db/deps.py`` must depend on
   ``get_current_user`` (not ``get_current_user_optional``).
2. Every ``Depends(get_db_with_tenant_public)`` call site must be listed in
   ``scripts/security/tenant_bind_public_allowlist.txt`` (signed webhooks only).

Run from repo root::

    python3 scripts/security/check_tenant_bind_auth.py
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEPS_FILE = REPO_ROOT / "backend" / "app" / "db" / "deps.py"
SCAN_ROOT = REPO_ROOT / "backend" / "app"
ALLOWLIST_FILE = REPO_ROOT / "scripts" / "security" / "tenant_bind_public_allowlist.txt"

PUBLIC_DEP = re.compile(r"Depends\(\s*get_db_with_tenant_public\s*\)")


def _load_allowlist() -> set[str]:
    if not ALLOWLIST_FILE.is_file():
        print(f"ERROR: missing allowlist file: {ALLOWLIST_FILE}", file=sys.stderr)
        sys.exit(2)
    out: set[str] = set()
    for raw in ALLOWLIST_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        out.add(line.replace("\\", "/"))
    return out


def _check_get_db_with_tenant_fail_closed() -> list[str]:
    errors: list[str] = []
    if not DEPS_FILE.is_file():
        return [f"missing {DEPS_FILE.relative_to(REPO_ROOT).as_posix()}"]
    src = DEPS_FILE.read_text(encoding="utf-8")
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        return [f"deps.py parse error: {exc}"]

    fn: ast.AsyncFunctionDef | ast.FunctionDef | None = None
    for node in tree.body:
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)) and node.name == "get_db_with_tenant":
            fn = node
            break
    if fn is None:
        return ["get_db_with_tenant() not found in backend/app/db/deps.py"]

    # Reconstruct defaults text for the ``user`` parameter.
    args = fn.args
    defaults = list(args.defaults)
    posonly = list(args.posonlyargs)
    plain = list(args.args)
    all_pos = posonly + plain
    # Map last N args to defaults
    default_map: dict[str, str] = {}
    if defaults:
        paired = all_pos[-len(defaults) :]
        for arg, default in zip(paired, defaults):
            default_map[arg.arg] = ast.get_source_segment(src, default) or ast.dump(default)

    user_default = default_map.get("user", "")
    if "get_current_user_optional" in user_default:
        errors.append(
            "get_db_with_tenant must not use get_current_user_optional "
            "(anonymous X-Tenant-Id bind is forbidden)"
        )
    if "get_current_user" not in user_default or "get_current_user_optional" in user_default:
        if "Depends(get_current_user)" not in user_default and "Depends( get_current_user" not in user_default:
            # Allow Depends(get_current_user) with whitespace variants via regex
            if not re.search(r"Depends\(\s*get_current_user\s*\)", user_default):
                errors.append(
                    "get_db_with_tenant(user=...) must be Depends(get_current_user); "
                    f"got: {user_default!r}"
                )
    return errors


def _check_public_allowlist(allow: set[str]) -> list[str]:
    violations: list[str] = []
    seen: set[str] = set()
    for path in sorted(SCAN_ROOT.rglob("*.py")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            return [f"ERROR reading {rel}: {exc}"]
        if "get_db_with_tenant_public" not in text:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if not PUBLIC_DEP.search(line) and "get_db_with_tenant_public" not in line:
                continue
            # Definition / import lines are fine.
            stripped = line.strip()
            if stripped.startswith("async def get_db_with_tenant_public") or stripped.startswith(
                "def get_db_with_tenant_public"
            ):
                continue
            if "import" in stripped and "get_db_with_tenant_public" in stripped:
                continue
            if "get_db_with_tenant_public" not in stripped:
                continue
            # Only flag Depends(...) / assignment usages as call sites.
            if "Depends(" not in stripped and "= get_db_with_tenant_public" not in stripped:
                continue
            key = f"{rel}:{lineno}"
            seen.add(rel)
            if rel not in allow:
                violations.append(f"{key}: {stripped}")
    # Allowlist entries that no longer exist → fail (drift).
    missing = sorted(allow - seen)
    for rel in missing:
        # Allow listing a file even if Depends spans multiple lines — re-scan file presence.
        path = REPO_ROOT / rel
        if not path.is_file():
            violations.append(f"allowlist entry missing on disk: {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        if "get_db_with_tenant_public" not in text:
            violations.append(f"allowlist entry unused (no get_db_with_tenant_public): {rel}")
    return violations


def main() -> int:
    allow = _load_allowlist()
    errors = _check_get_db_with_tenant_fail_closed()
    errors.extend(_check_public_allowlist(allow))
    if errors:
        print(
            "Tenant bind auth gate failed.\n"
            "CRM routes must use fail-closed get_db_with_tenant (authenticated).\n"
            "Anonymous signed webhooks must use get_db_with_tenant_public and be allowlisted.\n"
            "See docs/security/runtime-roadmap.md\n",
            file=sys.stderr,
        )
        for err in errors:
            print(f"  {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
