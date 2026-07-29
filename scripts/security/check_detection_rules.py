#!/usr/bin/env python3
"""
Merge gate: Phase 7 detection rules must have owner + runbook on disk.

Run from repo root::

    python3 scripts/security/check_detection_rules.py
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RULES_FILE = REPO_ROOT / "backend" / "app" / "security" / "detection_rules.py"


def _load_rules_module():
    spec = importlib.util.spec_from_file_location("detection_rules_gate", RULES_FILE)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load detection_rules")
    mod = importlib.util.module_from_spec(spec)
    # Minimal package path so dataclass file imports work without full app.
    sys.modules["detection_rules_gate"] = mod
    # Execute as plain file — it only imports dataclasses/typing.
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    if not RULES_FILE.is_file():
        print(f"ERROR: missing {RULES_FILE}", file=sys.stderr)
        return 2
    # Import via package path when PYTHONPATH includes repo root.
    sys.path.insert(0, str(REPO_ROOT))
    try:
        from backend.app.security.detection_rules import DETECTION_RULES
    except Exception:
        # Fallback: load file directly (dataclasses only).
        mod = _load_rules_module()
        DETECTION_RULES = mod.DETECTION_RULES

    errors: list[str] = []
    if not DETECTION_RULES:
        errors.append("DETECTION_RULES is empty")
    for rule in DETECTION_RULES:
        if not (rule.owner or "").strip():
            errors.append(f"{rule.rule_id}: missing owner")
        if not (rule.runbook_path or "").strip():
            errors.append(f"{rule.rule_id}: missing runbook_path")
            continue
        path = REPO_ROOT / rule.runbook_path
        if not path.is_file():
            errors.append(f"{rule.rule_id}: runbook missing on disk: {rule.runbook_path}")
        elif rule.rule_id not in path.read_text(encoding="utf-8"):
            errors.append(f"{rule.rule_id}: runbook does not mention rule_id")
    if errors:
        print(
            "Detection rules gate failed (Phase 7).\n"
            "Every rule needs owner + existing runbook documenting triage.\n",
            file=sys.stderr,
        )
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
