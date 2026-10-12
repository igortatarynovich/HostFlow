"""Applicability of stay and work for employment in Poland.

The vacancy profile decides which documents the job asks for. This catalog
decides which legal bases can apply to a person, and what evidence each basis
requires. The candidate card and HR both read it. A screen does not keep a
second list. The resolver executes a row; it does not grow a branch per basis.

Frozen for this slice. A new basis, exemption, or work procedure is a new row
with the fields below. It is not a new resolver condition.

Basis evidence contract: ``evidence`` groups (document codes, metadata, label),
``validity_rules``, ``confirm`` (``evidence`` or ``never``), ``work_effect``,
``work_condition``, ``recommends_work_required``, ``exemption_code``.
Exemption contract: ``confirm`` is ``citizenship_class``, ``basis``,
``work_effect``, or ``never``. Work procedure contract: document codes,
metadata, and whether the employer must match.
"""

from __future__ import annotations

from typing import Any, Mapping

from backend.app.reference.document_policy_merge import oswiadczenie_eligible_alpha2_lower
from backend.app.reference.legal_eligibility_chain import citizenship_class

POLICY_ID = "legalization_applicability.v1"
RULE_VERSION = "2026-10-12"
APPLICABLE_FROM = "2026-10-12"

# Schengen short-stay exemption used by Poland. Not free movement, and not a
# work right. A country absent from this set is not offered visa-free stay.
VISA_FREE_SHORT_STAY = frozenset({
    "AD", "AE", "AG", "AL", "AR", "AU", "BA", "BB", "BN", "BR", "BS", "CA",
    "CL", "CO", "CR", "DM", "GB", "GD", "GE", "GT", "HK", "HN", "IL", "JP",
    "KI", "KN", "KR", "LC", "MD", "ME", "MH", "MK", "MO", "MU", "MX", "MY",
    "NI", "NR", "NZ", "PA", "PE", "PW", "PY", "RS", "SB", "SC", "SG", "SM",
    "SV", "TL", "TO", "TT", "TV", "TW", "UA", "US", "UY", "VA", "VC", "VU",
})

CARD_KINDS = ("pobytu", "rezydent", "temporary", "permanent", "eu_long_term")

_CARD_DOCUMENTS = ("residence_card", "residence_permit", "karta_pobytu")
_DECISION_DOCUMENTS = ("decision", "decyzja", "voivodeship_decision", "temporary_residence_decision")


def _group(label: str, codes: tuple[str, ...], metadata: tuple[str, ...]) -> dict[str, Any]:
    return {"label": label, "codes": codes, "metadata": metadata}


def _basis(
    code: str,
    *,
    kind: str,
    stay_basis: str,
    classes: frozenset[str] = frozenset(),
    alpha2: frozenset[str] = frozenset(),
    documents: tuple[str, ...] = (),
    dependent_documents: tuple[str, ...] = (),
    card_kind: str | None = None,
    card_kinds: tuple[str, ...] = (),
    stay_bases: tuple[str, ...] = (),
    work_effect: str = "none",
    validity: tuple[str, ...] = (),
    evidence: tuple[dict[str, Any], ...] | None = None,
    confirm: str = "evidence",
    metadata: tuple[str, ...] = ("number", "expire_date"),
    dependent_metadata: tuple[str, ...] = ("number",),
    recommends_work_required: bool | None = None,
    exemption_code: str | None = None,
    offers_included_work: bool = False,
    work_condition: str | None = None,
    accepted_meta_kinds: tuple[str, ...] = (),
) -> dict[str, Any]:
    groups = list(evidence or ())
    if evidence is None:
        if documents:
            groups.append(_group(documents[0], documents, metadata))
        if dependent_documents:
            groups.append(_group(dependent_documents[0], dependent_documents, dependent_metadata))
    return {
        "code": code,
        "kind": kind,
        "stay_basis": stay_basis,
        "stay_bases": stay_bases or (stay_basis,),
        "card_kind": card_kind,
        "card_kinds": card_kinds or ((card_kind,) if card_kind else ()),
        "classes": classes,
        "alpha2": alpha2,
        "documents": documents,
        "dependent_documents": dependent_documents,
        "evidence": groups,
        "confirm": confirm,
        "work_effect": work_effect,
        "work_condition": work_condition,
        "accepted_meta_kinds": accepted_meta_kinds,
        "validity_rules": validity,
        "recommends_work_required": recommends_work_required,
        "exemption_code": exemption_code,
        "offers_included_work": offers_included_work,
        "rule_version": RULE_VERSION,
        "applicable_from": APPLICABLE_FROM,
    }


def stay_catalog() -> tuple[dict[str, Any], ...]:
    third = frozenset({"third_country"})
    return (
        _basis(
            "visa",
            kind="document",
            stay_basis="visa_d",
            stay_bases=("visa_c", "visa_d"),
            classes=third,
            documents=("visa",),
            validity=("visa_type",),
        ),
        _basis(
            "visa_free",
            kind="regime",
            stay_basis="visa_free",
            classes=third,
            alpha2=VISA_FREE_SHORT_STAY,
            validity=("schengen_90_180",),
            evidence=(_group("passport", ("passport", "international_passport"), ("expire_date",)),),
        ),
        _basis(
            "temporary",
            kind="document",
            stay_basis="karta_pobytu",
            card_kind="temporary",
            card_kinds=("temporary", "pobytu"),
            classes=third,
            documents=_CARD_DOCUMENTS,
            dependent_documents=_DECISION_DOCUMENTS,
            work_effect="conditional",
            offers_included_work=True,
        ),
        _basis(
            "permanent",
            kind="document",
            stay_basis="karta_pobytu",
            card_kind="permanent",
            classes=third,
            documents=_CARD_DOCUMENTS,
            dependent_documents=_DECISION_DOCUMENTS,
            work_effect="free_access",
            recommends_work_required=False,
            exemption_code="permanent_stay",
            offers_included_work=True,
        ),
        _basis(
            "eu_long_term",
            kind="document",
            stay_basis="karta_pobytu",
            card_kind="eu_long_term",
            card_kinds=("eu_long_term", "rezydent"),
            classes=third,
            documents=_CARD_DOCUMENTS,
            dependent_documents=_DECISION_DOCUMENTS,
            work_effect="free_access_if_polish",
            work_condition="polish_issuing_country",
            accepted_meta_kinds=("eu_long_term", "rezydent", "long_term_resident"),
            recommends_work_required=False,
            exemption_code="eu_long_term_pl",
            offers_included_work=True,
        ),
        _basis(
            "special_protection",
            kind="regime",
            stay_basis="special_protection",
            classes=third,
            work_effect="conditional",
            confirm="never",
            offers_included_work=True,
        ),
        _basis(
            "waiting_for_trc",
            kind="regime",
            stay_basis="waiting_for_trc",
            classes=third,
            confirm="never",
        ),
        _basis(
            "withdrawal_agreement",
            kind="regime",
            stay_basis="withdrawal_agreement",
            alpha2=frozenset({"GB"}),
            work_effect="conditional",
            confirm="never",
            recommends_work_required=False,
            exemption_code="withdrawal_agreement",
            offers_included_work=True,
        ),
        _basis(
            "other",
            kind="regime",
            stay_basis="other",
            classes=frozenset({"pl", "eu_eea_ch", "third_country"}),
            confirm="never",
        ),
    )


def _codes(facts: Mapping[str, Any]) -> list[str]:
    raw = facts.get("citizenship")
    if isinstance(raw, list):
        values = raw
    else:
        values = [raw]
    out: list[str] = []
    for value in values:
        text = str(value or "").strip().upper()
        if text and text not in out:
            out.append(text)
    return out


def _matches(entry: Mapping[str, Any], citizenships: list[str]) -> bool:
    if not citizenships:
        return False
    classes = {citizenship_class(code) for code in citizenships}
    classes.discard(None)
    allowed_classes = set(entry.get("classes") or [])
    allowed_alpha = {str(code).upper() for code in (entry.get("alpha2") or [])}
    class_ok = bool(allowed_classes & classes) if allowed_classes else False
    alpha_ok = bool(allowed_alpha & set(citizenships)) if allowed_alpha else False
    if allowed_classes and allowed_alpha:
        return class_ok and alpha_ok
    if allowed_alpha:
        return alpha_ok
    return class_ok


def applicable_stay(citizenships: list[str]) -> list[dict[str, Any]]:
    return [_public(entry) for entry in stay_catalog() if _matches(entry, citizenships)]


def _public(entry: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "code": entry["code"],
        "kind": entry["kind"],
        "stay_basis": entry["stay_basis"],
        "stay_bases": list(entry.get("stay_bases") or []),
        "card_kind": entry.get("card_kind"),
        "card_kinds": list(entry.get("card_kinds") or []),
        "documents": list(entry.get("documents") or []),
        "dependent_documents": list(entry.get("dependent_documents") or []),
        "evidence": [
            {"label": group["label"], "codes": list(group["codes"]), "metadata": list(group["metadata"])}
            for group in entry.get("evidence") or []
        ],
        "confirm": entry.get("confirm"),
        "work_effect": entry.get("work_effect"),
        "work_condition": entry.get("work_condition"),
        "accepted_meta_kinds": list(entry.get("accepted_meta_kinds") or []),
        "validity_rules": list(entry.get("validity_rules") or []),
        "recommends_work_required": entry.get("recommends_work_required"),
        "exemption_code": entry.get("exemption_code"),
        "offers_included_work": bool(entry.get("offers_included_work")),
        "rule_version": entry["rule_version"],
    }


def exemption_catalog() -> tuple[dict[str, Any], ...]:
    """How an exemption becomes confirmed. ``never`` stays unverified."""

    return (
        {"code": "citizenship_pl", "confirm": "citizenship_class", "citizenship_class": "pl"},
        {"code": "citizenship_eu_eea_ch", "confirm": "citizenship_class", "citizenship_class": "eu_eea_ch"},
        {"code": "not_required", "confirm": "never"},
        {"code": "permanent_stay", "confirm": "basis", "basis": "permanent"},
        {"code": "eu_long_term_pl", "confirm": "basis", "basis": "eu_long_term", "work_condition": "polish_issuing_country"},
        {"code": "included_in_stay", "confirm": "work_effect"},
        {"code": "withdrawal_agreement", "confirm": "never"},
        {"code": "other", "confirm": "never"},
    )


def work_procedure_catalog() -> tuple[dict[str, Any], ...]:
    return (
        {
            "code": "work_permit",
            "procedure_types": ("work_permit_a",),
            "documents": ("work_permit", "zezwolenie_a", "work_permit_a"),
            "metadata": ("number", "expire_date"),
            "match_employer": True,
        },
        {
            "code": "oswiadczenie",
            "procedure_types": ("employer_declaration",),
            "documents": ("oswiadczenie", "employer_declaration"),
            "metadata": ("number", "expire_date"),
            "match_employer": True,
        },
    )


def _selected_stay(facts: Mapping[str, Any], options: list[dict[str, Any]]) -> str | None:
    stay = facts.get("stay_basis")
    codes = {item["code"] for item in options}
    kind = str(facts.get("stay_card_kind") or "")
    for item in options:
        bases = set(item.get("stay_bases") or [item.get("stay_basis")])
        if stay not in bases:
            continue
        kinds = set(item.get("card_kinds") or [])
        if kinds and kind not in kinds and not (not kind and item.get("card_kind") in {None, "temporary"} and "pobytu" in kinds):
            continue
        if item["code"] in codes:
            return item["code"]
    if stay in codes:
        return str(stay)
    return None


def _recommendation(citizenships: list[str], facts: Mapping[str, Any]) -> dict[str, Any]:
    if not citizenships:
        return {"stay_required": None, "work_required": None, "reason": "citizenship_unknown"}
    classes = {citizenship_class(code) for code in citizenships}
    if "pl" in classes:
        reason = "citizenship_pl"
        stay_required = False
        work_required = False
    elif "eu_eea_ch" in classes:
        reason = "citizenship_eu_eea_ch"
        stay_required = False
        work_required = False
    else:
        reason = "third_country"
        stay_required = True
        work_required = True
    selected = _selected_entry(facts)
    if selected is not None and selected.get("recommends_work_required") is False:
        work_required = False
        reason = selected.get("exemption_code") or reason
    return {"stay_required": stay_required, "work_required": work_required, "reason": reason}


def _selected_entry(facts: Mapping[str, Any]) -> dict[str, Any] | None:
    options = [_public(entry) for entry in stay_catalog()]
    code = _selected_stay(facts, options)
    return next((entry for entry in stay_catalog() if entry["code"] == code), None)


def _work_options(citizenships: list[str], facts: Mapping[str, Any], *, required: bool | None) -> list[dict[str, Any]]:
    if required is not True:
        return []
    eligible = {code.upper() for code in oswiadczenie_eligible_alpha2_lower()}
    options = [{"code": "work_permit", "kind": "procedure"}]
    if set(citizenships) & eligible:
        options.append({"code": "oswiadczenie", "kind": "procedure"})
    selected = _selected_entry(facts)
    if selected is not None and selected.get("offers_included_work"):
        options.append({"code": "included_in_stay", "kind": "exemption"})
    return options


def _exemptions(reason: str, citizenships: list[str], facts: Mapping[str, Any]) -> list[str]:
    codes = ["other"]
    classes = {citizenship_class(code) for code in citizenships}
    if "pl" in classes or "eu_eea_ch" in classes:
        codes.insert(0, "not_required")
    if facts.get("stay_card_kind") == "permanent":
        codes.insert(0, "permanent_stay")
    if facts.get("stay_card_kind") in {"eu_long_term", "rezydent"}:
        codes.insert(0, "eu_long_term_pl")
    if "GB" in citizenships or facts.get("stay_basis") == "withdrawal_agreement":
        codes.insert(0, "withdrawal_agreement")
    if reason in {"citizenship_pl", "citizenship_eu_eea_ch", "permanent_stay", "eu_long_term_pl", "withdrawal_agreement"}:
        if reason not in codes:
            codes.insert(0, reason)
    return list(dict.fromkeys(codes))


def _confirmed_regime(reason: str, manual: bool) -> bool:
    return not manual and reason in {"citizenship_pl", "citizenship_eu_eea_ch"}


def resolve_legalization(facts: Mapping[str, Any]) -> dict[str, Any]:
    """Recommendation, operator selection, and the status that still needs proof."""

    citizenships = _codes(facts)
    recommendation = _recommendation(citizenships, facts)
    stay_override = facts.get("stay_required_override")
    work_override = facts.get("work_required_override")
    stay_required = recommendation["stay_required"] if stay_override is None else bool(stay_override)
    work_required = recommendation["work_required"] if work_override is None else bool(work_override)
    stay_manual = stay_override is not None and stay_override != recommendation["stay_required"]
    work_manual = work_override is not None and work_override != recommendation["work_required"]
    options = applicable_stay(citizenships) if stay_required is True else []
    selected = _selected_stay(facts, options) if stay_required is True else None
    selected_entry = next((item for item in options if item["code"] == selected), None)
    stored_stay = facts.get("stay_basis")
    applicable_codes = {item["stay_basis"] for item in options}
    if stored_stay in {"visa_c", "visa_d"}:
        stored_matches = "visa_d" in applicable_codes or "visa_c" in applicable_codes
    else:
        stored_matches = stored_stay in applicable_codes or stored_stay in {None, "not_required", "none"}
    needs_review = bool(stored_stay) and stay_required is not True and recommendation["stay_required"] is False and stored_stay not in {None, "not_required", "none"}
    if stay_required is True and stored_stay and not stored_matches:
        needs_review = True

    if stay_required is None:
        residence = "needs_verification"
    elif needs_review:
        residence = "needs_review"
    elif stay_required is False and _confirmed_regime(recommendation["reason"], stay_manual):
        residence = "confirmed"
    elif stay_required is False:
        residence = "needs_verification"
    elif selected_entry is None:
        residence = "needs_document"
    elif selected_entry["kind"] == "document":
        residence = "needs_document"
    else:
        residence = "needs_verification"

    if work_required is None:
        work = "needs_verification"
    elif work_manual and recommendation["work_required"] is False and work_required is True:
        work = "needs_review"
    elif work_required is False and _confirmed_regime(recommendation["reason"], work_manual):
        work = "confirmed"
    elif work_required is False:
        work = "needs_verification"
    else:
        label = facts.get("work_authorization_basis")
        procedure = facts.get("procedure_type")
        nested = facts.get("work") if isinstance(facts.get("work"), Mapping) else {}
        if label is None:
            label = nested.get("work_authorization_basis")
            procedure = nested.get("procedure_type")
        if nested.get("valid_no") and label not in {"included_in_stay", "separate_required"}:
            work = "not_confirmed"
        elif procedure or label == "separate_required":
            work = "needs_permit"
        else:
            work = "needs_permit"

    exemption = None
    if stay_required is False:
        exemption = recommendation["reason"] if not stay_manual else (facts.get("stay_exemption") or "other")
    return {
        "policy_id": POLICY_ID,
        "rule_version": RULE_VERSION,
        "applicable_from": APPLICABLE_FROM,
        "citizenships": citizenships,
        "recommendation": recommendation,
        "operator": {
            "stay_required": stay_override,
            "work_required": work_override,
            "stay_basis": stored_stay,
            "stay_exemption": facts.get("stay_exemption"),
        },
        "selection": {
            "stay_required": stay_required,
            "work_required": work_required,
            "stay_manual": stay_manual,
            "work_manual": work_manual,
            "stay_code": selected,
            "stay_exemption": exemption,
            "work_exemption": (
                recommendation["reason"] if work_required is False and not work_manual
                else (facts.get("work_exemption") or "other") if work_required is False
                else None
            ),
            "visa_type": "C" if stored_stay == "visa_c" else "D" if stored_stay == "visa_d" else facts.get("visa_type"),
        },
        "resolved": {"residence": residence, "work": work},
        "applicable_stay": options,
        "applicable_work": _work_options(citizenships, facts, required=work_required),
        "work_exemptions": _exemptions(recommendation["reason"], citizenships, facts) if work_required is False else [],
        "stay_exemptions": _exemptions(recommendation["reason"], citizenships, facts) if stay_required is False else [],
        "selected_stay": selected_entry,
    }
