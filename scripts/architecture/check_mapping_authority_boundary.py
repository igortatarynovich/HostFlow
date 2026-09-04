#!/usr/bin/env python3
"""Mapping Authority Contract guard — one write, twelve classified answerers."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT = REPO_ROOT / "backend" / "app" / "reference" / "mapping_authority.py"
ALLOWLIST = (
    REPO_ROOT / "scripts" / "architecture" / "mapping_authority_boundary_allowlist.txt"
)
ARCH_DOC = REPO_ROOT / "docs" / "specs" / "architecture" / "mapping-authority-contract.md"
BRIEF = REPO_ROOT / "docs" / "specs" / "tasks" / "mapping-authority.md"

EXPECTED_COUNT = 12


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
    from backend.app.reference.mapping_authority import (  # noqa: PLC0415
        ANSWERERS,
        CLOSED_ROLES,
        CONTRACT_ID,
        WRITE_PRODUCER_REL,
        write_authority_answerers,
    )

    return {
        "ANSWERERS": ANSWERERS,
        "CLOSED_ROLES": CLOSED_ROLES,
        "CONTRACT_ID": CONTRACT_ID,
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
        print(f"missing Mapping brief: {BRIEF}", file=sys.stderr)
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
    if len(writers) != 1 or writers[0].code != "intake_source_profile_mapping_rules":
        print(
            "exactly one write_authority must be intake_source_profile_mapping_rules",
            file=sys.stderr,
        )
        return 1

    for row in answerers:
        if row.role not in contract["CLOSED_ROLES"]:
            print(f"unknown MA role: {row.code}={row.role}", file=sys.stderr)
            return 1
        for rel in row.paths:
            path = REPO_ROOT / rel
            if not path.exists():
                print(f"answerer path missing: {row.code} -> {rel}", file=sys.stderr)
                return 1

    allowlist = load_allowlist(ALLOWLIST)
    if allowlist != [contract["WRITE_PRODUCER_REL"]]:
        print(
            "allowlist must name exactly the intake-source mapping write producer",
            file=sys.stderr,
        )
        return 1

    arch = ARCH_DOC.read_text(encoding="utf-8")
    if contract["CONTRACT_ID"] not in arch:
        print("architecture SoT must name the contract id", file=sys.stderr)
        return 1
    lowered = arch.lower()
    required = (
        "option map",
        "schema",
        "sample",
        "mapped",
        "ignored",
        "unmapped",
        "needs review",
        "thirteenth write",
        "no_fit",
        "qualified_code",
        "field registry",
    )
    missing = [item for item in required if item not in lowered]
    if missing:
        print("architecture SoT missing required contract shape: " + ", ".join(missing), file=sys.stderr)
        return 1

    print("Mapping Authority Contract boundary: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
