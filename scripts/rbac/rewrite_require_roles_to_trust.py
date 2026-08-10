#!/usr/bin/env python3
"""Rewrite require_roles(job/portal…) call sites to ADR-036 trust deps.

Classification:
  - only admin/owner/superadmin → require_trust_admin()
  - includes viewer or client_* → require_trust_read()
  - otherwise operational mutate → require_trust_write()

Skips:
  - require_roles(*SOME_CONSTANT) star-expansions (update constants separately)
  - already-trust-only lists (administrator/employee/viewer only)
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "backend" / "app"

ADMIN = {
    "administrator",
    "admin",
    "owner",
    "superadmin",
    "Role.administrator",
    "Role.admin",
    "Role.owner",
    "Role.superadmin",
    "AuthRole.administrator",
    "AuthRole.admin",
    "AuthRole.superadmin",
    "UserRole.administrator",
    "UserRole.admin",
    "UserRole.superadmin",
}
VIEWERISH = {
    "viewer",
    "user",
    "client_manager",
    "client_processor",
    "client",
    "processor",
    "Role.viewer",
    "Role.client_manager",
    "Role.client_processor",
    "AuthRole.viewer",
    "AuthRole.client_manager",
    "AuthRole.client_processor",
    "UserRole.viewer",
    "UserRole.client_manager",
    "UserRole.client_processor",
}
TRUST_ONLY = {
    "administrator",
    "employee",
    "viewer",
    "superadmin",
    "Role.administrator",
    "Role.employee",
    "Role.viewer",
    "Role.superadmin",
    "AuthRole.administrator",
    "AuthRole.employee",
    "AuthRole.viewer",
    "AuthRole.superadmin",
}

CALL_RE = re.compile(
    r"require_roles\((?P<args>[^)*]+?)\)",
    re.MULTILINE,
)


def _role_tokens(args: str) -> list[str]:
    parts = []
    for raw in args.split(","):
        tok = raw.strip()
        if not tok or tok.startswith("*"):
            continue
        # Role.x / "x" / 'x'
        m = re.match(r"^(?:Role|AuthRole|UserRole)\.(\w+)$", tok)
        if m:
            parts.append(f"Role.{m.group(1)}")
            continue
        m = re.match(r"^['\"](\w+)['\"]$", tok)
        if m:
            parts.append(m.group(1))
            continue
        parts.append(tok)
    return parts


def classify(tokens: list[str]) -> str | None:
    if not tokens:
        return None
    if any(t.startswith("*") for t in tokens):
        return None
    # Unknown non-role identifiers → skip
    for t in tokens:
        if t.startswith("Role.") or t in ADMIN | VIEWERISH | TRUST_ONLY:
            continue
        if re.fullmatch(r"\w+", t) and t in {
            "administrator",
            "employee",
            "viewer",
            "recruiter",
            "supervisor",
            "manager",
            "hr_officer",
            "compliance_officer",
            "client_manager",
            "client_processor",
            "admin",
            "owner",
            "superadmin",
        }:
            continue
        return None

    names = set()
    for t in tokens:
        if t.startswith("Role."):
            names.add(t.split(".", 1)[1])
        else:
            names.add(t)

    if names <= {"administrator", "admin", "owner", "superadmin"}:
        return "admin"
    if names <= {"administrator", "employee", "viewer", "superadmin"}:
        return None  # already trust
    if names & {"viewer", "user", "client_manager", "client_processor", "client", "processor"}:
        return "read"
    return "write"


def rewrite_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    original = text

    def repl(match: re.Match[str]) -> str:
        args = match.group("args")
        if "*" in args:
            return match.group(0)
        tokens = _role_tokens(args)
        kind = classify(tokens)
        if kind == "admin":
            return "require_trust_admin()"
        if kind == "read":
            return "require_trust_read()"
        if kind == "write":
            return "require_trust_write()"
        return match.group(0)

    text = CALL_RE.sub(repl, text)
    if text == original:
        return False

    # Ensure import for trust deps when we introduced require_trust_*
    needs = []
    for name in ("require_trust_read", "require_trust_write", "require_trust_admin"):
        if name in text and f"import {name}" not in text and f"{name}," not in text.split("trust_role_deps")[0] if "trust_role_deps" in text else True:
            if name in text and "trust_role_deps" not in text:
                needs.append(name)
            elif name in text and "trust_role_deps" in text:
                # may already import some — fix below
                pass

    if any(n in text for n in ("require_trust_read", "require_trust_write", "require_trust_admin")):
        if "trust_role_deps" not in text:
            import_line = (
                "from backend.app.auth.trust_role_deps import "
                "require_trust_admin, require_trust_read, require_trust_write\n"
            )
            # Prefer after deps import
            if "from backend.app.auth.deps import" in text:
                text = text.replace(
                    "from backend.app.auth.deps import",
                    import_line + "from backend.app.auth.deps import",
                    1,
                )
            else:
                text = import_line + text
        else:
            # Expand existing import if incomplete
            m = re.search(
                r"from backend\.app\.auth\.trust_role_deps import ([^\n]+)",
                text,
            )
            if m:
                existing = {x.strip() for x in m.group(1).split(",")}
                for n in ("require_trust_admin", "require_trust_read", "require_trust_write"):
                    if n in text:
                        existing.add(n)
                new_imp = (
                    "from backend.app.auth.trust_role_deps import "
                    + ", ".join(sorted(existing))
                )
                text = text[: m.start()] + new_imp + text[m.end() :]

    path.write_text(text, encoding="utf-8")
    return True


def main() -> int:
    changed = 0
    for path in sorted(APP.rglob("*.py")):
        if path.name == "trust_role_deps.py":
            continue
        if rewrite_file(path):
            changed += 1
            print(path.relative_to(ROOT))
    print(f"rewrote {changed} files", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
