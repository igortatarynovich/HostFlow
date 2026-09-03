#!/usr/bin/env python3
"""Requirement Policy Authority guard — one write, nine classified answerers."""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT = REPO_ROOT / "backend" / "app" / "reference" / "requirement_policy_authority.py"
ALLOWLIST = (
    REPO_ROOT
    / "scripts"
    / "architecture"
    / "requirement_policy_authority_boundary_allowlist.txt"
)
ARCH_DOC = REPO_ROOT / "docs" / "specs" / "architecture" / "requirement-policy-authority.md"
BRIEF = REPO_ROOT / "docs" / "specs" / "tasks" / "requirement-policy-management.md"

EXPECTED_COUNT = 9
WRITE_API = "merge_resolved_policy"


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
    from backend.app.reference.requirement_policy_authority import (  # noqa: PLC0415
        ANSWERERS,
        CLOSED_ROLES,
        CONTRACT_ID,
        WRITE_MERGE_API,
        WRITE_PRODUCER_REL,
        write_authority_answerers,
    )

    return {
        "ANSWERERS": ANSWERERS,
        "CLOSED_ROLES": CLOSED_ROLES,
        "CONTRACT_ID": CONTRACT_ID,
        "WRITE_MERGE_API": WRITE_MERGE_API,
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
        print(f"missing RPM brief: {BRIEF}", file=sys.stderr)
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
    if len(writers) != 1 or writers[0].code != "r5_pack_tenant_delta":
        print("exactly one write_authority must be r5_pack_tenant_delta", file=sys.stderr)
        return 1

    for row in answerers:
        if row.role not in contract["CLOSED_ROLES"]:
            print(f"unknown RPM role: {row.code}={row.role}", file=sys.stderr)
            return 1
        for rel in row.paths:
            path = REPO_ROOT / rel
            if not path.exists():
                print(f"answerer path missing: {row.code} -> {rel}", file=sys.stderr)
                return 1

    allowlist = load_allowlist(ALLOWLIST)
    if allowlist != [contract["WRITE_PRODUCER_REL"]]:
        print("allowlist must name exactly the R5 merge producer", file=sys.stderr)
        return 1

    producer = REPO_ROOT / contract["WRITE_PRODUCER_REL"]
    tree = ast.parse(producer.read_text(encoding="utf-8"))
    defined = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == WRITE_API
    ]
    if len(defined) != 1:
        print(f"{WRITE_API} must be defined once on the allowlisted producer", file=sys.stderr)
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
            "second merge_resolved_policy definition is a second write: "
            + ", ".join(extra_defs),
            file=sys.stderr,
        )
        return 1

    arch = ARCH_DOC.read_text(encoding="utf-8")
    if contract["CONTRACT_ID"] not in arch:
        print("architecture SoT must name the contract id", file=sys.stderr)
        return 1
    if "tenth write" not in arch.lower() and "tenth" not in arch.lower():
        print("architecture SoT must forbid a tenth write", file=sys.stderr)
        return 1

    print("Requirement Policy Authority boundary: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
