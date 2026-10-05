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

from backend.app.reference.country_registry import get_country_registry_entry

POLICY_REQUIREMENT_RESOLUTION = "requirement_resolution.v1"

# Non-eu_member countries of the closed class ``eu_eea_ch``. EU members are
# read from the country registry (``eu_member``). This is not a published list.
_EEA_CH_NOT_EU = frozenset({"IS", "LI", "NO", "CH"})

_STAY = frozenset(
    {
        "visa_d",
        "visa_c",
        "karta_pobytu",
        "visa_free",
        "waiting_for_trc",
        "special_protection",
        "other",
        "none",
    }
)
_STAY_NEEDS_PARAMETERS = frozenset({"visa_d", "visa_c"})
_WORK_LABELS = {
    "work_permit": ("separate_required", "work_permit_a"),
    "oswiadczenie": ("separate_required", "employer_declaration"),
    "included_in_stay": ("included_in_stay", None),
    "not_required": ("not_required", None),
}
_PROCEDURE_LABELS = frozenset({"work_permit", "oswiadczenie"})
_LICENCE_CATEGORIES = frozenset({"B", "C", "CE", "C1", "C1E", "D", "DE"})
_LEVELS = frozenset({"REQUIRED", "PREFERRED", "NOT_REQUIRED"})

# Document asks this surface governs. They are withheld until a fact path
# that already exists asks for a file. Tachograph, ADR, and legal-stay
# documents are never asked here: the matrix is not filled, and tachograph
# and ADR are professional facts.
_GOVERNED_ALIASES = {
    "driver_license": "driver_license",
    "driver_licence": "driver_license",
    "drivers_license": "driver_license",
    "prawo_jazdy": "driver_license",
    "driver_license_code95": "driver_license_code95",
    "driver_license_with_code95": "driver_license_code95",
    "eu_license_code95": "driver_license_code95",
    "code95": "code95",
    "code_95": "code95",
    "qualification_code95": "code95",
    "qualification_card": "code95",
    "driver_qualification_card": "code95",
    "tacho_card": "tacho_card",
    "tachograph": "tacho_card",
    "tachograph_card": "tacho_card",
    "karta_tachografu": "tacho_card",
    "adr": "adr",
    "adr_certificate": "adr",
    "adr_card": "adr",
    "visa": "visa",
    "visa_d": "visa",
    "visa_c": "visa",
    "residence_permit": "residence_permit",
    "residence_card": "residence_permit",
    "karta_pobytu": "residence_permit",
    "work_permit": "work_permit",
    "decision": "decision",
    "voivodeship_decision": "decision",
    "decyzja": "decision",
    "passport": "passport",
    "medical_certificate": "medical_certificate",
    "medical": "medical_certificate",
    "badania_lekarskie": "medical_certificate",
    "psych_tests": "psych_tests",
    "psychotest": "psych_tests",
    "psychotests": "psych_tests",
    "additional_document": "additional_document",
}


class OperatorFactsRejected(ValueError):
    """A patch value is not one the accepted contracts already name."""


def canonical_document_code(code: str) -> str:
    raw = str(code or "").strip().lower()
    return _GOVERNED_ALIASES.get(raw, raw)


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


def citizenship_class(citizenship: str | None) -> str | None:
    """``pl``, ``eu_eea_ch``, or ``third_country``. Absent citizenship is not a class."""

    code = _text(citizenship)
    if not code:
        return None
    entry = get_country_registry_entry(code.upper())
    if entry is None:
        return None
    alpha2 = entry.identity.alpha2
    if alpha2 == "PL":
        return "pl"
    if entry.classifications.eu_member or alpha2 in _EEA_CH_NOT_EU:
        return "eu_eea_ch"
    return "third_country"


def issuing_evidence_shape(country: str | None) -> str | None:
    """Shared for an EU/EEA/CH licence, separate otherwise. Unknown stays unknown."""

    klass = citizenship_class(country)
    if klass is None:
        return None
    if klass in {"pl", "eu_eea_ch"}:
        return "shared"
    return "separate"


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
        "ce_level": "REQUIRED",
        "code95_level": "REQUIRED",
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


def _categories(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        code = str(item or "").strip().upper()
        if code in _LICENCE_CATEGORIES and code not in out:
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
    return "REQUIRED"


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
                if stay not in _STAY_NEEDS_PARAMETERS:
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
    stay = facts.get("stay_basis")
    if stay not in _STAY:
        return True
    if stay in _STAY_NEEDS_PARAMETERS:
        return not facts.get("visa_type") or not facts.get("visa_purpose")
    return False


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


def _row_state(
    *,
    level: str,
    applicable: bool,
    country_known: bool,
    blocking: bool,
) -> dict[str, Any]:
    if not applicable or level == "NOT_REQUIRED":
        return {
            "applicable": False,
            "level": level,
            "progress": None,
            "resolution": None,
            "holds_entrance": False,
        }
    if not country_known:
        return {
            "applicable": True,
            "level": level,
            "progress": "needs_input",
            "resolution": "unresolved",
            "holds_entrance": level == "REQUIRED",
        }
    if blocking:
        return {
            "applicable": True,
            "level": level,
            "progress": "blocking",
            "resolution": "blocking",
            "holds_entrance": level == "REQUIRED",
        }
    return {
        "applicable": True,
        "level": level,
        "progress": "needs_evidence",
        "resolution": "unresolved",
        "holds_entrance": level == "REQUIRED",
    }


def resolve_ce_code95(
    facts: Mapping[str, Any],
    *,
    today: date | None = None,
) -> dict[str, Any]:
    """CE + Code 95 under ``requirement_resolution.v1``. Does not write a row."""

    ce_level = _level(facts.get("ce_level"))
    code_level = _level(facts.get("code95_level"))
    ce_applicable = ce_level != "NOT_REQUIRED"
    code_applicable = code_level != "NOT_REQUIRED"
    country = facts.get("licence_issuing_country")
    country_known = bool(country) and issuing_evidence_shape(country) is not None
    shape = issuing_evidence_shape(country) if country_known and (ce_applicable or code_applicable) else None
    categories = list(facts.get("licence_categories") or [])
    ce_blocking = bool(categories) and "CE" not in categories
    presence = facts.get("code95_presence")
    valid_to = _parse_date(facts.get("code95_valid_to"))
    on = today or date.today()
    code_blocking = presence is False or (valid_to is not None and valid_to < on)
    ce = _row_state(
        level=ce_level,
        applicable=ce_applicable,
        country_known=country_known,
        blocking=ce_blocking and country_known,
    )
    code95 = _row_state(
        level=code_level,
        applicable=code_applicable,
        country_known=country_known,
        blocking=code_blocking and country_known,
    )
    uploads: list[str] = []
    if shape and country_known:
        ce_file = ce["progress"] == "needs_evidence"
        code_file = code95["progress"] == "needs_evidence"
        if shape == "shared":
            if ce_file and code_file:
                uploads = ["driver_license_code95"]
            elif ce_file:
                uploads = ["driver_license"]
            elif code_file:
                uploads = ["driver_license_code95"]
        elif ce_file or code_file:
            if ce_file:
                uploads.append("driver_license")
            if code_file:
                uploads.append("code95")
    variant = None
    if shape == "shared":
        variant = "combined_eu_license"
    elif shape == "separate":
        variant = "separate_license_and_code95"
    if not country_known and (ce_applicable or code_applicable):
        progress = "needs_input"
    elif ce["resolution"] == "blocking" or code95["resolution"] == "blocking":
        progress = "blocking"
    elif uploads:
        progress = "needs_evidence"
    else:
        progress = None
    return {
        "policy_id": POLICY_REQUIREMENT_RESOLUTION,
        "evidence_shape": shape,
        "evidence_variant": variant,
        "progress": progress,
        "upload_codes": uploads,
        "asks_file": bool(uploads),
        "ce": ce,
        "code95": code95,
    }


def situation_upload_codes(facts: Mapping[str, Any]) -> list[str]:
    """Files the recorded situation already asks for.

    Passport is always asked. A residence card also asks for the decision.
    A professional document is asked only when the operator says it exists.
    Visa, residence card, and work permit files stay unasked.
    """

    codes = ["passport"]
    if facts.get("stay_basis") == "karta_pobytu":
        codes.append("decision")
    if facts.get("tachograph_presence") is True:
        codes.append("tacho_card")
    if facts.get("adr_presence") is True:
        codes.append("adr")
    if facts.get("medical_presence") is True:
        codes.append("medical_certificate")
    if facts.get("psych_presence") is True:
        codes.append("psych_tests")
    if facts.get("additional_presence") is True:
        codes.append("additional_document")
    return codes


def build_operator_facts_view(
    facts: Mapping[str, Any],
    *,
    employment_id: str | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    klass = citizenship_class(facts.get("citizenship"))
    chain = chain_reading(facts, employment_id=employment_id)
    work = _work_for(facts, employment_id)
    stay_visible = klass == "third_country"
    parameters_visible = stay_visible and facts.get("stay_basis") in _STAY_NEEDS_PARAMETERS
    work_visible = stay_visible and not _stay_withholds_work(facts)
    valid_visible = work_visible and chain.get("work_authorization_basis") in {
        "included_in_stay",
        "separate_required",
    }
    ce = resolve_ce_code95(facts, today=today)
    uploads = list(ce["upload_codes"])
    for code in situation_upload_codes(facts):
        if code not in uploads:
            uploads.append(code)
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
            "visible": True,
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
        "employment_id": employment_id,
    }


def withheld_document_norms(facts: Mapping[str, Any], *, employment_id: str | None = None, today: date | None = None) -> frozenset[str]:
    view = build_operator_facts_view(facts, employment_id=employment_id, today=today)
    allowed = {canonical_document_code(code) for code in view["upload_codes"]}
    governed = frozenset(_GOVERNED_ALIASES.values())
    return frozenset(code for code in governed if code not in allowed)


def _facts_for_existing_driver_ask(
    facts: Mapping[str, Any],
    required_types: list[Any] | None,
) -> dict[str, Any]:
    """CE and Code 95 stay applicable only when the current ask already names them.

    The surface replaces that ask. It does not add the requirement.
    """

    norms = {
        canonical_document_code(str(raw))
        for raw in (required_types or [])
        if str(raw or "").strip()
    }
    named = bool(norms & {"driver_license", "driver_license_code95", "code95"})
    if named:
        return dict(facts)
    adjusted = dict(facts)
    adjusted["ce_level"] = "NOT_REQUIRED"
    adjusted["code95_level"] = "NOT_REQUIRED"
    return adjusted


def project_required_document_types(
    required_types: list[Any] | None,
    facts: Mapping[str, Any],
    *,
    employment_id: str | None = None,
    today: date | None = None,
) -> list[str]:
    """Drop unconditional asks this surface governs. Keep a file only when CE asks for it."""

    facts = _facts_for_existing_driver_ask(facts, required_types)
    withheld = withheld_document_norms(facts, employment_id=employment_id, today=today)
    view = build_operator_facts_view(facts, employment_id=employment_id, today=today)
    out: list[str] = []
    seen: set[str] = set()
    for raw in required_types or []:
        text = str(raw or "").strip()
        if not text:
            continue
        canon = canonical_document_code(text)
        if canon in withheld:
            continue
        if canon in seen:
            continue
        seen.add(canon)
        out.append(text)
    for code in view["upload_codes"]:
        canon = canonical_document_code(code)
        if canon in seen:
            continue
        seen.add(canon)
        out.append(code)
    return out


def drop_withheld_document_codes(
    codes: list[Any] | None,
    facts: Mapping[str, Any],
    *,
    employment_id: str | None = None,
    today: date | None = None,
) -> list[str]:
    facts = _facts_for_existing_driver_ask(facts, codes)
    withheld = withheld_document_norms(facts, employment_id=employment_id, today=today)
    view = build_operator_facts_view(facts, employment_id=employment_id, today=today)
    out: list[str] = []
    removed_driver = False
    for raw in codes or []:
        text = str(raw or "").strip()
        if not text:
            continue
        canon = canonical_document_code(text)
        if canon in withheld:
            if canon in {"driver_license", "code95", "driver_license_code95"}:
                removed_driver = True
            continue
        out.append(text)
    if removed_driver:
        seen = {canonical_document_code(item) for item in out}
        for code in view["upload_codes"]:
            if canonical_document_code(code) not in seen:
                out.append(code)
                seen.add(canonical_document_code(code))
    return out


def project_document_summary(
    summary: Mapping[str, Any],
    facts: Mapping[str, Any],
    *,
    employment_id: str | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    """Operator-facing summary. Does not write ``r5_required_set``."""

    checklist_in = dict(summary.get("checklist") or {})
    facts = _facts_for_existing_driver_ask(facts, list(checklist_in.get("requiredTypes") or []))
    withheld = withheld_document_norms(facts, employment_id=employment_id, today=today)
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
        canonical_document_code(str(item)) in {"driver_license", "code95", "driver_license_code95"}
        and canonical_document_code(str(item)) in withheld
        for item in original_missing
    )
    checklist = dict(out.get("checklist") or {})
    checklist["requiredTypes"] = project_required_document_types(
        list(checklist.get("requiredTypes") or []),
        facts,
        employment_id=employment_id,
        today=today,
    )
    if replaced_driver:
        seen = {canonical_document_code(str(item)) for item in required["missing"]}
        for code in checklist["requiredTypes"]:
            canon = canonical_document_code(str(code))
            if canon in {"driver_license", "code95", "driver_license_code95"} and canon not in seen:
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
        "ce_level": facts.get("ce_level") or "REQUIRED",
        "code95_level": facts.get("code95_level") or "REQUIRED",
    }
    return personal
