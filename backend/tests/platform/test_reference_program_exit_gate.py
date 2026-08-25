"""Reference Program Exit Gate — Q1–Q5 single reference ownership chain.

Proves R1–R5 converge to one authoritative answer per architectural question.
Does not re-run slice gates; integrates Country Registry → runtime projection →
Document Type Registry → alias registry → resolved policy evaluator.
"""

from __future__ import annotations

from pathlib import Path

from backend.app.constants.catalogs import COUNTRIES, DIAL_CODES
from backend.app.document_types.registry import canonical_codes, normalize_input_doc_type
from backend.app.modules.documents.pack_definitions import DOCUMENT_PACK_DEFINITIONS
from backend.app.reference.country_registry import (
    country_registry_alpha2_set,
    get_country_registry_entry,
    list_country_registry_entries,
)
from backend.app.reference.document_policy_merge import (
    candidate_requires_document,
    collect_pack_document_codes,
    eu_member_alpha2_lower,
    merge_resolved_policy,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_SOT = _REPO_ROOT / "docs" / "specs" / "tasks" / "platform-reference-identity-sot.md"
_QUEUE = _REPO_ROOT / "docs" / "specs" / "tasks" / "sales-to-comms-sequential-queue.md"


def test_exit_q1_through_q5_single_reference_chain() -> None:
    """One scenario: registry → projection → type → alias → resolved policy."""
    # Q1 — country existence (Country Registry sole authority)
    pl = get_country_registry_entry("PL")
    assert pl is not None
    assert get_country_registry_entry("XX") is None
    assert "PL" in country_registry_alpha2_set()

    # Q2 — dial code (same registry classifications; runtime is projection only)
    assert pl.classifications.dial_code == "+48"
    assert DIAL_CODES["PL"] == pl.classifications.dial_code

    # Q3 — document type existence (Document Type Registry sole authority)
    registry_codes = canonical_codes()
    assert "residence_card" in registry_codes
    assert "not_a_real_doc_type_xyz" not in registry_codes
    assert normalize_input_doc_type("residence_card") == "residence_card"

    # Q4 — alias equivalence (registry + alias registry; not parallel taxonomy)
    assert normalize_input_doc_type("residence_permit") == "residence_card"

    # Q5 — required document (resolved platform pack + evaluator; alias-aware input)
    ctx = {
        "residency_status": "card",
        "citizenship": "UA",
        "work_country": "PL",
        "position_category": "driver",
    }
    assert candidate_requires_document(ctx, "residence_card")
    assert candidate_requires_document(ctx, "residence_permit")

    # Pack policy codes and EU membership derive from the same reference layer.
    pack_codes = collect_pack_document_codes()
    assert pack_codes.issubset(registry_codes)
    assert "pl" in eu_member_alpha2_lower()
    assert all(code in registry_codes for pack in DOCUMENT_PACK_DEFINITIONS for code in pack.document_codes)


def test_exit_no_parallel_country_or_policy_sot() -> None:
    """Runtime catalogs and pack definitions must not diverge from registry answers."""
    alpha2 = country_registry_alpha2_set()
    assert set(COUNTRIES) == alpha2
    assert DIAL_CODES == {
        entry.identity.alpha2: entry.classifications.dial_code
        for entry in list_country_registry_entries()
    }
    # Resolved policy is always projected from platform pack merge helper.
    resolved = merge_resolved_policy()
    assert resolved["candidate"]["defaults"]["requiredTypes"]


def test_exit_named_ci_gate_after_r5() -> None:
    ci = _CI.read_text(encoding="utf-8")
    assert "Reference Program Exit Gate" in ci
    assert "test_reference_program_exit_gate.py" in ci
    r5_at = ci.index("Reference R5 Policy Merge Gate")
    exit_at = ci.index("Reference Program Exit Gate")
    lint_at = ci.index("- name: Lint")
    assert r5_at < exit_at < lint_at


def test_exit_gate_filename_and_queue_row() -> None:
    assert Path(__file__).name == "test_reference_program_exit_gate.py"
    sot = _SOT.read_text(encoding="utf-8")
    queue = _QUEUE.read_text(encoding="utf-8")
    assert "Five architectural questions" in sot
    assert "Reference Program Exit Gate" in sot
    assert "ref-id-exit" in queue
    assert "Q1–Q5" in queue or "Q1-Q5" in queue
