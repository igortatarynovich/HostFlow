"""DOCUMENT_REQUIRED ↔ Hub storage alias gate (requirement evaluation).

Named gate: document-required-hub-alias-gate

Canon: DOCUMENT_REQUIRED resolves requirement codes through
``hub_storage_keys_for_requirement_code`` (shared mapping authority).
Approved Hub ``code95`` satisfies ``driver_qualification_card``.
No DQC-specific if. Does not reopen Full Spine.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.entity_profile.manifests.recruitment import recruitment_candidate_driver_ce_profile
from backend.app.requirement_rules.evaluator import evaluate_requirement_rules
from backend.app.services.document_type_canonical_bridge import (
    hub_storage_keys_for_requirement_code,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "document-required-hub-alias-gap.md"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_EVALUATOR = _REPO_ROOT / "backend" / "app" / "requirement_rules" / "evaluator.py"
_BRIDGE = _REPO_ROOT / "backend" / "app" / "services" / "document_type_canonical_bridge.py"


def _driver_ce_profile_view() -> dict:
    manifest = recruitment_candidate_driver_ce_profile()
    return {
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


def _dqc_document_missing(evaluation: dict) -> bool:
    for blocker in evaluation.get("blockers") or []:
        if not isinstance(blocker, dict):
            continue
        if blocker.get("code") != "document_missing":
            continue
        if blocker.get("document_type_code") == "driver_qualification_card":
            return True
        if blocker.get("source_rule_id") == "driver_qualification_card":
            return True
        message = str(blocker.get("message") or "")
        if "driver_qualification_card" in message:
            return True
    return False


def _approved_doc(doc_type: str) -> dict:
    future = (date.today() + timedelta(days=120)).isoformat()
    return {
        "type": doc_type,
        "status": "approved",
        "has_files": True,
        "expires_on": future,
    }


def test_document_required_hub_alias_gate_filename() -> None:
    assert Path(__file__).name == "test_document_required_hub_alias_gate.py"


def test_brief_locks_evaluator_consumer() -> None:
    text = _BRIEF.read_text(encoding="utf-8")
    assert "DOCUMENT_REQUIRED" in text
    assert "driver_qualification_card" in text
    assert "code95" in text
    assert "document_missing" in text
    assert "Full Spine" in text
    assert "DQC-specific" in text or "if driver_qualification_card" in text.lower()


def test_shared_authority_includes_code95_for_dqc() -> None:
    keys = hub_storage_keys_for_requirement_code("driver_qualification_card")
    assert keys[0] == "driver_qualification_card"
    assert "code95" in keys


def test_exact_code_document_still_satisfies() -> None:
    """Exact-code Hub row continues to satisfy DOCUMENT_REQUIRED (regression)."""
    evaluation = evaluate_requirement_rules(
        _driver_ce_profile_view(),
        context="readiness",
        normalized_payload={},
        documents=[_approved_doc("driver_qualification_card")],
    )
    assert not _dqc_document_missing(evaluation)


def test_canonical_alias_code95_satisfies_dqc_requirement() -> None:
    """Approved Hub code95 satisfies DOCUMENT_REQUIRED(driver_qualification_card)."""
    evaluation = evaluate_requirement_rules(
        _driver_ce_profile_view(),
        context="readiness",
        normalized_payload={},
        documents=[_approved_doc("code95")],
    )
    assert not _dqc_document_missing(evaluation)
    assert any(
        isinstance(row, dict) and row.get("document_type_code") == "driver_qualification_card"
        for row in (evaluation.get("required_documents") or [])
    )


def test_missing_code95_still_document_missing_dqc() -> None:
    """Alias expansion must not weaken the requirement when Hub evidence is absent."""
    evaluation = evaluate_requirement_rules(
        _driver_ce_profile_view(),
        context="readiness",
        normalized_payload={},
        documents=[],
    )
    assert _dqc_document_missing(evaluation)


def test_no_dqc_specific_if_in_evaluator() -> None:
    text = _EVALUATOR.read_text(encoding="utf-8")
    assert "hub_storage_keys_for_requirement_code" in text
    assert "_lookup_document_for_requirement" in text
    lowered = text.lower()
    assert 'if doc_code == "driver_qualification_card"' not in lowered
    assert 'if requirement_code == "driver_qualification_card"' not in lowered


def test_ci_wires_named_gate() -> None:
    text = _CI.read_text(encoding="utf-8")
    assert "document-required-hub-alias-gate" in text
    assert "test_document_required_hub_alias_gate.py" in text


def test_implementation_files_present() -> None:
    assert _BRIDGE.is_file()
    assert "hub_storage_keys_for_requirement_code" in _BRIDGE.read_text(encoding="utf-8")
    assert _EVALUATOR.is_file()
    assert "_lookup_document_for_requirement" in _EVALUATOR.read_text(encoding="utf-8")
