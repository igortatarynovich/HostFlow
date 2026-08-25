"""DR1-contract — Engine → Hub outstanding-ask contract gate.

Seals Requirement Engine evaluation → Hub ``outstanding_asks`` projection.
No mass generation. DR1-runtime (write path) is a later slice.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from backend.app.document_types.registry import is_canonical_code
from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.modules.documents.owner_summary import compute_owner_summary
from backend.app.requirement_rules.constants import REQUIREMENT_EVALUATION_V1
from backend.app.requirement_rules.document_hub_bridge import (
    SOURCE_LAYER,
    map_requirement_evaluation_to_document_hub,
    merge_requirement_engine_into_owner_summary,
)
from backend.app.requirement_rules.engine_to_hub_outstanding_ask_contract import (
    CONTRACT_ID,
    HUB_ADAPTER_ID,
    OUTSTANDING_ASK_STATES,
    contract_metadata,
    hub_section_to_outstanding_asks,
    project_engine_evaluation_to_outstanding_asks,
    validate_outstanding_ask_row,
)
from backend.app.services.document_ruleset import load_default_ruleset

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "engine-document-request-dr1-contract.md"
_CONTRACT = _REPO_ROOT / "backend" / "app" / "requirement_rules" / "engine_to_hub_outstanding_ask_contract.py"
_GUARD = _REPO_ROOT / "scripts" / "architecture" / "check_engine_outstanding_ask_boundary.py"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"


def _synthetic_evaluation(*, documents: list[dict] | None = None) -> dict:
    return {
        "entity_profile_code": DRIVER_CE_PROFILE_CODE,
        "evaluation_version": REQUIREMENT_EVALUATION_V1,
        "context": "readiness",
        "satisfied": False,
        "required_documents": [
            {"document_type_code": "passport", "level": "blocking", "verification": "required"},
            {"document_type_code": "driver_license", "level": "blocking", "verification": "required"},
            {"document_type_code": "driver_qualification_card", "level": "blocking", "verification": "required"},
            {"document_type_code": "tachograph_card", "level": "blocking", "verification": "required"},
        ],
        "rule_sources_applied": [],
        "documents": documents or [],
    }


def _synthetic_hub_section() -> dict:
    return {
        "applied": True,
        "source_layer": SOURCE_LAYER,
        "missing_documents": ["driver_license", "driver_qualification_card", "tachograph_card"],
        "pending_documents": ["passport"],
        "problem_documents": [],
    }


def test_dr1_brief_and_contract_module_exist() -> None:
    assert _BRIEF.is_file()
    assert _CONTRACT.is_file()
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "DR1 Contract Gate" in brief
    assert "no mass generation" in brief.lower()


def test_dr1_contract_metadata() -> None:
    meta = contract_metadata()
    assert meta["contract_id"] == CONTRACT_ID
    assert meta["hub_adapter_id"] == HUB_ADAPTER_ID
    assert meta["source_layer"] == SOURCE_LAYER


def test_dr1_hub_section_maps_outstanding_ask_states() -> None:
    asks = hub_section_to_outstanding_asks(_synthetic_hub_section())
    assert asks
    assert all(validate_outstanding_ask_row(row) for row in asks)
    assert {row["doc_type"] for row in asks if row["state"] == "missing"} == {
        "driver_license",
        "driver_qualification_card",
        "tachograph_card",
    }
    assert {row["doc_type"] for row in asks if row["state"] == "requested"} == {"passport"}


def test_dr1_engine_projects_canonical_outstanding_asks() -> None:
    evaluation = _synthetic_evaluation()
    asks = project_engine_evaluation_to_outstanding_asks(evaluation)
    assert asks
    assert all(validate_outstanding_ask_row(row) for row in asks)
    assert all(is_canonical_code(row["doc_type"]) for row in asks)
    assert all(row["state"] in OUTSTANDING_ASK_STATES for row in asks)
    missing_types = {row["doc_type"] for row in asks if row["state"] == "missing"}
    assert missing_types == {
        "passport",
        "driver_license",
        "driver_qualification_card",
        "tachograph_card",
    }


def test_dr1_engine_path_aligns_with_hub_required_buckets() -> None:
    evaluation = _synthetic_evaluation(
        documents=[{"type": "passport", "status": "uploaded", "has_files": True}],
    )
    hub = map_requirement_evaluation_to_document_hub(
        evaluation,
        documents=evaluation["documents"],
    )
    engine_asks = hub_section_to_outstanding_asks(hub)
    by_type = {row["doc_type"]: row["state"] for row in engine_asks}

    merged = merge_requirement_engine_into_owner_summary(
        compute_owner_summary(
            {"position_category": "driver"},
            load_default_ruleset(),
            [{"type": "passport", "status": "uploaded"}],
        ),
        hub,
    )
    required = merged.get("required") or {}

    assert len(by_type) == len(engine_asks)
    assert by_type["passport"] == "requested"
    assert by_type["driver_license"] == "missing"
    assert set(by_type) == set(required.get("missing_types") or []) | set(
        required.get("in_progress_types") or []
    )
    assert all(validate_outstanding_ask_row(row) for row in engine_asks)


def test_dr1_does_not_imply_runtime_generation() -> None:
    contract = _CONTRACT.read_text(encoding="utf-8")
    lowered = contract.lower()
    assert "no persistence" in lowered or "no mass generation" in lowered
    assert "dr1-runtime" in lowered or "dr1_runtime" in lowered or "later slice" in lowered
    assert "INSERT" not in contract
    assert "create_document" not in lowered


def test_dr1_driver_ce_evaluation_version_preserved() -> None:
    evaluation = _synthetic_evaluation()
    assert evaluation.get("entity_profile_code") == DRIVER_CE_PROFILE_CODE
    assert evaluation.get("evaluation_version") == REQUIREMENT_EVALUATION_V1
    hub = map_requirement_evaluation_to_document_hub(evaluation)
    assert hub.get("evaluation_version") == REQUIREMENT_EVALUATION_V1


def test_dr1_engine_outstanding_ask_boundary_guard() -> None:
    result = subprocess.run(
        [sys.executable, str(_GUARD)],
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_dr1_named_ci_gate() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "DR1 Contract Gate" in ci
    assert "test_dr1_contract_gate.py" in ci


def test_dr1_gate_filename() -> None:
    assert Path(__file__).name == "test_dr1_contract_gate.py"
