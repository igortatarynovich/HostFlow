#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_ROOT = REPO_ROOT / "backend" / "app"
ALLOWLIST = REPO_ROOT / "scripts" / "architecture" / "reference_facade_allowlist.txt"
BASELINE = REPO_ROOT / "scripts" / "architecture" / "reference_facade_boundary_baseline.txt"
REPORT = REPO_ROOT / "docs" / "specs" / "gates" / "ref3_1_guard_scan_latest.md"
MARKER = REPO_ROOT / "docs" / "specs" / "gates" / "ref3_1_arch_violation_marker.md"


@dataclass(frozen=True)
class Finding:
    rule: str
    path: str
    line: int
    snippet: str


RULES: list[tuple[str, re.Pattern[str]]] = [
    ("DIRECT_APPLICABILITY_RESOLVER", re.compile(r"\bDocumentApplicabilityResolver\b")),
    ("DIRECT_TYPE_RUNTIME_RESOLVER", re.compile(r"\bDocumentTypeRuntimeResolver\b")),
    (
        "DIRECT_REFERENCE_MODEL_IMPORT",
        re.compile(r"from\s+backend\.app\.models\.ref_document_type\s+import"),
    ),
]


def load_allowlist(path: Path) -> list[str]:
    out: list[str] = []
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        out.append(s)
    return out


def load_baseline(path: Path) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#") or "|" not in s:
            continue
        rule, p = s.split("|", 1)
        out.add((rule.strip(), p.strip()))
    return out


def is_allowlisted(rel_path: str, allowlist: list[str]) -> bool:
    for entry in allowlist:
        if entry.endswith("/"):
            if rel_path.startswith(entry):
                return True
        elif rel_path == entry:
            return True
    return False


def scan() -> list[Finding]:
    findings: list[Finding] = []
    for path in sorted(SCAN_ROOT.rglob("*.py")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore")
        for no, line in enumerate(text.splitlines(), start=1):
            for rule, pattern in RULES:
                if pattern.search(line):
                    findings.append(Finding(rule=rule, path=rel, line=no, snippet=line.strip()))
    return findings


def write_report(findings: list[Finding], new_violations: set[tuple[str, str]], baseline: set[tuple[str, str]]) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# REF-3.1 Guard Scan Report")
    lines.append("")
    lines.append(f"- Findings: {len(findings)}")
    lines.append(f"- New violations vs baseline: {len(new_violations)}")
    lines.append("")
    lines.append("## New Violations")
    if not new_violations:
        lines.append("- none")
    else:
        for rule, path in sorted(new_violations):
            lines.append(f"- `{rule}` | `{path}`")
    lines.append("")
    lines.append("## Baseline Keys")
    for rule, path in sorted(baseline):
        lines.append(f"- `{rule}` | `{path}`")
    lines.append("")
    lines.append("## Raw Findings")
    for f in findings:
        lines.append(f"- `{f.rule}` `{f.path}:{f.line}` :: `{f.snippet}`")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_marker(new_violations: set[tuple[str, str]]) -> None:
    MARKER.parent.mkdir(parents=True, exist_ok=True)
    if not new_violations:
        if MARKER.exists():
            MARKER.unlink()
        return
    lines = [
        "# ARCHITECTURAL VIOLATION MARKER",
        "",
        "Status: FAIL",
        "Reason: New direct reference/resolver access detected outside approved baseline.",
        "Action: Architectural review required before merge.",
        "",
        "## New Violations",
    ]
    for rule, path in sorted(new_violations):
        lines.append(f"- `{rule}` | `{path}`")
    MARKER.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-baseline", action="store_true")
    args = parser.parse_args()

    allowlist = load_allowlist(ALLOWLIST)
    baseline = load_baseline(BASELINE)

    raw = scan()
    enforce: list[Finding] = [f for f in raw if not is_allowlisted(f.path, allowlist)]

    keys = {(f.rule, f.path) for f in enforce}

    if args.write_baseline:
        data = ["# Format: <RULE>|<path>"]
        for rule, path in sorted(keys):
            data.append(f"{rule}|{path}")
        BASELINE.write_text("\n".join(data) + "\n", encoding="utf-8")

    new_violations = keys - baseline
    write_report(enforce, new_violations, baseline)
    write_marker(new_violations)

    if new_violations:
        print("ARCH_REVIEW_REQUIRED: new facade-boundary violations detected")
        return 2
    print("REF-3.1 guard scan passed (no new violations vs baseline)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
