"""Mapping Consumer Cutover Gate (MA-4).

qualified_code is the only intake write vocabulary. Dual leftover ``target``
is not a production writer. OCR / Telegram stay named leftovers.
Gate **PASS** after the brief stamp. Not leftover-store deletion. Not
External Intake / Forms Publish / Hiring. RS-3 remains program proof.
"""

from __future__ import annotations

from pathlib import Path

from backend.app.reference.mapping_authority import (
    ANSWERERS,
    DESTINATION_VOCABULARY,
    leftover_answerers,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "mapping-authority.md"
_QUEUE = _REPO_ROOT / "docs" / "specs" / "tasks" / "sales-to-comms-sequential-queue.md"
_AGENTS = _REPO_ROOT / "AGENTS.md"
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_INTAKE_MAP = _REPO_ROOT / "backend" / "app" / "field_registry" / "intake_mapping.py"
_CONVERSION = _REPO_ROOT / "backend" / "app" / "modules" / "leads" / "conversion_mapping.py"
_NORMALIZER = _REPO_ROOT / "backend" / "app" / "modules" / "leads" / "normalizer.py"
_INGEST = _REPO_ROOT / "backend" / "app" / "entity_profile" / "ingest_runtime.py"
_PAYLOAD = _REPO_ROOT / "backend" / "app" / "entity_profile" / "public_intake_draft_session.py"
_VALIDATION = _REPO_ROOT / "backend" / "app" / "entity_profile" / "mapping_validation.py"
_HIRING = _REPO_ROOT / "docs" / "specs" / "tasks" / "hiring-workflow-e2e.md"
_INTAKE = _REPO_ROOT / "docs" / "specs" / "tasks" / "external-intake-forms-publish.md"


def test_ma4_gate_filename() -> None:
    assert Path(__file__).name == "test_mapping_authority_consumer_cutover_gate.py"


def test_ma4_destination_vocabulary_is_qualified_code() -> None:
    assert DESTINATION_VOCABULARY == "qualified_code"
    dual = next(row for row in ANSWERERS if row.code == "dual_vocabulary_and_hardcoded_extractors")
    assert dual.role == "consume"


def test_ma4_leftovers_have_owner_and_expiry() -> None:
    leftovers = leftover_answerers()
    assert leftovers
    for row in leftovers:
        assert row.owner, f"{row.code} leftover missing owner"
        assert row.expiry, f"{row.code} leftover missing expiry"
    ocr = next(row for row in leftovers if row.code == "ocr_and_telegram_bootstrap")
    assert "Documents" in (ocr.owner or "")
    assert "Communications" in (ocr.owner or "")
    assert "OCR" in (ocr.expiry or "")
    assert "Telegram" in (ocr.expiry or "") or "External Intake" in (ocr.expiry or "")


def test_ma4_production_writers_do_not_use_second_vocabulary() -> None:
    intake_map = _INTAKE_MAP.read_text(encoding="utf-8")
    assert "Do not mint" in intake_map or "do not mint" in intake_map
    conversion = _CONVERSION.read_text(encoding="utf-8")
    assert "LEAD_INTAKE_QUALIFIED_TO_NORMALIZED" not in conversion
    assert "rule_write_qualified_code" in conversion
    assert "canonical_facts_of" in conversion
    normalizer = _NORMALIZER.read_text(encoding="utf-8")
    assert "write_canonical_fact" in normalizer
    assert "resolve_intake_mapping_target" not in normalizer
    ingest = _INGEST.read_text(encoding="utf-8")
    assert "PUBLIC_INTAKE_FIELD_TO_QUALIFIED" not in ingest
    assert "pseudo_rules" not in ingest
    assert "resolve_mapping_authority" in ingest
    payload = _PAYLOAD.read_text(encoding="utf-8")
    assert "conversion_payload_from_normalized" in payload
    assert 'personal.get("citizenship")' not in payload
    validation = _VALIDATION.read_text(encoding="utf-8")
    assert "entity_profile_unscoped_mapping_legacy_allowed" not in validation
    assert "legacy_candidate_profile_unscoped_mapping_rejected" in validation


def test_ma4_brief_gate_pass() -> None:
    text = _BRIEF.read_text(encoding="utf-8")
    current = text.split("## History", 1)[0]
    assert "Mapping Consumer Cutover Gate **PASS**" in current
    assert "feat locked" in current.lower()
    assert "Mapping program close" in current
    assert "fddadd39" in current
    lowered = text.lower()
    assert "leftover-store deletion" in lowered
    assert "external intake" in lowered
    assert "hiring" in lowered
    queue = _QUEUE.read_text(encoding="utf-8")
    queue_current = queue.split("## 8. History", 1)[0]
    assert "**Active Product** | **[FP-4](external-intake-forms-publish.md)**" in queue_current
    assert "Mapping program close" in queue_current
    assert "Active (Product):** **[FP-4](external-intake-forms-publish.md)**" in queue_current
    assert "Mapping Consumer Cutover Gate **PASS**" in queue_current
    assert "feat/mapping-authority-ma4-consumer-cutover" in queue
    agents = _AGENTS.read_text(encoding="utf-8")
    assert "Mapping Consumer Cutover Gate **PASS**" in agents or "Cutover Gate **PASS**" in agents
    assert "Mapping program close" in agents


def test_ma4_leaves_intake_hiring_queued() -> None:
    hiring = _HIRING.read_text(encoding="utf-8")
    assert "**QUEUED**" in hiring
    assert "not scheduled" in hiring.lower()
    intake = _INTAKE.read_text(encoding="utf-8")
    assert "**ACTIVE**" in intake.split("## History", 1)[0]


def test_ma4_named_ci_gate() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "Mapping Consumer Cutover Gate" in ci
    assert "test_mapping_authority_consumer_cutover_gate.py" in ci
    assert "test_mapping_authority_consumer_cutover.py" in ci
