"""DQC catalog ↔ recruitment pack bridge gate.

Named gate: dqc-catalog-pack-bridge-gate

Canon (Accepted): pack/R5 ``driver_qualification_card`` ≡ Hub storage ``code95``.
No second Hub type. Does not open Full Spine / license evidence fixes.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from backend.app.document_runtime.delivery_contract import (
    build_required_documents_delivery_via_contract,
)
from backend.app.document_types.definitions import DOCUMENT_TYPE_DEFINITIONS
from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.entity_profile.manifests.recruitment import recruitment_candidate_driver_ce_profile
from backend.app.requirement_rules.document_hub_bridge import map_requirement_evaluation_to_document_hub
from backend.app.requirement_rules.evaluator import evaluate_requirement_rules
from backend.app.services.document_catalog import (
    DOCUMENT_TYPE_DEFAULTS,
    normalize_doc_type,
)
from backend.app.services.document_type_canonical_bridge import (
    legacy_codes_for_ref_canonical,
    normalize_legacy_doc_type,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "dqc-catalog-pack-bridge-gap.md"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_DEFINITIONS = _REPO_ROOT / "backend" / "app" / "document_types" / "definitions.py"
_DELIVERY = _REPO_ROOT / "backend" / "app" / "document_runtime" / "delivery_contract.py"


def test_dqc_gate_filename() -> None:
    assert Path(__file__).name == "test_dqc_catalog_pack_bridge_gate.py"


def test_brief_locks_accepted_canon() -> None:
    text = _BRIEF.read_text(encoding="utf-8")
    assert "driver_qualification_card" in text
    assert "code95" in text
    assert "Accepted" in text or "Accept" in text
    assert "second hub type" in text.lower() or "параллельного Hub" in text or "запрещён" in text
    assert "Full Spine" in text


def test_no_second_hub_type_driver_qualification_card() -> None:
    assert "driver_qualification_card" not in DOCUMENT_TYPE_DEFAULTS
    codes = {d.code for d in DOCUMENT_TYPE_DEFINITIONS}
    assert "code95" in codes
    assert "driver_qualification_card" not in codes


def test_inbound_normalize_dqc_persists_as_code95() -> None:
    assert normalize_doc_type("driver_qualification_card") == "code95"
    assert normalize_doc_type("code95") == "code95"
    assert normalize_doc_type("code_95") == "code95"
    assert normalize_doc_type("qualification_card") == "code95"
    assert normalize_doc_type("driver_qualification_card") != "additional_document"


def test_ref_bridge_code95_is_dqc() -> None:
    assert normalize_legacy_doc_type("code95") == "driver_qualification_card"
    aliases = legacy_codes_for_ref_canonical("driver_qualification_card")
    assert "code95" in aliases


def test_delivery_contract_code95_satisfies_dqc_requirement() -> None:
    future = (date.today() + timedelta(days=120)).isoformat()
    evaluation = {
        "required_documents": [
            {
                "document_type_code": "driver_qualification_card",
                "level": "blocking",
                "verification": "optional",
                "pack_code": "recruitment.driver_ce_documents",
                "source": "document_pack",
            }
        ]
    }
    delivery = build_required_documents_delivery_via_contract(
        evaluation,
        documents=[
            {
                "type": "code95",
                "status": "approved",
                "has_files": True,
                "expires_on": future,
            }
        ],
    )
    assert "driver_qualification_card" not in delivery["missing_documents"]
    assert "driver_qualification_card" in delivery["satisfied_documents"]
    item = next(
        row
        for row in delivery["items"]
        if row["document_type_code"] == "driver_qualification_card"
    )
    assert item["satisfies_requirement"] is True
    assert item["status"] == "satisfied"


def test_hub_bridge_approved_code95_clears_dqc_missing() -> None:
    future = (date.today() + timedelta(days=120)).isoformat()
    manifest = recruitment_candidate_driver_ce_profile()
    profile_view = {
        "entity_profile_code": DRIVER_CE_PROFILE_CODE,
        "profile_code": manifest["profile_code"],
        "profile": {
            "profile_code": manifest["profile_code"],
            "entity_type": manifest["entity_type"],
            "document_pack_code": manifest["document_pack_code"],
            "process_profile_code": manifest["process_profile_code"],
        },
        "fields": manifest["fields"],
    }
    evaluation = evaluate_requirement_rules(
        profile_view,
        context="readiness",
        normalized_payload={},
        documents=[
            {"type": "code95", "status": "approved", "has_files": True, "expires_on": future}
        ],
    )
    hub = map_requirement_evaluation_to_document_hub(
        evaluation,
        documents=[
            {"type": "code95", "status": "approved", "has_files": True, "expires_on": future}
        ],
    )
    missing = set(hub.get("missing_documents") or [])
    assert "driver_qualification_card" not in missing


def test_ci_wires_named_gate() -> None:
    text = _CI.read_text(encoding="utf-8")
    assert "dqc-catalog-pack-bridge-gate" in text
    assert "test_dqc_catalog_pack_bridge_gate.py" in text


def test_implementation_files_present() -> None:
    assert _DEFINITIONS.is_file()
    assert "driver_qualification_card" in _DEFINITIONS.read_text(encoding="utf-8")
    assert "hub_storage_keys_for_requirement_code" in (
        (_REPO_ROOT / "backend" / "app" / "services" / "document_type_canonical_bridge.py")
        .read_text(encoding="utf-8")
    )