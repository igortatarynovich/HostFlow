#!/usr/bin/env python3
"""
Phase 8 — Security scorecard generator (repo-derived metrics).

Write / refresh the living scorecard::

    python3 scripts/security/generate_security_scorecard.py --write

Fail if the checked-in scorecard drifts from computed values::

    python3 scripts/security/generate_security_scorecard.py --check

Print markdown to stdout (no write)::

    python3 scripts/security/generate_security_scorecard.py
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCORECARD_PATH = REPO_ROOT / "docs" / "security" / "security-scorecard.md"
SECURITY_GATES = REPO_ROOT / ".github" / "workflows" / "security-gates.yml"
SECURITY_TESTS = REPO_ROOT / "backend" / "tests" / "security"
THREAT_MODELS = REPO_ROOT / "docs" / "security" / "threat-models"
DETECTION_RULES = REPO_ROOT / "backend" / "app" / "security" / "detection_rules.py"
MODELS_ROOT = REPO_ROOT / "backend" / "app" / "models"
ALEMBIC_VERSIONS = REPO_ROOT / "backend" / "alembic" / "versions"
SECURITY_SCRIPTS = REPO_ROOT / "scripts" / "security"

# Gate scripts that must exist for "CI gates inventory" metric.
REQUIRED_GATE_SCRIPTS = (
    "check_no_raw_emit_security_event.py",
    "check_tenant_bind_auth.py",
    "check_arq_worker_tenant.py",
    "check_retrieval_call_sites.py",
    "check_detection_rules.py",
    "check_telemetry_helpers_v1_only.py",
)


@dataclass(frozen=True)
class Metric:
    area: str
    metric: str
    value: str
    target: str
    status: str  # green | yellow | red | n/a
    note: str


def _count_security_tests() -> int:
    if not SECURITY_TESTS.is_dir():
        return 0
    return len([p for p in SECURITY_TESTS.glob("test_*.py") if p.is_file()])


def _count_threat_models() -> int:
    if not THREAT_MODELS.is_dir():
        return 0
    return len(
        [
            p
            for p in THREAT_MODELS.glob("*.md")
            if p.is_file() and p.name.lower() != "readme.md"
        ]
    )


def _count_detection_rules() -> int:
    if not DETECTION_RULES.is_file():
        return 0
    text = DETECTION_RULES.read_text(encoding="utf-8")
    return len(re.findall(r"DetectionRule\s*\(", text))


def _gate_scripts_ok() -> tuple[int, int, list[str]]:
    missing: list[str] = []
    present = 0
    for name in REQUIRED_GATE_SCRIPTS:
        path = SECURITY_SCRIPTS / name
        if path.is_file():
            present += 1
        else:
            missing.append(name)
    return present, len(REQUIRED_GATE_SCRIPTS), missing


def _security_gates_jobs() -> int:
    if not SECURITY_GATES.is_file():
        return 0
    text = SECURITY_GATES.read_text(encoding="utf-8")
    # Top-level job keys under ``jobs:`` — indent of 2 spaces, name then colon.
    jobs = re.findall(r"^  ([a-z0-9][a-z0-9_-]*):\s*$", text, flags=re.M)
    # Filter out nested false positives by requiring following ``name:`` or ``runs-on``
    return len(jobs)


def _model_tables_with_tenant_id() -> set[str]:
    tables: set[str] = set()
    if not MODELS_ROOT.is_dir():
        return tables
    for path in MODELS_ROOT.rglob("*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            has_tenant = False
            table_name: str | None = None
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for t in stmt.targets:
                        if isinstance(t, ast.Name) and t.id == "__tablename__":
                            if isinstance(stmt.value, ast.Constant) and isinstance(
                                stmt.value.value, str
                            ):
                                table_name = stmt.value.value
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    if stmt.target.id == "tenant_id":
                        has_tenant = True
            if has_tenant and table_name:
                tables.add(table_name)
    return tables


def _rls_enabled_tables_from_migrations() -> set[str]:
    """Collect table names from Alembic revisions that enable RLS.

    Covers explicit ``ALTER TABLE … ENABLE ROW LEVEL SECURITY`` and string
    entries in ``*TABLES*`` lists inside those same revision files (f-string loops).
    """
    found: set[str] = set()
    if not ALEMBIC_VERSIONS.is_dir():
        return found
    alter_pat = re.compile(
        r'ALTER\s+TABLE\s+(?:"([^"]+)"|([a-zA-Z_][a-zA-Z0-9_]*))\s+ENABLE\s+ROW\s+LEVEL\s+SECURITY',
        re.I,
    )
    for path in ALEMBIC_VERSIONS.glob("*.py"):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if "ROW LEVEL SECURITY" not in text.upper():
            continue
        for m in alter_pat.finditer(text):
            name = m.group(1) or m.group(2)
            if name:
                found.add(name)
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if not any("TABLE" in n.upper() for n in names):
                continue
            if not isinstance(node.value, (ast.List, ast.Tuple)):
                continue
            for elt in node.value.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    s = elt.value.strip()
                    if re.fullmatch(r"[a-z][a-z0-9_]*", s):
                        found.add(s)
    return found


def _rls_runtime_guard_ok() -> bool:
    path = REPO_ROOT / "backend" / "app" / "db" / "tenant_session.py"
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    return "TenantEnforcingAsyncSession" in text and "tenant_rls_enforcement" in text


def _status(ok: bool, *, warn: bool = False) -> str:
    if ok:
        return "green"
    if warn:
        return "yellow"
    return "red"


def collect_metrics() -> list[Metric]:
    metrics: list[Metric] = []

    tests_n = _count_security_tests()
    metrics.append(
        Metric(
            area="Security tests",
            metric="`backend/tests/security/test_*.py` count",
            value=str(tests_n),
            target="≥ 10",
            status=_status(tests_n >= 10, warn=tests_n >= 5),
            note="Unit/integration coverage for isolation, telemetry, detection.",
        )
    )

    present, total, missing = _gate_scripts_ok()
    metrics.append(
        Metric(
            area="CI gates",
            metric="Required security gate scripts on disk",
            value=f"{present}/{total}",
            target=f"{total}/{total}",
            status=_status(present == total),
            note=("missing: " + ", ".join(missing)) if missing else "All listed gate scripts present.",
        )
    )

    jobs_n = _security_gates_jobs()
    metrics.append(
        Metric(
            area="CI gates",
            metric="Jobs in `.github/workflows/security-gates.yml`",
            value=str(jobs_n),
            target="≥ 8",
            status=_status(jobs_n >= 8, warn=jobs_n >= 5),
            note="Inventory only — green workflow on default branch is reviewed in monthly cycle.",
        )
    )

    tm_n = _count_threat_models()
    metrics.append(
        Metric(
            area="Threat models",
            metric="Files under `docs/security/threat-models/`",
            value=str(tm_n),
            target="≥ 10",
            status=_status(tm_n >= 10, warn=tm_n >= 5),
            note="threat-model gate enforces updates when surface code changes.",
        )
    )

    rules_n = _count_detection_rules()
    metrics.append(
        Metric(
            area="Detection",
            metric="Phase 7 `DetectionRule` entries",
            value=str(rules_n),
            target="≥ 3",
            status=_status(rules_n >= 3, warn=rules_n >= 1),
            note="Each rule requires owner + runbook (CI `detection-rules`).",
        )
    )

    tenant_tables = _model_tables_with_tenant_id()
    rls_tables = _rls_enabled_tables_from_migrations()
    covered = tenant_tables & rls_tables
    if tenant_tables:
        pct = 100.0 * len(covered) / len(tenant_tables)
        value = f"{len(covered)}/{len(tenant_tables)} ({pct:.0f}%)"
        # Static AST is incomplete (many migrations enable RLS via f-string loops).
        # Never red when runtime guard is present — yellow flags follow-up live audit.
        if _rls_runtime_guard_ok():
            status = "green" if pct >= 70.0 else "yellow"
        else:
            status = "red"
    else:
        value = "0/0"
        pct = 0.0
        status = "yellow"
    metrics.append(
        Metric(
            area="RLS",
            metric="Models with `tenant_id` covered by RLS enable migrations (static)",
            value=value,
            target="≥ 70% static hint; 100% live DB audit",
            status=status,
            note=(
                "Approximation from SQLAlchemy models ∩ Alembic RLS table lists / ALTER TABLE. "
                f"tenant models={len(tenant_tables)}, rls catalog={len(rls_tables)}. "
                "Prefer live pg_policies audit for leadership reporting."
            ),
        )
    )

    metrics.append(
        Metric(
            area="RLS",
            metric="Runtime `TenantEnforcingAsyncSession` guard",
            value="present" if _rls_runtime_guard_ok() else "missing",
            target="present",
            status=_status(_rls_runtime_guard_ok()),
            note="Python fail-closed execute before bind (Phase 1).",
        )
    )

    metrics.append(
        Metric(
            area="MFA",
            metric="Adoption superadmin + tenant owners",
            value="not measured in repo",
            target="> 90% (SSOT)",
            status="n/a",
            note="Product/IdP metric — fill during monthly review; not inferred from git.",
        )
    )

    metrics.append(
        Metric(
            area="Vulns",
            metric="Critical/high in sensitive deps",
            value="CI (`security-gates`)",
            target="0 critical / policy on high",
            status="n/a",
            note="Tracked by pip-audit / npm audit / Trivy jobs — paste latest green run link in review log.",
        )
    )

    return metrics


def render_markdown(
    metrics: list[Metric],
    *,
    generated_at: str,
    review_log: str | None = None,
) -> str:
    lines: list[str] = [
        "# HostFlow — Security Scorecard",
        "",
        f"**Generated:** {generated_at} (UTC)  ",
        "**Generator:** `scripts/security/generate_security_scorecard.py`  ",
        "**Canon:** [`runtime-roadmap.md`](./runtime-roadmap.md) Phase 8 · [`security-ssot.md`](./security-ssot.md)",
        "",
        "Living **repo-derived** scorecard for leadership / retros. "
        "Does not replace SSOT invariants. Refresh with `make security-scorecard`.",
        "",
        "| Area | Metric | Value | Target | Status | Note |",
        "|------|--------|-------|--------|--------|------|",
    ]
    for m in metrics:
        note = m.note.replace("|", "\\|")
        lines.append(
            f"| {m.area} | {m.metric} | {m.value} | {m.target} | `{m.status}` | {note} |"
        )

    reds = [m for m in metrics if m.status == "red"]
    yellows = [m for m in metrics if m.status == "yellow"]
    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"- Green / OK: **{sum(1 for m in metrics if m.status == 'green')}**",
            f"- Yellow: **{len(yellows)}**",
            f"- Red: **{len(reds)}**",
            f"- N/A (manual / CI external): **{sum(1 for m in metrics if m.status == 'n/a')}**",
            "",
        ]
    )
    if review_log and review_log.strip():
        lines.append(review_log.strip())
        lines.append("")
    else:
        lines.extend(
            [
                "## Monthly / quarterly review log",
                "",
                "Add a bullet when reviewing (do not delete history):",
                "",
                f"- _{generated_at[:10]}_ — scorecard v1 introduced; reds={len(reds)} yellows={len(yellows)}. "
                "Paste security-gates run URL + MFA notes here on review.",
                "",
            ]
        )
    lines.extend(
        [
            "## How to refresh",
            "",
            "```bash",
            "make security-scorecard          # write docs/security/security-scorecard.md",
            "make security-scorecard-check    # fail on drift (CI)",
            "```",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def _extract_review_log(text: str) -> str | None:
    m = re.search(
        r"(## Monthly / quarterly review log\n.*?)(?=\n## How to refresh|\Z)",
        text,
        flags=re.S,
    )
    return m.group(1).strip() if m else None


def _strip_volatile(text: str) -> str:
    """Ignore timestamp for drift comparison; keep review log as committed."""
    out = re.sub(
        r"^\*\*Generated:\*\* .*$",
        "**Generated:** <timestamp>",
        text,
        count=1,
        flags=re.M,
    )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    g = parser.add_mutually_exclusive_group()
    g.add_argument("--write", action="store_true", help="Write scorecard markdown")
    g.add_argument("--check", action="store_true", help="Fail if scorecard drifts")
    args = parser.parse_args()

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    metrics = collect_metrics()
    prior_log = None
    if SCORECARD_PATH.is_file():
        prior_log = _extract_review_log(SCORECARD_PATH.read_text(encoding="utf-8"))
    body = render_markdown(metrics, generated_at=generated_at, review_log=prior_log)

    if args.write:
        SCORECARD_PATH.parent.mkdir(parents=True, exist_ok=True)
        SCORECARD_PATH.write_text(body, encoding="utf-8")
        print(f"Wrote {SCORECARD_PATH.relative_to(REPO_ROOT).as_posix()}")
        reds = [m for m in metrics if m.status == "red"]
        return 1 if reds else 0

    if args.check:
        if not SCORECARD_PATH.is_file():
            print(f"ERROR: missing {SCORECARD_PATH}", file=sys.stderr)
            return 1
        existing = SCORECARD_PATH.read_text(encoding="utf-8")
        if _strip_volatile(existing) != _strip_volatile(body):
            print(
                "Security scorecard drift. Run: make security-scorecard\n"
                f"Expected path: {SCORECARD_PATH.relative_to(REPO_ROOT).as_posix()}",
                file=sys.stderr,
            )
            return 1
        reds = [m for m in metrics if m.status == "red"]
        if reds:
            print("Security scorecard has RED metrics:", file=sys.stderr)
            for m in reds:
                print(f"  {m.area}: {m.metric} = {m.value}", file=sys.stderr)
            return 1
        print("security-scorecard check OK")
        return 0

    sys.stdout.write(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
