"""HR employee record projection.

One reading of owners that already exist. The response is hierarchical.
It is not a stored aggregate and it does not copy a fact into an HR bag.
"""

from __future__ import annotations

from typing import Any, Mapping

from backend.app.services.operator_facts_surface import (
    OperatorFactsRejected,
    apply_operator_facts_patch,
    chain_reading,
    facts_from_personal_data,
    personal_data_with_facts,
)

SECTION_ORDER: tuple[tuple[str, str], ...] = (
    ("dane_osobowe", "Dane osobowe"),
    ("pobyt_i_prawo_do_pracy", "Pobyt i prawo do pracy"),
    ("zatrudnienie", "Zatrudnienie"),
    ("kwalifikacje_i_uprawnienia", "Kwalifikacje i uprawnienia"),
    ("doswiadczenie", "Doświadczenie"),
    ("dokumenty", "Dokumenty"),
    ("badania", "Badania"),
    ("ubezpieczenia", "Ubezpieczenia"),
    ("zus", "ZUS"),
    ("historia", "Historia"),
)

_MEDICAL_DOCUMENT_CODES = frozenset({"medical_certificate", "psychological_certificate"})

_FACT_PATCH = {
    "person.citizenship": "citizenship",
    "stay.basis": "stay_basis",
    "stay.visa_type": "visa_type",
    "stay.visa_purpose": "visa_purpose",
    "stay.valid_to": "stay_valid_to",
    "work.authorization_basis": "work_authorization_basis",
    "work.procedure_type": "procedure_type",
    "qualification.licence_country": "licence_issuing_country",
    "qualification.licence_categories": "licence_categories",
    "qualification.licence_valid_to": "licence_valid_to",
    "qualification.code95_presence": "code95_presence",
    "qualification.code95_valid_to": "code95_valid_to",
    "medical.presence": "medical_presence",
    "psych.presence": "psych_presence",
}

_COLUMN_FIELDS = {
    "person.legal_name": ("first_name", "last_name"),
    "person.latin_name": ("first_name_latin", "last_name_latin"),
    "person.phone": ("phone", "phone_country_code"),
    "person.email": ("email",),
    "person.languages": ("languages",),
}

_PERSONAL_DATA_FIELDS = {
    "person.birth_date": ("birth_date",),
    "person.pesel": ("pesel",),
    "person.address": ("address", "city", "country_code", "address_latin", "city_latin"),
}

_EMPLOYMENT_FIELDS = {
    "employment.client": "client_company_id",
    "employment.started_on": "started_on",
    "employment.ended_on": "ended_on",
}


class RecordWriteRejected(Exception):
    """The address is not writable from this projection."""


def _field(address: str, value: Any, act: str, storage: str) -> dict[str, Any]:
    return {"address": address, "value": value, "act": act, "storage": storage}


def _requirement(rows: list[Mapping[str, Any]], key: str) -> dict[str, Any] | None:
    for row in rows:
        if row.get("definition_key") == key:
            return {
                "definition_key": key,
                "applicability": row.get("applicability"),
                "resolution": row.get("resolution"),
            }
    return None


def _work(facts: Mapping[str, Any], employment_id: str) -> Mapping[str, Any]:
    employments = facts.get("employments")
    if isinstance(employments, Mapping):
        found = employments.get(employment_id)
        if isinstance(found, Mapping):
            return found
    work = facts.get("work")
    return work if isinstance(work, Mapping) else {}


def project_employee_record(source: Mapping[str, Any]) -> dict[str, Any]:
    """Assemble the ten groups from values the caller already loaded."""

    employment_id = str(source["employment_id"])
    person = source.get("person") if isinstance(source.get("person"), Mapping) else {}
    personal = source.get("personal_data") if isinstance(source.get("personal_data"), Mapping) else {}
    facts = facts_from_personal_data(personal)
    if person.get("citizenship") and not facts.get("citizenship"):
        facts = dict(facts)
        facts["citizenship"] = person.get("citizenship")
    chain = chain_reading(facts, employment_id=employment_id)
    requirements = [row for row in source.get("requirements") or [] if isinstance(row, Mapping)]
    documents = [row for row in source.get("documents") or [] if isinstance(row, Mapping)]
    evidence = [row for row in source.get("evidence") or [] if isinstance(row, Mapping)]
    employment = source.get("employment") if isinstance(source.get("employment"), Mapping) else {}
    work = _work(facts, employment_id)
    certificates = [
        {"id": row.get("id"), "doc_type": row.get("doc_type")}
        for row in documents
        if row.get("doc_type") in _MEDICAL_DOCUMENT_CODES
    ]
    open_keys = {
        item.get("definition_key")
        for item in requirements
        if item.get("applicability") != "not_applicable"
        and item.get("resolution") in {None, "unresolved"}
    }
    open_codes = [
        code
        for row in evidence
        if row.get("requirement_code") in open_keys
        for code in (row.get("document_codes") or [])
    ]

    sections = {
        "dane_osobowe": [
            _field("person.legal_name", {"first_name": person.get("first_name"), "last_name": person.get("last_name")}, "edit", "candidates.first_name, candidates.last_name"),
            _field("person.latin_name", {"first_name_latin": person.get("first_name_latin"), "last_name_latin": person.get("last_name_latin")}, "edit", "candidates.first_name_latin, candidates.last_name_latin"),
            _field("person.birth_date", personal.get("birth_date"), "edit", "candidates.personal_data.birth_date"),
            _field("person.citizenship", facts.get("citizenship"), "edit", "candidates.personal_data.citizenship"),
            _field("person.phone", {"phone": person.get("phone"), "phone_country_code": person.get("phone_country_code")}, "edit", "candidates.phone, candidates.phone_country_code"),
            _field("person.email", person.get("email"), "edit", "candidates.email"),
            _field(
                "person.address",
                {key: personal.get(key) for key in ("address", "city", "country_code", "address_latin", "city_latin")},
                "edit",
                "candidates.personal_data",
            ),
            _field("person.pesel", personal.get("pesel"), "edit", "candidates.personal_data.pesel"),
            _field("person.languages", person.get("languages") or [], "edit", "candidates.languages"),
            _field("person.display_name", person.get("display_name"), "view", "workforce_employees.display_name"),
        ],
        "pobyt_i_prawo_do_pracy": [
            _field("stay.basis", facts.get("stay_basis"), "edit", "candidates.personal_data.operator_facts.stay_basis"),
            _field("stay.visa_type", facts.get("visa_type"), "edit", "candidates.personal_data.operator_facts.visa_type"),
            _field("stay.visa_purpose", facts.get("visa_purpose"), "edit", "candidates.personal_data.operator_facts.visa_purpose"),
            _field("stay.valid_to", facts.get("stay_valid_to"), "edit", "candidates.personal_data.operator_facts.stay_valid_to"),
            _field("work.authorization_basis", work.get("work_authorization_basis"), "edit", "candidates.personal_data.operator_facts.employments"),
            _field("work.procedure_type", work.get("procedure_type"), "edit", "candidates.personal_data.operator_facts.employments"),
            _field("legal.valid_for_this_employment", chain.get("valid_for_this_employment"), "view", "legal_eligibility.v1"),
            _field("legal.outcome", (source.get("legal_decision") or {}).get("outcome") if isinstance(source.get("legal_decision"), Mapping) else None, "view", "hr_legal_eligibility_gate_decisions"),
            _field("requirement.legal_stay_confirmation", _requirement(requirements, "legal_stay_confirmation"), "view", "hr_employment_requirements"),
            _field("requirement.labor_market_access", _requirement(requirements, "labor_market_access"), "view", "hr_employment_requirements"),
        ],
        "zatrudnienie": [
            _field("employment.state", employment.get("state"), "view", "hr_employments.state"),
            _field("employment.client", employment.get("client_company_id"), "edit", "hr_employments.client_company_id"),
            _field("employment.vacancy", employment.get("vacancy_id"), "view", "hr_employments.vacancy_id"),
            _field("employment.started_on", employment.get("started_on"), "edit", "hr_employments.started_on"),
            _field("employment.ended_on", employment.get("ended_on"), "edit", "hr_employments.ended_on"),
            _field("employment.terms", source.get("terms"), "edit", "hr_employment_terms"),
            _field("employment.contract_cards", list(source.get("contract_cards") or []), "view", "workforce_employments"),
            _field("employment.ready_to_start", source.get("ready_to_start"), "view", "hr_ready_to_start_decisions"),
        ],
        "kwalifikacje_i_uprawnienia": [
            _field("qualification.licence_country", facts.get("licence_issuing_country"), "edit", "candidates.personal_data.operator_facts.licence_issuing_country"),
            _field("qualification.licence_categories", list(facts.get("licence_categories") or []), "edit", "candidates.personal_data.operator_facts.licence_categories"),
            _field("qualification.licence_valid_to", facts.get("licence_valid_to"), "edit", "candidates.personal_data.operator_facts.licence_valid_to"),
            _field("qualification.code95_presence", facts.get("code95_presence"), "edit", "candidates.personal_data.operator_facts.code95_presence"),
            _field("qualification.code95_valid_to", facts.get("code95_valid_to"), "edit", "candidates.personal_data.operator_facts.code95_valid_to"),
            _field(
                "qualification.tachograph",
                {
                    "presence": facts.get("tachograph_presence"),
                    "issuing_country": facts.get("tachograph_issuing_country"),
                    "valid_to": facts.get("tachograph_valid_to"),
                },
                "edit",
                "candidates.personal_data.operator_facts",
            ),
            _field(
                "qualification.adr",
                {
                    "presence": facts.get("adr_presence"),
                    "issuing_country": facts.get("adr_issuing_country"),
                    "valid_to": facts.get("adr_valid_to"),
                },
                "edit",
                "candidates.personal_data.operator_facts",
            ),
            _field("requirement.driver_entitlement", _requirement(requirements, "driver_entitlement"), "view", "hr_employment_requirements"),
            _field("requirement.professional_qualification", _requirement(requirements, "professional_qualification"), "view", "hr_employment_requirements"),
        ],
        "doswiadczenie": [
            _field("experience.prior_jobs", list(source.get("prior_jobs") or []), "view", "candidate_employments"),
        ],
        "dokumenty": [
            _field("document.rows", [{"id": row.get("id"), "doc_type": row.get("doc_type")} for row in documents], "view", "documents"),
            _field("evidence.rows", evidence, "verify", "candidate_evidence"),
            _field("requirement.required_set", open_codes, "view", "hr required set already materialized"),
        ],
        "badania": [
            _field("medical.presence", facts.get("medical_presence"), "edit", "candidates.personal_data.operator_facts.medical_presence"),
            _field("psych.presence", facts.get("psych_presence"), "edit", "candidates.personal_data.operator_facts.psych_presence"),
            _field("medical.certificates", certificates, "view", "documents"),
        ],
        "ubezpieczenia": [
            _field("insurance.profile", source.get("insurance"), "view", "workforce_insurance_profiles"),
        ],
        "zus": [
            _field("zus.profile", source.get("zus"), "view", "workforce_zus_profiles"),
        ],
        "historia": [
            _field("history.handoff", {
                "handoff_at": employment.get("handoff_at"),
                "handoff_by_user_id": employment.get("handoff_by_user_id"),
                "handoff_id": employment.get("handoff_id"),
                "candidate_snapshot": employment.get("candidate_snapshot"),
            }, "view", "hr_employments"),
            _field("history.legal_decisions", list(source.get("legal_decisions") or []), "view", "hr_legal_eligibility_gate_decisions"),
            _field("history.ready_to_start", list(source.get("ready_decisions") or []), "view", "hr_ready_to_start_decisions"),
            _field("history.requirements", requirements, "view", "hr_employment_requirements"),
        ],
    }
    return {
        "employment_id": employment_id,
        "candidate_id": source.get("candidate_id"),
        "employee_id": source.get("employee_id"),
        "employments": list(source.get("employments") or []),
        "sections": [
            {"key": key, "label": label, "fields": sections[key]}
            for key, label in SECTION_ORDER
        ],
    }


def write_plan(address: str) -> dict[str, Any]:
    """Name the existing writer. A view address has no writer."""

    if address in _FACT_PATCH:
        return {"kind": "operator_facts", "patch_key": _FACT_PATCH[address]}
    if address == "qualification.tachograph":
        return {"kind": "operator_facts", "patch_key": "tachograph"}
    if address == "qualification.adr":
        return {"kind": "operator_facts", "patch_key": "adr"}
    if address in _COLUMN_FIELDS:
        return {"kind": "candidate_columns", "columns": _COLUMN_FIELDS[address]}
    if address in _PERSONAL_DATA_FIELDS:
        return {"kind": "personal_data", "keys": _PERSONAL_DATA_FIELDS[address]}
    if address in _EMPLOYMENT_FIELDS:
        return {"kind": "employment", "column": _EMPLOYMENT_FIELDS[address]}
    if address == "employment.terms":
        return {"kind": "employment_terms", "writer": "confirm_employment_terms"}
    if address == "evidence.status":
        return {"kind": "candidate_evidence", "writer": "approve_evidence"}
    raise RecordWriteRejected(address)


def operator_facts_patch(address: str, value: Any) -> dict[str, Any]:
    plan = write_plan(address)
    if plan["kind"] != "operator_facts":
        raise RecordWriteRejected(address)
    return _fact_patch(plan["patch_key"], value)


def apply_person_write(
    personal_data: Mapping[str, Any] | None,
    *,
    address: str,
    value: Any,
    employment_id: str,
) -> dict[str, Any]:
    """Write one person address onto the current person storage."""

    plan = write_plan(address)
    personal = dict(personal_data or {})
    if plan["kind"] == "operator_facts":
        patch = _fact_patch(plan["patch_key"], value)
        try:
            facts = apply_operator_facts_patch(
                facts_from_personal_data(personal),
                patch,
                employment_id=employment_id,
            )
        except OperatorFactsRejected as exc:
            raise RecordWriteRejected(str(exc)) from exc
        return personal_data_with_facts(personal, facts)
    if plan["kind"] == "personal_data":
        if address == "person.address":
            if not isinstance(value, Mapping):
                raise RecordWriteRejected("person.address")
            for key in plan["keys"]:
                if key in value:
                    personal[key] = value.get(key)
            return personal
        personal[plan["keys"][0]] = value
        return personal
    raise RecordWriteRejected(address)


def _fact_patch(patch_key: str, value: Any) -> dict[str, Any]:
    if patch_key == "tachograph":
        if not isinstance(value, Mapping):
            raise RecordWriteRejected("qualification.tachograph")
        return {
            "tachograph_presence": value.get("presence"),
            "tachograph_issuing_country": value.get("issuing_country"),
            "tachograph_valid_to": value.get("valid_to"),
        }
    if patch_key == "adr":
        if not isinstance(value, Mapping):
            raise RecordWriteRejected("qualification.adr")
        return {
            "adr_presence": value.get("presence"),
            "adr_issuing_country": value.get("issuing_country"),
            "adr_valid_to": value.get("valid_to"),
        }
    return {patch_key: value}


def apply_column_write(address: str, value: Any) -> dict[str, Any]:
    plan = write_plan(address)
    if plan["kind"] != "candidate_columns":
        raise RecordWriteRejected(address)
    if address == "person.email":
        return {"email": value}
    if address == "person.languages":
        return {"languages": list(value or [])}
    if not isinstance(value, Mapping):
        raise RecordWriteRejected(address)
    return {column: value.get(column) for column in plan["columns"]}


def apply_employment_write(employment: Any, *, address: str, value: Any) -> None:
    plan = write_plan(address)
    if plan["kind"] != "employment":
        raise RecordWriteRejected(address)
    setattr(employment, plan["column"], value)
