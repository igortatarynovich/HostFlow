"""DR1-runtime — Engine → Hub outstanding-ask write gate.

Engine creates Hub outstanding asks from CL7 evaluate (Overlay as
defined input) via DR1-contract projection. Not CL8. Not Engine v2.
Not E8. Not mass generation. Not a Hub request table. Not Catalog
``document.requested``. Overlay is input, not this writer.
No Postgres required.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from backend.app.document_types.registry import is_canonical_code
from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.entity_profile.engine_eval_runtime import (
    CONTRACT_ID as ENGINE_CONTRACT_ID,
    ERROR_HUB_ASK_WRITE,
    KIND_DOCUMENT,
    KIND_PRESENCE,
    KIND_PROCESS,
    KIND_VALUE,
    evaluate,
)
from backend.app.entity_profile.flight_map_runtime import (
    CONTRACT_ID as FLIGHT_CONTRACT_ID,
)
from backend.app.entity_profile.layout_runtime import (
    CONTRACT_ID as LAYOUT_CONTRACT_ID,
)
from backend.app.entity_profile.qa_runtime import CONTRACT_ID as QA_CONTRACT_ID
from backend.app.entity_profile.vacancy_overlay_runtime import (
    CONTRACT_ID as OVERLAY_CONTRACT_ID,
    OP_ADD,
    OP_TIGHTEN,
)
from backend.app.requirement_rules.engine_outstanding_ask_runtime import (
    ERROR_CATALOG_DOCUMENT_REQUESTED,
    ERROR_CL8,
    ERROR_E8,
    ERROR_ENGINE_V2,
    ERROR_HUB_REQUEST_TABLE,
    ERROR_MASS_GENERATE,
    ERROR_MISSING_ENTITY_REF,
    contract_metadata,
    write_engine_outstanding_asks,
)
from backend.app.requirement_rules.engine_to_hub_outstanding_ask_contract import (
    CONTRACT_ID,
    HUB_ADAPTER_ID,
    OUTSTANDING_ASK_STATES,
    validate_outstanding_ask_row,
)
from backend.app.services.document_hub_delivery_contract import (
    ADAPTER_ID,
    E4_LINKED_ENTITY_TYPE,
    load_outstanding_asks_via_contract,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "engine-document-request-dr1-runtime.md"
_RUNTIME = (
    _REPO_ROOT
    / "backend"
    / "app"
    / "requirement_rules"
    / "engine_outstanding_ask_runtime.py"
)
_CONTRACT = (
    _REPO_ROOT
    / "backend"
    / "app"
    / "requirement_rules"
    / "engine_to_hub_outstanding_ask_contract.py"
)
_ENGINE = _REPO_ROOT / "backend" / "app" / "entity_profile" / "engine_eval_runtime.py"
_DELIVERY = (
    _REPO_ROOT
    / "backend"
    / "app"
    / "services"
    / "document_hub_delivery_contract.py"
)
_GUARD = (
    _REPO_ROOT
    / "scripts"
    / "architecture"
    / "check_engine_outstanding_ask_writer_boundary.py"
)
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_PANEL = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "entity-workspace"
    / "CandidateEntityWorkspacePanel.tsx"
)
_ZONE = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "entity-workspace"
    / "CandidateInformationLayout.tsx"
)
_QA = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "entity-workspace"
    / "CandidateQaPanel.tsx"
)
_FLIGHT = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "entity-workspace"
    / "CandidateFlightMapPanel.tsx"
)
_ENGINE_PANEL = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "entity-workspace"
    / "CandidateEngineEvalPanel.tsx"
)
_CAPABILITY = (
    _REPO_ROOT
    / "hostflow-frontend"
    / "src"
    / "platform"
    / "capabilities"
    / "documents"
    / "DocumentsCapability.tsx"
)

_YEARS_CE = "recruitment.candidate.experience.years_ce"


def _ready_entity(*, entity_id: str) -> dict:
    return {
        "id": entity_id,
        "linked_entity_type": E4_LINKED_ENTITY_TYPE,
        "values": {
            "recruitment.candidate.first_name": "Jan",
            "recruitment.candidate.last_name": "Kowalski",
            "recruitment.candidate.contacts.phone": "+48 111",
            "recruitment.candidate.contacts.email": "jan@example.com",
            "platform.identity.citizenship": "PL",
            "platform.identity.address": "Warsaw",
            _YEARS_CE: 4,
        },
        "documents": [
            {"document_type_code": "passport", "verified": True},
            {"document_type_code": "driver_license", "verified": True},
            {"document_type_code": "code95", "verified": True},
            {"document_type_code": "tacho_card", "verified": True},
        ],
    }


def _four_kind_vacancy() -> dict:
    return {
        "vacancy_ref": "vac-driver-ce-1",
        "delta": [
            {
                "kind": KIND_VALUE,
                "code": "screening.years_ce.min",
                "owner": "vacancy",
                "op": OP_TIGHTEN,
                "predicate": {
                    "qualified_code": _YEARS_CE,
                    "op": ">=",
                    "value": 5,
                },
            },
            {
                "kind": KIND_DOCUMENT,
                "code": "document.adr.missing",
                "owner": "vacancy",
                "op": OP_ADD,
                "predicate": {"document_type_code": "adr"},
            },
            {
                "kind": KIND_PRESENCE,
                "code": "presence.platform.identity.address",
                "owner": "vacancy",
                "op": OP_ADD,
                "predicate": {
                    "qualified_code": "platform.identity.address",
                    "context": "card_save",
                },
            },
            {
                "kind": KIND_PROCESS,
                "code": "process.handoff.passport_verified",
                "owner": "vacancy",
                "op": OP_ADD,
                "predicate": {
                    "document_type_code": "passport",
                    "verified": True,
                    "process_point": "handoff",
                },
            },
        ],
    }


def test_dr1_runtime_brief_and_writer_exist() -> None:
    assert _BRIEF.is_file()
    assert _RUNTIME.is_file()
    assert _CONTRACT.is_file()
    brief = _BRIEF.read_text(encoding="utf-8")
    assert "DR1 Runtime Gate" in brief
    assert "**Phase class:** platform" in brief
    assert "## Original Goal → Completion Proof" in brief
    assert CONTRACT_ID in brief
    assert "not CL8" in brief.lower() or "Not CL8" in brief
    assert "mass generation" in brief.lower()
    runtime = _RUNTIME.read_text(encoding="utf-8")
    lowered = runtime.lower()
    assert "no alembic" in lowered
    assert "not cl8" in lowered
    assert "mass generation" in lowered
    assert "document.requested" in runtime
    assert "hub request table" in lowered
    assert "DROP TABLE" not in runtime
    assert "CREATE TABLE" not in runtime


def test_dr1_runtime_writer_creates_canonical_hub_asks() -> None:
    meta = contract_metadata()
    assert meta["contract_id"] == CONTRACT_ID
    assert meta["hub_adapter_id"] == HUB_ADAPTER_ID == ADAPTER_ID
    assert meta["proof_profile"] == DRIVER_CE_PROFILE_CODE

    missing = _ready_entity(entity_id="cand-dr1-missing")
    missing["documents"] = []
    written = write_engine_outstanding_asks(
        missing,
        DRIVER_CE_PROFILE_CODE,
        vacancy=None,
        process_point="card_save",
    )
    assert written["ok"] is True
    assert written["contract_id"] == CONTRACT_ID
    assert written["hub_adapter_id"] == HUB_ADAPTER_ID
    assert written["profile_code"] == DRIVER_CE_PROFILE_CODE
    assert written["persisted"] is True
    assert written["mass_generate"] is False
    assert written["hub_request_table"] is False
    assert written["catalog_event"] is None
    asks = written["outstanding_asks"]
    assert asks
    assert all(validate_outstanding_ask_row(row) for row in asks)
    assert all(is_canonical_code(row["doc_type"]) for row in asks)
    assert all(row["state"] in OUTSTANDING_ASK_STATES for row in asks)
    assert all(row["state"] == "missing" for row in asks)
    missing_types = {row["doc_type"] for row in asks}
    assert "passport" in missing_types
    assert "driver_license" in missing_types
    assert "driver_qualification_card" in missing_types
    assert "tachograph_card" in missing_types
    loaded = load_outstanding_asks_via_contract(
        linked_entity_type=E4_LINKED_ENTITY_TYPE,
        linked_entity_id="cand-dr1-missing",
    )
    assert loaded == asks


def test_dr1_runtime_overlay_is_defined_input_not_producer() -> None:
    entity = _ready_entity(entity_id="cand-dr1-overlay")
    written = write_engine_outstanding_asks(
        entity,
        DRIVER_CE_PROFILE_CODE,
        vacancy=_four_kind_vacancy(),
        process_point="card_save",
    )
    assert written["ok"] is True
    assert written["overlay"]["contract_id"] == OVERLAY_CONTRACT_ID
    asks = written["outstanding_asks"]
    assert any(row["doc_type"] == "adr_certificate" and row["state"] == "missing" for row in asks)
    engine = _ENGINE.read_text(encoding="utf-8")
    assert "Does not write" in engine or "does not write" in engine.lower()
    assert "persist_outstanding_asks_via_contract" not in engine
    assert "write_engine_outstanding_asks" not in engine
    overlay_src = (
        _REPO_ROOT
        / "backend"
        / "app"
        / "entity_profile"
        / "vacancy_overlay_runtime.py"
    ).read_text(encoding="utf-8")
    assert "write_engine_outstanding_asks" not in overlay_src
    assert "persist_outstanding_asks_via_contract" not in overlay_src


def test_dr1_runtime_classifies_requested_and_problem_states() -> None:
    entity = _ready_entity(entity_id="cand-dr1-states")
    entity["documents"] = [
        {"document_type_code": "passport", "status": "uploaded", "has_files": True},
        {"document_type_code": "driver_license", "status": "rejected"},
        {"document_type_code": "code95", "verified": True},
        {"document_type_code": "tacho_card", "verified": True},
    ]
    written = write_engine_outstanding_asks(
        entity,
        DRIVER_CE_PROFILE_CODE,
        vacancy=None,
        process_point="card_save",
    )
    assert written["ok"] is True
    by_type = {row["doc_type"]: row["state"] for row in written["outstanding_asks"]}
    assert by_type.get("passport") == "requested"
    assert by_type.get("driver_license") == "problem"
    assert "driver_qualification_card" not in by_type
    assert "tachograph_card" not in by_type


def test_dr1_runtime_evaluate_still_does_not_write() -> None:
    blocked = evaluate(
        _ready_entity(entity_id="cand-dr1-eval-block"),
        DRIVER_CE_PROFILE_CODE,
        vacancy={"persist_asks": True},
        process_point="card_save",
    )
    assert blocked["error"] == ERROR_HUB_ASK_WRITE
    assert blocked["contract_id"] == ENGINE_CONTRACT_ID


def test_dr1_runtime_rejects_false_closes() -> None:
    base = _ready_entity(entity_id="cand-dr1-false")
    mass = write_engine_outstanding_asks(
        {**base, "mass_generate": True},
        DRIVER_CE_PROFILE_CODE,
    )
    assert mass["error"] == ERROR_MASS_GENERATE
    tenants = write_engine_outstanding_asks(
        {**base, "id": "cand-dr1-tenants", "tenant_ids": ["t1", "t2"]},
        DRIVER_CE_PROFILE_CODE,
    )
    assert tenants["error"] == ERROR_MASS_GENERATE
    cl8 = write_engine_outstanding_asks(
        {**base, "id": "cand-dr1-cl8", "cl8": True},
        DRIVER_CE_PROFILE_CODE,
    )
    assert cl8["error"] == ERROR_CL8
    e8 = write_engine_outstanding_asks(
        {**base, "id": "cand-dr1-e8", "e8_bind": True},
        DRIVER_CE_PROFILE_CODE,
    )
    assert e8["error"] == ERROR_E8
    engine_v2 = write_engine_outstanding_asks(
        {**base, "id": "cand-dr1-v2", "engine_v2": True},
        DRIVER_CE_PROFILE_CODE,
    )
    assert engine_v2["error"] == ERROR_ENGINE_V2
    table = write_engine_outstanding_asks(
        {**base, "id": "cand-dr1-table", "hub_request_table": True},
        DRIVER_CE_PROFILE_CODE,
    )
    assert table["error"] == ERROR_HUB_REQUEST_TABLE
    catalog = write_engine_outstanding_asks(
        {**base, "id": "cand-dr1-catalog", "catalog_event": "document.requested"},
        DRIVER_CE_PROFILE_CODE,
    )
    assert catalog["error"] == ERROR_CATALOG_DOCUMENT_REQUESTED
    missing_ref = write_engine_outstanding_asks(
        {"values": {}, "documents": []},
        DRIVER_CE_PROFILE_CODE,
    )
    assert missing_ref["error"] == ERROR_MISSING_ENTITY_REF
    models_dir = _REPO_ROOT / "backend" / "app" / "models"
    hub_models = "\n".join(
        path.read_text(encoding="utf-8") for path in models_dir.glob("document*.py")
    )
    assert "class DocumentRequest" not in hub_models
    assert "class HubRequest" not in hub_models
    assert "class DocumentReminder" not in hub_models
    delivery = _DELIVERY.read_text(encoding="utf-8")
    assert "persist_outstanding_asks_via_contract" in delivery
    assert "hub_adapter_v2" not in delivery


def test_dr1_runtime_d4_places_documents_other_zones_stay() -> None:
    assert _ZONE.is_file()
    assert _QA.is_file()
    assert _FLIGHT.is_file()
    assert _ENGINE_PANEL.is_file()
    assert _CAPABILITY.is_file()
    zone = _ZONE.read_text(encoding="utf-8")
    qa = _QA.read_text(encoding="utf-8")
    flight = _FLIGHT.read_text(encoding="utf-8")
    engine = _ENGINE_PANEL.read_text(encoding="utf-8")
    panel = _PANEL.read_text(encoding="utf-8")
    capability = _CAPABILITY.read_text(encoding="utf-8")
    assert "CandidateInformationLayout" in panel
    assert "CandidateQaPanel" in panel
    assert "CandidateFlightMapPanel" in panel
    assert "CandidateEngineEvalPanel" in panel
    assert LAYOUT_CONTRACT_ID in zone
    assert 'data-host-region="information"' in zone
    assert CONTRACT_ID not in zone
    assert QA_CONTRACT_ID in qa
    assert 'data-host-region="qa"' in qa
    assert FLIGHT_CONTRACT_ID in flight
    assert 'data-host-region="flight-map"' in flight
    assert ENGINE_CONTRACT_ID in engine
    assert OVERLAY_CONTRACT_ID in engine
    assert 'data-host-region="engine-eval"' in engine
    assert 'data-hub-asks="false"' in engine
    assert "VacancyCard" not in engine
    assert 'data-adapter-id=' in capability
    assert CONTRACT_ID in capability
    assert 'data-engine-ask-writer="true"' in capability
    assert 'data-mass-generate="false"' in capability
    assert 'data-hub-request-table="false"' in capability
    assert 'data-catalog-document-requested="false"' in capability
    assert 'data-outstanding-ask' in capability


def test_dr1_runtime_writer_boundary_guard() -> None:
    result = subprocess.run(
        [sys.executable, str(_GUARD)],
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_dr1_runtime_named_ci_gate() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "DR1 Runtime Gate" in ci
    assert "test_dr1_runtime_gate.py" in ci


def test_dr1_runtime_gate_filename() -> None:
    assert Path(__file__).name == "test_dr1_runtime_gate.py"
