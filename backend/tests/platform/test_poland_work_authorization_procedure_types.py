"""Poland work-authorization procedure types are named and not passed.

The closed set is the two procedures the product already selects.
Document codes are not procedure types. No kod_zawodu row and no
document list are written.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PRESETS = (
    _REPO_ROOT / "docs" / "specs" / "architecture" / "poland-work-authorization-presets.md"
)
_BRIEF = _REPO_ROOT / "docs" / "specs" / "tasks" / "poland-work-authorization-presets.md"
_QUEUE = _REPO_ROOT / "docs" / "specs" / "tasks" / "sales-to-comms-sequential-queue.md"
_CONTRACT = (
    _REPO_ROOT / "docs" / "specs" / "architecture" / "work-authorization-procedure-contract.md"
)
_RUNTIME = _REPO_ROOT / "backend" / "app" / "reference" / "work_authorization_procedure.py"


def test_poland_work_authorization_procedure_types_filename() -> None:
    assert Path(__file__).name == "test_poland_work_authorization_procedure_types.py"


def test_poland_procedure_type_set_is_closed_without_documents() -> None:
    text = _PRESETS.read_text(encoding="utf-8")
    assert "Poland Work Authorization Presets Gate **PASS**" in text
    assert "Poland Work Authorization Presets Gate **not PASS**" not in text
    assert "`employer_declaration`" in text
    assert "`work_permit_a`" in text
    assert "The list is closed." in text
    assert "document code `oswiadczenie`" in text
    assert "document code `zezwolenie_A`" in text
    assert "`procedure_type`, `work_permit_type`, and a document or evidence code are three different things." in text
    assert "They are not aliases of these two values." in text
    assert "No path starts `type_b`, `type_c`, `other`, or a procedure value other than the two in the closed set." in text
    assert "The write does not start a procedure" in text
    assert "`type_b`, `type_c`, and `other`" in text
    assert "they are not members of the set." in text
    assert "`work_permit_type is None` is not a third procedure type." in text
    assert "does not choose `kod_zawodu`." in text
    assert "Many `kod_zawodu` values resolve to the same preset." in text
    assert "`kod_zawodu` stays an attribute of the application and the key that identifies the profession." in text
    assert "It is not a source of the document list." in text
    assert "Document or evidence requirement" in text
    assert "Declaration or attestation" in text
    assert "Evidence constraint" in text
    assert "Conditional requirement" in text
    assert "Authority-requested extra" in text
    assert "A sworn translation is an evidence constraint." in text
    assert "It is not written into the preset in advance." in text
    assert "The two baselines are filled." in text
    assert "Dz.U. 2025 poz. 1617" in text
    assert "This slice does not correct either list" in text
    assert "oswiadczenie-country-set-drift.md" in text
    assert "It does not assign a HostFlow document type." in text
    assert "No `kod_zawodu` row is written." in text
    assert "Amount: 400 zł" in text
    assert "200 zł when the intended period does not exceed 3 months" in text
    assert "Code 95 and ADR are not baseline requirements." in text
    assert "`prawo_jazdy`, `karta_tachografu`, `badania_lekarskie`, `swiadectwo_kierowcy`, `visa_D`, and `umowa_o_prace` are not baseline requirements." in text
    assert "That resolver is not this baseline." not in text
    assert "Dz.U. 2025 poz. 1534" in text
    assert "A decision therefore stores the classification instrument, its effective date, and the code." in text
    assert "The KZiS resolver identifies the profession only. It does not derive `profession_is_regulated`." in text
    assert "The absence of an automatic rule is never `no`." in text
    assert "`profession_is_regulated` is an optional condition. It does not block this gate." in text
    assert "An unresolved value does not keep the ordinary package from `submission_ready`." in text
    assert "This determination writes no KZiS to regulated mapping, no heuristic, and no qualification-document mapping." in text
    assert "official procedure baseline" in text
    assert "+ profession preset" in text
    assert "+ vacancy overrides" in text
    assert "+ operator-added requirements" in text
    assert "− waivers" in text
    assert "= effective readiness" in text
    assert "| `employment` |" in text
    assert "| `submission` |" in text
    assert "| `both` |" in text
    assert "That default is not a claim that those five documents are attachments required by Dz.U. 2025 poz. 1629." in text
    assert "Absence from the list is not `not_regulated`" in text
    assert "Driver requirements, Code 95, and ADR are not that source." in text
    assert "The two baselines share one requirement schema. The fee policy differs." in text
    assert "`temporary_agency_agreement` is conditional on `employer_is_temporary_work_agency = true`." in text
    assert "An authority-requested extra is not a baseline requirement." in text
    assert "Existing evidence satisfies a document or evidence requirement without a second upload." in text
    assert "`r5_required_set` remains the only writer." in text
    assert "The country-set drift stays a separate blocker. This PASS does not correct it." in text
    assert "Further research of `profession_is_regulated` stops here." in text
    assert "`employer_declaration` | `PSZ-OPPC`" in text
    assert "`work_permit_a` | `ZC-WWZPP`" in text
    assert "not `ZC-WWZ`" in text
    assert "No public REST API was found" in text
    assert "Browser automation is not the first path." in text
    assert "This slice does not implement that connection." in text
    assert "Feat stays locked." in text
    assert "Runtime is not authorized." in text
    assert (_REPO_ROOT / "docs" / "specs" / "tasks" / "oswiadczenie-country-set-drift.md").is_file()
    assert not _RUNTIME.exists()
    contract = _CONTRACT.read_text(encoding="utf-8")
    assert "Work Authorization Procedure Contract Gate **PASS**" in contract
    assert "**not PASS**" not in contract


def test_poland_procedure_types_are_the_active_product() -> None:
    queue = _QUEUE.read_text(encoding="utf-8")
    current, history = queue.split("## 8. History", 1)
    assert (
        "**Active Product** | **[Poland Work Authorization Presets](poland-work-authorization-presets.md)**"
        in current
    )
    assert "Poland Work Authorization Presets Gate **PASS**" in current
    assert "Poland Work Authorization Presets Gate **not PASS**" not in current
    assert "no `kod_zawodu` row" in current
    assert "Work Authorization Procedure Contract Gate **PASS**" in current
    assert "Work Authorization Procedure Contract Gate **not PASS**" not in current
    assert "Poland procedure types named." in history
    assert "Poland Work Authorization Presets Gate **not PASS**" in history
    assert "Poland Work Authorization Presets program close recorded" in current
    assert "Product **DONE** with no named successor until amendment" in current
    brief = _BRIEF.read_text(encoding="utf-8")
    brief_current, brief_history = brief.split("## History", 1)
    assert "**DONE**" in brief_current
    assert "program close recorded" in brief_current
    assert "**OPENED**" not in brief_current
    assert "`employer_declaration` and `work_permit_a`" in brief_current
    assert "Poland Work Authorization Presets Gate **PASS**" in brief_current
    assert "Poland Work Authorization Presets Gate **not PASS**" not in brief_current
    assert "Poland Work Authorization Presets Gate **not PASS**" in brief_history
    assert "no named successor until amendment" in brief_current
    assert "Feat locked" in brief_current
    assert "Runtime not authorized" in brief_current
