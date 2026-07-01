#!/usr/bin/env python3
"""
ADR-014 Phase 1–2 — merge-blocking guardrails for the **documents-db** Python module.

Scans ``backend/app/modules/documents/**/*.py`` for forbidden authorization patterns
(module-specific ACL forks, header-only owner gates, bypassing the resolver owner path,
resolver importing the HTTP router, owner-load calls outside the provider + resolver).

Usage (repo root):

    python3 backend/scripts/check_adr014_document_access.py

See: ``docs/devel/pr-checklist-adr014-document-access.md``.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DOC_MODULE_ROOT = BACKEND_ROOT / "app" / "modules" / "documents"
RESOLVER_FILE = "document_access_resolver.py"
OWNER_ACCESS_FILE = "candidate_document_owner_access.py"

_FILES_ALLOWED_OWNER_LOAD = frozenset({OWNER_ACCESS_FILE, RESOLVER_FILE})

_RESOLVER_ROUTER_IMPORT_MARKERS = (
    "documents.router",
    "from .router",
    "from backend.app.modules.documents import router",
)

_FORBIDDEN_SUBSTRINGS = (
    "ensure_candidate_own_company_scope",
    "ensure_hr_document_scope",
    "ensure_transport_document_scope",
    "ensure_finance_document_scope",
    "ensure_finance_documents_scope",
)

_FORBIDDEN_RE = (re.compile(r"\bensure_[a-z0-9_]+_document_scope\b"),)

_HEADER_AUTH_RE = (
    re.compile(r"""headers\s*\.\s*get\s*\(\s*['"]X-Own-Company-Id['"]""", re.IGNORECASE),
    re.compile(r"""headers\s*\[\s*['"]X-Own-Company-Id['"]\s*\]""", re.IGNORECASE),
    re.compile(r"""request\s*\.\s*headers\s*\.\s*get\s*\(\s*['"]X-Own-Company-Id['"]""", re.IGNORECASE),
)

_LEGACY_LOAD = "await _load_candidate_context"
_OWNER_LOAD_TOKEN = "load_candidate_documents_owner_context("


def _strip_python_comment(line: str) -> str:
    in_sq = in_dq = in_tsq = in_tdq = False
    escape = False
    out: list[str] = []
    i = 0
    while i < len(line):
        ch = line[i]
        if in_tdq:
            if ch == '"' and line[i : i + 3] == '"""' and not escape:
                in_tdq = False
                i += 3
                continue
        elif in_tsq:
            if ch == "'" and line[i : i + 3] == "'''" and not escape:
                in_tsq = False
                i += 3
                continue
        elif in_dq:
            if ch == "\\" and not escape:
                escape = True
                i += 1
                continue
            if ch == '"' and not escape:
                in_dq = False
                i += 1
                continue
            escape = False
        elif in_sq:
            if ch == "\\" and not escape:
                escape = True
                i += 1
                continue
            if ch == "'" and not escape:
                in_sq = False
                i += 1
                continue
            escape = False
        else:
            if ch == "#":
                break
            if ch == '"' and line[i : i + 3] == '"""':
                in_tdq = True
                i += 3
                continue
            if ch == "'" and line[i : i + 3] == "'''":
                in_tsq = True
                i += 3
                continue
            if ch == '"':
                in_dq = True
                i += 1
                continue
            if ch == "'":
                in_sq = True
                i += 1
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def _check_file(path: Path) -> list[str]:
    rel = path.relative_to(BACKEND_ROOT)
    bad: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"{rel}: <read error: {exc}>"]

    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = _strip_python_comment(raw).rstrip()
        stripped = line.lstrip()
        if not stripped:
            continue

        if path.name == RESOLVER_FILE:
            for marker in _RESOLVER_ROUTER_IMPORT_MARKERS:
                if marker in line:
                    bad.append(
                        f"{rel}:{lineno}: DocumentAccessResolver must not import the HTTP router "
                        f"({marker!r}); use candidate_document_owner_access instead"
                    )

        for sub in _FORBIDDEN_SUBSTRINGS:
            if sub in line:
                bad.append(f"{rel}:{lineno}: forbidden substring {sub!r}")

        for rx in _FORBIDDEN_RE:
            if rx.search(line):
                bad.append(f"{rel}:{lineno}: forbidden pattern {rx.pattern!r}: {line.strip()!r}")

        for rx in _HEADER_AUTH_RE:
            if rx.search(line):
                bad.append(
                    f"{rel}:{lineno}: direct X-Own-Company-Id header access — use "
                    f"Depends(resolve_active_own_company_id_optional) + resolver workspace leg; "
                    f"matched {rx.pattern!r}"
                )

        if _LEGACY_LOAD in line:
            bad.append(
                f"{rel}:{lineno}: {_LEGACY_LOAD!r} removed in Phase 2 — use "
                f"load_candidate_documents_owner_context from candidate_document_owner_access "
                f"via DocumentAccessResolver only"
            )

        if _OWNER_LOAD_TOKEN in line and path.name not in _FILES_ALLOWED_OWNER_LOAD:
            bad.append(
                f"{rel}:{lineno}: load_candidate_documents_owner_context must only be invoked "
                f"from {sorted(_FILES_ALLOWED_OWNER_LOAD)} (not {path.name!r})"
            )

        if "await load_candidate_documents_owner_context" in line and path.name not in _FILES_ALLOWED_OWNER_LOAD:
            bad.append(
                f"{rel}:{lineno}: await load_candidate_documents_owner_context — forbidden outside "
                f"{sorted(_FILES_ALLOWED_OWNER_LOAD)}"
            )

    return bad


def main() -> int:
    if not DOC_MODULE_ROOT.is_dir():
        print(f"Expected documents module at {DOC_MODULE_ROOT}", file=sys.stderr)
        return 1

    failures: list[str] = []
    for path in sorted(DOC_MODULE_ROOT.rglob("*.py")):
        failures.extend(_check_file(path))

    if failures:
        print(
            "ADR-014 document access guardrails FAILED (merge blocker).\n\n"
            "Forbidden pattern(s) under app/modules/documents:\n\n"
            + "\n".join(failures),
            file=sys.stderr,
        )
        return 1

    print("ADR-014 document access guardrails passed (app/modules/documents).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
