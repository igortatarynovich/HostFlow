#!/usr/bin/env python3
"""If PR touches security-sensitive code paths, require docs/security updates."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import PurePosixPath


def _git_diff_names(base: str, head: str) -> list[str]:
    out = subprocess.check_output(
        ["git", "diff", "--name-only", base, head],
        cwd=os.environ.get("GITHUB_WORKSPACE") or ".",
        text=True,
    )
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def _is_security_doc(path: str) -> bool:
    p = PurePosixPath(path)
    parts = p.parts
    if len(parts) >= 2 and parts[0] == "docs" and parts[1] == "security":
        return True
    return path == ".github/workflows/security-gates.yml"


def _is_sensitive(path: str) -> bool:
    p = path.replace("\\", "/")
    sensitive_prefixes = (
        "backend/app/auth/",
        "backend/app/api/public/",
        "backend/app/api/v1/candidate",
        "backend/app/api/v1/client",
        "backend/app/api/v1/candidates",
        "backend/app/api/v1/settings",
        "backend/app/api/v1/platform",
        "backend/app/core/security",
        "backend/app/db/deps.py",
        "backend/app/db/session",
        "backend/alembic/versions/",
        "backend/app/modules/documents/",
        "backend/app/modules/leads/webhook",
        "backend/app/modules/leads/inbound_public",
        "backend/app/services/billing_restrictions",
        "hostflow-frontend/src/pages/public/",
        "hostflow-frontend/src/modules/candidates",
    )
    if any(p.startswith(pref) for pref in sensitive_prefixes):
        return True
    if "/webhook" in p and p.startswith("backend/app/"):
        return True
    if "/export" in p and p.startswith("backend/app/api/"):
        return True
    if "handoff" in p.lower() and (p.startswith("backend/app/") or p.startswith("hostflow-frontend/")):
        return True
    if "automation" in p.lower() and "backend/app/" in p:
        return True
    return False


def main() -> int:
    base = os.environ.get("BASE_SHA", "").strip()
    head = os.environ.get("HEAD_SHA", "").strip()
    if not base or not head:
        print("threat_model_gate: BASE_SHA/HEAD_SHA not set; skipping", file=sys.stderr)
        return 0

    changed = _git_diff_names(base, head)
    sensitive = any(_is_sensitive(f) for f in changed)
    doc_touch = any(_is_security_doc(f) for f in changed)

    if sensitive and not doc_touch:
        print(
            "This PR modifies security-sensitive paths but does not update anything under "
            "`docs/security/` (or `security-gates.yml`).\n\n"
            "Update the relevant threat model in `docs/security/threat-models/` or "
            "`docs/security/security-ssot.md` / `security-review-checklist.md`.\n\n"
            "Changed files:\n  - "
            + "\n  - ".join(changed[:200])
            + ("\n  …" if len(changed) > 200 else ""),
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
