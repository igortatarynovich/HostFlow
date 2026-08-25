#!/usr/bin/env python3
"""DR1-runtime guard — one Hub outstanding-ask writer for this contract."""

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
    / "engine_outstanding_ask_writer_boundary_allowlist.txt"
)

CONTRACT_ID = "engine_to_hub_outstanding_ask.v1"
WRITE_API = re.compile(r"def\s+write_engine_outstanding_asks\s*\(")
PERSIST_CALL = re.compile(r"persist_outstanding_asks_via_contract\s*\(")
HUB_PERSIST = (
    "backend/app/services/document_hub_delivery_contract.py"
)


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
            if WRITE_API.search(line) and rel not in allowlist:
                findings.append(
                    Finding(
                        rule="engine_outstanding_ask_writer",
                        path=rel,
                        line=idx,
                        snippet=line.strip(),
                    )
                )
            if PERSIST_CALL.search(line) and rel not in allowlist and rel != HUB_PERSIST:
                findings.append(
                    Finding(
                        rule="engine_outstanding_ask_persist",
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
        print("DR1-runtime allowlist must name exactly one writer path", file=sys.stderr)
        return 1
    producer = REPO_ROOT / allowlist[0]
    if not producer.is_file():
        print(f"DR1-runtime writer missing: {allowlist[0]}", file=sys.stderr)
        return 1
    text = producer.read_text(encoding="utf-8")
    if CONTRACT_ID not in text or WRITE_API.search(text) is None:
        print(
            "DR1-runtime allowlist writer must define write_engine_outstanding_asks",
            file=sys.stderr,
        )
        return 1
    if "project_engine_evaluation_to_outstanding_asks" not in text:
        print("DR1-runtime writer must reuse DR1-contract projection", file=sys.stderr)
        return 1
    if "persist_outstanding_asks_via_contract" not in text:
        print("DR1-runtime writer must persist via Hub adapter", file=sys.stderr)
        return 1
    if "def project_engine_evaluation_to_outstanding_asks" in text:
        print("DR1-runtime writer must not fork the projection producer", file=sys.stderr)
        return 1
    print("DR1-runtime Hub outstanding-ask writer boundary: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
