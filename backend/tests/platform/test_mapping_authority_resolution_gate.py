"""Mapping Authority Resolution Gate (MA-2).

One store. One resolver. Precedence chain removed.
Not MA-3 editor. Not External Intake. Not Hiring E2E.
"""

from __future__ import annotations

from pathlib import Path

from backend.app.reference.mapping_authority import (
    ANSWERERS,
    CONTRACT_ID,
    RESOLVER_API,
    RESOLVER_REL,
    RULES_SOURCE_AUTHORITY,
    WRITE_AUTHORITY,
    classified_codes,
    write_authority_answerers,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "mapping-authority.md"
_ARCH = _REPO_ROOT / "docs" / "specs" / "architecture" / "mapping-authority-contract.md"
_RESOLVE_DOC = _REPO_ROOT / "docs" / "specs" / "architecture" / "mapping-authority-resolution.md"
_QUEUE = _REPO_ROOT / "docs" / "specs" / "tasks" / "sales-to-comms-sequential-queue.md"
_AGENTS = _REPO_ROOT / "AGENTS.md"
_RESOLVER = _REPO_ROOT / RESOLVER_REL
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_HIRING = _REPO_ROOT / "docs" / "specs" / "tasks" / "hiring-workflow-e2e.md"
_INTAKE = _REPO_ROOT / "docs" / "specs" / "tasks" / "external-intake-forms-publish.md"
_HR = _REPO_ROOT / "docs" / "specs" / "tasks" / "recruitment-hr-minimal-handoff.md"
_INGEST = _REPO_ROOT / "backend" / "app" / "entity_profile" / "ingest_runtime.py"
_WRAPPER = _REPO_ROOT / "backend" / "app" / "modules" / "leads" / "field_mapping_resolve.py"


def test_ma2_gate_filename() -> None:
    assert Path(__file__).name == "test_mapping_authority_resolution_gate.py"


def test_ma2_one_store_one_resolver() -> None:
    assert CONTRACT_ID == "mapping_authority.v1"
    assert WRITE_AUTHORITY == "intake_source_profile_mapping_rules"
    assert RESOLVER_API == "resolve_mapping_authority"
    assert RULES_SOURCE_AUTHORITY == "authority"
    writers = write_authority_answerers()
    assert len(writers) == 1
    assert writers[0].code == "intake_source_profile_mapping_rules"
    assert classified_codes()[3] == "silent_precedence_chain"
    chain = next(row for row in ANSWERERS if row.code == "silent_precedence_chain")
    assert chain.role == "consume"
    assert chain.paths == (RESOLVER_REL,)
    text = _RESOLVER.read_text(encoding="utf-8")
    assert f"async def {RESOLVER_API}(" in text
    assert "intake_source_profiles" in text or "mapping_rules" in text


def test_ma2_ingest_has_no_precedence_chain() -> None:
    ingest = _INGEST.read_text(encoding="utf-8")
    wrapper = _WRAPPER.read_text(encoding="utf-8")
    assert "resolve_mapping_authority" in ingest
    assert "meta_form_or_tenant" not in ingest
    assert "source_rules = isp.mapping_rules" not in ingest
    assert "resolve_mapping_authority" in wrapper
    assert "get_meta_form_mapping" not in wrapper
    assert "_tenant_fallback_rules" not in wrapper


def test_ma2_resolution_doc_is_sot() -> None:
    text = _RESOLVE_DOC.read_text(encoding="utf-8")
    assert "Mapping Resolution Gate" in text
    assert RESOLVER_API in text
    assert "intake_source_profiles" in text
    assert "read-through" in text.lower() or "read through" in text.lower()
    assert "precedence" in text.lower()
    assert "mapping_applied_v1" in text
    assert "MA-3" in text
    assert "Zapier" in text or "fourth store" in text.lower()
    arch = _ARCH.read_text(encoding="utf-8")
    assert "mapping-authority-resolution.md" in arch
    assert "one resolver" in arch.lower() or "MA-2" in arch


def test_ma2_brief_resolution_gate_pass() -> None:
    text = _BRIEF.read_text(encoding="utf-8")
    assert "Mapping Resolution Gate" in text
    assert "**PASS**" in text
    assert "feat locked" in text.lower()
    assert "MA-3" in text
    assert "resolve_mapping_authority" in text or "one resolver" in text.lower()
    assert "External Intake" in text
    assert "Hiring E2E" in text


def test_ma2_queue_names_ma3_successor() -> None:
    text = _QUEUE.read_text(encoding="utf-8")
    assert "Mapping Resolution Gate" in text
    assert "**Active Product** | **[MA-3](mapping-authority.md)**" in text
    assert "Active (Product):** **[MA-3](mapping-authority.md)**" in text
    assert "feat locked this PR" in text
    assert "Active (Product):** **[MA-2](mapping-authority.md)**" not in text
    agents = _AGENTS.read_text(encoding="utf-8")
    assert "mapping-authority.md" in agents
    assert "MA-3" in agents
    assert "Mapping Resolution Gate" in agents or "MA-2" in agents
    assert "CL8" in text


def test_ma2_leaves_intake_hiring_hr_queued() -> None:
    for path in (_HIRING, _INTAKE, _HR):
        text = path.read_text(encoding="utf-8")
        assert "**QUEUED**" in text
        assert "not scheduled" in text.lower()
        assert "MA-3" in text
        assert "mapping-authority.md" in text


def test_ma2_named_ci_gate() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "Mapping Resolution Gate" in ci
    assert "test_mapping_authority_resolution_gate.py" in ci
    assert "test_mapping_resolve.py" in ci
    assert "docs/specs/architecture/mapping-authority-resolution.md" in ci
