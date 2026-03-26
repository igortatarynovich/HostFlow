#!/usr/bin/env python3
"""
Generate TypeScript and Python SPA path modules from **shared/crm_app_paths.json**.

  python3 scripts/codegen/generate_crm_app_paths.py           # write outputs
  python3 scripts/codegen/generate_crm_app_paths.py --check   # fail if drift

See **docs/SSOT.md** §1.6.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPO_ROOT / "shared" / "crm_app_paths.json"
SCHEMA_PATH = REPO_ROOT / "shared" / "crm_app_paths.schema.json"
TS_OUT = REPO_ROOT / "hostflow-frontend" / "src" / "app" / "crmAppPaths.generated.ts"
PY_OUT = REPO_ROOT / "backend" / "app" / "constants" / "spa_paths.py"

_TS_HEADER = """/**
 * GENERATED FILE — do not edit by hand.
 * Source: `shared/crm_app_paths.json`.
 * Regenerate: `python3 scripts/codegen/generate_crm_app_paths.py` or `npm run codegen:crm-app-paths`.
 */

"""

_PY_HEADER = """# GENERATED FILE — do not edit by hand.
# Source: shared/crm_app_paths.json
# Regenerate: python3 scripts/codegen/generate_crm_app_paths.py

\"\"\"
Canonical SPA paths under /app (generated from shared/crm_app_paths.json).

Human-oriented rules and docs: docs/SSOT.md §1.6.
\"\"\"

"""


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _merged_paths(data: dict) -> dict[str, str]:
    paths = dict(data["paths"])
    extra = data.get("python_only_paths") or {}
    overlap = set(paths) & set(extra)
    if overlap:
        raise ValueError(f"python_only_paths keys overlap paths: {sorted(overlap)}")
    paths.update(extra)
    return paths


def _validate(data: dict) -> None:
    required = ("schema_version", "paths", "drilldown_hrefs", "python_exports")
    missing = [k for k in required if k not in data]
    if missing:
        raise ValueError(f"Manifest missing keys: {missing}")

    if data.get("schema_version") != 1:
        raise ValueError("schema_version must be 1")

    for key, val in data["paths"].items():
        if not isinstance(val, str) or not val.startswith("/app"):
            raise ValueError(f"paths.{key}: must be string starting with /app, got {val!r}")

    app_shell = data["paths"].get("appShellPrefix")
    if app_shell != "/app":
        raise ValueError(f'paths.appShellPrefix must be "/app", got {app_shell!r}')

    for key, val in (data.get("python_only_paths") or {}).items():
        if not isinstance(val, str) or not val.startswith("/app"):
            raise ValueError(f"python_only_paths.{key}: must start with /app")

    merged = _merged_paths(data)
    for key, val in data["drilldown_hrefs"].items():
        if not isinstance(val, str) or not val.startswith("/app"):
            raise ValueError(f"drilldown_hrefs.{key}: must start with /app")

    const_pat = re.compile(r"^[A-Z][A-Z0-9_]*$")
    for entry in data["python_exports"]["constants"]:
        name = entry["name"]
        if not const_pat.match(name):
            raise ValueError(f"Invalid python constant name: {name}")
        if "literal" in entry:
            continue
        pk = entry["path_key"]
        if pk not in merged:
            raise ValueError(f"python_exports.constants {name}: unknown path_key {pk!r}")

    allowed_py_consts = {e["name"] for e in data["python_exports"]["constants"]}
    body_const_pat = re.compile(r"\b([A-Z][A-Z0-9_]*)\b")
    for fn in data["python_exports"]["functions"]:
        for ref in body_const_pat.findall(fn["body"]):
            if ref not in allowed_py_consts:
                raise ValueError(
                    f"python function {fn['name']}: body references unknown constant {ref}"
                )


def _emit_typescript(data: dict) -> str:
    paths = data["paths"]
    comments = data.get("path_comments") or {}
    lines = [_TS_HEADER, "export const CRM_APP_PATHS = {\n"]
    for key, val in paths.items():
        c = comments.get(key)
        if c:
            lines.append(f"  /** {c} */\n")
        lines.append(f"  {key}: {json.dumps(val)},\n")
    lines.append("} as const\n\n")
    lines.append("export const CRM_APP_DRILLDOWN_HREFS = {\n")
    dcomments = data.get("drilldown_comments") or {}
    for key, val in data["drilldown_hrefs"].items():
        c = dcomments.get(key)
        if c:
            lines.append(f"  /** {c} */\n")
        lines.append(f"  {key}: {json.dumps(val)},\n")
    lines.append("} as const\n")
    return "".join(lines)


def _emit_python(data: dict) -> str:
    merged = _merged_paths(data)
    lines = [_PY_HEADER]
    for entry in data["python_exports"]["constants"]:
        name = entry["name"]
        if "literal" in entry:
            val = entry["literal"]
            lines.append(f'{name} = {json.dumps(val)}\n')
        else:
            val = merged[entry["path_key"]]
            lines.append(f"{name} = {json.dumps(val)}\n")
    lines.append("\n")
    for fn in data["python_exports"]["functions"]:
        params = ", ".join(fn["params"])
        lines.append(f"def {fn['name']}({params}) -> str:\n")
        lines.append(f"    {fn['body']}\n\n\n")
    return "".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if generated files differ from manifest (CI drift gate).",
    )
    args = parser.parse_args()

    if not MANIFEST.is_file():
        print(f"Missing manifest: {MANIFEST}", file=sys.stderr)
        return 1

    data = _load_json(MANIFEST)
    if not SCHEMA_PATH.is_file():
        print(f"Missing schema: {SCHEMA_PATH}", file=sys.stderr)
        return 1
    _load_json(SCHEMA_PATH)
    _validate(data)

    ts_body = _emit_typescript(data)
    py_body = _emit_python(data)

    if args.check:
        errors = []
        if not TS_OUT.is_file() or TS_OUT.read_text(encoding="utf-8") != ts_body:
            errors.append(str(TS_OUT.relative_to(REPO_ROOT)))
        if not PY_OUT.is_file() or PY_OUT.read_text(encoding="utf-8") != py_body:
            errors.append(str(PY_OUT.relative_to(REPO_ROOT)))
        if errors:
            print(
                "Generated CRM path files are out of date. Run:\n"
                "  python3 scripts/codegen/generate_crm_app_paths.py\n"
                "Stale:\n  "
                + "\n  ".join(errors),
                file=sys.stderr,
            )
            return 1
        print("codegen check: crm_app_paths OK")
        return 0

    TS_OUT.parent.mkdir(parents=True, exist_ok=True)
    PY_OUT.parent.mkdir(parents=True, exist_ok=True)
    TS_OUT.write_text(ts_body, encoding="utf-8")
    PY_OUT.write_text(py_body, encoding="utf-8")
    print(f"Wrote {TS_OUT.relative_to(REPO_ROOT)}")
    print(f"Wrote {PY_OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
