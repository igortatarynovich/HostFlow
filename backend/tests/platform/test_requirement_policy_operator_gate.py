"""Requirement Policy Operator Gate (RPM-2).

One job UI. Documents-first compiler → validate_tenant_overlay_delta →
merge_resolved_policy → evaluate. Persisted overlay loads into D4 resolve.
Not P3B. Not document_policies. Not ruleset leftover. Not candidate-context proof.
Not Mapping / Hiring E2E / Overlay rewrite / CL8 / Hub packages.
"""

from __future__ import annotations

import ast
from pathlib import Path

from backend.app.document_types.registry import is_canonical_code
from backend.app.reference.document_policy_merge import (
    merge_resolved_policy,
    validate_tenant_overlay_delta,
)
from backend.app.reference.requirement_policy_authority import WRITE_AUTHORITY
from backend.app.reference.requirement_policy_operator import (
    CONTRACT_ID,
    OperatorOverlayError,
    build_operator_view,
    compile_operator_overlay_delta,
    project_operator_override,
)
from backend.app.reference.tenant_lifecycle_participants import (
    OVERLAY_TABLE,
    participant_claims_table,
)
from backend.app.services.document_hub_delivery_contract import (
    APPLICABILITY_REQUIRED,
    evaluate_required_doc_applicability_via_contract,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "requirement-policy-management.md"
_QUEUE = _REPO_ROOT / "docs" / "specs" / "tasks" / "sales-to-comms-sequential-queue.md"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_OPERATOR = (
    _REPO_ROOT / "backend" / "app" / "reference" / "requirement_policy_operator.py"
)
_REPO = (
    _REPO_ROOT
    / "backend"
    / "app"
    / "reference"
    / "document_policy_tenant_overlay_repository.py"
)
_API = (
    _REPO_ROOT
    / "backend"
    / "app"
    / "api"
    / "v1"
    / "platform"
    / "requirement_policy_operator.py"
)
_RESOLVE = (
    _REPO_ROOT / "backend" / "app" / "api" / "v1" / "platform" / "documents_public.py"
)
_MIGRATION = (
    _REPO_ROOT
    / "backend"
    / "alembic"
    / "versions"
    / "202609020002_document_policy_tenant_overlays_rpm2.py"
)
_UI = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "pages"
    / "admin"
    / "RequirementPolicyOperatorPage.tsx"
)
_PATHS = _REPO_ROOT / "shared" / "crm_app_paths.json"
_PARTICIPANTS = (
    _REPO_ROOT / "docs" / "specs" / "platform" / "tenant-lifecycle-participants-v1.json"
)


def _by_state(result: dict) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for row in result.get("applicability") or []:
        if not isinstance(row, dict):
            continue
        state = str(row.get("applicability") or "")
        code = str(row.get("doc_type") or "")
        out.setdefault(state, set()).add(code)
    return out


def test_rpm2_contract_and_compiler() -> None:
    assert CONTRACT_ID == "requirement_policy_operator.v1"
    assert WRITE_AUTHORITY == "r5_merge_pack_tenant_delta"
    empty = compile_operator_overlay_delta(require=[], remove=[])
    assert empty == {}
    validate_tenant_overlay_delta(empty)
    delta = compile_operator_overlay_delta(
        require=["adr_certificate"], remove=["passport"]
    )
    assert delta == {
        "candidate": {
            "overrides": [
                {
                    "when": {},
                    "require": ["adr_certificate"],
                    "remove": ["passport"],
                }
            ]
        }
    }
    validate_tenant_overlay_delta(delta)
    merged = merge_resolved_policy(delta)
    assert "adr_certificate" in (
        (merged.get("candidate") or {}).get("overrides") or [{}]
    )[-1].get("require", [])
    projection = project_operator_override(delta)
    assert projection["require"] == ["adr_certificate"]
    assert projection["remove"] == ["passport"]


def test_rpm2_strict_shape_rejects_noncanonical_and_fork() -> None:
    try:
        compile_operator_overlay_delta(require=["not_a_real_doc_type_zzz"], remove=[])
        raise AssertionError("expected OperatorOverlayError")
    except OperatorOverlayError as exc:
        assert "noncanonical" in str(exc)
    # alias must not pass as operator write — only canonical codes
    assert not is_canonical_code("code95")
    try:
        compile_operator_overlay_delta(require=["code95"], remove=[])
        raise AssertionError("expected OperatorOverlayError for alias")
    except OperatorOverlayError:
        pass
    try:
        validate_tenant_overlay_delta(
            {"candidate": {"defaults": {"requiredTypes": ["passport"]}}}
        )
        raise AssertionError("expected fork rejection")
    except ValueError as exc:
        assert "defaults" in str(exc).lower() or "forbidden" in str(exc).lower()


def test_rpm2_base_is_evaluate_without_delta_not_raw_defaults() -> None:
    view = build_operator_view(
        delta={"candidate": {"overrides": [{"when": {}, "require": ["adr_certificate"]}]}},
        reason="need ADR",
        revision=1,
        preview_context={},
    )
    assert view["contract_id"] == CONTRACT_ID
    assert view["write_authority"] == WRITE_AUTHORITY
    base_state = _by_state(view["base"])
    result_state = _by_state(view["result"])
    assert "passport" in base_state.get(APPLICABILITY_REQUIRED, set())
    assert "adr_certificate" not in base_state.get(APPLICABILITY_REQUIRED, set())
    assert "adr_certificate" in result_state.get(APPLICABILITY_REQUIRED, set())
    # pack_defaults is metadata, not labelled operator base
    assert "requiredTypes" in view["pack_defaults"]
    assert view["base"] is not view["pack_defaults"]


def test_rpm2_evaluate_matches_d4_contract_helper() -> None:
    delta = compile_operator_overlay_delta(require=["adr_certificate"], remove=[])
    direct = evaluate_required_doc_applicability_via_contract(tenant_delta=delta)
    via_view = build_operator_view(delta=delta, reason="x", revision=1)["result"]
    assert _by_state(direct)[APPLICABILITY_REQUIRED] == _by_state(via_view)[
        APPLICABILITY_REQUIRED
    ]


def test_rpm2_ui_four_panels_and_path() -> None:
    assert _UI.is_file()
    ui = _UI.read_text(encoding="utf-8")
    for marker in (
        'data-rpm-base="true"',
        'data-rpm-override="true"',
        'data-rpm-reason="true"',
        'data-rpm-result="true"',
        "expected_revision",
    ):
        assert marker in ui, marker
    paths = _PATHS.read_text(encoding="utf-8")
    assert "settingsRequirementPolicy" in paths
    assert "/app/settings/requirement-policy" in paths


def test_rpm2_api_rbac_read_vs_admin() -> None:
    text = _API.read_text(encoding="utf-8")
    assert "require_trust_read" in text
    assert "require_trust_admin" in text
    assert "compile_operator_overlay_delta" in text
    assert "save_tenant_overlay" in text
    assert "build_operator_view" in text
    get_block = text[text.index("@router.get") : text.index("async def get_requirement_policy_operator")]
    put_block = text[text.index("@router.put") : text.index("async def put_requirement_policy_operator")]
    assert "require_trust_read" in get_block
    assert "require_trust_admin" not in get_block
    assert "require_trust_admin" in put_block
    assert "require_trust_read" not in put_block
    forbidden_snippets = (
        "TenantRequirementOverride",
        "models.document_policy import",
        "models.document_ruleset import",
        "DocumentRulesetVersion",
    )
    for name in forbidden_snippets:
        assert name not in text, name
    op_src = _OPERATOR.read_text(encoding="utf-8")
    for name in forbidden_snippets:
        assert name not in op_src, name
    repo_src = _REPO.read_text(encoding="utf-8")
    for name in forbidden_snippets:
        assert name not in repo_src, name
    assert "DocumentPolicyTenantOverlay" in repo_src
    assert "from backend.app.models.document_policy import" not in repo_src


def test_rpm2_resolve_loads_overlay_via_repository() -> None:
    text = _RESOLVE.read_text(encoding="utf-8")
    assert "load_tenant_delta" in text
    assert "document_policy_tenant_overlay_repository" in text
    assert "tenant_delta=tenant_delta" in text
    assert "project_required_doc_applicability_via_contract(" in text
    tree = ast.parse(_REPO.read_text(encoding="utf-8"))
    names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "load_tenant_delta" in names
    assert "save_tenant_overlay" in names
    # repository must not define a second merge
    assert "merge_resolved_policy" not in names


def test_rpm2_repository_revision_and_atomic_audit() -> None:
    text = _REPO.read_text(encoding="utf-8")
    assert "OverlayRevisionConflict" in text
    assert "expected_revision" in text
    assert "with_for_update" in text
    assert "IntegrityError" in text
    assert "UserAuditLog" in text
    assert '"previous_delta"' in text
    assert '"new_delta"' in text
    assert '"previous_revision"' in text
    assert '"new_revision"' in text
    assert "AUDIT_ACTION" in text
    # payload must not re-SoT actor/tenant
    payload_block = text[text.index("payload={") : text.index("payload={") + 280]
    assert "actor_id" not in payload_block
    assert "tenant_id" not in payload_block


def test_rpm2_migration_rls_and_lifecycle_claim() -> None:
    assert _MIGRATION.is_file()
    mig = _MIGRATION.read_text(encoding="utf-8")
    assert OVERLAY_TABLE in mig
    assert "ENABLE ROW LEVEL SECURITY" in mig
    assert "FORCE ROW LEVEL SECURITY" in mig
    assert "rls_{table}_tenant" in mig or f"rls_{OVERLAY_TABLE}_tenant" in mig
    assert "current_setting('app.tenant_id')" in mig
    assert "WITH CHECK" in mig
    assert participant_claims_table(OVERLAY_TABLE)
    participants = _PARTICIPANTS.read_text(encoding="utf-8")
    assert OVERLAY_TABLE in participants
    assert "requirement_policy_tenant_overlay" in participants
    # Must not be parked on the TI uncovered allowlist (gap may only shrink).
    uncovered = (
        _REPO_ROOT / "backend" / "tests" / "security" / "rls_uncovered_tables.txt"
    )
    if uncovered.is_file():
        allow = {
            line.strip()
            for line in uncovered.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        }
        assert OVERLAY_TABLE not in allow
    force_exc = (
        _REPO_ROOT / "scripts" / "security" / "rls_force_exceptions.txt"
    )
    if force_exc.is_file():
        names = {
            line.split()[0]
            for line in force_exc.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        }
        assert OVERLAY_TABLE not in names


def test_rpm2_brief_and_queue() -> None:
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "Requirement Policy Operator Gate" in brief
    assert "requirement_policy_operator.v1" in brief or CONTRACT_ID in brief
    assert "RPM-2" in brief and "PASS" in brief
    assert "RPM-3A" in brief and "PASS" in brief
    assert "Active Product = RPM-3B" in brief or "Active = RPM-3B" in brief
    assert "document_required" in brief
    assert "policy answer" in brief.lower() or "policy-answer" in brief.lower()
    assert "tenant-level unconditional" in brief.lower() or "unconditional" in brief.lower()
    assert "Mapping" in brief
    assert "Hiring E2E" in brief
    assert "CL8" in brief
    queue = _QUEUE.read_text(encoding="utf-8")
    assert "RPM-3A" in queue
    assert "Parallel Authority Retirement" in queue or "parallel authority" in queue.lower()
    # After Operator Gate PASS, Active Product must not remain RPM-2.
    assert "**Active Product**" in queue or "Active (Product)" in queue
    assert "RPM-2" in queue and "PASS" in queue
    # Active Product line points at RPM-3A, not RPM-2 / bare RPM-3 as live.
    assert (
        "Active Product** | **[RPM-3B" in queue
        or "Active (Product):** **[RPM-3B" in queue
        or "**Active Product** | **[RPM-3B" in queue
    )

def test_rpm2_named_ci_gate() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "Requirement Policy Operator Gate" in ci
    assert "test_requirement_policy_operator_gate.py" in ci
    assert "rpm2" in ci


def test_rpm2_gate_filename() -> None:
    assert Path(__file__).name == "test_requirement_policy_operator_gate.py"
