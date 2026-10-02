"""Legal Eligibility live model is the decision chain, not a six-tuple lookup.

Evidence lists are not encoded. r5_required_set stays the only writer.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CONTRACT = _REPO_ROOT / "docs" / "specs" / "architecture" / "legal-eligibility-contract.md"
_MATRIX = _REPO_ROOT / "docs" / "specs" / "architecture" / "legal-eligibility-matrix.md"


def test_legal_eligibility_decision_model_filename() -> None:
    assert Path(__file__).name == "test_legal_eligibility_decision_model.py"


def test_legal_eligibility_decision_chain_is_the_live_model() -> None:
    contract = _CONTRACT.read_text(encoding="utf-8")
    assert "**Status:** **Accepted**" in contract
    assert "**not PASS**" not in contract
    assert "## Decision chain" in contract
    assert "The six-tuple lookup is not the live geometry." in contract
    assert "Does this person have a lawful basis to be in Poland?" in contract
    assert "Does this person have a lawful basis to perform this employment?" in contract
    for value in ("`pl`", "`eu_eea_ch`", "`third_country`"):
        assert value in contract
    for value in (
        "`not_required`",
        "`visa_d`",
        "`visa_c`",
        "`karta_pobytu`",
        "`visa_free`",
        "`waiting_for_trc`",
        "`special_protection`",
        "`other`",
        "`none`",
    ):
        assert value in contract
    assert "Empty card `stay_basis` (`''`) is not `none`" in contract
    assert "`included_in_stay`" in contract
    assert "`separate_required`" in contract
    assert "`operator_verification`" in contract
    assert "An operator hold is not a fourth basis" in contract
    assert "`waiting_for_trc` does not select one" in contract
    assert "the card is not sufficient" in contract or "the card is the document issued after a permit" in contract
    assert "does not create the right to work" in contract
    assert "A work authorization does not replace a stay basis." in contract
    assert "It is not ineligible" in contract
    assert "`qualification_jurisdiction` are not inputs" in contract
    assert "It does not take `kod zawodu`." in contract
    assert "country + procedure type + `kod zawodu`" in contract
    assert "Work Authorization Procedure is not opened." in contract
    assert "A preset is default policy." in contract
    assert "Legal Eligibility is not an insurmountable system ban" in contract
    assert "`waive_requirement`" in contract
    assert "`override_readiness`" in contract
    assert "`update_preset`" in contract
    assert "`rule_changed`" in contract
    assert "Five `rule_changed` waives of the same requirement are a review signal" in contract
    assert "The system does not edit the preset from that count." in contract
    assert "A waive does not delete that requirement" in contract
    assert "effective readiness" in contract
    assert "required − satisfied − waived" in contract
    assert "`override_readiness` does not mark a requirement satisfied and does not mark it waived." in contract
    assert "A requirement is not an upload slot." in contract
    assert "One evidence object may satisfy more than one requirement" in contract
    assert "An EU driving licence that carries a valid Code 95 may satisfy both" in contract
    assert "This amendment writes no driver preset, no Code 95 legal rule, and no extraction." in contract
    assert "Code 95 is not a Legal Eligibility input." in contract
    assert "RPM `r5_required_set` stays the only writer." in contract
    assert "This amendment assigns neither id" in contract
    assert "exclusively `r5_required_set`" in contract
    assert "No runtime module" in contract
    assert not (_REPO_ROOT / "backend" / "app" / "reference" / "legal_eligibility.py").exists()

    matrix = _MATRIX.read_text(encoding="utf-8")
    live = matrix.split("## History", 1)[0]
    assert "| `pl` | `not_required` | `not_required` | `yes` |" in live
    assert "| `eu_eea_ch` | `not_required` | `not_required` | `yes` |" in live
    assert "| `visa_d` |" in live
    assert "| `karta_pobytu` |" in live
    assert "| `waiting_for_trc` |" in live
    assert "| `none` |" in live
    assert "| `''` |" in live
    assert "`visa_d` is not given the pack row for `visa`" in live
    assert "`karta_pobytu` is not given the pack row for `card`" in live
    assert "assigned to no chain result" in live
    assert "Legal Eligibility Matrix Gate **not PASS**" in live
    assert "The chain is default policy, not a ban." in live
    assert "Effective readiness is required − satisfied − waived." in live
    assert "`override_readiness` does not mark a requirement satisfied or waived" in live
    assert "One evidence object may satisfy more than one requirement" in live
    assert "Five `rule_changed` waives of the same requirement are a review signal, not an edit." in live
