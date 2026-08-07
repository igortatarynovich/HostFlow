#!/usr/bin/env python3
"""Scan HostFlow for legacy / trust role usage. Writes CSV + inventory markdown.

Usage (repo root):
  python scripts/rbac/scan_role_usage.py
"""
from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PAT_REQUIRE = re.compile(r"require_roles\([^)]*\)", re.M)
PAT_ROLE_ENUM = re.compile(
    r"Role\.(recruiter|supervisor|client_manager|client_processor|"
    r"compliance_officer|hr_officer|administrator|superadmin|viewer|employee|"
    r"owner|admin|manager)\b"
)
PAT_FE_ROLE = re.compile(
    r"\b(client_manager|client_processor|compliance_officer|hr_officer|recruiter|supervisor)\b"
)

TARGET = {
    "TRUST": "keep canonical trust role",
    "JOB_PROXY": "employee + permission/module gate + preset",
    "ORG_PROXY": "employee + supervisor_id/org + permission",
    "PORTAL_LEGACY": "viewer + access_context=portal + scope",
    "ALIAS": "normalize via normalize_trust_role",
    "SEAT": "recount seats Admin/Employee/Viewer",
    "UI_ONLY": "align FE with BE trust + permissions",
    "DOC": "update to ADR-036 language",
    "TEST": "update fixtures/asserts after mapping",
}


def classify(roles: list[str], is_test: bool, kind: str) -> tuple[str, str]:
    if is_test:
        return "TEST", "L"
    if kind == "seat":
        return "SEAT", "H"
    if kind == "doc":
        return "DOC", "L"
    if kind == "ui_map":
        return "UI_ONLY", "H"
    if any(r in ("client_manager", "client_processor") for r in roles):
        return "PORTAL_LEGACY", "H"
    if "supervisor" in roles and kind == "require":
        return "ORG_PROXY", "H"
    if any(r in ("recruiter", "hr_officer", "compliance_officer") for r in roles):
        return "JOB_PROXY", "H"
    if any(r in ("owner", "admin", "manager") for r in roles):
        return "ALIAS", "M"
    if roles and all(r in ("administrator", "superadmin", "viewer", "employee") for r in roles):
        return "TRUST", "M"
    return "JOB_PROXY", "M"


def main() -> None:
    rows: list[dict[str, str]] = []
    nid = 0

    def add(
        surface: str,
        path: str,
        snippet: str,
        roles: list[str],
        kind: str,
        is_test: bool = False,
    ) -> None:
        nonlocal nid
        nid += 1
        klass, risk = classify(roles, is_test, kind)
        rows.append(
            {
                "id": f"{surface.upper()}-{nid:04d}",
                "surface": surface,
                "path": path,
                "snippet": snippet[:160].replace("\n", " ").replace("|", "/"),
                "legacy_roles": ",".join(sorted(set(roles))) if roles else "",
                "class": klass,
                "target_mapping": TARGET[klass],
                "risk": risk,
                "status": "open",
            }
        )

    for p in (ROOT / "backend").rglob("*.py"):
        if any(x in str(p) for x in (".venv", "venv", "__pycache__")):
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        rel = str(p.relative_to(ROOT))
        is_test = "/tests/" in rel
        for m in PAT_REQUIRE.finditer(text):
            sn = m.group(0)
            roles = re.findall(r"Role\.(\w+)", sn)
            add("test" if is_test else "be", rel, sn, roles, "require", is_test)
        for m in PAT_ROLE_ENUM.finditer(text):
            line_start = text.rfind("\n", 0, m.start()) + 1
            line_end = text.find("\n", m.start())
            line = text[line_start : line_end if line_end != -1 else None]
            if "require_roles" in line:
                continue
            add(
                "test" if is_test else "be",
                f"{rel}:{text[: m.start()].count(chr(10)) + 1}",
                line.strip(),
                [m.group(1)],
                "enum",
                is_test,
            )

    fe_root = ROOT / "hostflow-frontend" / "src"
    for p in list(fe_root.rglob("*.ts")) + list(fe_root.rglob("*.tsx")):
        text = p.read_text(encoding="utf-8", errors="ignore")
        rel = str(p.relative_to(ROOT))
        is_test = "__tests__" in rel or ".test." in rel
        found = sorted(set(PAT_FE_ROLE.findall(text)))
        if "max_client_managers" in text or "client_manager_count" in text:
            add("fe", rel, "seat/counter client_manager", ["client_manager"], "seat", is_test)
        if (
            "ROLE_PERMISSIONS" in text
            or "ROLE_LABEL_KEYS" in text
            or "RoleModuleMatrixRole" in text
        ):
            add("fe", rel, "role matrix / permissions map", found or ["roles"], "ui_map", is_test)
        elif found:
            add("fe", rel, ",".join(found), found, "require", is_test)

    for p in (ROOT / "docs").rglob("*.md"):
        if "rbac-role-usage-inventory" in str(p):
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        if not re.search(
            r"client_manager|client_processor|hr_officer|compliance_officer|`recruiter`|Role\.recruiter",
            text,
        ):
            continue
        found = sorted(set(PAT_FE_ROLE.findall(text)))
        add("doc", str(p.relative_to(ROOT)), "legacy role mention", found or ["legacy"], "doc")

    out_dir = ROOT / "scripts" / "rbac"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "role_usage_inventory.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    h_paths: dict[str, dict] = defaultdict(lambda: {"classes": set(), "roles": set(), "count": 0})
    by_class: dict[str, int] = defaultdict(int)
    for r in rows:
        by_class[r["class"]] += 1
        if r["risk"] != "H":
            continue
        path = r["path"].split(":")[0]
        h_paths[path]["classes"].add(r["class"])
        h_paths[path]["roles"].update(x for x in r["legacy_roles"].split(",") if x)
        h_paths[path]["count"] += 1

    md_path = ROOT / "docs" / "specs" / "architecture" / "rbac-role-usage-inventory.md"
    md: list[str] = []
    md.append("# RBAC role usage inventory (ADR-036 migration gate)\n\n")
    md.append(
        "**Status:** NORMATIVE checklist (L2) — gate before Phase 2 runtime delete of legacy role branches  \n"
    )
    md.append(
        "**Parent:** [`ADR-036-four-trust-roles-rbac.md`](ADR-036-four-trust-roles-rbac.md) · "
        "[`rbac_matrix.md`](rbac_matrix.md)  \n"
    )
    md.append(
        "**Full machine dump:** [`scripts/rbac/role_usage_inventory.csv`]"
        "(../../../scripts/rbac/role_usage_inventory.csv)  \n"
    )
    md.append("**Scanner:** [`scripts/rbac/scan_role_usage.py`](../../../scripts/rbac/scan_role_usage.py)\n\n")
    md.append("## Summary\n\n")
    md.append(f"- Auto-collected call sites: **{len(rows)}** (see CSV)\n")
    md.append(f"- Distinct High-risk paths: **{len(h_paths)}**\n")
    md.append(
        "- By class: "
        + ", ".join(f"`{k}`={v}" for k, v in sorted(by_class.items()))
        + "\n\n"
    )
    md.append("### Gate rules\n\n")
    md.append(
        "1. Phase 2 starts only when every **H** path below has an agreed `target_mapping` "
        "(defaults from class; refine in PR notes if needed).\n"
    )
    md.append(
        "2. Phase 3 delete of a legacy role string only when CSV rows for that role are "
        "`removed` or `aliased` on the shim allowlist.\n"
    )
    md.append(
        "3. Re-run `python scripts/rbac/scan_role_usage.py` after refactors; "
        "unexplained new H paths block merge.\n\n"
    )
    md.append("### Migration map\n\n")
    md.append("| Legacy | Canonical trust | Extra |\n|--------|-----------------|-------|\n")
    md.append("| administrator, owner, admin | administrator | — |\n")
    md.append("| recruiter, hr, compliance_officer, hr_officer | employee | preset |\n")
    md.append("| supervisor, manager | employee | preset `team_lead` + `supervisor_id` |\n")
    md.append("| client_manager, client_processor | viewer | `access_context=portal` + scope |\n")
    md.append("| viewer, user | viewer | `tenant` or `portal` |\n")
    md.append("| superadmin | superadmin | — |\n\n")
    md.append("## High-risk paths (aggregated)\n\n")
    md.append(
        "| path | hits | classes | legacy_roles_seen | target_mapping | status |\n"
        "|------|------|---------|-------------------|----------------|--------|\n"
    )
    for path in sorted(h_paths.keys()):
        info = h_paths[path]
        classes = ",".join(sorted(info["classes"]))
        roles = ",".join(sorted(info["roles"]))
        primary = (
            "PORTAL_LEGACY"
            if "PORTAL_LEGACY" in info["classes"]
            else (
                "SEAT"
                if "SEAT" in info["classes"]
                else (
                    "ORG_PROXY"
                    if "ORG_PROXY" in info["classes"]
                    else (
                        "JOB_PROXY"
                        if "JOB_PROXY" in info["classes"]
                        else ("UI_ONLY" if "UI_ONLY" in info["classes"] else "TRUST")
                    )
                )
            )
        )
        md.append(
            f"| `{path}` | {info['count']} | {classes} | {roles} | {TARGET[primary]} | open |\n"
        )
    md.append("\n## Status workflow\n\n")
    md.append("`open` → `aliased` (normalize live) → `migrated` → `removed`.\n")
    md.append("\n## DB appendix\n\n")
    md.append("```sql\nSELECT role, count(*) FROM users GROUP BY 1 ORDER BY 2 DESC;\n```\n")
    md.append("Record counts in Phase 2 PR description.\n")
    md_path.write_text("".join(md), encoding="utf-8")
    print(f"rows={len(rows)} h_paths={len(h_paths)} csv={csv_path} md={md_path}")


if __name__ == "__main__":
    main()
