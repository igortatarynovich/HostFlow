"""Requirement Policy Consumer Cutover Gate (RPM-3 close).

3A ∧ 3B remain PASS. Remaining live required-set readers load persisted
tenant_delta. D4 matches the operator write. Named leftovers stay
leftover-out-of-scope. Does not reopen 3A/3B, restore writers, or start
Mapping feat.
"""

from __future__ import annotations

from pathlib import Path

from backend.app.reference.requirement_policy_consumer_cutover import (
    CONTRACT_ID,
    LEFTOVER_OUT_OF_SCOPE,
    LIVE_TENANT_DELTA_READERS,
)
from backend.app.reference.requirement_policy_consumer_parity import (
    CONSUMER_CLASSIFICATION,
    PROOF_X_REMOVE,
    PROOF_X_REQUIRE,
    overlay_r5_required_on_expected_rows,
    owner_summary_required_set,
    preview_context,
    r5_required_set,
    remove_overlay_delta,
    require_overlay_delta,
    transfer_candidate_required_set,
)
from backend.app.reference.requirement_policy_parallel_authority_retirement import (
    CONTRACT_ID as RPM3A_CONTRACT_ID,
)
from backend.app.services.document_hub_delivery_contract import (
    project_outstanding_asks_via_contract,
    project_required_doc_applicability_via_contract,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "requirement-policy-management.md"
_ARCH = _REPO_ROOT / "docs" / "specs" / "architecture" / "requirement-policy-authority.md"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_HELPER = _REPO_ROOT / "backend" / "app" / "reference" / "requirement_policy_consumer_cutover.py"
_PARITY = _REPO_ROOT / "backend" / "app" / "reference" / "requirement_policy_consumer_parity.py"
_RETIRE = (
    _REPO_ROOT
    / "backend"
    / "app"
    / "reference"
    / "requirement_policy_parallel_authority_retirement.py"
)
_RESOLVE = _REPO_ROOT / "backend" / "app" / "api" / "v1" / "platform" / "documents_public.py"
_STORE = _REPO_ROOT / "backend" / "app" / "reference" / "document_policy_overlay_store.py"
_DELIVERY = _REPO_ROOT / "backend" / "app" / "services" / "document_hub_delivery_contract.py"
_CHECKER = _REPO_ROOT / "backend" / "app" / "services" / "requirement_checker.py"
_ETA = _REPO_ROOT / "backend" / "app" / "services" / "documents.py"
_APPLICABILITY = _REPO_ROOT / "backend" / "app" / "services" / "document_applicability_policy.py"
_QUEUE = _REPO_ROOT / "docs" / "specs" / "tasks" / "sales-to-comms-sequential-queue.md"

_SCENARIOS = (
    ("base-only", {}),
    ("require-x", require_overlay_delta()),
    ("remove-x", remove_overlay_delta()),
)


def _x_required(required: frozenset[str], delta: dict) -> bool:
    if delta == {}:
        return PROOF_X_REQUIRE not in required and PROOF_X_REMOVE in required
    if "require" in str(delta):
        return PROOF_X_REQUIRE in required
    return PROOF_X_REMOVE not in required


def test_rpm_cutover_gate_filename() -> None:
    assert Path(__file__).name == "test_requirement_policy_consumer_cutover_gate.py"


def test_rpm_cutover_contract_id() -> None:
    assert CONTRACT_ID == "requirement_policy_consumer_cutover.v1"
    assert _HELPER.is_file()
    helper = _HELPER.read_text(encoding="utf-8")
    assert "def merge_resolved_policy(" not in helper
    assert RPM3A_CONTRACT_ID == "requirement_policy_parallel_authority_retirement.v1"
    assert _RETIRE.is_file()
    assert _PARITY.is_file()


def test_rpm_cutover_prior_gates_remain() -> None:
    assert CONSUMER_CLASSIFICATION["A"] == "consume"
    assert CONSUMER_CLASSIFICATION["B"] == "consume"
    assert CONSUMER_CLASSIFICATION["I"] == "already-parity"
    for key in LEFTOVER_OUT_OF_SCOPE:
        assert CONSUMER_CLASSIFICATION[key] == "leftover-out-of-scope"


def test_rpm_cutover_live_readers_load_persisted_delta() -> None:
    marker = "load_persisted_tenant_delta"
    for rel in LIVE_TENANT_DELTA_READERS:
        path = _REPO_ROOT / rel
        assert path.is_file(), rel
        text = path.read_text(encoding="utf-8")
        assert marker in text, rel


def test_rpm_cutover_d4_matches_operator_write() -> None:
    resolve = _RESOLVE.read_text(encoding="utf-8")
    assert "load_persisted_tenant_delta" in resolve
    assert "project_required_doc_applicability_via_contract" in resolve
    assert "tenant_delta=tenant_delta" in resolve
    store = _STORE.read_text(encoding="utf-8")
    assert "def load_persisted_tenant_delta(" in store
    assert "def save_persisted_tenant_delta(" in store
    ctx = preview_context()
    leftover_rows = [
        {"document_code": "passport", "required": False},
        {"document_code": "code95", "required": True},
    ]
    for _name, delta in _SCENARIOS:
        r5 = r5_required_set(ctx, delta)
        assert _x_required(r5, delta), (_name, sorted(r5))
        projected = project_required_doc_applicability_via_contract(tenant_delta=delta)
        projected_required = frozenset(
            str(row.get("doc_type") or "").strip().lower()
            for row in projected
            if str(row.get("applicability") or "") == "required"
            and str(row.get("doc_type") or "").strip()
        )
        assert projected_required == r5
        stamped = overlay_r5_required_on_expected_rows(leftover_rows, ctx, delta)
        assert owner_summary_required_set(ctx, delta) == r5
        assert {row["document_code"] for row in stamped if row.get("required")} == r5


def test_rpm_cutover_outstanding_asks_consume_delta() -> None:
    delivery = _DELIVERY.read_text(encoding="utf-8")
    assert "tenant_delta" in delivery
    assert 'ctx["tenant_delta"]' in delivery or "ctx['tenant_delta']" in delivery
    base_codes = {
        str(row.get("doc_type") or "").strip().lower()
        for row in project_outstanding_asks_via_contract([], tenant_delta={})
    }
    require_codes = {
        str(row.get("doc_type") or "").strip().lower()
        for row in project_outstanding_asks_via_contract([], tenant_delta=require_overlay_delta())
    }
    remove_codes = {
        str(row.get("doc_type") or "").strip().lower()
        for row in project_outstanding_asks_via_contract([], tenant_delta=remove_overlay_delta())
    }
    assert PROOF_X_REMOVE in base_codes
    assert PROOF_X_REMOVE not in remove_codes
    assert require_codes != base_codes


def test_rpm_cutover_stage_and_transfer_do_not_contradict() -> None:
    ctx = preview_context()
    for _name, delta in _SCENARIOS:
        r5 = r5_required_set(ctx, delta)
        assert transfer_candidate_required_set(ctx, delta) == r5
        assert owner_summary_required_set(ctx, delta) == r5


def test_rpm_cutover_named_leftovers_do_not_answer() -> None:
    checker = _CHECKER.read_text(encoding="utf-8")
    assert "document_type_id and not policy.requirement_code" in checker
    eta = _ETA.read_text(encoding="utf-8")
    assert "visa_D" in eta
    assert "prawo_jazdy" in eta
    assert "seal_checklist_required_types" not in eta
    order_api = (_REPO_ROOT / "backend" / "app" / "api" / "v1" / "documents.py").read_text(
        encoding="utf-8"
    )
    assert "seal_checklist_required_types" in order_api
    applicability = _APPLICABILITY.read_text(encoding="utf-8")
    assert "requiredTypes" not in applicability
    assert "merge_resolved_policy" not in applicability


def test_rpm_cutover_brief_gate_pass() -> None:
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "Requirement Policy Consumer Cutover Gate" in brief
    assert CONTRACT_ID.split(".")[0].replace("_", " ") in brief.lower() or CONTRACT_ID in brief
    assert "PASS" in brief
    assert "918274d1" in brief
    assert "Mapping" in brief
    assert "Hiring E2E" in brief
    arch = _ARCH.read_text(encoding="utf-8")
    assert "Consumer Cutover" in arch
    assert "PASS" in arch
    queue = _QUEUE.read_text(encoding="utf-8")
    assert "Consumer Cutover Gate" in queue


def test_rpm_cutover_named_ci_gate() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "Requirement Policy Consumer Cutover Gate" in ci
    assert "test_requirement_policy_consumer_cutover_gate.py" in ci
    assert "rpm_cutover" in ci or "rpm-cutover" in ci
