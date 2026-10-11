"""Canonical Fact Authority Contract Gate proves the mechanism.

The sentences are the invariants. The gate assigns no capability and
authorizes no field-permissions store.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CONTRACT = (
    _REPO_ROOT
    / "docs"
    / "specs"
    / "architecture"
    / "canonical-fact-authority-contract.md"
)
_BRIEF = (
    _REPO_ROOT / "docs" / "specs" / "tasks" / "employee-record-employment-lifecycle.md"
)
_RUNTIME = _REPO_ROOT / "backend" / "app" / "reference" / "canonical_fact_authority.py"

_INVARIANTS = (
    "One address serves several processes. Recruitment and HR read one `citizenship`. There is no `recruitment.citizenship` and no `hr.citizenship`.",
    "Handoff changes authority, not ownership. Before and after the handoff the canonical address stays the same.",
    "Capabilities are independent. `edit` does not mean `verify`. `verify` does not mean `edit`. `invalidate` does not mean `delete`.",
    "Concurrent authority is allowed. Handoff does not have to make the previous process read-only. Policy decides.",
    "A finished process does not freeze the value. When policy allows another process to change the fact, one value changes and dependent decisions become stale.",
    "Evidence is not the fact. `verify` on `citizenship` does not grant `edit` or `delete` on the passport.",
    "An employment-scoped fact does not become a person fact. `compensation` and `planned_start` belong to one Employment even when several modules display them.",
    "Authority does not decide applicability. An HR `edit` on Code 95 does not mean this Employment requires Code 95.",
    "A missing capability forbids the operation. The module does not create a local copy in its place.",
    "A projection is not an owner. No UI or API DTO becomes a canonical address.",
    "The subject of a capability decision is `actor + process context + tenant + canonical fact address + capability`.",
)


def test_canonical_fact_authority_contract_gate_filename() -> None:
    assert Path(__file__).name == "test_canonical_fact_authority_contract_gate.py"


def test_canonical_fact_authority_contract_gate_pass_holds_the_invariants() -> None:
    text = _CONTRACT.read_text(encoding="utf-8")
    assert "## Canonical Fact Authority Contract Gate" in text
    assert "**Outcome:** **PASS**." in text
    assert "Canonical Fact Authority Contract Gate **PASS**" in text
    assert "The Contract Gate is not passed." not in text
    for sentence in _INVARIANTS:
        assert sentence in text
    assert "This contract does not assign a verb to a named person, and it does not open an RBAC matrix." in text
    assert "No field-permissions subsystem is authorized." in text
    assert "The reading of current RBAC is not opened." in text
    assert "An ACL on every field is not indicated." in text
    assert "No schema is written." in text
    assert "No runtime module is authorized." in text
    assert not _RUNTIME.exists()

    brief = _BRIEF.read_text(encoding="utf-8")
    current = brief.split("## History", 1)[0]
    assert "Canonical Fact Authority Contract Gate **PASS**" in current
    assert "canonical_fact_authority.v1" in current
    assert "The reading of current RBAC is not opened." in current
