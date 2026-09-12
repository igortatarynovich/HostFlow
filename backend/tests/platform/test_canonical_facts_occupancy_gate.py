"""Canonical Facts Occupancy Gate — source independence for decision consumers.

Contract: docs/specs/tasks/canonical-facts-completeness.md

Proves: source → mapping/convert → canonical occupancy → existing RSO/ESO
consumers, without decision authority on field_answers / country / nationality
twins / normalized.documents[].

Does not implement Vacancy Requirements evaluator.
"""

from __future__ import annotations

from types import SimpleNamespace

from backend.app.field_registry.canonical_facts import (
    CITIZENSHIP_QUALIFIED,
    YEARS_CE_QUALIFIED,
    project_identity_facts_from_candidate,
    read_citizenship_alpha2,
    read_years_ce,
)
from backend.app.field_registry.intake_mapping import legacy_normalized_target_from_qualified
from backend.app.modules.leads.conversion_mapping import apply_executable_intake_mapping
from backend.app.reference.early_employability import (
    DECISION_EMPLOYABLE,
    DECISION_INSUFFICIENT_FACTS,
    evaluate_early_employability_v1,
)
from backend.app.reference.ready_for_employment import CONTRACT_ID
from backend.app.requirement_rules.readiness_bridge import build_normalized_payload_from_candidate


def _candidate(**kwargs: object) -> SimpleNamespace:
    personal = dict(kwargs.pop("personal_data", {}) or {})  # type: ignore[arg-type]
    extra = dict(kwargs.pop("extra", {}) or {})  # type: ignore[arg-type]

    def _get_personal_data() -> dict:
        return personal

    def _get_extra() -> dict:
        return extra

    return SimpleNamespace(
        personal_data=personal,
        extra=extra,
        _get_personal_data=_get_personal_data,
        _get_extra=_get_extra,
        first_name=kwargs.get("first_name", "Ada"),
        last_name=kwargs.get("last_name", "Kowalska"),
        phone=kwargs.get("phone"),
        email=kwargs.get("email"),
    )


def _eso_package(*, citizenship: str | None = "PL") -> dict:
    identity: dict = {"first_name": "Ada"}
    if citizenship:
        identity["citizenship"] = citizenship
    return {
        "contract_id": CONTRACT_ID,
        "tenant_id": "11111111-1111-1111-1111-111111111111",
        "person": {
            "person_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "identity_facts": identity,
        },
        "target_work": {
            "vacancy_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "employer_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
            "employment_country": "PL",
        },
        "recruitment_facts": {"language_ok": True},
        "evidence": {"source": "meta_lead", "document_ids": []},
        "fits_decision": {
            "decision": "fits",
            "decided_at": "2026-09-09T10:00:00+00:00",
            "actor_id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
        },
        "context_refs": {"application_id": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"},
    }


def test_intake_mapping_citizenship_is_not_country() -> None:
    assert (
        legacy_normalized_target_from_qualified(CITIZENSHIP_QUALIFIED) == "citizenship"
    )


def test_citizenship_source_independence_occupies_personal_only() -> None:
    """Same PL via field_answers, normalized.citizenship, or legacy country transport."""
    via_answers = apply_executable_intake_mapping(
        {"field_answers": [{"name": "гражданство", "values": ["PL"]}]}
    )
    via_normalized = apply_executable_intake_mapping({"citizenship": "PL"})
    via_legacy_country = apply_executable_intake_mapping({"country": "PL"})

    for mapped in (via_answers, via_normalized, via_legacy_country):
        assert mapped.personal.get("citizenship") == "PL"
        assert "citizenship" not in mapped.extra

    results = []
    for mapped in (via_answers, via_normalized, via_legacy_country):
        cand = _candidate(
            personal_data=dict(mapped.personal),
            extra=dict(mapped.extra),
            first_name="Ada",
        )
        identity = project_identity_facts_from_candidate(cand)
        pkg = _eso_package(citizenship=None)
        pkg["person"]["identity_facts"] = identity
        results.append(
            evaluate_early_employability_v1(
                package=pkg,
                handoff_status="accepted",
                employment_context={"employment_country": "PL"},
            )
        )

    assert {r["decision"] for r in results} == {DECISION_EMPLOYABLE}
    assert all(r["citizenship"] == "PL" for r in results)


def test_nationality_alone_is_not_citizenship_for_eso() -> None:
    pkg = _eso_package(citizenship=None)
    pkg["person"]["identity_facts"] = {"first_name": "Ada", "nationality": "UA"}
    pkg["person"]["nationality"] = "UA"
    pkg["recruitment_facts"] = {"nationality": "UA", "language_ok": True}

    assert read_citizenship_alpha2(pkg) == ""
    result = evaluate_early_employability_v1(
        package=pkg,
        handoff_status="accepted",
        employment_context={"employment_country": "PL", "position_category": "driver"},
    )
    assert result["decision"] == DECISION_INSUFFICIENT_FACTS
    assert result.get("citizenship") in (None, "")
    assert any(r.get("code") == "citizenship" for r in result["requirements"])


def test_years_ce_source_independence_nested_storage() -> None:
    via_normalized = apply_executable_intake_mapping({"experience_eu_years": 3})
    via_answers = apply_executable_intake_mapping(
        {
            "field_answers": [
                {
                    "name": "какой у вас опыт работы водителем c+e в международных перевозках по ес?",
                    "values": ["3"],
                }
            ]
        }
    )
    for mapped in (via_normalized, via_answers):
        assert mapped.extra.get("experience", {}).get("years_ce") is not None
        assert "experience_eu_years" not in mapped.extra

    cand = _candidate(
        personal_data={},
        extra={"experience": {"years_ce": 3}},
    )
    payload = build_normalized_payload_from_candidate(cand)
    assert payload.get(YEARS_CE_QUALIFIED) == 3
    assert read_years_ce(cand) == 3


def test_legacy_extra_citizenship_strangler_not_country_or_nationality() -> None:
    """Leftover Candidate.extra.citizenship may occupy; country/nationality must not."""
    leftover = _candidate(personal_data={}, extra={"citizenship": "DE"})
    assert read_citizenship_alpha2(leftover) == "DE"

    geo_only = _candidate(
        personal_data={"nationality": "UA", "country_of_citizenship": "UA"},
        extra={"country_code": "UA", "country": "UA"},
    )
    assert read_citizenship_alpha2(geo_only) == ""


def test_normalized_documents_are_not_citizenship_authority() -> None:
    """documents[] on transport must not invent citizenship for ESO."""
    pkg = _eso_package(citizenship=None)
    pkg["recruitment_facts"] = {
        "language_ok": True,
        "documents": ["passport", "driver_license", "code95"],
    }
    assert read_citizenship_alpha2(pkg) == ""
    result = evaluate_early_employability_v1(
        package=pkg,
        handoff_status="accepted",
        employment_context={"employment_country": "PL"},
    )
    assert result["decision"] == DECISION_INSUFFICIENT_FACTS


def test_decision_consumers_do_not_or_country_or_nationality() -> None:
    """Static scan: RSO/ESO decision files must not reintroduce source-local OR."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "app"
    files = [
        root / "reference" / "early_employability.py",
        root / "reference" / "employment_formalize.py",
        root / "reference" / "employment_missing_resolution.py",
        root / "requirement_rules" / "readiness_bridge.py",
        root / "services" / "handoff.py",
        root / "services" / "handoff_snapshot.py",
        root / "services" / "hr_recruitment_transfer.py",
        root / "services" / "recruitment_package_readiness.py",
        root / "services" / "transfer_policy_resolver.py",
        root / "requirement_rules" / "evaluation" / "candidate_bridge.py",
        root / "services" / "workforce_eligibility_resolver.py",
        root / "services" / "workforce_action_policy.py",
        root / "services" / "candidate_doc_pipeline_guard.py",
    ]
    citizenship_or_patterns = (
        'extra.get("citizenship") or personal.get("citizenship")',
        'personal.get("citizenship") or extra.get("citizenship")',
        'or extra.get("country_code")',
        'or personal.get("nationality")',
        'for key in ("citizenship", "nationality"',
        'for key in ("citizenship", "nationality", "country_of_citizenship")',
    )
    for path in files:
        text = path.read_text(encoding="utf-8")
        for pat in citizenship_or_patterns:
            assert pat not in text, f"{path.name} still contains forbidden OR: {pat!r}"


def test_vacancy_requirements_evaluator_not_in_this_slice() -> None:
    """Occupancy cutover must not ship Vacancy Requirements evaluator runtime."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    banned = list((root / "backend" / "app").rglob("*vacancy*requirement*eval*.py"))
    banned += list((root / "backend" / "app").rglob("*vacancy_recruitment_fit*.py"))
    assert banned == [], f"Unexpected evaluator files in occupancy cutover: {banned}"
