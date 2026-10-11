"""Canonical Fact Authority is opened over the addresses that already exist.

The contract names ownership and authority as two readings. It assigns no
capability set, writes no store, and does not rewrite the HR surface.
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
_RUNTIME = _REPO_ROOT / "backend" / "app" / "reference" / "canonical_fact_authority.py"


def test_canonical_fact_authority_contract_open_filename() -> None:
    assert Path(__file__).name == "test_canonical_fact_authority_contract_open.py"


def test_canonical_fact_authority_contract_is_opened_and_not_passed() -> None:
    text = _CONTRACT.read_text(encoding="utf-8")
    assert "canonical_fact_authority.v1" in text
    assert (
        "Handoff does not transfer a person, card, field or value. "
        "Handoff changes process context and capabilities over canonical facts."
        in text
    )
    assert "Ownership and authority are two readings." in text
    assert "`edit` does not mean `verify`." in text
    assert "`verify` does not mean `edit`." in text
    for verb in ("view", "create", "edit", "verify", "invalidate", "delete"):
        assert f"`{verb}`" in text
    assert "They are not an assignment." in text
    assert "capability set is recalculated" in text
    assert "canonical fact changed → dependent decisions become stale" in text
    assert "Canonical Fact → Evidence → Authority → Process → Projection" in text
    assert "No Person table is authorized." in text
    assert "No `canonical_facts` store is authorized." in text
    assert "Employment Terms are not rewritten." in text
    assert "The HR Driver Operator Surface is not rewritten." in text
    assert "No schema is written." in text
    assert "No runtime module is authorized." in text
    assert "## Canonical Fact Authority Contract Gate" in text
    assert not _RUNTIME.exists()
