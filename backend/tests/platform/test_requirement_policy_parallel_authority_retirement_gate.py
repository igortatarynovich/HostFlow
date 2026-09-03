"""Requirement Policy Parallel Authority Retirement Gate (RPM-3A).

Retires independent “need document X?” writers outside R5:
A document_policies · C leftover ruleset writes · J P3B document_required only.
Does not retire field_required / other P3B. Does not start RPM-3B consumer parity.
"""

from __future__ import annotations

from pathlib import Path

from backend.app.reference.requirement_policy_parallel_authority_retirement import (
    CONTRACT_ID,
    DOCUMENT_POLICIES_WRITES_RETIRED,
    P3B_DOCUMENT_REQUIRED_RETIRED,
    RULESET_WRITES_RETIRED,
    filter_out_document_required_overrides,
)
from backend.app.requirement_rules.constants import (
    RULE_TYPE_DOCUMENT_REQUIRED,
    RULE_TYPE_FIELD_REQUIRED,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "requirement-policy-management.md"
_QUEUE = _REPO_ROOT / "docs" / "specs" / "tasks" / "sales-to-comms-sequential-queue.md"
_AGENTS = _REPO_ROOT / "AGENTS.md"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_RETIRE = (
    _REPO_ROOT
    / "backend"
    / "app"
    / "reference"
    / "requirement_policy_parallel_authority_retirement.py"
)
_DOC_POLICIES_API = (
    _REPO_ROOT / "backend" / "app" / "api" / "v1" / "document_policies.py"
)
_DOC_ROUTER = _REPO_ROOT / "backend" / "app" / "modules" / "documents" / "router.py"
_P3B_API = (
    _REPO_ROOT
    / "backend"
    / "app"
    / "api"
    / "v1"
    / "platform"
    / "tenant_requirement_overrides.py"
)
_P3B_APPLY = (
    _REPO_ROOT / "backend" / "app" / "requirement_rules" / "tenant_override_source.py"
)
_OVERLAY_STORE = (
    _REPO_ROOT / "backend" / "app" / "reference" / "document_policy_overlay_store.py"
)
_COMPANIES = _REPO_ROOT / "hostflow-frontend" / "src" / "pages" / "Companies.tsx"
_RULESET_UI = (
    _REPO_ROOT / "hostflow-frontend" / "src" / "pages" / "admin" / "RulesetVersionsPage.tsx"
)


def test_rpm3a_contract_id() -> None:
    assert CONTRACT_ID == "requirement_policy_parallel_authority_retirement.v1"
    assert _RETIRE.is_file()


def test_rpm3a_document_policies_writes_retired() -> None:
    text = _DOC_POLICIES_API.read_text(encoding="utf-8")
    assert "raise_document_policies_writes_retired" in text
    for name in ("create_document_policy", "update_document_policy", "delete_document_policy"):
        block = text[text.index(f"async def {name}") : text.index(f"async def {name}") + 900]
        assert "raise_document_policies_writes_retired" in block, name
    assert DOCUMENT_POLICIES_WRITES_RETIRED in _RETIRE.read_text(encoding="utf-8")
    assert "async def list_document_policies" in text


def test_rpm3a_ruleset_writes_retired_gets_kept() -> None:
    text = _DOC_ROUTER.read_text(encoding="utf-8")
    assert "raise_ruleset_writes_retired" in text
    for name in (
        "api_create_ruleset_version",
        "api_activate_ruleset_version",
        "api_rollback_ruleset_version",
        "api_update_ruleset",
    ):
        block = text[text.index(f"async def {name}") : text.index(f"async def {name}") + 600]
        assert "raise_ruleset_writes_retired" in block, name
    assert "async def api_list_ruleset_versions_route" in text
    assert "async def api_get_ruleset" in text
    assert RULESET_WRITES_RETIRED in _RETIRE.read_text(encoding="utf-8")


def test_rpm3a_p3b_document_required_only() -> None:
    api = _P3B_API.read_text(encoding="utf-8")
    assert "raise_p3b_document_required_retired" in api
    create = api[api.index("async def create_tenant_requirement_override") :]
    create = create[:1200]
    assert "raise_p3b_document_required_retired" in create
    apply_src = _P3B_APPLY.read_text(encoding="utf-8")
    assert "filter_out_document_required_overrides" in apply_src
    filtered = filter_out_document_required_overrides(
        [
            {"rule_type": RULE_TYPE_DOCUMENT_REQUIRED, "target_code": "passport"},
            {"rule_type": RULE_TYPE_FIELD_REQUIRED, "target_code": "license_number"},
            {"rule_type": "document_required", "target_code": "adr_certificate"},
        ]
    )
    assert len(filtered) == 1
    assert filtered[0]["rule_type"] == RULE_TYPE_FIELD_REQUIRED
    assert P3B_DOCUMENT_REQUIRED_RETIRED in _RETIRE.read_text(encoding="utf-8")
    assert "field_required" in api


def test_rpm3a_does_not_rewrite_r5_or_overlay() -> None:
    store = _OVERLAY_STORE.read_text(encoding="utf-8")
    assert "def load_persisted_tenant_delta(" in store
    assert "def save_persisted_tenant_delta(" in store
    assert "merge_resolved_policy" in store


def test_rpm3a_ui_companions() -> None:
    companies = _COMPANIES.read_text(encoding="utf-8")
    assert 'data-rpm3a-document-policies-retired="true"' in companies
    assert "settingsRequirementPolicy" in companies
    ruleset = _RULESET_UI.read_text(encoding="utf-8")
    assert 'data-rpm3a-ruleset-writes-retired="true"' in ruleset
    assert "settingsRequirementPolicy" in ruleset
    assert "handleActivate" not in ruleset


def test_rpm3a_brief_and_queue() -> None:
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "RPM-3A" in brief
    assert "Parallel Authority Retirement" in brief or "parallel authority" in brief.lower()
    assert "document_required" in brief
    assert "field_required" in brief or "other P3B" in brief
    assert "RPM-3A" in brief and ("PASS" in brief or "✅" in brief)
    queue = _QUEUE.read_text(encoding="utf-8")
    assert "RPM-3B" in queue
    assert (
        "Active Product** | **[RPM-3B" in queue
        or "Active (Product):** **[RPM-3B" in queue
        or "Active Product = RPM-3B" in brief
        or "Active = RPM-3B" in brief
    )
    agents = _AGENTS.read_text(encoding="utf-8")
    assert "RPM-3B" in agents


def test_rpm3a_named_ci_gate() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "Requirement Policy Parallel Authority Retirement Gate" in ci
    assert "test_requirement_policy_parallel_authority_retirement_gate.py" in ci
    assert "rpm3a" in ci


def test_rpm3a_gate_filename() -> None:
    assert Path(__file__).name == (
        "test_requirement_policy_parallel_authority_retirement_gate.py"
    )
