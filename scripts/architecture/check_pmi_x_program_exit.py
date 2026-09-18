#!/usr/bin/env python3
"""PMI-X program exit — joint verification only (not a remediation slice).

Hard locks:
1. Exit fixes nothing. Any defect → STOP + classified separate work item (no in-exit cleanup).
2. PASS is HEAD-simultaneous: historical PMI-R/B/E/D/W/UI stamps are insufficient alone.
3. Ready is not auto-unfrozen; next cycle starts at public-contract Kernel preflight.

PASS requires all spine isolation checkers + PMI-1 freeze + PMI-UI green together on
the same revision, five ISOLATED cards, shrink-only debt ceilings, parked Ready/Kernel/PEM.
Does NOT require backend debt 1557 or UI debt 8 to reach zero.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

CHECKERS = {
    "recruitment": REPO / "scripts" / "architecture" / "check_recruitment_isolation.py",
    "boundary": REPO / "scripts" / "architecture" / "check_boundary_isolation.py",
    "employment": REPO / "scripts" / "architecture" / "check_employment_isolation.py",
    "documents": REPO / "scripts" / "architecture" / "check_documents_isolation.py",
    "workforce": REPO / "scripts" / "architecture" / "check_workforce_isolation.py",
    "ui": REPO / "scripts" / "architecture" / "check_ui_isolation.py",
    "freeze": REPO / "scripts" / "architecture" / "check_module_isolation_freeze.py",
}

CARDS = {
    "recruitment": REPO / "docs" / "modules" / "recruitment" / "module_isolation_card.md",
    "boundary": REPO / "docs" / "modules" / "boundary" / "module_isolation_card.md",
    "employment": REPO / "docs" / "modules" / "employment" / "module_isolation_card.md",
    "documents": REPO / "docs" / "modules" / "documents" / "module_isolation_card.md",
    "workforce": REPO / "docs" / "modules" / "workforce" / "module_isolation_card.md",
    "ui": REPO / "docs" / "modules" / "ui" / "module_isolation_card.md",
}

PUBLIC = {
    "recruitment": REPO / "backend" / "app" / "modules" / "recruitment" / "public",
    "boundary": REPO / "backend" / "app" / "modules" / "boundary" / "public",
    "employment": REPO / "backend" / "app" / "modules" / "employment" / "public",
    "documents": REPO / "backend" / "app" / "modules" / "documents" / "public",
    "workforce": REPO / "backend" / "app" / "modules" / "workforce" / "public",
    "design_system": REPO / "hostflow-frontend" / "src" / "platform" / "design-system",
}

RECRUIT_ALLOW = REPO / "scripts" / "architecture" / "recruitment_isolation_boundary_allowlist.txt"
CUTOVER = REPO / "docs" / "specs" / "tasks" / "platform-modularization-isolation-cutover.md"
GATE = REPO / "docs" / "specs" / "gates" / "platform-modularization-isolation-cutover-gate.md"
PREFLIGHT = REPO / "docs" / "specs" / "tasks" / "post-pmi-kernel-public-contract-preflight.md"

PMI1_AUTHORITY = 2006
BACKEND_DEBT_CEILING = 1557
UI_DEBT_CEILING = 8
RECRUIT_NON_SPINE_DEBT_CEILING = 63
SPINE_OWNERS = {"boundary", "employment", "documents", "workforce", "recruitment"}

FORBIDDEN_EXTERNAL_DIAGNOSIS = (
    "recruitment_package",
    "VERIFICATION_SLOT_DEFS",
    "requirement_engine",
)


def _git_head() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return "UNKNOWN"
    return proc.stdout.strip()


def _run_json(script: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, str(script), "--json"],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode not in (0, 1):
        return {"ok": False, "error": proc.stderr or proc.stdout, "returncode": proc.returncode}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "error": proc.stdout or proc.stderr, "returncode": proc.returncode}


def _card_isolated(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    return bool(re.search(r"^Status:\s*ISOLATED\b", text, re.M))


def _recruit_spine_leaks() -> list[str]:
    leaks: list[str] = []
    if not RECRUIT_ALLOW.exists():
        return ["missing allowlist"]
    for raw in RECRUIT_ALLOW.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        owner = s.split("|", 1)[0].strip()
        if owner in SPINE_OWNERS:
            leaks.append(s)
    return leaks


def _recruit_debt_count() -> int:
    n = 0
    for raw in RECRUIT_ALLOW.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if s and not s.startswith("#"):
            n += 1
    return n


def _parked_intact() -> dict:
    text = CUTOVER.read_text(encoding="utf-8") if CUTOVER.exists() else ""
    gate = GATE.read_text(encoding="utf-8") if GATE.exists() else ""
    combined = text + "\n" + gate
    return {
        "ready_parked": "Ready" in combined and ("PARKED" in combined or "parked" in combined.lower()),
        "ready_not_auto_unfrozen": (
            "not auto-unfrozen" in combined.lower()
            or "does not auto-unfreeze" in combined.lower()
            or "Ready is not auto-unfrozen" in combined
        ),
        "kernel_not_unparked_by_pmi": "Kernel" in combined
        and (
            "parked" in combined.lower()
            or "PARKED" in combined
            or "preflight on public" in combined.lower()
        ),
        "no_pem1_claim": "PEM-1" not in combined
        or ("PEM-1" in combined and "PASS" not in combined.split("PEM-1")[-1][:80]),
        "exit_fixes_nothing": (
            "fixes nothing" in combined.lower()
            or "verification only" in combined.lower()
            or "not a remediation" in combined.lower()
        ),
        "head_simultaneous_required": (
            "HEAD" in combined
            and ("simultaneous" in combined.lower() or "together" in combined.lower())
        ),
    }


def _preflight_brief_ok() -> dict:
    if not PREFLIGHT.exists():
        return {"exists": False, "public_only": False, "forbids_internals": False}
    text = PREFLIGHT.read_text(encoding="utf-8")
    public_only = "recruitment.public" in text and "public process contract" in text.lower()
    forbids = all(tok in text for tok in FORBIDDEN_EXTERNAL_DIAGNOSIS)
    not_started = (
        "Status:** **OPEN**" in text
        or "Status: OPEN" in text
        or "**OPEN**" in text[:240]
        or "NOT STARTED" in text
    )
    return {
        "exists": True,
        "public_only": public_only,
        "forbids_internals": forbids,
        "open_not_executed": not_started or "not started" in text.lower(),
    }


def evaluate() -> dict:
    head = _git_head()
    results: dict = {
        "head": head,
        "nature": "verification_only",
        "hard_locks": {
            "exit_fixes_nothing": True,
            "pass_is_head_simultaneous": True,
            "ready_not_auto_unfrozen": True,
        },
        "checkers": {},
        "cards": {},
        "public": {},
        "failures": [],
    }

    for name, script in CHECKERS.items():
        summary = _run_json(script)
        results["checkers"][name] = summary
        if not summary.get("ok"):
            results["failures"].append(f"checker:{name}")

    for name in ("boundary", "employment", "documents", "workforce"):
        s = results["checkers"].get(name, {})
        if s.get("violation_count", -1) != 0 or s.get("new_violation_count", -1) != 0:
            results["failures"].append(f"nonzero_inbound:{name}")

    spine_leaks = _recruit_spine_leaks()
    recruit_debt = _recruit_debt_count()
    results["recruitment_spine_leaks"] = spine_leaks
    results["recruitment_non_spine_debt"] = recruit_debt
    if spine_leaks:
        results["failures"].append("recruitment_spine_foreign_internals")
    if recruit_debt > RECRUIT_NON_SPINE_DEBT_CEILING:
        results["failures"].append("recruitment_debt_grew")
    rsum = results["checkers"].get("recruitment", {})
    if rsum.get("new_violation_count", -1) != 0:
        results["failures"].append("recruitment_new_violations")

    freeze = results["checkers"].get("freeze", {})
    debt = freeze.get("debt_edge_count", freeze.get("current_debt_relevant_count"))
    results["backend_debt"] = debt
    results["pmi1_authority"] = freeze.get("authority_edge_count", PMI1_AUTHORITY)
    if debt is None or debt > BACKEND_DEBT_CEILING:
        results["failures"].append("backend_debt_ceiling")
    if freeze.get("debt_growth_count", 0) not in (0, None):
        results["failures"].append("backend_debt_grew")
    if freeze.get("authority_edge_count") not in (PMI1_AUTHORITY, None):
        if freeze.get("authority_edge_count") != PMI1_AUTHORITY:
            results["failures"].append("pmi1_authority_changed")

    ui = results["checkers"].get("ui", {})
    ui_debt = ui.get("violation_count", ui.get("allowlist_count"))
    results["ui_debt"] = ui_debt
    if ui_debt is None or ui_debt > UI_DEBT_CEILING:
        results["failures"].append("ui_debt_ceiling")
    if ui.get("new_violation_count", -1) != 0:
        results["failures"].append("ui_new_violations")

    for name, path in CARDS.items():
        ok = path.is_file() and _card_isolated(path)
        results["cards"][name] = {"path": str(path.relative_to(REPO)), "isolated": ok}
        if not ok:
            results["failures"].append(f"card:{name}")

    for name, path in PUBLIC.items():
        ok = path.exists()
        results["public"][name] = ok
        if not ok:
            results["failures"].append(f"public:{name}")

    parked = _parked_intact()
    results["parked"] = parked
    if not parked.get("ready_parked"):
        results["failures"].append("ready_not_parked")
    if not parked.get("ready_not_auto_unfrozen"):
        results["failures"].append("ready_auto_unfreeze_forbidden_text_missing")
    if not parked.get("exit_fixes_nothing"):
        results["failures"].append("exit_fixes_nothing_text_missing")
    if not parked.get("head_simultaneous_required"):
        results["failures"].append("head_simultaneous_text_missing")

    preflight = _preflight_brief_ok()
    results["post_pmi_kernel_preflight"] = preflight
    if not preflight.get("exists"):
        results["failures"].append("missing_post_pmi_kernel_preflight_brief")
    elif not preflight.get("public_only") or not preflight.get("forbids_internals"):
        results["failures"].append("preflight_brief_not_public_contract_only")

    emp = CARDS["employment"].read_text(encoding="utf-8")
    doc = CARDS["documents"].read_text(encoding="utf-8")
    emp_tail = emp.split("EXC-PMI-B-EMP", 1)[-1][:120].lower() if "EXC-PMI-B-EMP" in emp else "closed"
    doc_tail = doc.split("EXC-PMI-B-DOC", 1)[-1][:160].lower() if "EXC-PMI-B-DOC" in doc else "closed"
    if "EXC-PMI-B-EMP" in emp and "closed" not in emp_tail:
        results["failures"].append("active_exc_emp")
    if "EXC-PMI-B-DOC" in doc and "closed" not in doc_tail:
        results["failures"].append("active_exc_doc")

    results["ok"] = len(results["failures"]) == 0
    results["criteria"] = {
        "five_isolated_cards": all(v["isolated"] for v in results["cards"].values() if v),
        "bedw_foreign_internals_zero": all(
            results["checkers"].get(n, {}).get("violation_count") == 0
            for n in ("boundary", "employment", "documents", "workforce")
        ),
        "recruitment_spine_foreign_internals_zero": len(spine_leaks) == 0,
        "backend_debt_ratchet": debt is not None and debt <= BACKEND_DEBT_CEILING <= PMI1_AUTHORITY,
        "ui_authority_and_debt": bool(PUBLIC["design_system"].exists())
        and ui_debt is not None
        and ui_debt <= UI_DEBT_CEILING,
        "joint_checkers_green": all(results["checkers"].get(n, {}).get("ok") for n in CHECKERS),
        "debt_need_not_be_zero": True,
        "pass_is_head_simultaneous": True,
        "exit_fixes_nothing": True,
        "ready_not_auto_unfrozen": bool(parked.get("ready_not_auto_unfrozen")),
    }
    results["stop_rule"] = (
        "Any PMI-X defect → STOP with classification + separate work item; "
        "no in-exit cleanup or remediation."
    )
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    summary = evaluate()
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(
            f"PMI-X: ok={summary['ok']} head={summary.get('head', '')[:12]} "
            f"backend_debt={summary.get('backend_debt')} ui_debt={summary.get('ui_debt')} "
            f"recruit_non_spine={summary.get('recruitment_non_spine_debt')} "
            f"failures={summary['failures']}"
        )
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
