#!/usr/bin/env python3
"""Scan public marketing surfaces for HostFlow-as-CRM categorization.

Groups:
  A) UNWANTED — product identity / CTA copy that labels HostFlow as a CRM/ATS-CRM
  B) ALLOWED_COMPARISON — generic CRM vs ATS discussion and sync-with-another-CRM
  C) INTENTIONAL_SEO_KEYWORDS — ATS-for-* / Applicant Tracking System Europe titles

Exit 1 if group A has matches outside the inline allowlist.
Prefer exit 0 when A is empty.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_SRC = REPO_ROOT / "hostflow-frontend" / "src"

# Paths relative to hostflow-frontend/src
PUBLIC_GLOBS = (
    "pages/public/**/*",
    "content/seo/**/*",
    "content/faq/**/*",
)
EXTRA_FILES = (
    "pages/SignupPage.tsx",
)
I18N_FILES = (
    "i18n/en.json",
    "i18n/ru.json",
    "i18n/pl.json",
)

# Inline allowlist: exact substrings that look like A but are intentional leftovers
# (path relative to hostflow-frontend/src, substring). Prefer keeping this empty.
ALLOWLIST: list[tuple[str, str]] = []

UNWANTED_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("HostFlow CRM", re.compile(r"HostFlow\s+CRM", re.I)),
    ("CRM for ", re.compile(r"\bCRM\s+for\s+", re.I)),
    ("Recruitment CRM with", re.compile(r"Recruitment\s+CRM\s+with", re.I)),
    ("Candidate Pipeline CRM", re.compile(r"Candidate\s+Pipeline\s+CRM", re.I)),
    ("operational CRM", re.compile(r"\boperational\s+CRM\b", re.I)),
    ("ATS/CRM HostFlow label", re.compile(r"\bATS\s*/\s*CRM\b", re.I)),
    ("Create your CRM workspace", re.compile(r"Create\s+your\s+CRM\s+workspace", re.I)),
    ("Click through the CRM", re.compile(r"Click\s+through\s+the\s+CRM", re.I)),
    ("Operations CRM", re.compile(r"\bOperations\s+CRM\b", re.I)),
    ("one CRM flow", re.compile(r"\bone\s+CRM\s+flow\b", re.I)),
    ("Driver recruitment CRM", re.compile(r"Driver\s+recruitment\s+CRM", re.I)),
    ("Transport companies CRM", re.compile(r"Transport\s+companies\s+CRM", re.I)),
    ("CRM-first as identity", re.compile(r"\bCRM-first\b", re.I)),
    ("switch to an operational CRM", re.compile(r"switch\s+to\s+an\s+operational\s+CRM", re.I)),
    ("Compare HostFlow CRM", re.compile(r"Compare\s+HostFlow\s+CRM", re.I)),
    ("pipeline CRM", re.compile(r"\bpipeline\s+CRM\b", re.I)),
    ("RU CRM workspace", re.compile(r"рабочее\s+пространство\s+CRM", re.I)),
    ("PL CRM workspace", re.compile(r"przestrzeń\s+CRM", re.I)),
    ("RU CRM HostFlow", re.compile(r"CRM\s+HostFlow", re.I)),
    ("PL CRM HostFlow", re.compile(r"CRM\s+HostFlow", re.I)),
    ("RU CRM-воронка", re.compile(r"CRM-воронк", re.I)),
    ("PL CRM pipeline title", re.compile(r"\bCRM\s+pipeline\s+kandydat", re.I)),
    ("RU CRM для (product)", re.compile(r"\bCRM\s+для\s+", re.I)),
    ("PL CRM dla (product)", re.compile(r"\bCRM\s+dla\s+", re.I)),
]

ALLOWED_COMPARISON_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Recruitment CRM vs ATS", re.compile(r"Recruitment\s+CRM\s+vs\s+ATS", re.I)),
    ("sync with another CRM", re.compile(r"sync\s+with\s+another\s+CRM", re.I)),
    ("another CRM (FAQ)", re.compile(r"(другой|innym)\s+CRM", re.I)),
    ("generic CRM and ATS coexist", re.compile(r"Can\s+CRM\s+and\s+ATS\s+coexist", re.I)),
    ("use CRM when… (comparison)", re.compile(r"Use\s+CRM\s+when", re.I)),
    ("CRM for operations (generic)", re.compile(r"use\s+CRM\s+for\s+operations", re.I)),
    ("CRM vs ATS related label", re.compile(r"\bCRM\s+vs\s+ATS\b", re.I)),
    ("Do we need ATS plus CRM?", re.compile(r"ATS\s+plus\s+CRM", re.I)),
    ("Is HostFlow an ATS or a CRM?", re.compile(r"Is\s+HostFlow\s+an\s+ATS\s+or\s+a\s+CRM", re.I)),
    ("look for in a CRM or ATS", re.compile(r"look\s+for\s+in\s+a\s+CRM\s+or\s+ATS", re.I)),
    ("overlaps with ATS and CRM", re.compile(r"overlaps\s+with\s+ATS\s+and\s+CRM", re.I)),
]

INTENTIONAL_SEO_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("ATS for Drivers", re.compile(r"ATS\s+for\s+Drivers", re.I)),
    ("ATS for Transport", re.compile(r"ATS\s+for\s+Transport", re.I)),
    ("ATS for transport (label)", re.compile(r"ATS\s+for\s+transport", re.I)),
    ("ATS for drivers (label)", re.compile(r"ATS\s+for\s+drivers", re.I)),
    ("Applicant Tracking System Europe", re.compile(r"Applicant\s+Tracking\s+System\s+(for\s+)?Europe", re.I)),
]


@dataclass(frozen=True)
class Hit:
    group: str
    label: str
    path: str
    line: int
    snippet: str


def _iter_public_files() -> list[Path]:
    files: list[Path] = []
    for pattern in PUBLIC_GLOBS:
        files.extend(FRONTEND_SRC.glob(pattern))
    for rel in EXTRA_FILES:
        files.append(FRONTEND_SRC / rel)
    for rel in I18N_FILES:
        files.append(FRONTEND_SRC / rel)
    out: list[Path] = []
    seen: set[Path] = set()
    for path in files:
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".ts", ".tsx", ".json", ".md"}:
            continue
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        out.append(path)
    return sorted(out)


def _i18n_public_slices(data: dict) -> str:
    """Only scan public.marketing + signup/demo strings (not app-internal CRM UI)."""
    chunks: list[str] = []
    public = data.get("public") or {}
    marketing = public.get("marketing")
    if marketing is not None:
        chunks.append(json.dumps(marketing, ensure_ascii=False, indent=2))
    demo = public.get("demo")
    if demo is not None:
        chunks.append(json.dumps(demo, ensure_ascii=False, indent=2))
    app = data.get("app") or {}
    signup = app.get("signup")
    if signup is not None:
        chunks.append(json.dumps({"app.signup": signup}, ensure_ascii=False, indent=2))
    seo_signup = ((app.get("seo") or {}).get("signup"))
    if seo_signup is not None:
        chunks.append(json.dumps({"app.seo.signup": seo_signup}, ensure_ascii=False, indent=2))
    return "\n".join(chunks)


def _line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _snippet(text: str, start: int, end: int, radius: int = 60) -> str:
    lo = max(0, start - radius)
    hi = min(len(text), end + radius)
    return " ".join(text[lo:hi].split())


def _is_allowlisted(rel: str, snippet: str) -> bool:
    for path_suffix, needle in ALLOWLIST:
        if rel.endswith(path_suffix) and needle in snippet:
            return True
    return False


def scan() -> list[Hit]:
    hits: list[Hit] = []
    for path in _iter_public_files():
        rel = str(path.relative_to(FRONTEND_SRC))
        raw = path.read_text(encoding="utf-8", errors="replace")
        if path.suffix.lower() == ".json":
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            text = _i18n_public_slices(data)
            if not text:
                continue
        else:
            text = raw

        for group, patterns in (
            ("A", UNWANTED_PATTERNS),
            ("B", ALLOWED_COMPARISON_PATTERNS),
            ("C", INTENTIONAL_SEO_PATTERNS),
        ):
            for label, pattern in patterns:
                for match in pattern.finditer(text):
                    snippet = _snippet(text, match.start(), match.end())
                    if group == "A" and _is_allowlisted(rel, snippet):
                        continue
                    # Generic comparison talk: "CRM for/для/dla operations" — not HostFlow product SEO.
                    if group == "A" and label in {
                        "CRM for ",
                        "RU CRM для (product)",
                        "PL CRM dla (product)",
                    }:
                        tail = match.group(0) + text[match.end() : match.end() + 32]
                        if re.search(
                            r"CRM\s+(for|для|dla)\s+(operations|операций|operacji)\b",
                            tail,
                            re.I,
                        ):
                            continue
                    hits.append(
                        Hit(
                            group=group,
                            label=label,
                            path=rel,
                            line=_line_of(text, match.start()),
                            snippet=snippet,
                        )
                    )
    return hits


def _print_group(title: str, group: str, hits: list[Hit]) -> None:
    subset = [h for h in hits if h.group == group]
    print(f"\n=== {title} ({len(subset)}) ===")
    if not subset:
        print("(none)")
        return
    for hit in subset:
        print(f"[{hit.label}] {hit.path}:{hit.line}")
        print(f"  {hit.snippet}")


def main() -> int:
    hits = scan()
    print("Public CRM categorization scan")
    print(f"Root: {FRONTEND_SRC}")
    _print_group("A) UNWANTED", "A", hits)
    _print_group("B) ALLOWED_COMPARISON", "B", hits)
    _print_group("C) INTENTIONAL_SEO_KEYWORDS", "C", hits)

    unwanted = [h for h in hits if h.group == "A"]
    if unwanted:
        print(f"\nFAIL: {len(unwanted)} unwanted categorization hit(s).", file=sys.stderr)
        return 1
    print("\nOK: no unwanted HostFlow-as-CRM categorization hits.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
