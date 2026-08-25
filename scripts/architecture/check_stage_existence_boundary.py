#!/usr/bin/env python3
"""LI-1 guard — exactly one is_stage_registered producer; block new copies."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_ROOT = REPO_ROOT / "backend" / "app"
ALLOWLIST = REPO_ROOT / "scripts" / "architecture" / "stage_existence_boundary_allowlist.txt"
BASELINE = REPO_ROOT / "scripts" / "architecture" / "stage_existence_boundary_baseline.txt"

EXISTENCE_API = re.compile(r"def\s+is_stage_registered\s*\(")


@dataclass(frozen=True)
class Finding:
    rule: str
    path: str
    line: int
    snippet: str


def load_paths(path: Path) -> list[str]:
    out: list[str] = []
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        if "|" in s:
            _, rel = s.split("|", 1)
            out.append(rel.strip())
        else:
            out.append(s)
    return out


def load_baseline(path: Path) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    for rel in load_paths(path):
        if "|" in rel:
            rule, p = rel.split("|", 1)
            out.add((rule.strip(), p.strip()))
    return out


def scan() -> list[Finding]:
    findings: list[Finding] = []
    for path in sorted(SCAN_ROOT.rglob("*.py")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        for no, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            if EXISTENCE_API.search(line):
                findings.append(
                    Finding(
                        rule="COMPETING_EXISTENCE_API",
                        path=rel,
                        line=no,
                        snippet=line.strip(),
                    )
                )
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-baseline", action="store_true")
    args = parser.parse_args(argv)

    allowlist = set(load_paths(ALLOWLIST))
    findings = scan()
    keyed = {(f.rule, f.path) for f in findings}
    baseline = load_baseline(BASELINE)

    if args.write_baseline:
        lines = [f"{rule}|{path}" for rule, path in sorted(keyed)]
        BASELINE.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        print(f"Wrote baseline ({len(lines)} keys) to {BASELINE}")
        return 0

    unexpected = [f for f in findings if f.path not in allowlist]
    new_violations = {(f.rule, f.path) for f in unexpected} - baseline
    if unexpected:
        for f in unexpected:
            print(f"{f.rule} {f.path}:{f.line} {f.snippet}", file=sys.stderr)
    if new_violations:
        print(
            f"LI-1 stage existence boundary: {len(new_violations)} new violation(s)",
            file=sys.stderr,
        )
        return 1
    if len(allowlist) != 1:
        print("LI-1 allowlist must name exactly one producer path", file=sys.stderr)
        return 1
    print("LI-1 stage existence boundary: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
