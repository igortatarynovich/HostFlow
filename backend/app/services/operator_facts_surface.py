"""Operator Facts Surface runtime.

Records facts the accepted contracts already name. It does not add a chain
value, a procedure type, a document type, or a column, and it does not fill
the Legal Eligibility matrix.

Citizenship is written on ``candidates.personal_data.citizenship``. Stay and
the professional facts are person facts in the existing ``personal_data``
JSON. The work basis belongs to one Employment and is stored in that same
JSON under the employment id, because ``hr_employments`` has no fact column
and this slice adds none.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Mapping

from backend.app.constants.reference_foundation import get_reference_domain
from backend.app.document_types.registry import (
    is_canonical_code,
    normalize_input_doc_type,
    registry_entry_for,
)
from backend.app.reference.country_registry import get_country_registry_entry
from backend.app.reference.legal_eligibility_chain import (
    OPERATOR_STAY_CHOICES as _STAY,
    OPERATOR_WORK_CHOICES,
    PROCEDURE_LABELS as _PROCEDURE_LABELS,
    STAY_WITH_VISA_PARAMETERS,
    WORK_LABELS as _WORK_LABELS,
    citizenship_class,
)
from backend.app.reference.requirement_resolution import (
    CE_DOCUMENT_CODES,
    POLICY_ID as POLICY_REQUIREMENT_RESOLUTION,
    REQUIREMENT_LEVELS as _LEVELS,
    apply_resolution_to_required_set,
    issuing_evidence_shape,
    requirements_named_by_documents,
    resolve_recruitment_requirements,
)

class OperatorFactsRejected(ValueError):
    """A patch value is not one the accepted contracts already name."""


def canonical_document_code(code: str) -> str:
    """Registry code. An unknown string is not rewritten into ``other``."""

    raw = str(code or "").strip().lower()
    if not raw:
        return raw
    mapped = normalize_input_doc_type(raw)
    if mapped == "other" and not is_canonical_code(raw):
        return raw
    return mapped


def registry_document_code(code: str) -> str | None:
    """A participating registry type. Inbox and unknown codes are not asks."""

    mapped = canonical_document_code(code)
    if not is_canonical_code(mapped):
        return None
    entry = registry_entry_for(mapped)
    if entry is None or not entry.participates_in_requirements or entry.classification_inbox_only:
        return None
    return entry.code


def _text(value: Any) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    return raw or None


def _is_unknown(value: Any) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() == "unknown"


def _country(value: Any) -> str | None:
    if _is_unknown(value) or value is None:
        return None
    raw = str(value).strip().upper()
    if not raw:
        return None
    if get_country_registry_entry(raw) is None:
        raise OperatorFactsRejected(f"unknown country {raw}")
    return raw


def _blank_work() -> dict[str, Any]:
    return {
        "work_authorization_basis": None,
        "procedure_type": None,
        "valid_no": False,
        "valid_from": None,
        "valid_to": None,
        "conditions": None,
    }


def empty_facts() -> dict[str, Any]:
    return {
        "citizenship": None,
        "stay_basis": None,
        "visa_type": None,
        "visa_purpose": None,
        "stay_valid_to": None,
        "work": _blank_work(),
        "employments": {},
        "licence_issuing_country": None,
        "licence_categories": [],
        "licence_valid_to": None,
        "code95_presence": None,
        "code95_valid_to": None,
        "tachograph_presence": None,
        "tachograph_issuing_country": None,
        "tachograph_valid_to": None,
        "adr_presence": None,
        "adr_issuing_country": None,
        "adr_valid_to": None,
        "medical_presence": None,
        "psych_presence": None,
        "additional_presence": None,
        "pesel_presence": None,
        "pesel": None,
        "ce_level": "NOT_REQUIRED",
        "code95_level": "NOT_REQUIRED",
    }


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def facts_from_personal_data(personal_data: Mapping[str, Any] | None) -> dict[str, Any]:
    personal = _as_dict(personal_data)
    raw = _as_dict(personal.get("operator_facts"))
    facts = empty_facts()
    citizenship = _text(personal.get("citizenship"))
    if citizenship and get_country_registry_entry(citizenship.upper()) is not None:
        facts["citizenship"] = citizenship.upper()
    stay = _text(raw.get("stay_basis"))
    if stay in _STAY:
        facts["stay_basis"] = stay
    facts["visa_type"] = _text(raw.get("visa_type"))
    facts["visa_purpose"] = _text(raw.get("visa_purpose"))
    facts["stay_valid_to"] = _date_text(raw.get("stay_valid_to"))
    facts["work"] = _read_work(raw.get("work"))
    employments: dict[str, Any] = {}
    for key, value in _as_dict(raw.get("employments")).items():
        employment_id = _text(key)
        if employment_id:
            employments[employment_id] = _read_work(value)
    facts["employments"] = employments
    country = _text(raw.get("licence_issuing_country"))
    if country and get_country_registry_entry(country.upper()) is not None:
        facts["licence_issuing_country"] = country.upper()
    facts["licence_categories"] = _categories(raw.get("licence_categories"))
    facts["licence_valid_to"] = _date_text(raw.get("licence_valid_to"))
    facts["code95_presence"] = _bool_or_none(raw.get("code95_presence"))
    facts["code95_valid_to"] = _date_text(raw.get("code95_valid_to"))
    facts["tachograph_presence"] = _bool_or_none(raw.get("tachograph_presence"))
    tacho_country = _text(raw.get("tachograph_issuing_country"))
    if tacho_country and get_country_registry_entry(tacho_country.upper()) is not None:
        facts["tachograph_issuing_country"] = tacho_country.upper()
    facts["tachograph_valid_to"] = _date_text(raw.get("tachograph_valid_to"))
    facts["adr_presence"] = _bool_or_none(raw.get("adr_presence"))
    adr_country = _text(raw.get("adr_issuing_country"))
    if adr_country and get_country_registry_entry(adr_country.upper()) is not None:
        facts["adr_issuing_country"] = adr_country.upper()
    facts["adr_valid_to"] = _date_text(raw.get("adr_valid_to"))
    facts["medical_presence"] = _bool_or_none(raw.get("medical_presence"))
    facts["psych_presence"] = _bool_or_none(raw.get("psych_presence"))
    facts["additional_presence"] = _bool_or_none(raw.get("additional_presence"))
    facts["pesel_presence"] = _bool_or_none(raw.get("pesel_presence"))
    facts["pesel"] = _text(raw.get("pesel"))
    facts["ce_level"] = _level(raw.get("ce_level"))
    facts["code95_level"] = _level(raw.get("code95_level"))
    return facts


def _read_work(value: Any) -> dict[str, Any]:
    raw = _as_dict(value)
    work = _blank_work()
    basis = _text(raw.get("work_authorization_basis"))
    if basis in {"included_in_stay", "separate_required", "not_required"}:
        work["work_authorization_basis"] = basis
    procedure = _text(raw.get("procedure_type"))
    if procedure in {"work_permit_a", "employer_declaration"} and basis == "separate_required":
        work["procedure_type"] = procedure
    work["valid_no"] = raw.get("valid_no") is True or _text(raw.get("valid_for_this_employment")) == "no"
    work["valid_from"] = _date_text(raw.get("valid_from"))
    work["valid_to"] = _date_text(raw.get("valid_to"))
    work["conditions"] = _text(raw.get("conditions"))
    return work


def licence_category_codes() -> list[str]:
    """Codes from the platform reference domain ``driver_license_categories``."""

    out: list[str] = []
    for row in get_reference_domain("driver_license_categories"):
        code = str(row.get("code") or "").strip().upper()
        if code and code not in out:
            out.append(code)
    return out


def _categories(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    allowed = set(licence_category_codes())
    out: list[str] = []
    for item in value:
        code = str(item or "").strip().upper()
        if code in allowed and code not in out:
            out.append(code)
    return out


def _date_text(value: Any) -> str | None:
    raw = _text(value)
    if raw is None:
        return None
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError:
        return None


def _bool_or_none(value: Any) -> bool | None:
    if value is None or _is_unknown(value):
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "yes", "1"}:
        return True
    if text in {"false", "no", "0"}:
        return False
    return None


def _level(value: Any) -> str:
    raw = str(value or "").strip().upper()
    if raw in _LEVELS:
        return raw
    return "NOT_REQUIRED"


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _assign_country(facts: dict[str, Any], key: str, value: Any) -> None:
    if _is_unknown(value) or value is None or str(value).strip() == "":
        facts[key] = None
        return
    facts[key] = _country(value)


def _work_for(facts: Mapping[str, Any], employment_id: str | None) -> dict[str, Any]:
    if employment_id:
        found = _as_dict(_as_dict(facts.get("employments")).get(employment_id))
        if found:
            return _read_work(found)
    return _read_work(facts.get("work"))


def apply_operator_facts_patch(
    facts: Mapping[str, Any],
    patch: Mapping[str, Any],
    *,
    employment_id: str | None = None,
) -> dict[str, Any]:
    """Apply one operator patch. ``unknown`` stores nothing for that fact."""

    nxt = facts_from_personal_data({"citizenship": facts.get("citizenship"), "operator_facts": facts})
    if "citizenship" in patch:
        if _is_unknown(patch.get("citizenship")) or not _text(patch.get("citizenship")):
            nxt["citizenship"] = None
        else:
            nxt["citizenship"] = _country(patch.get("citizenship"))
    klass = citizenship_class(nxt.get("citizenship"))
    if klass in {"pl", "eu_eea_ch"}:
        nxt["stay_basis"] = None
        nxt["visa_type"] = None
        nxt["visa_purpose"] = None
        nxt["stay_valid_to"] = None
        nxt["work"] = _blank_work()
        if employment_id:
            employments = dict(nxt["employments"])
            employments.pop(employment_id, None)
            nxt["employments"] = employments
    else:
        if "stay_basis" in patch:
            if _is_unknown(patch.get("stay_basis")) or not _text(patch.get("stay_basis")):
                nxt["stay_basis"] = None
            else:
                stay = str(patch.get("stay_basis")).strip()
                if stay not in _STAY:
                    raise OperatorFactsRejected(f"stay_basis {stay} is not a chain value")
                nxt["stay_basis"] = stay
                nxt["visa_type"] = None
                nxt["visa_purpose"] = None
        if "visa_type" in patch:
            nxt["visa_type"] = None if _is_unknown(patch.get("visa_type")) else _text(patch.get("visa_type"))
        if "visa_purpose" in patch:
            nxt["visa_purpose"] = None if _is_unknown(patch.get("visa_purpose")) else _text(patch.get("visa_purpose"))
        if "stay_valid_to" in patch:
            nxt["stay_valid_to"] = None if _is_unknown(patch.get("stay_valid_to")) else _date_text(patch.get("stay_valid_to"))
        if any(
            key in patch
            for key in (
                "work_label",
                "work_authorization_basis",
                "procedure_type",
                "valid_for_this_employment",
                "authorization_valid_from",
                "authorization_valid_to",
                "authorization_conditions",
            )
        ):
            _apply_work_patch(nxt, patch, employment_id)
    if "licence_issuing_country" in patch:
        _assign_country(nxt, "licence_issuing_country", patch.get("licence_issuing_country"))
    if "licence_categories" in patch:
        if _is_unknown(patch.get("licence_categories")):
            nxt["licence_categories"] = []
        else:
            nxt["licence_categories"] = _categories(patch.get("licence_categories"))
    if "licence_valid_to" in patch:
        nxt["licence_valid_to"] = None if _is_unknown(patch.get("licence_valid_to")) else _date_text(patch.get("licence_valid_to"))
    if "code95_presence" in patch:
        nxt["code95_presence"] = None if _is_unknown(patch.get("code95_presence")) else _bool_or_none(patch.get("code95_presence"))
    if "code95_valid_to" in patch:
        nxt["code95_valid_to"] = None if _is_unknown(patch.get("code95_valid_to")) else _date_text(patch.get("code95_valid_to"))
    if "tachograph_presence" in patch:
        nxt["tachograph_presence"] = None if _is_unknown(patch.get("tachograph_presence")) else _bool_or_none(patch.get("tachograph_presence"))
    if "tachograph_issuing_country" in patch:
        _assign_country(nxt, "tachograph_issuing_country", patch.get("tachograph_issuing_country"))
    if "tachograph_valid_to" in patch:
        nxt["tachograph_valid_to"] = None if _is_unknown(patch.get("tachograph_valid_to")) else _date_text(patch.get("tachograph_valid_to"))
    if "adr_presence" in patch:
        nxt["adr_presence"] = None if _is_unknown(patch.get("adr_presence")) else _bool_or_none(patch.get("adr_presence"))
    if "adr_issuing_country" in patch:
        _assign_country(nxt, "adr_issuing_country", patch.get("adr_issuing_country"))
    if "adr_valid_to" in patch:
        nxt["adr_valid_to"] = None if _is_unknown(patch.get("adr_valid_to")) else _date_text(patch.get("adr_valid_to"))
    if "medical_presence" in patch:
        nxt["medical_presence"] = None if _is_unknown(patch.get("medical_presence")) else _bool_or_none(patch.get("medical_presence"))
    if "psych_presence" in patch:
        nxt["psych_presence"] = None if _is_unknown(patch.get("psych_presence")) else _bool_or_none(patch.get("psych_presence"))
    if "additional_presence" in patch:
        nxt["additional_presence"] = None if _is_unknown(patch.get("additional_presence")) else _bool_or_none(patch.get("additional_presence"))
    if "pesel_presence" in patch:
        nxt["pesel_presence"] = None if _is_unknown(patch.get("pesel_presence")) else _bool_or_none(patch.get("pesel_presence"))
        if nxt["pesel_presence"] is not True:
            nxt["pesel"] = None
    if "pesel" in patch:
        nxt["pesel"] = None if _is_unknown(patch.get("pesel")) else _text(patch.get("pesel"))
    if "ce_level" in patch:
        nxt["ce_level"] = _level(patch.get("ce_level"))
    if "code95_level" in patch:
        nxt["code95_level"] = _level(patch.get("code95_level"))
    return nxt


def operator_work_label(work: Mapping[str, Any]) -> str | None:
    """The operator's choice. A stored procedure code is not this label."""

    basis = work.get("work_authorization_basis")
    if work.get("valid_no") and basis not in {"included_in_stay", "separate_required"}:
        return "no_right"
    if basis == "not_required":
        return "not_required"
    if basis == "included_in_stay":
        return "included_in_stay"
    procedure = work.get("procedure_type")
    if basis == "separate_required" and procedure == "work_permit_a":
        return "work_permit"
    if basis == "separate_required" and procedure == "employer_declaration":
        return "oswiadczenie"
    return None


def _apply_work_patch(facts: dict[str, Any], patch: Mapping[str, Any], employment_id: str | None) -> None:
    current = _work_for(facts, employment_id)
    if "work_authorization_basis" in patch:
        raw = patch.get("work_authorization_basis")
        if _is_unknown(raw) or not _text(raw):
            current["work_authorization_basis"] = None
        else:
            basis = str(raw).strip()
            if basis not in {"not_required", "included_in_stay", "separate_required"}:
                raise OperatorFactsRejected(f"work_authorization_basis {basis} is not a chain value")
            current["work_authorization_basis"] = basis
    if "procedure_type" in patch:
        raw = patch.get("procedure_type")
        if _is_unknown(raw) or not _text(raw):
            current["procedure_type"] = None
        else:
            procedure = str(raw).strip()
            if procedure not in {"work_permit_a", "employer_declaration"}:
                raise OperatorFactsRejected(f"procedure_type {procedure} is not a chain value")
            current["procedure_type"] = procedure
    if "work_label" in patch:
        label = patch.get("work_label")
        if _is_unknown(label) or not _text(label):
            current = _blank_work()
        else:
            key = str(label).strip()
            if key == "no_right":
                current = _blank_work()
                current["valid_no"] = True
            elif key not in _WORK_LABELS:
                raise OperatorFactsRejected(f"work label {key} is not a projection")
            else:
                basis, procedure = _WORK_LABELS[key]
                kept = current if key in _PROCEDURE_LABELS else _blank_work()
                current = {
                    "work_authorization_basis": basis,
                    "procedure_type": procedure,
                    "valid_no": False,
                    "valid_from": kept.get("valid_from"),
                    "valid_to": kept.get("valid_to"),
                    "conditions": kept.get("conditions"),
                }
    if "valid_for_this_employment" in patch:
        raw = patch.get("valid_for_this_employment")
        if _is_unknown(raw) or not _text(raw):
            current["valid_no"] = False
        elif str(raw).strip() == "no":
            current["valid_no"] = True
        else:
            raise OperatorFactsRejected("valid_for_this_employment accepts only no or unknown")
    if "authorization_valid_from" in patch:
        raw = patch.get("authorization_valid_from")
        current["valid_from"] = None if _is_unknown(raw) else _date_text(raw)
    if "authorization_valid_to" in patch:
        raw = patch.get("authorization_valid_to")
        current["valid_to"] = None if _is_unknown(raw) else _date_text(raw)
    if "authorization_conditions" in patch:
        raw = patch.get("authorization_conditions")
        current["conditions"] = None if _is_unknown(raw) else _text(raw)
    if employment_id:
        employments = dict(facts.get("employments") or {})
        employments[employment_id] = current
        facts["employments"] = employments
    else:
        facts["work"] = current


def _stay_withholds_work(facts: Mapping[str, Any]) -> bool:
    """Work stays hidden until a stay basis is chosen. Visa C and Visa D are that basis."""

    return facts.get("stay_basis") not in _STAY


def chain_reading(facts: Mapping[str, Any], *, employment_id: str | None = None) -> dict[str, str | None]:
    """The ``legal_eligibility.v1`` reading. Determined steps are filled here."""

    klass = citizenship_class(facts.get("citizenship"))
    if klass in {"pl", "eu_eea_ch"}:
        return {
            "citizenship_class": klass,
            "stay_basis": "not_required",
            "work_authorization_basis": "not_required",
            "valid_for_this_employment": "yes",
        }
    if klass is None:
        return {
            "citizenship_class": None,
            "stay_basis": None,
            "work_authorization_basis": None,
            "valid_for_this_employment": None,
        }
    stay = facts.get("stay_basis") if facts.get("stay_basis") in _STAY else None
    if stay is None or _stay_withholds_work(facts):
        return {
            "citizenship_class": klass,
            "stay_basis": stay,
            "work_authorization_basis": None,
            "valid_for_this_employment": None,
        }
    work = _work_for(facts, employment_id)
    basis = work.get("work_authorization_basis")
    if work.get("valid_no") and basis not in {"included_in_stay", "separate_required"}:
        return {
            "citizenship_class": klass,
            "stay_basis": stay,
            "work_authorization_basis": None,
            "valid_for_this_employment": "no",
        }
    if basis == "not_required":
        return {
            "citizenship_class": klass,
            "stay_basis": stay,
            "work_authorization_basis": "not_required",
            "valid_for_this_employment": "yes",
        }
    if basis not in {"included_in_stay", "separate_required"}:
        return {
            "citizenship_class": klass,
            "stay_basis": stay,
            "work_authorization_basis": None,
            "valid_for_this_employment": None,
        }
    valid = "no" if work.get("valid_no") else "operator_verification"
    return {
        "citizenship_class": klass,
        "stay_basis": stay,
        "work_authorization_basis": basis,
        "valid_for_this_employment": valid,
    }


def _ce_aggregate(resolutions: list[dict[str, Any]]) -> dict[str, Any]:
    """Card reading of the CE case. Absent requirements are not a case."""

    by_code = {row["requirement_code"]: row for row in resolutions}
    ce = by_code.get("ce")
    code95 = by_code.get("code95")
    shape = None
    if ce or code95:
        shape = (ce or code95 or {}).get("evidence_shape")
    uploads: list[str] = []
    for row in (ce, code95):
        if not row:
            continue
        for code in row.get("document_codes") or []:
            surfaced = registry_document_code(str(code))
            if surfaced and surfaced not in uploads:
                uploads.append(surfaced)
    if ce and ce.get("progress") == "needs_input" or code95 and code95.get("progress") == "needs_input":
        progress = "needs_input"
    elif (ce and ce.get("resolution") == "blocking") or (code95 and code95.get("resolution") == "blocking"):
        progress = "blocking"
    elif uploads:
        progress = "needs_evidence"
    elif ce and ce.get("progress") == "satisfied" and (code95 is None or code95.get("progress") == "satisfied"):
        progress = "satisfied"
    elif ce and ce.get("progress") == "under_review":
        progress = "under_review"
    else:
        progress = None
    variant = None
    if shape == "shared":
        variant = "combined_eu_license"
    elif shape == "separate":
        variant = "separate_license_and_code95"
    quiet = {
        "applicable": False,
        "level": "NOT_REQUIRED",
        "progress": None,
        "resolution": None,
        "holds_entrance": False,
    }
    return {
        "policy_id": POLICY_REQUIREMENT_RESOLUTION,
        "evidence_shape": shape,
        "evidence_variant": variant,
        "progress": progress,
        "upload_codes": uploads,
        "asks_file": bool(uploads),
        "ce": _card_row(ce) if ce else quiet,
        "code95": _card_row(code95) if code95 else quiet,
    }


def _card_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "applicable": row.get("applicable"),
        "level": row.get("level"),
        "progress": row.get("progress"),
        "resolution": row.get("resolution"),
        "holds_entrance": row.get("holds_entrance"),
    }


def build_operator_facts_view(
    facts: Mapping[str, Any],
    *,
    employment_id: str | None = None,
    today: date | None = None,
    requirements: list[Mapping[str, Any]] | None = None,
    evidence: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    klass = citizenship_class(facts.get("citizenship"))
    chain = chain_reading(facts, employment_id=employment_id)
    work = _work_for(facts, employment_id)
    stay_visible = klass == "third_country"
    parameters_visible = stay_visible and facts.get("stay_basis") in STAY_WITH_VISA_PARAMETERS
    work_visible = stay_visible and not _stay_withholds_work(facts)
    valid_visible = work_visible and chain.get("work_authorization_basis") in {
        "included_in_stay",
        "separate_required",
    }
    resolutions = resolve_recruitment_requirements(
        list(requirements or []),
        facts,
        evidence,
        today=today,
    )
    ce = _ce_aggregate(resolutions)
    uploads = list(ce["upload_codes"])
    steps = [
        {"key": "citizenship", "visible": True, "stored": facts.get("citizenship")},
        {
            "key": "stay_basis",
            "visible": stay_visible,
            "stored": facts.get("stay_basis") if stay_visible else None,
            "valid_to": facts.get("stay_valid_to") if stay_visible else None,
        },
        {
            "key": "stay_parameters",
            "visible": parameters_visible,
            "visa_type": facts.get("visa_type") if parameters_visible else None,
            "visa_purpose": facts.get("visa_purpose") if parameters_visible else None,
        },
        {
            "key": "work",
            "visible": work_visible,
            "operator_label": operator_work_label(work) if work_visible else None,
            "work_authorization_basis": chain.get("work_authorization_basis") if work_visible else None,
            "procedure_type": work.get("procedure_type") if work_visible else None,
            "valid_from": work.get("valid_from") if work_visible else None,
            "valid_to": work.get("valid_to") if work_visible else None,
            "conditions": work.get("conditions") if work_visible else None,
        },
        {
            "key": "valid_for_this_employment",
            "visible": valid_visible,
            "stored": chain.get("valid_for_this_employment") if valid_visible else None,
        },
        {
            "key": "driving_licence",
            "visible": True,
            "issuing_country": facts.get("licence_issuing_country"),
            "categories": list(facts.get("licence_categories") or []),
            "valid_to": facts.get("licence_valid_to"),
        },
        {
            "key": "code95",
            "visible": issuing_evidence_shape(facts.get("licence_issuing_country")) == "separate",
            "presence": facts.get("code95_presence"),
            "valid_to": facts.get("code95_valid_to"),
            "evidence_shape": ce["evidence_shape"],
            "asks_file": ce["asks_file"],
        },
        {
            "key": "tachograph",
            "visible": True,
            "presence": facts.get("tachograph_presence"),
            "issuing_country": facts.get("tachograph_issuing_country"),
            "valid_to": facts.get("tachograph_valid_to"),
            "asks_file": False,
        },
        {
            "key": "adr",
            "visible": True,
            "presence": facts.get("adr_presence"),
            "issuing_country": facts.get("adr_issuing_country"),
            "valid_to": facts.get("adr_valid_to"),
            "asks_file": False,
        },
        {"key": "medical", "visible": True, "presence": facts.get("medical_presence")},
        {"key": "psych", "visible": True, "presence": facts.get("psych_presence")},
        {"key": "pesel", "visible": True, "presence": facts.get("pesel_presence"), "stored": facts.get("pesel")},
        {"key": "additional", "visible": True, "presence": facts.get("additional_presence")},
    ]
    return {
        "citizenship_class": klass,
        "chain": chain,
        "steps": steps,
        "ce_code95": ce,
        "upload_codes": uploads,
        "asks_file": ce["asks_file"],
        "licence_category_codes": licence_category_codes(),
        "stay_choices": list(_STAY),
        "work_choices": list(OPERATOR_WORK_CHOICES),
        "employment_id": employment_id,
    }


def _policy_codes(required_types: list[Any] | None) -> list[str]:
    out: list[str] = []
    for raw in required_types or []:
        text = str(raw or "").strip()
        if not text:
            continue
        code = canonical_document_code(text)
        if code and code not in out:
            out.append(code)
    return out


def _resolve_named(
    facts: Mapping[str, Any],
    required_types: list[Any] | None,
    *,
    today: date | None = None,
    evidence: list[Mapping[str, Any]] | None = None,
) -> tuple[list[str], list[dict[str, Any]]]:
    codes = _policy_codes(required_types)
    resolutions = resolve_recruitment_requirements(
        requirements_named_by_documents(codes),
        facts,
        evidence,
        today=today,
    )
    return codes, resolutions


def withheld_document_norms(
    facts: Mapping[str, Any],
    *,
    employment_id: str | None = None,
    today: date | None = None,
    required_types: list[Any] | None = None,
    evidence: list[Mapping[str, Any]] | None = None,
) -> frozenset[str]:
    """CE-family codes the current resolution is not asking for.

    Identity, stay, and professional documents are not withheld here. They stay
    when the recruitment policy named them.
    """

    del employment_id
    _codes, resolutions = _resolve_named(facts, required_types, today=today, evidence=evidence)
    pending = {str(code) for row in resolutions for code in row.get("document_codes") or []}
    return frozenset(CE_DOCUMENT_CODES - pending)


def requirement_codes_for_operator(
    policy_codes: list[Any] | None,
    facts: Mapping[str, Any],
    *,
    today: date | None = None,
    evidence: list[Mapping[str, Any]] | None = None,
) -> list[str]:
    """Policy codes that still block this candidate.

    ``r5_required_set`` still names the policy set. A CE or Code 95 code the
    current resolution is not asking for is the old unconditional qualification
    card. It leaves the blocker list. Every other policy code stays.
    """

    withheld = withheld_document_norms(
        facts,
        today=today,
        required_types=list(policy_codes or []),
        evidence=evidence,
    )
    out: list[str] = []
    for raw in policy_codes or []:
        code = str(raw or "").strip().lower()
        if not code or code in out:
            continue
        canon = canonical_document_code(code)
        if code in withheld or canon in withheld:
            continue
        out.append(code)
    return out


_RECORDED_ON_DOCUMENT: dict[str, tuple[str | None, str | None, str | None]] = {
    "driver_license": ("licence_valid_to", "licence_categories", "licence_issuing_country"),
    "driver_license_code95": ("licence_valid_to", "licence_categories", "licence_issuing_country"),
    "code95": ("code95_valid_to", None, None),
    "driver_qualification_card": ("code95_valid_to", None, None),
    "tacho_card": ("tachograph_valid_to", None, "tachograph_issuing_country"),
    "tachograph_card": ("tachograph_valid_to", None, "tachograph_issuing_country"),
    "residence_permit": ("stay_valid_to", None, None),
    "residence_card": ("stay_valid_to", None, None),
    "adr": ("adr_valid_to", None, "adr_issuing_country"),
    "adr_certificate": ("adr_valid_to", None, "adr_issuing_country"),
}

_RECORDED_ON_PROFESSIONAL: dict[str, tuple[str | None, str | None, str | None]] = {
    "driving_licence": ("licence_valid_to", "licence_categories", "licence_issuing_country"),
    "code_95": ("code95_valid_to", None, None),
    "tachograph_card": ("tachograph_valid_to", None, "tachograph_issuing_country"),
}

_PROFESSIONAL_KEY_ALIASES = {
    "driver_license": "driving_licence",
    "driver_license_code95": "driving_licence",
    "driver_licence": "driving_licence",
    "code95": "code_95",
    "driver_qualification_card": "code_95",
    "tachograph": "tachograph_card",
    "tacho_card": "tachograph_card",
}


def _recorded_triple(
    spec: tuple[str | None, str | None, str | None] | None,
    facts: Mapping[str, Any],
) -> dict[str, Any]:
    if spec is None:
        return {}
    valid_key, categories_key, country_key = spec
    out: dict[str, Any] = {}
    if valid_key and facts.get(valid_key):
        out["expire_date"] = str(facts[valid_key])
    if categories_key:
        categories = [str(item) for item in (facts.get(categories_key) or []) if str(item).strip()]
        if categories:
            out["categories"] = categories
    if country_key and facts.get(country_key):
        out["issuing_country"] = facts[country_key]
    return out


def recorded_document_fields(doc_type: str, facts: Mapping[str, Any]) -> dict[str, Any]:
    """Operator fact values a document shows when its own field is still empty.

    The fact stays on the candidate. This does not write the document.
    """

    code = str(doc_type or "").strip().lower()
    return _recorded_triple(_RECORDED_ON_DOCUMENT.get(code), facts)


def recorded_professional_fields(fact_key: str, facts: Mapping[str, Any]) -> dict[str, Any]:
    """The same fact, read on the employee qualification row."""

    raw = str(fact_key or "").strip().lower()
    key = _PROFESSIONAL_KEY_ALIASES.get(raw, raw)
    fields = _recorded_triple(_RECORDED_ON_PROFESSIONAL.get(key), facts)
    if "expire_date" in fields:
        fields["valid_until"] = fields.pop("expire_date")
    return fields


def evidence_asks_from_facts(facts: Mapping[str, Any]) -> list[str]:
    """Files the checklist asks for because the operator already recorded the fact.

    ``r5_required_set`` still writes the policy set. These codes are the evidence
    of an answered fact: a residence card and its decision, a medical certificate,
    and psychological tests. An unknown or negative answer asks for nothing.
    """

    asks: list[str] = []
    if facts.get("stay_basis") == "karta_pobytu":
        asks.extend(["residence_card", "decision"])
    if facts.get("medical_presence") is True:
        asks.append("medical_certificate")
    if facts.get("psych_presence") is True:
        asks.append("psychological_certificate")
    return asks


def project_required_document_types(
    required_types: list[Any] | None,
    facts: Mapping[str, Any],
    *,
    employment_id: str | None = None,
    today: date | None = None,
    evidence: list[Mapping[str, Any]] | None = None,
) -> list[str]:
    """Policy set, with CE and Code 95 replaced by the resolved evidence codes."""

    del employment_id
    codes, resolutions = _resolve_named(facts, required_types, today=today, evidence=evidence)
    resolved = apply_resolution_to_required_set(codes, resolutions)
    out: list[str] = []
    for code in resolved:
        surfaced = registry_document_code(code)
        if surfaced and surfaced not in out:
            out.append(surfaced)
    for code in evidence_asks_from_facts(facts):
        if code not in out:
            out.append(code)
    return out


def drop_withheld_document_codes(
    codes: list[Any] | None,
    facts: Mapping[str, Any],
    *,
    employment_id: str | None = None,
    today: date | None = None,
    include_replacement: bool = True,
    evidence: list[Mapping[str, Any]] | None = None,
    required_types: list[Any] | None = None,
) -> list[str]:
    """Drop CE-family codes the current resolution is not asking for.

    ``codes`` is the slice being filtered. ``required_types`` is the full named
    set the resolution reads when that slice is only part of it. The stage
    guard passes the set so a qualification card in one list is judged against
    the licence named beside it.
    """

    del employment_id
    if include_replacement:
        return project_required_document_types(codes, facts, today=today, evidence=evidence)
    canonical, resolutions = _resolve_named(facts, codes, today=today, evidence=evidence)
    if required_types is not None:
        _named, resolutions = _resolve_named(facts, required_types, today=today, evidence=evidence)
    pending = {str(code) for row in resolutions for code in row.get("document_codes") or []}
    out: list[str] = []
    for code in canonical:
        if code in CE_DOCUMENT_CODES and code not in pending:
            continue
        surfaced = registry_document_code(code)
        if surfaced and surfaced not in out:
            out.append(surfaced)
    return out


def project_document_summary(
    summary: Mapping[str, Any],
    facts: Mapping[str, Any],
    *,
    employment_id: str | None = None,
    today: date | None = None,
    evidence: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Operator-facing summary. Does not write ``r5_required_set``."""

    checklist_in = dict(summary.get("checklist") or {})
    policy_types = list(checklist_in.get("requiredTypes") or [])
    withheld = withheld_document_norms(
        facts,
        employment_id=employment_id,
        today=today,
        required_types=policy_types,
        evidence=evidence,
    )
    out = dict(summary)
    required = dict(out.get("required") or {})
    for key in ("missing", "problematic", "ready_types", "in_progress_types"):
        required[key] = [
            item
            for item in (required.get(key) or [])
            if canonical_document_code(str(item)) not in withheld
        ]
    required["missing_count"] = len(required["missing"])
    required["problems"] = len(required["problematic"])
    required["in_progress"] = len(required["in_progress_types"])
    required["ready"] = len(required["ready_types"])
    required["approved"] = required["ready"]
    required["total"] = (
        required["ready"] + required["in_progress"] + required["missing_count"] + required["problems"]
    )
    original_missing = list((summary.get("required") or {}).get("missing") or [])
    replaced_driver = any(
        canonical_document_code(str(item)) in {"driver_license", "driver_qualification_card"}
        and canonical_document_code(str(item)) in withheld
        for item in original_missing
    )
    checklist = dict(out.get("checklist") or {})
    checklist["requiredTypes"] = project_required_document_types(
        policy_types,
        facts,
        employment_id=employment_id,
        today=today,
        evidence=evidence,
    )
    asked_now = [str(code) for code in checklist["requiredTypes"]]
    optional = [
        item
        for item in (checklist.get("optionalTypes") or [])
        if canonical_document_code(str(item)) not in set(asked_now)
        and str(item) not in set(asked_now)
    ]
    if checklist.get("optionalTypes") is not None:
        checklist["optionalTypes"] = optional
    classified = {
        canonical_document_code(str(item))
        for key in ("missing", "problematic", "ready_types", "in_progress_types")
        for item in (required.get(key) or [])
    }
    classified.update(
        str(item)
        for key in ("missing", "problematic", "ready_types", "in_progress_types")
        for item in (required.get(key) or [])
    )
    for code in asked_now:
        if code in classified or canonical_document_code(code) in classified:
            continue
        required.setdefault("missing", []).append(code)
        classified.add(code)
    if replaced_driver:
        seen = {canonical_document_code(str(item)) for item in required["missing"]}
        for code in checklist["requiredTypes"]:
            canon = canonical_document_code(str(code))
            if canon in {"driver_license", "driver_qualification_card"} and canon not in seen:
                required["missing"].append(code)
                seen.add(canon)
        required["missing_count"] = len(required["missing"])
        required["total"] = (
            required["ready"] + required["in_progress"] + required["missing_count"] + required["problems"]
        )
    out["required"] = required
    out["checklist"] = checklist
    packs = out.get("packs")
    if isinstance(packs, list):
        scrubbed = []
        for pack in packs:
            if not isinstance(pack, Mapping):
                scrubbed.append(pack)
                continue
            row = dict(pack)
            for key in ("required", "missing", "gaps", "blockers"):
                if isinstance(row.get(key), list):
                    row[key] = [
                        item
                        for item in row[key]
                        if canonical_document_code(str(item)) not in withheld
                    ]
            scrubbed.append(row)
        out["packs"] = scrubbed
    return out


def personal_data_with_facts(
    personal_data: Mapping[str, Any] | None,
    facts: Mapping[str, Any],
) -> dict[str, Any]:
    personal = _as_dict(personal_data)
    if facts.get("citizenship"):
        personal["citizenship"] = facts["citizenship"]
    else:
        personal.pop("citizenship", None)
    personal["operator_facts"] = {
        "stay_basis": facts.get("stay_basis"),
        "visa_type": facts.get("visa_type"),
        "visa_purpose": facts.get("visa_purpose"),
        "stay_valid_to": facts.get("stay_valid_to"),
        "work": facts.get("work") or _blank_work(),
        "employments": facts.get("employments") or {},
        "licence_issuing_country": facts.get("licence_issuing_country"),
        "licence_categories": list(facts.get("licence_categories") or []),
        "licence_valid_to": facts.get("licence_valid_to"),
        "code95_presence": facts.get("code95_presence"),
        "code95_valid_to": facts.get("code95_valid_to"),
        "tachograph_presence": facts.get("tachograph_presence"),
        "tachograph_issuing_country": facts.get("tachograph_issuing_country"),
        "tachograph_valid_to": facts.get("tachograph_valid_to"),
        "adr_presence": facts.get("adr_presence"),
        "adr_issuing_country": facts.get("adr_issuing_country"),
        "adr_valid_to": facts.get("adr_valid_to"),
        "medical_presence": facts.get("medical_presence"),
        "psych_presence": facts.get("psych_presence"),
        "additional_presence": facts.get("additional_presence"),
        "pesel_presence": facts.get("pesel_presence"),
        "pesel": facts.get("pesel"),
        "ce_level": facts.get("ce_level") or "NOT_REQUIRED",
        "code95_level": facts.get("code95_level") or "NOT_REQUIRED",
    }
    return personal


async def load_candidate_resolution_evidence(
    session: Any,
    *,
    tenant_id: str,
    candidate_id: str,
) -> list[dict[str, Any]]:
    """Candidate Evidence rows the recruitment resolver already accepts.

    The row stays a recruitment record for one candidate. This slice does not
    read an Employment requirement.
    """

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from backend.app.models.candidate_evidence import CandidateEvidence

    rows = (
        await session.scalars(
            select(CandidateEvidence)
            .options(selectinload(CandidateEvidence.documents))
            .where(
                CandidateEvidence.tenant_id == str(tenant_id),
                CandidateEvidence.candidate_id == str(candidate_id),
            )
        )
    ).all()
    evidence: list[dict[str, Any]] = []
    for row in rows:
        evidence.append(
            {
                "requirement_code": row.requirement_code,
                "evidence_variant_code": row.evidence_variant_code,
                "status": row.status,
                "document_ids": [
                    link.document_id for link in (row.documents or []) if link.document_id
                ],
            }
        )
    return evidence
