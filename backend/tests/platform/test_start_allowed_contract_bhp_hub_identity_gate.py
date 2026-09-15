"""start_allowed Contract/BHP Hub identity gate.

Named gate: start-allowed-contract-bhp-hub-identity-gate

Canon: Hub stores ``employment_contract`` and ``bhp`` (not additional_document).
start_allowed picks via ``document_storage_type_matches`` (shared bridge).
No type-specific if in orchestrator. Does not reopen Full Spine.
"""

from __future__ import annotations

from pathlib import Path

from backend.app.document_types.definitions import DOCUMENT_TYPE_DEFINITIONS
from backend.app.reference.employment_start_allowed import (
    DECISION_START_ALLOWED,
    evaluate_employment_start_allowed_v1,
)
from backend.app.services.document_catalog import DOCUMENT_TYPE_DEFAULTS, normalize_doc_type
from backend.app.services.document_type_canonical_bridge import (
    document_storage_type_matches,
    hub_storage_keys_for_requirement_code,
    normalize_legacy_doc_type,
)
from backend.app.services.employment_start_allowed_evidence import (
    project_bhp_evidence_view,
    project_contract_evidence_view,
    project_medical_evidence_view,
)
from backend.app.services.employment_start_allowed_orchestrator import _pick_doc

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "start-allowed-contract-bhp-hub-identity-gap.md"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_ORCH = _REPO_ROOT / "backend" / "app" / "services" / "employment_start_allowed_orchestrator.py"
_BRIDGE = _REPO_ROOT / "backend" / "app" / "services" / "document_type_canonical_bridge.py"
_DEFS = _REPO_ROOT / "backend" / "app" / "document_types" / "definitions.py"


def _pem1_ctx(**extra):
    ctx = {
        "employment_country": "PL",
        "pathway_id": "pl_eu_eea_free_movement",
        "contract_type": "employment_contract",
        "employer_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "post_key": "driver_ce",
        "planned_start_date": "2026-10-01",
    }
    ctx.update(extra)
    return ctx


def test_gate_filename() -> None:
    assert Path(__file__).name == "test_start_allowed_contract_bhp_hub_identity_gate.py"


def test_brief_locks_inventory_and_canon() -> None:
    text = _BRIEF.read_text(encoding="utf-8")
    assert "employment_contract" in text
    assert "bhp" in text
    assert "additional_document" in text
    assert "meta.type" in text
    assert "Full Spine" in text
    assert "if contract" in text.lower() or "if bhp" in text.lower()


def test_hub_stores_contract_and_bhp_not_additional() -> None:
    codes = {d.code for d in DOCUMENT_TYPE_DEFINITIONS}
    assert "employment_contract" in codes
    assert "bhp" in codes
    assert "employment_contract" in DOCUMENT_TYPE_DEFAULTS
    assert "bhp" in DOCUMENT_TYPE_DEFAULTS
    assert normalize_doc_type("employment_contract") == "employment_contract"
    assert normalize_doc_type("contract") == "employment_contract"
    assert normalize_doc_type("umowa_o_prace") == "employment_contract"
    assert normalize_doc_type("bhp") == "bhp"
    assert normalize_doc_type("szkolenia_bhp") == "bhp"
    assert normalize_doc_type("bhp_instruction") == "bhp"
    assert normalize_doc_type("employment_contract") != "additional_document"
    assert normalize_doc_type("bhp") != "additional_document"


def test_ref_bridge_aligns_contract_and_bhp() -> None:
    assert normalize_legacy_doc_type("umowa_o_prace") == "employment_contract"
    assert normalize_legacy_doc_type("contract") == "employment_contract"
    assert normalize_legacy_doc_type("szkolenia_bhp") == "bhp"
    assert "umowa_o_prace" in hub_storage_keys_for_requirement_code("employment_contract")
    assert "szkolenia_bhp" in hub_storage_keys_for_requirement_code("bhp")


def test_shared_match_no_consumer_alias_table() -> None:
    assert document_storage_type_matches("employment_contract", "umowa_o_prace", "contract")
    assert document_storage_type_matches("umowa_o_prace", "employment_contract")
    assert document_storage_type_matches("bhp", "szkolenia_bhp", "bhp_instruction")
    assert not document_storage_type_matches("additional_document", "employment_contract", "bhp")


def test_pick_doc_uses_shared_authority() -> None:
    docs = [
        {"id": "1", "type": "additional_document", "meta": {}},
        {
            "id": "2",
            "type": "employment_contract",
            "status": "approved",
            "meta": {"signed_at": "2026-09-20", "employer_name": "PL Sp."},
        },
        {
            "id": "3",
            "type": "bhp",
            "status": "approved",
            "meta": {
                "training_date": "2026-09-15",
                "training_kind": "introductory",
                "employer_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                "post_key": "driver_ce",
            },
        },
    ]
    contract = _pick_doc(docs, "employment_contract", "umowa_o_prace", "contract")
    bhp = _pick_doc(docs, "bhp", "szkolenia_bhp", "introductory_bhp")
    assert contract is not None and contract["id"] == "2"
    assert bhp is not None and bhp["id"] == "3"
    assert _pick_doc(docs, "medical_certificate") is None


def test_start_allowed_true_with_hub_typed_evidence() -> None:
    contract = project_contract_evidence_view(
        {
            "id": "c1",
            "type": "employment_contract",
            "meta": {
                "signed_at": "2026-09-20",
                "employer_name": "PL Sp. z o.o.",
                "start_at": "2026-10-01",
            },
        }
    )
    medical = project_medical_evidence_view(
        {
            "id": "m1",
            "type": "medical_certificate",
            "meta": {
                "expires_at": "2027-01-01",
                "fit_for_work": True,
                "applies_to_post": "driver_ce",
                "conditions_match": True,
            },
        }
    )
    bhp = project_bhp_evidence_view(
        {
            "id": "b1",
            "type": "bhp",
            "meta": {
                "training_date": "2026-09-15",
                "training_kind": "introductory",
                "employer_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                "post_key": "driver_ce",
            },
        }
    )
    result = evaluate_employment_start_allowed_v1(
        employee_id="e1",
        employment_context=_pem1_ctx(),
        contract_view=contract,
        medical_view=medical,
        bhp_view=bhp,
        planned_start_date="2026-10-01",
    )
    assert result["start_allowed"] is True
    assert result["decision"] == DECISION_START_ALLOWED


def test_missing_contract_still_blocks() -> None:
    medical = project_medical_evidence_view(
        {
            "id": "m1",
            "type": "medical_certificate",
            "meta": {
                "expires_at": "2027-01-01",
                "fit_for_work": True,
                "applies_to_post": "driver_ce",
                "conditions_match": True,
            },
        }
    )
    bhp = project_bhp_evidence_view(
        {
            "id": "b1",
            "type": "bhp",
            "meta": {
                "training_date": "2026-09-15",
                "training_kind": "introductory",
                "employer_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                "post_key": "driver_ce",
            },
        }
    )
    result = evaluate_employment_start_allowed_v1(
        employee_id="e1",
        employment_context=_pem1_ctx(),
        contract_view=None,
        medical_view=medical,
        bhp_view=bhp,
        planned_start_date="2026-10-01",
    )
    assert result["start_allowed"] is False
    codes = {row.get("code") for row in (result.get("active_missing") or [])}
    assert "written_employment_contract_or_confirmation" in codes


def test_no_type_specific_if_in_orchestrator_pick() -> None:
    text = _ORCH.read_text(encoding="utf-8")
    assert "document_storage_type_matches" in text
    lowered = text.lower()
    assert 'if dtype == "employment_contract"' not in lowered
    assert 'if dtype == "bhp"' not in lowered
    assert 'if doc_type == "bhp"' not in lowered


def test_ci_wires_named_gate() -> None:
    text = _CI.read_text(encoding="utf-8")
    assert "start-allowed-contract-bhp-hub-identity-gate" in text
    assert "test_start_allowed_contract_bhp_hub_identity_gate.py" in text


def test_implementation_files_present() -> None:
    assert "employment_contract" in _DEFS.read_text(encoding="utf-8")
    assert 'code="bhp"' in _DEFS.read_text(encoding="utf-8")
    assert "document_storage_type_matches" in _BRIDGE.read_text(encoding="utf-8")
