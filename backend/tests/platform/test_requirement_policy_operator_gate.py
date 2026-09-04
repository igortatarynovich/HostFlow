"""Requirement Policy Operator Gate (RPM-2).

One writer of the existing R5 tenant_delta. GET returns resolved_policy from
merge_resolved_policy. reason is sibling metadata. D4 proof is operational
applicability, not a sample evaluator.
"""

from __future__ import annotations

from pathlib import Path

from backend.app.reference.document_policy_merge import merge_resolved_policy
from backend.app.reference.document_policy_overlay_store import (
    overlay_delta_payload,
    resolved_policy_from_delta,
)
from backend.app.services.document_hub_delivery_contract import (
    APPLICABILITY_REQUIRED,
    evaluate_required_doc_applicability_via_contract,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "requirement-policy-management.md"
_ARCH = _REPO_ROOT / "docs" / "specs" / "architecture" / "requirement-policy-authority.md"
_MERGE = _REPO_ROOT / "backend" / "app" / "reference" / "document_policy_merge.py"
_STORE = _REPO_ROOT / "backend" / "app" / "reference" / "document_policy_overlay_store.py"
_API = _REPO_ROOT / "backend" / "app" / "api" / "v1" / "platform" / "document_policy_overlay.py"
_RESOLVE = _REPO_ROOT / "backend" / "app" / "api" / "v1" / "platform" / "documents_public.py"
_MODEL = _REPO_ROOT / "backend" / "app" / "models" / "tenant_document_policy_delta.py"
_PAGE = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "pages"
    / "admin"
    / "RequirementPolicyOverlayPage.tsx"
)
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_QUEUE = _REPO_ROOT / "docs" / "specs" / "tasks" / "sales-to-comms-sequential-queue.md"
_AGENTS = _REPO_ROOT / "AGENTS.md"

PROOF_DELTA = {
    "vacancy": {
        "additions": [{"when": {}, "require": ["adr_certificate"]}],
    }
}


def test_rpm2_gate_filename() -> None:
    assert Path(__file__).name == "test_requirement_policy_operator_gate.py"


def test_rpm2_brief_names_operator_gate() -> None:
    text = _BRIEF.read_text(encoding="utf-8")
    assert "Requirement Policy Operator Gate" in text
    assert "resolved_policy" in text
    assert "sibling" in text.lower() or "sibling column" in text
    assert "merge_resolved_policy" in text
    assert "sample" not in text.lower() or "not a sample" in text.lower() or "not a hypothetical" in text.lower()
    assert "Mapping Authority" in text or "mapping-authority.md" in text
    assert "lead_criteria_v1" in text
    assert "tenant_requirement_overrides" in text or "second store" in text.lower()
    assert "RPM-3A" in text
    assert "Parallel Authority Retirement" in text or "parallel authority retirement" in text.lower()
    assert "RPM-3B" in text
    queue = _QUEUE.read_text(encoding="utf-8")
    assert "RPM-3A" in queue
    assert "RPM-3B" in queue
    agents = _AGENTS.read_text(encoding="utf-8")
    assert "RPM-3A" in agents or "RPM-3B" in agents


def test_rpm2_does_not_reopen_authority_or_merge() -> None:
    arch = _ARCH.read_text(encoding="utf-8")
    assert "requirement_policy_authority.v1" in arch
    assert "nine rows" in arch.lower() or "Nine" in arch
    merge = _MERGE.read_text(encoding="utf-8")
    assert "def merge_resolved_policy(" in merge
    assert "def validate_tenant_overlay_delta(" in merge
    store = _STORE.read_text(encoding="utf-8")
    assert "merge_resolved_policy" in store
    assert "validate_tenant_overlay_delta" in store
    assert "def merge_resolved_policy(" not in store


def test_rpm2_reason_is_metadata_not_delta() -> None:
    model = _MODEL.read_text(encoding="utf-8")
    api = _API.read_text(encoding="utf-8")
    store = _STORE.read_text(encoding="utf-8")
    assert "reason" in model
    assert "tenant_delta" in model
    assert "reason is metadata" in store or "sibling" in store
    assert "resolved_policy" in api
    assert "sample" not in api.lower()
    try:
        overlay_delta_payload({"reason": "operator note", "vacancy": {"additions": []}})
    except ValueError as exc:
        assert "reason" in str(exc)
    else:
        raise AssertionError("reason must not be accepted inside tenant_delta")


def test_rpm2_resolved_policy_is_existing_merge() -> None:
    merged = merge_resolved_policy(PROOF_DELTA)
    via_store = resolved_policy_from_delta(PROOF_DELTA)
    assert via_store == merged
    additions = (via_store.get("vacancy") or {}).get("additions") or []
    required = [
        code
        for rule in additions
        if isinstance(rule, dict)
        for code in (rule.get("require") or [])
    ]
    assert "adr_certificate" in required


def test_rpm2_d4_projection_uses_same_merge_delta() -> None:
    empty = evaluate_required_doc_applicability_via_contract()
    overlay = evaluate_required_doc_applicability_via_contract(tenant_delta=PROOF_DELTA)
    empty_required = {
        row["doc_type"]
        for row in empty.get("applicability") or []
        if row.get("applicability") == APPLICABILITY_REQUIRED
    }
    overlay_required = {
        row["doc_type"]
        for row in overlay.get("applicability") or []
        if row.get("applicability") == APPLICABILITY_REQUIRED
    }
    assert "adr_certificate" not in empty_required
    assert "adr_certificate" in overlay_required


def test_rpm2_d4_resolve_loads_persisted_delta() -> None:
    resolve = _RESOLVE.read_text(encoding="utf-8")
    assert "load_persisted_tenant_delta" in resolve
    assert "project_required_doc_applicability_via_contract" in resolve
    assert "tenant_delta=tenant_delta" in resolve or "tenant_delta = tenant_delta" in resolve


def test_rpm2_one_operator_page() -> None:
    page = _PAGE.read_text(encoding="utf-8")
    assert 'data-rpm-operator="true"' in page
    assert "resolved_policy" in page
    assert "sample" not in page.lower()
    assert "requirement-overrides" not in page
    ci = _CI.read_text(encoding="utf-8")
    assert "Requirement Policy Operator Gate" in ci
    assert "test_requirement_policy_operator_gate.py" in ci
