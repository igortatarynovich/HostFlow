#!/usr/bin/env python3
"""Reference R5 guard — pack codes subset of registry; no module EU frozensets."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PACK_DEFINITIONS = REPO_ROOT / "backend" / "app" / "modules" / "documents" / "pack_definitions.py"


def main() -> int:
    errors: list[str] = []

    source = PACK_DEFINITIONS.read_text(encoding="utf-8")
    if "_DEFAULT_EU_COUNTRIES" in source or "EU_COUNTRIES" in source:
        errors.append("pack_definitions.py must not define module-local EU country frozensets")

    from backend.app.document_types.registry import canonical_codes
    from backend.app.modules.documents.pack_definitions import DOCUMENT_PACK_DEFINITIONS
    from backend.app.reference.document_policy_merge import collect_pack_document_codes

    registry = canonical_codes()
    pack_codes = collect_pack_document_codes()
    for code in sorted(pack_codes):
        if code not in registry:
            errors.append(f"platform pack code not in document type registry: {code}")

    for pack in DOCUMENT_PACK_DEFINITIONS:
        for code in pack.document_codes:
            if code not in registry:
                errors.append(f"pack {pack.code} code not in registry: {code}")

    if errors:
        for item in errors:
            print(item, file=sys.stderr)
        return 1

    print("check_document_policy_r5: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
