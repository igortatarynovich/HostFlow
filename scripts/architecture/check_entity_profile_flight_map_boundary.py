#!/usr/bin/env python3
"""CL6 guard — one Entity Profile Flight map runtime producer."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_ROOT = REPO_ROOT / "backend" / "app"
ALLOWLIST = (
    REPO_ROOT
    / "scripts"
    / "architecture"
    / "entity_profile_flight_map_boundary_allowlist.txt"
)

MAP_API = re.compile(r"def\s+apply_map\s*\(")


@dataclass(frozen=True)
class Finding:
    rule: str
    path: str
    line: int
    snippet: str


def load_allowlist(path: Path) -> list[str]:
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


def scan() -> list[Finding]:
    allowlist = set(load_allowlist(ALLOWLIST))
    findings: list[Finding] = []
    for path in sorted(SCAN_ROOT.rglob("*.py")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        for idx, line in enumerate(text.splitlines(), start=1):
            if not MAP_API.search(line):
                continue
            if rel in allowlist:
                continue
            findings.append(
                Finding(
                    rule="entity_profile_flight_map_producer",
                    path=rel,
                    line=idx,
                    snippet=line.strip(),
                )
            )
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)

    findings = scan()
    if findings:
        for row in findings:
            print(
                f"{row.rule}: {row.path}:{row.line}: {row.snippet}",
                file=sys.stderr,
            )
        return 1

    allowlist = load_allowlist(ALLOWLIST)
    if len(allowlist) != 1:
        print("CL6 allowlist must name exactly one producer path", file=sys.stderr)
        return 1
    print("CL6 Entity Profile Flight map boundary: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
