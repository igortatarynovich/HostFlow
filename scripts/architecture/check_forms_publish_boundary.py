#!/usr/bin/env python3
"""Forms Publish Contract guard — one write, twelve classified answerers."""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT = REPO_ROOT / "backend" / "app" / "reference" / "forms_publish_contract.py"
ALLOWLIST = (
    REPO_ROOT / "scripts" / "architecture" / "forms_publish_boundary_allowlist.txt"
)
ARCH_DOC = REPO_ROOT / "docs" / "specs" / "architecture" / "forms-publish-contract.md"
BRIEF = REPO_ROOT / "docs" / "specs" / "tasks" / "external-intake-forms-publish.md"

EXPECTED_COUNT = 12
WRITE_API = "commit_publish"


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


def _load_contract():
    sys.path.insert(0, str(REPO_ROOT))
    from backend.app.reference.forms_publish_contract import (  # noqa: PLC0415
        ANSWERERS,
        CLOSED_ROLES,
        CONTRACT_ID,
        WRITE_API as CONTRACT_WRITE_API,
        WRITE_PRODUCER_REL,
        write_authority_answerers,
    )

    return {
        "ANSWERERS": ANSWERERS,
        "CLOSED_ROLES": CLOSED_ROLES,
        "CONTRACT_ID": CONTRACT_ID,
        "WRITE_API": CONTRACT_WRITE_API,
        "WRITE_PRODUCER_REL": WRITE_PRODUCER_REL,
        "write_authority_answerers": write_authority_answerers,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)

    if not CONTRACT.is_file():
        print(f"missing contract: {CONTRACT}", file=sys.stderr)
        return 1
    if not ARCH_DOC.is_file():
        print(f"missing architecture SoT: {ARCH_DOC}", file=sys.stderr)
        return 1
    if not BRIEF.is_file():
        print(f"missing Forms Publish brief: {BRIEF}", file=sys.stderr)
        return 1

    contract = _load_contract()
    answerers = contract["ANSWERERS"]
    if len(answerers) != EXPECTED_COUNT:
        print(
            f"expected {EXPECTED_COUNT} answerers, found {len(answerers)}",
            file=sys.stderr,
        )
        return 1

    codes = [row.code for row in answerers]
    if len(codes) != len(set(codes)):
        print("duplicate answerer codes", file=sys.stderr)
        return 1

    writers = contract["write_authority_answerers"]()
    if len(writers) != 1 or writers[0].code != "commit_publish_ledger":
        print(
            "exactly one write_authority must be commit_publish_ledger",
            file=sys.stderr,
        )
        return 1

    for row in answerers:
        if row.role not in contract["CLOSED_ROLES"]:
            print(f"unknown FP role: {row.code}={row.role}", file=sys.stderr)
            return 1
        for rel in row.paths:
            path = REPO_ROOT / rel
            if not path.exists():
                print(f"answerer path missing: {row.code} -> {rel}", file=sys.stderr)
                return 1

    allowlist = load_allowlist(ALLOWLIST)
    if allowlist != [contract["WRITE_PRODUCER_REL"]]:
        print("allowlist must name exactly the commit_publish producer", file=sys.stderr)
        return 1

    producer = REPO_ROOT / contract["WRITE_PRODUCER_REL"]
    tree = ast.parse(producer.read_text(encoding="utf-8"))
    defined = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == WRITE_API
    ]
    if len(defined) != 1:
        print(
            f"{WRITE_API} must be defined once on the allowlisted producer",
            file=sys.stderr,
        )
        return 1

    extra_defs: list[str] = []
    scan_root = REPO_ROOT / "backend" / "app"
    for path in sorted(scan_root.rglob("*.py")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel == contract["WRITE_PRODUCER_REL"]:
            continue
        text = path.read_text(encoding="utf-8")
        if f"def {WRITE_API}(" not in text:
            continue
        extra_defs.append(rel)
    if extra_defs:
        print(
            "second commit_publish definition is a second write: "
            + ", ".join(extra_defs),
            file=sys.stderr,
        )
        return 1

    arch = ARCH_DOC.read_text(encoding="utf-8")
    if contract["CONTRACT_ID"] not in arch:
        print("architecture SoT must name the contract id", file=sys.stderr)
        return 1
    if "thirteenth write" not in arch.lower():
        print("architecture SoT must forbid a thirteenth write", file=sys.stderr)
        return 1
    if "out-of-band" not in arch.lower() and "outside the ledger" not in arch.lower():
        print("architecture SoT must forbid out-of-band published_version", file=sys.stderr)
        return 1

    print("Forms Publish Contract boundary: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
