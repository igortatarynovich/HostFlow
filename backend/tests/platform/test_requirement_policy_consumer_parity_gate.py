"""Requirement Policy Consumer Parity Gate (RPM-3B).

Same pack + same tenant_delta → R5 resolved policy → each surviving consumer
→ identical required-set membership (base / require X / remove X).
Does not restore writers, rewrite Overlay, or start Mapping / program close.
"""

from __future__ import annotations

from pathlib import Path

from backend.app.reference.requirement_policy_consumer_parity import (
    CONSUMER_CLASSIFICATION,
    CONTRACT_ID,
    PROOF_X_REMOVE,
    PROOF_X_REQUIRE,
    engine_document_required_set,
    expected_rows_required_set,
    leftover_ruleset_payload,
    overlay_r5_required_on_expected_rows,
    owner_summary_required_set,
    pack_grouping_required_set,
    preview_context,
    r5_required_set,
    remove_overlay_delta,
    require_overlay_delta,
    transfer_candidate_required_set,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "requirement-policy-management.md"
_QUEUE = _REPO_ROOT / "docs" / "specs" / "tasks" / "sales-to-comms-sequential-queue.md"
_AGENTS = _REPO_ROOT / "AGENTS.md"
_ARCH = _REPO_ROOT / "docs" / "specs" / "architecture" / "requirement-policy-authority.md"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_HELPER = _REPO_ROOT / "backend" / "app" / "reference" / "requirement_policy_consumer_parity.py"
_MERGE = _REPO_ROOT / "backend" / "app" / "reference" / "document_policy_merge.py"
_STORE = _REPO_ROOT / "backend" / "app" / "reference" / "document_policy_overlay_store.py"
_OVERLAY_RT = _REPO_ROOT / "backend" / "app" / "entity_profile" / "vacancy_overlay_runtime.py"
_ENGINE = _REPO_ROOT / "backend" / "app" / "requirement_rules" / "registry.py"
_PACKS = _REPO_ROOT / "backend" / "app" / "modules" / "documents" / "pack_definitions.py"
_TRANSFER = _REPO_ROOT / "backend" / "app" / "services" / "transfer_policy_resolver.py"
_RESOLVER = _REPO_ROOT / "backend" / "app" / "services" / "document_applicability_resolver.py"
_CHECKER = _REPO_ROOT / "backend" / "app" / "services" / "requirement_checker.py"
_APPLICABILITY = _REPO_ROOT / "backend" / "app" / "services" / "document_applicability_policy.py"
_FE_STAGE = _REPO_ROOT / "hostflow-frontend" / "src" / "utils" / "candidateStageDocPolicy.ts"

_SCENARIOS = (
    ("base-only", {}),
    ("require-x", require_overlay_delta()),
    ("remove-x", remove_overlay_delta()),
)

_PACK_CTX = {
    "citizenship": "UA",
    "work_country": "PL",
    "position_category": "driver",
}


def _x_required(required: frozenset[str], delta: dict) -> bool:
    if delta == {}:
        return PROOF_X_REQUIRE not in required and PROOF_X_REMOVE in required
    if "require" in str(delta):
        return PROOF_X_REQUIRE in required
    return PROOF_X_REMOVE not in required


def test_rpm3b_gate_filename() -> None:
    assert Path(__file__).name == "test_requirement_policy_consumer_parity_gate.py"


def test_rpm3b_contract_id() -> None:
    assert CONTRACT_ID == "requirement_policy_consumer_parity.v1"
    assert _HELPER.is_file()
    helper = _HELPER.read_text(encoding="utf-8")
    assert "def merge_resolved_policy(" not in helper
    assert "evaluate_required_doc_applicability_via_contract" in helper


def test_rpm3b_classification_covers_matrix() -> None:
    assert CONSUMER_CLASSIFICATION["A"] == "consume"
    assert CONSUMER_CLASSIFICATION["B"] == "consume"
    assert CONSUMER_CLASSIFICATION["C"] == "consume"
    assert CONSUMER_CLASSIFICATION["D"] == "leftover-out-of-scope"
    assert CONSUMER_CLASSIFICATION["E"] == "consume"
    assert CONSUMER_CLASSIFICATION["F"] == "consume"
    assert CONSUMER_CLASSIFICATION["G"] == "consume"
    assert CONSUMER_CLASSIFICATION["H"] == "already-parity"
    assert CONSUMER_CLASSIFICATION["I"] == "already-parity"
    assert CONSUMER_CLASSIFICATION["requirement_checker_gates"] == "leftover-out-of-scope"
    assert CONSUMER_CLASSIFICATION["documents_eta_legacy_codes"] == "leftover-out-of-scope"


def test_rpm3b_policy_answer_parity_b_c_e_g() -> None:
    ctx = preview_context()
    leftover = leftover_ruleset_payload()
    for _name, delta in _SCENARIOS:
        r5 = r5_required_set(ctx, delta)
        assert _x_required(r5, delta), (_name, sorted(r5))
        assert owner_summary_required_set(ctx, delta, leftover_ruleset=leftover) == r5
        assert transfer_candidate_required_set(ctx, delta) == r5
        assert engine_document_required_set({}, tenant_delta=delta, owner_context=ctx) == r5
        assert leftover["candidate"]["defaults"]["requiredTypes"] != sorted(r5)


def test_rpm3b_pack_grouping_subset_never_invents() -> None:
    for _name, delta in _SCENARIOS:
        r5 = r5_required_set(_PACK_CTX, delta)
        packs = pack_grouping_required_set(_PACK_CTX, delta)
        assert packs <= r5
        assert PROOF_X_REQUIRE not in packs
        if delta == {}:
            assert PROOF_X_REMOVE in packs
        if delta == remove_overlay_delta():
            assert PROOF_X_REMOVE not in packs


def test_rpm3b_applicability_rows_consume_r5() -> None:
    leftover_rows = [
        {"document_code": "passport", "required": False},
        {"document_code": "code95", "required": True},
    ]
    ctx = preview_context()
    for _name, delta in _SCENARIOS:
        r5 = r5_required_set(ctx, delta)
        stamped = overlay_r5_required_on_expected_rows(leftover_rows, ctx, delta)
        assert expected_rows_required_set(stamped) == r5
        by_code = {str(row["document_code"]): row for row in stamped}
        assert by_code["code95"]["required"] is False
        assert by_code[PROOF_X_REMOVE]["required"] is (PROOF_X_REMOVE in r5)
        if PROOF_X_REQUIRE in r5:
            assert by_code[PROOF_X_REQUIRE]["required"] is True
        else:
            assert PROOF_X_REQUIRE not in by_code


def test_rpm3b_live_paths_consume_not_invent() -> None:
    engine = _ENGINE.read_text(encoding="utf-8")
    assert "r5_merge_pack_tenant_delta" in engine
    assert "r5_required_set" in engine
    packs = _PACKS.read_text(encoding="utf-8")
    assert "r5_required_set" in packs
    assert "derive_document_applicability_decision" not in packs
    transfer = _TRANSFER.read_text(encoding="utf-8")
    assert "r5_required_set" in transfer
    assert "transfer_operation_documents" in transfer
    resolver = _RESOLVER.read_text(encoding="utf-8")
    assert "overlay_r5_required_on_expected_rows" in resolver
    checker = _CHECKER.read_text(encoding="utf-8")
    assert "document_type_id and not policy.requirement_code" in checker
    applicability = _APPLICABILITY.read_text(encoding="utf-8")
    assert "requiredTypes" not in applicability
    assert "merge_resolved_policy" not in applicability


def test_rpm3b_overlay_and_r5_unchanged() -> None:
    overlay = _OVERLAY_RT.read_text(encoding="utf-8")
    assert "ERROR_R5_POLICY_MERGE" in overlay
    merge = _MERGE.read_text(encoding="utf-8")
    assert "def merge_resolved_policy(" in merge
    store = _STORE.read_text(encoding="utf-8")
    assert "def load_persisted_tenant_delta(" in store
    assert "def save_persisted_tenant_delta(" in store
    assert "def merge_resolved_policy(" not in store


def test_rpm3b_frontend_does_not_invent_types() -> None:
    fe = _FE_STAGE.read_text(encoding="utf-8")
    assert "adr_certificate" not in fe
    assert "requiredTypes" not in fe
    assert "passport" not in fe


def test_rpm3b_brief_and_queue() -> None:
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "Requirement Policy Consumer Parity Gate" in brief
    assert "RPM-3B" in brief and ("PASS" in brief or "✅" in brief)
    assert "base-only" in brief or "base / require" in brief or "require X" in brief
    assert "field_required" in brief
    assert "Mapping" in brief
    queue = _QUEUE.read_text(encoding="utf-8")
    assert "Consumer Cutover Gate" in queue
    assert (
        "Active Product** | **[RPM-3" not in queue
        or "Consumer Cutover" in queue
    )
    assert (
        "Active (Product):** **Consumer Cutover Gate" in queue
        or "Active Product = Consumer Cutover Gate" in brief
        or "Active = Consumer Cutover Gate" in brief
        or "Active:** **Consumer Cutover Gate" in brief
    )
    agents = _AGENTS.read_text(encoding="utf-8")
    assert "Consumer Cutover" in agents or "RPM-3B" in agents
    arch = _ARCH.read_text(encoding="utf-8")
    assert "RPM-3B" in arch
    assert "PASS" in arch


def test_rpm3b_named_ci_gate() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "Requirement Policy Consumer Parity Gate" in ci
    assert "test_requirement_policy_consumer_parity_gate.py" in ci
    assert "rpm3b" in ci
