#!/usr/bin/env python3
"""OL-2C: repo-root alembic.ini is the only Alembic entrypoint.

backend/alembic.ini may exist only as a shim (same keys, script_location
relative to backend/). A second SoT is a process fail.
"""

from __future__ import annotations

import configparser
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CANONICAL = REPO_ROOT / "alembic.ini"
SHIM = REPO_ROOT / "backend" / "alembic.ini"
DOCUMENTS = REPO_ROOT / "backend" / "app" / "modules" / "documents" / "alembic.ini"


def _alembic_section(path: Path) -> configparser.SectionProxy:
    cfg = configparser.ConfigParser()
    if not cfg.read(path):
        raise SystemExit(f"cannot read {path}")
    if "alembic" not in cfg:
        raise SystemExit(f"{path} has no [alembic] section")
    return cfg["alembic"]


def main() -> int:
    errors: list[str] = []
    if not CANONICAL.is_file():
        errors.append(f"canonical missing: {CANONICAL}")
        print("\n".join(errors), file=sys.stderr)
        return 2
    canon = _alembic_section(CANONICAL)
    if canon.get("script_location") != "backend/alembic":
        errors.append(
            f"{CANONICAL} script_location must be backend/alembic, "
            f"got {canon.get('script_location')!r}"
        )
    if SHIM.is_file():
        shim = _alembic_section(SHIM)
        if shim.get("script_location") != "alembic":
            errors.append(
                f"{SHIM} is not a valid shim: script_location must be "
                f"'alembic', got {shim.get('script_location')!r}"
            )
        header = SHIM.read_text(encoding="utf-8", errors="replace")[:400]
        if "SHIM" not in header:
            errors.append(
                f"{SHIM} must declare itself a SHIM in the first lines; "
                "canonical config is the repo-root alembic.ini"
            )
    if not DOCUMENTS.is_file():
        # Not an error — documents graph is out of this slice.
        pass
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 2
    print(f"canonical Alembic entrypoint: {CANONICAL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
